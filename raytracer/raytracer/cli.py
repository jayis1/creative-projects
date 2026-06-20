"""cli.py — Command-line interface for the ray tracer.

Subcommands
------------
* ``render``    — render a single image from a preset or scene file
* ``animate``   — render a frame sequence (camera orbit / dolly / spline)
* ``scenes``    — list available preset scenes
* ``info``      — show version + capabilities
* ``validate``  — validate a scene file without rendering
* ``stats``     — render and print render statistics (rays, time, r/s)

Examples
--------
Render the Cornell box at 256x256 with 8 samples and save PNG::

    python -m raytracer.cli render --scene cornell --width 256 --height 256 \\
        --samples 8 --out out.png --format png

Render a normal-shading debug preview of the three-balls scene::

    python -m raytracer.cli render --scene three-balls --mode normal \\
        --width 128 --height 72 --out normals.png

Render an ambient-occlusion pass of a YAML-defined scene using 4 threads::

    python -m raytracer.cli render --scene-file my_scene.yaml --mode ao \\
        --samples 32 --width 200 --height 200 --threads 4 --out ao.png

Render a 60-frame orbit animation::

    python -m raytracer.cli animate --scene three-balls --orbit \\
        --frames 60 --radius 4 --height 1.5 --width 320 --height 180 \\
        --samples 4 --out-dir frames/

List available scenes::

    python -m raytracer.cli scenes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from .scene import (
    build_three_balls, build_cornell_box, build_random_spheres,
    build_solar_system, build_marble_hall, build_nebula, PRESETS,
)
from .serialize import load_scene_file, SUPPORTED_FORMATS
from .renderer import MODES
from . import imageio
from .logging import configure as configure_logging, logger
from .animation import orbit_path, linear_path, render_animation
from .vec import Vec3

SCENES = {
    "three-balls": build_three_balls,
    "cornell": build_cornell_box,
    "random": build_random_spheres,
    "solar-system": build_solar_system,
    "marble-hall": build_marble_hall,
    "nebula": build_nebula,
}


def _progress(done: int, total: int) -> None:
    bar_len = 40
    filled = int(bar_len * done / total)
    bar = "=" * filled + "-" * (bar_len - filled)
    pct = 100.0 * done / total
    sys.stderr.write(f"\rRendering [{bar}] {pct:5.1f}% ")
    sys.stderr.flush()
    if done == total:
        sys.stderr.write("\n")


def _resolve_scene(args, aspect: float):
    """Build a Scene from either --scene or --scene-file.

    Returns ``(scene, error_code)`` where ``error_code`` is ``0`` on success
    or a nonzero int on failure (caller should return it from the command
    function).  This keeps the function testable without it calling
    ``sys.exit`` directly.
    """
    if args.scene_file:
        if not os.path.exists(args.scene_file):
            print(f"scene file not found: {args.scene_file}", file=sys.stderr)
            return None, 2
        scene = load_scene_file(args.scene_file, aspect=aspect, fmt=args.format)
    elif args.scene:
        if args.scene not in SCENES:
            print(f"unknown scene '{args.scene}'; choose from {', '.join(SCENES)}",
                  file=sys.stderr)
            return None, 2
        scene = SCENES[args.scene](aspect=aspect)
    else:
        print("specify --scene or --scene-file", file=sys.stderr)
        return None, 2
    return scene, 0


def _write_output(path: str, pixels, fmt: str, gamma: float, ascii_width: int = 80) -> str:
    """Write pixels to *path* using *fmt*; returns the actual written path."""
    if fmt == "ppm":
        imageio.write_ppm(path, pixels, gamma=gamma)
    elif fmt == "png":
        try:
            imageio.write_png(path, pixels, gamma=gamma)
        except ImportError:
            print("Pillow not available; falling back to PPM", file=sys.stderr)
            path = os.path.splitext(path)[0] + ".ppm"
            imageio.write_ppm(path, pixels, gamma=gamma)
    elif fmt in ("ascii", "txt", "ans"):
        imageio.write_ascii(path, pixels, width=ascii_width)
    else:
        print(f"unsupported output format '{fmt}'", file=sys.stderr)
        sys.exit(2)
    return path


def _infer_format(path: str, fmt: str) -> str:
    if fmt != "auto":
        return fmt
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in ("png", "ppm", "ascii", "txt", "ans"):
        return ext if ext != "txt" and ext != "ans" else "ascii"
    return "png"


def cmd_render(args: argparse.Namespace) -> int:
    aspect = args.width / max(1, args.height)
    scene, err = _resolve_scene(args, aspect)
    if err:
        return err

    renderer = scene.make_renderer(
        max_depth=args.max_depth,
        samples=args.samples,
        mode=args.mode,
        ao_distance=args.ao_distance,
        gamma=args.gamma,
        seed=args.seed or None,
        rr_start_depth=args.rr_start_depth,
    )
    start = time.time()
    pixels = renderer.render(
        scene.camera, args.width, args.height,
        progress=None if args.quiet else _progress,
        num_threads=args.threads,
    )
    elapsed = time.time() - start
    if not args.quiet:
        print(f"Rendered {args.width}x{args.height} in {elapsed:.2f}s "
              f"({args.samples} spp, mode={args.mode}, depth {args.max_depth}, "
              f"threads {args.threads}, {renderer.stats.rays} rays, "
              f"{renderer.stats.rays_per_second():.0f} r/s)",
              file=sys.stderr)

    fmt = _infer_format(args.out, args.format)
    path = _write_output(args.out, pixels, fmt, args.gamma, args.ascii_width)
    if not args.quiet:
        print(f"Wrote {path}")
    if args.stats:
        print(json.dumps(renderer.stats.as_dict(), indent=2))
    return 0


def cmd_animate(args: argparse.Namespace) -> int:
    aspect = args.width / max(1, args.height_px)
    scene, err = _resolve_scene(args, aspect)
    if err:
        return err
    # Generate eye positions.
    if args.orbit:
        center = Vec3(*args.center) if args.center else scene.camera.look_at
        positions = orbit_path(
            center=center,
            radius=args.radius,
            height=args.height,
            frames=args.frames,
            look_at=center,
        )
    elif args.dolly:
        start = Vec3(*args.start) if args.start else scene.camera.look_from
        end = Vec3(*args.end) if args.end else scene.camera.look_at
        positions = linear_path(start, end, args.frames)
    elif args.spline:
        pts = [Vec3(*p) for p in args.spline]
        positions = __import__("raytracer.animation", fromlist=["spline_path"]).spline_path(pts, args.frames)
    else:
        print("specify --orbit, --dolly, or --spline", file=sys.stderr)
        return 2
    fmt = "png" if args.out_format == "auto" else args.out_format
    if not args.quiet:
        print(f"Rendering {args.frames} frames to {args.out_dir}/", file=sys.stderr)
    paths = render_animation(
        scene=scene,
        eye_positions=positions,
        out_dir=args.out_dir,
        width=args.width,
        height=args.height_px,
        samples=args.samples,
        max_depth=args.max_depth,
        fmt=fmt,
        look_at=Vec3(*args.look_at) if args.look_at else None,
        progress=not args.quiet,
    )
    if not args.quiet:
        print(f"Wrote {len(paths)} frames to {args.out_dir}/")
    return 0


def cmd_scenes(args: argparse.Namespace) -> int:
    for name, builder in SCENES.items():
        doc = (builder.__doc__ or "").strip().splitlines()[0] if builder.__doc__ else ""
        print(f"{name:16s} {doc}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    from . import __version__
    print(f"raytracer v{__version__}")
    print("Pure-Python recursive ray tracer with BVH acceleration,")
    print("Lambertian/Metal/Dielectric/Emissive/Checker/Isotropic materials,")
    print("spheres/planes/triangles/rects/box/disk/cylinder, depth-of-field,")
    print("path/ambient-occlusion/normal/depth integrators, NEE, Russian roulette,")
    print("Perlin/marble/noise textures, JSON/YAML/TOML scene files,")
    print("multi-threaded tile rendering, animation, CLI.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a scene file without rendering."""
    if not os.path.exists(args.scene_file):
        print(f"scene file not found: {args.scene_file}", file=sys.stderr)
        return 2
    try:
        scene = load_scene_file(args.scene_file, aspect=16/9, fmt=args.format)
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    n_objs = 0
    try:
        # Count objects via the BVH leaf count — best-effort.
        n_objs = getattr(scene.world, "box", None) is not None
        n_objs = "yes" if n_objs else "unknown"
    except Exception:
        n_objs = "unknown"
    print(f"OK: scene loaded (camera vfov={scene.camera.vfov}, world={n_objs})")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Render a small image and print render statistics as JSON."""
    aspect = args.width / max(1, args.height)
    scene, err = _resolve_scene(args, aspect)
    if err:
        return err
    renderer = scene.make_renderer(
        max_depth=args.max_depth,
        samples=args.samples,
        mode=args.mode,
        seed=args.seed or None,
    )
    pixels = renderer.render(
        scene.camera, args.width, args.height,
        progress=None, num_threads=args.threads,
    )
    print(json.dumps(renderer.stats.as_dict(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="raytracer",
        description="From-scratch recursive ray tracer (pure Python).",
    )
    p.add_argument("--log-level", default="WARNING",
                   help="Logging level (DEBUG/INFO/WARNING/ERROR).")
    sub = p.add_subparsers(dest="cmd", required=True)

    # -- render ------------------------------------------------------------- #
    p_render = sub.add_parser("render", help="Render a scene to a file.")
    src = p_render.add_mutually_exclusive_group()
    src.add_argument("--scene", default=None,
                     choices=sorted(SCENES),
                     help="Preset scene name.")
    src.add_argument("--scene-file", default=None,
                     help="Path to a JSON/YAML/TOML scene description file.")
    p_render.add_argument("--scene-format", default="auto",
                           choices=["auto"] + list(SUPPORTED_FORMATS),
                           help="Scene file format (auto = infer from extension).")
    p_render.add_argument("--mode", default="path", choices=list(MODES),
                          help="Integrator mode: path / ao / normal / depth.")
    p_render.add_argument("--width", type=int, default=320)
    p_render.add_argument("--height", type=int, default=180)
    p_render.add_argument("--samples", type=int, default=4,
                           help="Samples per pixel for anti-aliasing (or AO samples).")
    p_render.add_argument("--max-depth", type=int, default=8,
                           help="Maximum ray bounce depth (path mode).")
    p_render.add_argument("--ao-distance", type=float, default=1e9,
                           help="Maximum occlusion ray length (ao/depth mode).")
    p_render.add_argument("--gamma", type=float, default=2.0,
                           help="Display gamma for tone mapping.")
    p_render.add_argument("--threads", type=int, default=1,
                           help="Number of worker processes for parallel rendering.")
    p_render.add_argument("--seed", type=int, default=0,
                           help="Random seed (0 = keep default).")
    p_render.add_argument("--rr-start-depth", type=int, default=0,
                           help="Russian-roulette path termination start depth (0=off).")
    p_render.add_argument("--out", "-o", default="out.png",
                           help="Output filename.")
    p_render.add_argument("--format", default="auto",
                           choices=["auto", "png", "ppm", "ascii"],
                           help="Output format (auto = infer from extension).")
    p_render.add_argument("--ascii-width", type=int, default=80)
    p_render.add_argument("--quiet", action="store_true")
    p_render.add_argument("--stats", action="store_true",
                           help="Print render statistics as JSON after rendering.")
    p_render.set_defaults(func=cmd_render)

    # -- animate ------------------------------------------------------------- #
    p_anim = sub.add_parser("animate", help="Render a frame sequence.")
    anim_src = p_anim.add_mutually_exclusive_group()
    anim_src.add_argument("--scene", default=None, choices=sorted(SCENES))
    anim_src.add_argument("--scene-file", default=None)
    p_anim.add_argument("--scene-format", default="auto",
                         choices=["auto"] + list(SUPPORTED_FORMATS))
    p_anim.add_argument("--out-format", default="auto",
                         choices=["auto", "png", "ppm", "ascii"],
                         help="Frame image format (auto=png).")
    motion = p_anim.add_mutually_exclusive_group()
    motion.add_argument("--orbit", action="store_true",
                         help="Circular camera orbit.")
    motion.add_argument("--dolly", action="store_true",
                         help="Linear camera dolly.")
    motion.add_argument("--spline", nargs="+", type=float, action="append",
                         help="Spline control points as 'x y z' triples.")
    p_anim.add_argument("--frames", type=int, default=30)
    p_anim.add_argument("--radius", type=float, default=4.0, help="Orbit radius.")
    p_anim.add_argument("--height", type=float, default=1.5, help="Orbit camera height.")
    p_anim.add_argument("--center", nargs=3, type=float, default=None,
                        help="Orbit center (default: look_at).")
    p_anim.add_argument("--look-at", nargs=3, type=float, default=None,
                        help="Camera look-at point (default: scene look_at).")
    p_anim.add_argument("--start", nargs=3, type=float, default=None,
                        help="Dolly start position.")
    p_anim.add_argument("--end", nargs=3, type=float, default=None,
                        help="Dolly end position.")
    p_anim.add_argument("--width", type=int, default=320)
    p_anim.add_argument("--height-px", dest="height_px", type=int, default=180)
    p_anim.add_argument("--samples", type=int, default=4)
    p_anim.add_argument("--max-depth", type=int, default=6)
    p_anim.add_argument("--seed", type=int, default=42)
    p_anim.add_argument("--out-dir", default="frames", help="Output directory.")
    p_anim.add_argument("--threads", type=int, default=1)
    p_anim.add_argument("--quiet", action="store_true")
    p_anim.set_defaults(func=cmd_animate)

    # -- scenes -------------------------------------------------------------- #
    p_scenes = sub.add_parser("scenes", help="List available preset scenes.")
    p_scenes.set_defaults(func=cmd_scenes)

    # -- info ---------------------------------------------------------------- #
    p_info = sub.add_parser("info", help="Show version info.")
    p_info.set_defaults(func=cmd_info)

    # -- validate ------------------------------------------------------------ #
    p_val = sub.add_parser("validate", help="Validate a scene file.")
    p_val.add_argument("scene_file", help="Path to the scene file.")
    p_val.add_argument("--scene-format", default="auto",
                       choices=["auto"] + list(SUPPORTED_FORMATS))
    p_val.set_defaults(func=cmd_validate)

    # -- stats --------------------------------------------------------------- #
    p_stats = sub.add_parser("stats", help="Render and print statistics as JSON.")
    ssrc = p_stats.add_mutually_exclusive_group()
    ssrc.add_argument("--scene", default=None, choices=sorted(SCENES))
    ssrc.add_argument("--scene-file", default=None)
    p_stats.add_argument("--scene-format", default="auto",
                          choices=["auto"] + list(SUPPORTED_FORMATS))
    p_stats.add_argument("--mode", default="path", choices=list(MODES))
    p_stats.add_argument("--width", type=int, default=64)
    p_stats.add_argument("--height", type=int, default=36)
    p_stats.add_argument("--samples", type=int, default=2)
    p_stats.add_argument("--max-depth", type=int, default=4)
    p_stats.add_argument("--threads", type=int, default=1)
    p_stats.add_argument("--seed", type=int, default=0)
    p_stats.set_defaults(func=cmd_stats)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Configure logging from the top-level --log-level flag.
    configure_logging(getattr(args, "log_level", "WARNING"))
    # Normalize: route --scene-format to the attribute name expected by
    # _resolve_scene / load_scene_file (``args.format``).
    if hasattr(args, "scene_format") and not hasattr(args, "format"):
        args.format = args.scene_format
    elif hasattr(args, "scene_format"):
        args.format = args.scene_format
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())