"""cli.py — Command-line interface for the ray tracer.

Examples
--------
Render the Cornell box at 256x256 with 8 samples and save PNG::

    python -m raytracer.cli render --scene cornell --width 256 --height 256 \\
        --samples 8 --out out.png --format png

Render a preview ASCII art of the three-balls scene::

    python -m raytracer.cli render --scene three-balls --width 64 --height 36 \\
        --samples 1 --out preview.txt --format ascii

List available scenes::

    python -m raytracer.cli scenes
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from .scene import build_three_balls, build_cornell_box, build_random_spheres
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
    if args.scene not in SCENES:
        print(f"unknown scene '{args.scene}'; choose from {', '.join(SCENES)}",
              file=sys.stderr)
        return 2
    aspect = args.width / max(1, args.height)
    scene = SCENES[args.scene](aspect=aspect)
    renderer = scene.make_renderer(
        max_depth=args.max_depth,
        samples=args.samples,
        seed=args.seed,
    )
    start = time.time()
    pixels = renderer.render(scene.camera, args.width, args.height,
                             progress=_progress if not args.quiet else None)
    elapsed = time.time() - start
    if not args.quiet:
        print(f"Rendered {args.width}x{args.height} in {elapsed:.2f}s "
              f"({args.samples} spp, depth {args.max_depth})",
              file=sys.stderr)

    ext = os.path.splitext(args.out)[1].lower().lstrip(".")
    fmt = args.format if args.format != "auto" else ext
    if fmt in ("ppm",):
        imageio.write_ppm(args.out, pixels)
    elif fmt in ("png",):
        imageio.write_png(args.out, pixels)
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
        print(f"{name:16s} {builder.__doc__.strip().splitlines()[0] if builder.__doc__ else ''}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    from . import __version__
    print(f"raytracer v{__version__}")
    print("Pure-Python recursive ray tracer with BVH acceleration,")
    print("Lambertian/Metal/Dielectric/Emissive/Checker materials,")
    print("spheres/planes/triangles/rects, depth-of-field, anti-aliasing.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="raytracer",
        description="From-scratch recursive ray tracer (pure Python).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_render = sub.add_parser("render", help="Render a scene to a file.")
    p_render.add_argument("--scene", default="three-balls",
                          choices=sorted(SCENES),
                          help="Preset scene name.")
    p_render.add_argument("--width", type=int, default=320)
    p_render.add_argument("--height", type=int, default=180)
    p_render.add_argument("--samples", type=int, default=4,
                          help="Samples per pixel for anti-aliasing.")
    p_render.add_argument("--max-depth", type=int, default=8,
                          help="Maximum ray bounce depth.")
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

    p_scenes = sub.add_parser("scenes", help="List available scenes.")
    p_scenes.set_defaults(func=cmd_scenes)

    p_info = sub.add_parser("info", help="Show version info.")
    p_info.set_defaults(func=cmd_info)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())