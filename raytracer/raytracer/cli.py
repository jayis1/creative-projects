"""cli.py — Command-line interface for the ray tracer.

Examples
--------
Render the Cornell box at 256x256 with 8 samples and save PNG::

    python -m raytracer.cli render --scene cornell --width 256 --height 256 \\
        --samples 8 --out out.png --format png

Render a normal-shading debug preview of the three-balls scene::

    python -m raytracer.cli render --scene three-balls --mode normal \\
        --width 128 --height 72 --out normals.png

Render an ambient-occlusion pass of a JSON-defined scene using 4 threads::

    python -m raytracer.cli render --scene-file my_scene.json --mode ao \\
        --samples 32 --width 200 --height 200 --threads 4 --out ao.png

List available scenes::

    python -m raytracer.cli scenes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from .scene import build_three_balls, build_cornell_box, build_random_spheres
from .serialize import load_scene_file
from .renderer import MODES
from . import imageio


SCENES = {
    "three-balls": build_three_balls,
    "cornell": build_cornell_box,
    "random": build_random_spheres,
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


def cmd_render(args: argparse.Namespace) -> int:
    aspect = args.width / max(1, args.height)
    if args.scene_file:
        if not os.path.exists(args.scene_file):
            print(f"scene file not found: {args.scene_file}", file=sys.stderr)
            return 2
        scene = load_scene_file(args.scene_file, aspect=aspect)
    elif args.scene:
        if args.scene not in SCENES:
            print(f"unknown scene '{args.scene}'; choose from {', '.join(SCENES)}",
                  file=sys.stderr)
            return 2
        scene = SCENES[args.scene](aspect=aspect)
    else:
        print("specify --scene or --scene-file", file=sys.stderr)
        return 2

    renderer = scene.make_renderer(
        max_depth=args.max_depth,
        samples=args.samples,
        mode=args.mode,
        ao_distance=args.ao_distance,
        gamma=args.gamma,
        seed=args.seed,
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
              f"threads {args.threads})",
              file=sys.stderr)

    ext = os.path.splitext(args.out)[1].lower().lstrip(".")
    fmt = args.format if args.format != "auto" else ext
    if fmt == "ppm":
        imageio.write_ppm(args.out, pixels, gamma=args.gamma)
    elif fmt == "png":
        try:
            imageio.write_png(args.out, pixels, gamma=args.gamma)
        except ImportError:
            print("Pillow not available; falling back to PPM", file=sys.stderr)
            args.out = os.path.splitext(args.out)[0] + ".ppm"
            imageio.write_ppm(args.out, pixels, gamma=args.gamma)
    elif fmt in ("ascii", "txt", "ans"):
        imageio.write_ascii(args.out, pixels, width=args.ascii_width)
    else:
        print(f"unsupported output format '{fmt}'", file=sys.stderr)
        return 2
    if not args.quiet:
        print(f"Wrote {args.out}")
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
    print("Lambertian/Metal/Dielectric/Emissive/Checker materials,")
    print("spheres/planes/triangles/rects, depth-of-field, anti-aliasing,")
    print("path / ambient-occlusion / normal-shading integrators,")
    print("JSON scene files, multi-threaded tile rendering.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a JSON scene file without rendering."""
    if not os.path.exists(args.scene_file):
        print(f"scene file not found: {args.scene_file}", file=sys.stderr)
        return 2
    try:
        with open(args.scene_file) as f:
            doc = json.load(f)
        scene = load_scene_file(args.scene_file, aspect=16/9)
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    n_objs = len(doc.get("objects", []))
    print(f"OK: {n_objs} object(s), camera vfov={scene.camera.vfov}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="raytracer",
        description="From-scratch recursive ray tracer (pure Python).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_render = sub.add_parser("render", help="Render a scene to a file.")
    src = p_render.add_mutually_exclusive_group()
    src.add_argument("--scene", default=None,
                     choices=sorted(SCENES),
                     help="Preset scene name.")
    src.add_argument("--scene-file", default=None,
                    help="Path to a JSON scene description file.")
    p_render.add_argument("--mode", default="path", choices=list(MODES),
                          help="Integrator mode: path / ao / normal.")
    p_render.add_argument("--width", type=int, default=320)
    p_render.add_argument("--height", type=int, default=180)
    p_render.add_argument("--samples", type=int, default=4,
                           help="Samples per pixel for anti-aliasing (or AO samples).")
    p_render.add_argument("--max-depth", type=int, default=8,
                           help="Maximum ray bounce depth (path mode).")
    p_render.add_argument("--ao-distance", type=float, default=1e9,
                           help="Maximum occlusion ray length (ao mode).")
    p_render.add_argument("--gamma", type=float, default=2.0,
                           help="Display gamma for tone mapping.")
    p_render.add_argument("--threads", type=int, default=1,
                           help="Number of worker processes for parallel rendering.")
    p_render.add_argument("--seed", type=int, default=0,
                           help="Random seed (0 = keep default).")
    p_render.add_argument("--out", "-o", default="out.png",
                           help="Output filename.")
    p_render.add_argument("--format", default="auto",
                           choices=["auto", "png", "ppm", "ascii"],
                           help="Output format (auto = infer from extension).")
    p_render.add_argument("--ascii-width", type=int, default=80)
    p_render.add_argument("--quiet", action="store_true")
    p_render.set_defaults(func=cmd_render)

    p_scenes = sub.add_parser("scenes", help="List available preset scenes.")
    p_scenes.set_defaults(func=cmd_scenes)

    p_info = sub.add_parser("info", help="Show version info.")
    p_info.set_defaults(func=cmd_info)

    p_val = sub.add_parser("validate", help="Validate a JSON scene file.")
    p_val.add_argument("scene_file", help="Path to the JSON scene file.")
    p_val.set_defaults(func=cmd_validate)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())