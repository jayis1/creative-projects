"""Command-line interface for Fractal Explorer.

Provides subcommands: render, julia, newton, ascii, zoom, palette, explore,
benchmark, info, buddhabrot, lyapunov, ifs, animate, preset, filter.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .iterators import FRACTALS
from .palettes import PALETTES
from .traps import TRAPS
from .viewport import Viewport
from .render import render_fractal, render_histogram_coloring
from .io_writers import write_png, write_ppm, write_svg, write_ascii, write_tga
from .zoom import render_zoom_sequence
from .julia import explore_julia
from .benchmark import benchmark
from .config import _load_config, _merge_config, _detect_explicit_args
from .buddhabrot import render_buddhabrot, AntiBuddhabrot
from .lyapunov import render_lyapunov
from .ifs import BARNSLEY_FERN, SIERPINSKI_TRIANGLE, DRAGON_CURVE, render_ifs
from .filters import FILTERS, apply_filter
from .animation import render_julia_morph, render_color_cycle
from .presets import PresetManager, PRESETS

logger = logging.getLogger("fractal_explorer")


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #

def _parse_complex(s):
    """Parse a complex number from a string.

    Accepts ``"re,im"``, ``"re+j·im"`` (e.g. ``"-0.7+0.27j"``), or a bare real.
    """
    if s is None:
        return None
    s = s.strip()
    if "j" in s or "J" in s:
        try:
            return complex(s.replace(" ", ""))
        except ValueError:
            raise ValueError(f"bad complex number: {s!r}")
    if "," in s:
        parts = s.split(",")
        if len(parts) != 2:
            raise ValueError(f"expected 're,im' but got {s!r}")
        try:
            return complex(float(parts[0]), float(parts[1]))
        except ValueError:
            raise ValueError(f"bad complex number: {s!r}")
    try:
        return complex(float(s))
    except ValueError:
        raise ValueError(f"bad complex number: {s!r}")


def _parse_rgb(s):
    """Parse an ``"r,g,b"`` string into a 3-tuple of ints in [0,255]."""
    parts = s.split(",")
    if len(parts) != 3:
        raise ValueError(f"expected 'r,g,b' but got {s!r}")
    try:
        vals = [int(x.strip()) for x in parts]
    except ValueError:
        raise ValueError(f"bad RGB (non-integer): {s!r}")
    from .palettes import _clamp_byte
    return tuple(_clamp_byte(p) for p in vals)


# --------------------------------------------------------------------------- #
# Render args
# --------------------------------------------------------------------------- #

def _add_render_args(p):
    p.add_argument("--kind", default="mandelbrot", choices=sorted(FRACTALS))
    p.add_argument("--width", type=int, default=600, help="image width px")
    p.add_argument("--height", type=int, default=450, help="image height px")
    p.add_argument("--max-iter", type=int, default=256)
    p.add_argument("--bailout", type=int, default=1 << 16)
    p.add_argument("--palette", default="fire")
    p.add_argument("--coloring", default="smooth",
                    choices=["smooth", "flat", "de", "trap", "root",
                             "histogram"])
    p.add_argument("--power", type=float, default=2.0)
    p.add_argument("--julia-c", default=None, help="complex constant for Julia")
    p.add_argument("--newton-power", type=int, default=3)
    p.add_argument("--phoenix-c", default=None, help="Phoenix coefficient")
    p.add_argument("--magnet-variant", type=int, default=1, choices=[1, 2])
    p.add_argument("--trap", default=None, choices=list(TRAPS),
                    help="orbit trap type (for --coloring trap)")
    p.add_argument("--trap-point", default="0,0", help="trap point")
    p.add_argument("--trap-angle", type=float, default=0.0, help="trap angle rad")
    p.add_argument("--trap-radius", type=float, default=1.0, help="trap radius")
    p.add_argument("--center", default="-0.5,0", help="real,imag center")
    p.add_argument("--viewport-width", type=float, default=3.0)
    p.add_argument("--viewport-height", type=float, default=None)
    p.add_argument("--interior", default="0,0,0", help="interior RGB")
    p.add_argument("--supersample", type=int, default=1,
                    help="anti-aliasing factor (1=off, 2/3/4=higher)")
    p.add_argument("--workers", "-j", type=int, default=1,
                    help="parallel worker processes")
    p.add_argument("--output", "-o", default="fractal.png")
    p.add_argument("--format", default=None,
                    choices=["png", "ppm", "svg", "ascii", "tga"])
    p.add_argument("--filter", default=None, choices=list(FILTERS),
                    help="post-processing filter")
    p.add_argument("--config", default=None)
    p.add_argument("--preset", default=None, help="named preset to use")


def _build_trap(args):
    from .traps import PointTrap, LineTrap, CircleTrap, CrossTrap
    if not args.trap:
        return None
    if args.trap == "point":
        pt = _parse_complex(args.trap_point) or (0 + 0j)
        return PointTrap(pt)
    if args.trap == "line":
        return LineTrap(args.trap_angle)
    if args.trap == "circle":
        return CircleTrap(args.trap_radius)
    if args.trap == "cross":
        return CrossTrap()
    return None


def _apply_config_file(args, explicit=None):
    if not args.config:
        return args
    cfg = _load_config(args.config)
    return _merge_config(args, cfg, explicit=explicit)


def _apply_preset(args):
    """Apply a named preset to args (only for keys not explicitly set)."""
    if not getattr(args, "preset", None):
        return args
    preset = PRESETS.get(args.preset)
    if preset is None:
        # Try loading from file
        pm = PresetManager("presets")
        try:
            preset = pm.load(args.preset)
        except FileNotFoundError:
            raise ValueError(f"Unknown preset: {args.preset!r}")
    for k, v in preset.items():
        ak = k.replace("-", "_")
        if hasattr(args, ak):
            setattr(args, ak, v)
    return args


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_render(args):
    center = _parse_complex(args.center)
    vp = Viewport(center, args.viewport_width, args.viewport_height)
    jc = _parse_complex(args.julia_c) if args.julia_c else None
    interior = _parse_rgb(args.interior)
    trap = _build_trap(args)

    if args.coloring == "histogram":
        pixels, stats = render_histogram_coloring(
            args.kind, vp, args.width, args.height, max_iter=args.max_iter,
            bailout=args.bailout, palette_name=args.palette, power=args.power,
            julia_c=jc)
    else:
        pixels, stats = render_fractal(
            args.kind, vp, args.width, args.height, max_iter=args.max_iter,
            bailout=args.bailout, palette_name=args.palette,
            coloring=args.coloring, power=args.power, julia_c=jc,
            newton_power=args.newton_power, interior_color=interior,
            trap=trap, supersample=args.supersample, workers=args.workers)

    # Post-processing filter
    if getattr(args, "filter", None):
        pixels = apply_filter(pixels, args.width, args.height, args.filter)

    fmt = args.format or args.output.rsplit(".", 1)[-1].lower()
    if fmt == "png":
        write_png(args.output, pixels, args.width, args.height,
                  text_meta={"fractal": args.kind,
                             "coloring": args.coloring,
                             "max_iter": str(args.max_iter)})
    elif fmt == "ppm":
        write_ppm(args.output, pixels, args.width, args.height)
    elif fmt == "svg":
        write_svg(args.output, pixels, args.width, args.height)
    elif fmt == "ascii":
        write_ascii(args.output, pixels, args.width, args.height)
    elif fmt == "tga":
        write_tga(args.output, pixels, args.width, args.height)
    else:
        write_png(args.output, pixels, args.width, args.height)
    print(json.dumps(stats, indent=2))
    print(f"Wrote {args.output}")


def cmd_julia(args):
    args.kind = "julia"
    cmd_render(args)


def cmd_newton(args):
    args.kind = "newton"
    cmd_render(args)


def cmd_zoom(args):
    center = _parse_complex(args.center)
    files = render_zoom_sequence(
        args.kind, center, args.start_width, args.end_width, args.frames,
        img_size=(args.width, args.height), max_iter=args.max_iter,
        palette_name=args.palette, output_dir=args.output_dir,
        prefix=args.prefix, high_precision=args.hp, prec=args.prec,
        coloring=args.coloring, workers=args.workers)
    print(json.dumps({"frames": files}, indent=2))


def cmd_ascii(args):
    args.format = "ascii"
    cmd_render(args)


def cmd_palette(args):
    from .palettes import get_palette
    pal = get_palette(args.name, args.size)
    w, h = args.size, 40
    pixels = []
    for _row in range(h):
        for col in range(w):
            pixels.append(pal[col])
    out = args.output or f"palette_{args.name}.png"
    write_png(out, pixels, w, h)
    print(f"Wrote palette strip -> {out}")


def cmd_explore(args):
    files = explore_julia(grid_size=args.grid,
                           img_size=(args.width, args.height),
                           output_dir=args.output_dir, max_iter=args.max_iter,
                           palette_name=args.palette, power=args.power,
                           c_radius=args.radius, workers=args.workers)
    print(json.dumps({"grid": f"{args.grid}x{args.grid}",
                       "files": len(files),
                       "index": os.path.join(args.output_dir, "index.html")},
                      indent=2))


def cmd_benchmark(args):
    results = benchmark(size=(args.width, args.height),
                        max_iter=args.max_iter, trials=args.trials)
    print(json.dumps(results, indent=2))


def cmd_info(args):
    print("Fractals available:", ", ".join(sorted(FRACTALS)))
    print("Palettes available:", ", ".join(sorted(PALETTES)))
    print("Coloring modes: smooth, flat, de, trap, root, histogram")
    print("Orbit traps:", ", ".join(sorted(TRAPS)))
    print("Output formats: png, ppm, svg, ascii, tga")
    print("Filters:", ", ".join(sorted(FILTERS)))
    print("Presets:", ", ".join(sorted(PRESETS)))


def cmd_buddhabrot(args):
    from .viewport import Viewport
    vp = Viewport(_parse_complex(args.center), args.viewport_width,
                  args.viewport_height)
    pixels, stats = render_buddhabrot(
        vp, args.width, args.height, samples=args.samples,
        max_iter=args.max_iter, palette_name=args.palette,
        seed=args.seed if hasattr(args, "seed") else None,
        anti=args.anti)
    write_png(args.output, pixels, args.width, args.height)
    print(json.dumps(stats, indent=2))
    print(f"Wrote {args.output}")


def cmd_lyapunov(args):
    pixels, stats = render_lyapunov(
        a_range=(args.a_min, args.a_max), b_range=(args.b_min, args.b_max),
        width=args.width, height=args.height, sequence=args.sequence,
        max_iter=args.max_iter, palette_name=args.palette)
    write_png(args.output, pixels, args.width, args.height)
    print(json.dumps(stats, indent=2))
    print(f"Wrote {args.output}")


def cmd_ifs(args):
    ifs_map = {"fern": BARNSLEY_FERN, "sierpinski": SIERPINSKI_TRIANGLE,
               "dragon": DRAGON_CURVE}
    ifs = ifs_map.get(args.type)
    if ifs is None:
        raise ValueError(f"Unknown IFS type: {args.type}")
    pixels, stats = render_ifs(ifs, width=args.width, height=args.height,
                                iterations=args.iterations,
                                palette_name=args.palette, seed=args.seed)
    write_png(args.output, pixels, args.width, args.height)
    print(json.dumps(stats, indent=2))
    print(f"Wrote {args.output}")


def cmd_animate(args):
    if args.mode == "julia-morph":
        c_start = _parse_complex(args.c_start)
        c_end = _parse_complex(args.c_end)
        files = render_julia_morph(c_start, c_end, args.frames, args.width,
                                    args.height, args.max_iter, args.palette,
                                    args.output_dir)
    elif args.mode == "color-cycle":
        from .viewport import Viewport
        vp = Viewport(_parse_complex(args.center), args.viewport_width)
        files = render_color_cycle(args.kind, vp, args.frames, args.width,
                                    args.height, args.max_iter, args.palette,
                                    args.output_dir)
    else:
        raise ValueError(f"Unknown animation mode: {args.mode}")
    print(json.dumps({"frames": len(files), "dir": args.output_dir}, indent=2))


def cmd_preset(args):
    pm = PresetManager("presets")
    if args.action == "list":
        presets = pm.list()
        for name in sorted(presets):
            print(f"  {name}: {presets[name]}")
        print(f"\nBuilt-in presets: {', '.join(sorted(PRESETS))}")
    elif args.action == "save":
        params = json.loads(args.params) if args.params else {}
        path = pm.save(args.name, params)
        print(f"Saved preset -> {path}")
    elif args.action == "load":
        params = pm.load(args.name)
        print(json.dumps(params, indent=2))
    elif args.action == "delete":
        if pm.delete(args.name):
            print(f"Deleted preset: {args.name}")
        else:
            print(f"No preset named: {args.name}")


def cmd_filter(args):
    """Apply a filter to an existing PNG (reads via zlib)."""
    # This is a simplified version that operates on a pre-rendered image.
    # We re-render to get pixels, apply the filter, and write out.
    print(f"Use --filter <name> with the render command instead. "
          f"Available filters: {', '.join(sorted(FILTERS))}")


# --------------------------------------------------------------------------- #
# Build CLI
# --------------------------------------------------------------------------- #

def build_cli():
    """Build the argparse CLI."""
    parser = argparse.ArgumentParser(
        prog="fractal-explorer",
        description="Complex dynamics fractal renderer (pure Python, stdlib only).")
    parser.add_argument("--log-level", default="WARNING")
    sub = parser.add_subparsers(dest="command", required=True)

    # render
    pr = sub.add_parser("render", help="Render a single fractal image")
    _add_render_args(pr)
    pr.set_defaults(func=cmd_render)

    # julia
    pj = sub.add_parser("julia", help="Render a Julia set (shortcut)")
    _add_render_args(pj)
    pj.set_defaults(func=cmd_julia)

    # newton
    pn = sub.add_parser("newton", help="Render a Newton basin fractal (shortcut)")
    _add_render_args(pn)
    pn.set_defaults(func=cmd_newton)

    # ascii
    pa = sub.add_parser("ascii", help="Render to an ASCII art file")
    _add_render_args(pa)
    pa.set_defaults(func=cmd_ascii)

    # zoom
    pz = sub.add_parser("zoom", help="Render a zoom sequence")
    pz.add_argument("--kind", default="mandelbrot", choices=sorted(FRACTALS))
    pz.add_argument("--center", default="-0.5,0")
    pz.add_argument("--start-width", type=float, default=3.0)
    pz.add_argument("--end-width", type=float, default=0.001)
    pz.add_argument("--frames", type=int, default=30)
    pz.add_argument("--width", type=int, default=400)
    pz.add_argument("--height", type=int, default=300)
    pz.add_argument("--max-iter", type=int, default=256)
    pz.add_argument("--palette", default="fire")
    pz.add_argument("--coloring", default="smooth",
                    choices=["smooth", "flat", "de"])
    pz.add_argument("--output-dir", default="zoom_frames")
    pz.add_argument("--prefix", default="zoom")
    pz.add_argument("--hp", action="store_true", help="high-precision Decimal")
    pz.add_argument("--prec", type=int, default=60)
    pz.add_argument("--workers", "-j", type=int, default=1)
    pz.set_defaults(func=cmd_zoom)

    # palette
    pp = sub.add_parser("palette", help="Render a palette strip")
    pp.add_argument("--name", default="fire", choices=sorted(PALETTES))
    pp.add_argument("--size", type=int, default=256)
    pp.add_argument("--output", default=None)
    pp.set_defaults(func=cmd_palette)

    # explore
    pe = sub.add_parser("explore", help="Render a grid of Julia sets")
    pe.add_argument("--grid", type=int, default=4, help="grid size N (NxN)")
    pe.add_argument("--width", type=int, default=150)
    pe.add_argument("--height", type=int, default=150)
    pe.add_argument("--max-iter", type=int, default=150)
    pe.add_argument("--palette", default="rainbow")
    pe.add_argument("--power", type=float, default=2.0)
    pe.add_argument("--radius", type=float, default=1.5)
    pe.add_argument("--output-dir", default="julia_grid")
    pe.add_argument("--workers", "-j", type=int, default=1)
    pe.set_defaults(func=cmd_explore)

    # benchmark
    pb = sub.add_parser("benchmark", help="Benchmark rendering throughput")
    pb.add_argument("--width", type=int, default=300)
    pb.add_argument("--height", type=int, default=300)
    pb.add_argument("--max-iter", type=int, default=200)
    pb.add_argument("--trials", type=int, default=3)
    pb.set_defaults(func=cmd_benchmark)

    # info
    pi = sub.add_parser("info", help="List available fractals & palettes")
    pi.set_defaults(func=cmd_info)

    # buddhabrot
    pbd = sub.add_parser("buddhabrot", help="Render a Buddhabrot image")
    pbd.add_argument("--center", default="-0.5,0")
    pbd.add_argument("--viewport-width", type=float, default=3.0)
    pbd.add_argument("--viewport-height", type=float, default=2.0)
    pbd.add_argument("--width", type=int, default=400)
    pbd.add_argument("--height", type=int, default=400)
    pbd.add_argument("--samples", type=int, default=200000)
    pbd.add_argument("--max-iter", type=int, default=500)
    pbd.add_argument("--palette", default="magma")
    pbd.add_argument("--seed", type=int, default=None)
    pbd.add_argument("--anti", action="store_true", help="Anti-Buddhabrot")
    pbd.add_argument("--output", "-o", default="buddhabrot.png")
    pbd.set_defaults(func=cmd_buddhabrot)

    # lyapunov
    ply = sub.add_parser("lyapunov", help="Render a Lyapunov fractal")
    ply.add_argument("--a-min", type=float, default=2.0)
    ply.add_argument("--a-max", type=float, default=4.0)
    ply.add_argument("--b-min", type=float, default=2.0)
    ply.add_argument("--b-max", type=float, default=4.0)
    ply.add_argument("--width", type=int, default=400)
    ply.add_argument("--height", type=int, default=400)
    ply.add_argument("--sequence", default="AB",
                      help="alternation sequence (e.g. AB, ABBA)")
    ply.add_argument("--max-iter", type=int, default=400)
    ply.add_argument("--palette", default="magma")
    ply.add_argument("--output", "-o", default="lyapunov.png")
    ply.set_defaults(func=cmd_lyapunov)

    # ifs
    pifs = sub.add_parser("ifs", help="Render an IFS fractal (fern, sierpinski, dragon)")
    pifs.add_argument("--type", default="fern",
                       choices=["fern", "sierpinski", "dragon"])
    pifs.add_argument("--width", type=int, default=400)
    pifs.add_argument("--height", type=int, default=400)
    pifs.add_argument("--iterations", type=int, default=100000)
    pifs.add_argument("--palette", default="forest")
    pifs.add_argument("--seed", type=int, default=None)
    pifs.add_argument("--output", "-o", default="ifs.png")
    pifs.set_defaults(func=cmd_ifs)

    # animate
    pan = sub.add_parser("animate", help="Render an animation sequence")
    pan.add_argument("--mode", default="julia-morph",
                      choices=["julia-morph", "color-cycle"])
    pan.add_argument("--kind", default="mandelbrot", choices=sorted(FRACTALS))
    pan.add_argument("--center", default="0,0")
    pan.add_argument("--viewport-width", type=float, default=3.0)
    pan.add_argument("--c-start", default="-0.4,0.6", help="Julia c start")
    pan.add_argument("--c-end", default="0.285,0.01", help="Julia c end")
    pan.add_argument("--frames", type=int, default=30)
    pan.add_argument("--width", type=int, default=300)
    pan.add_argument("--height", type=int, default=200)
    pan.add_argument("--max-iter", type=int, default=150)
    pan.add_argument("--palette", default="rainbow")
    pan.add_argument("--output-dir", default="animation")
    pan.set_defaults(func=cmd_animate)

    # preset
    ppre = sub.add_parser("preset", help="Manage render presets")
    ppre.add_argument("action", choices=["list", "save", "load", "delete"])
    ppre.add_argument("--name", default=None)
    ppre.add_argument("--params", default=None, help="JSON params for save")
    ppre.set_defaults(func=cmd_preset)

    # filter
    pflt = sub.add_parser("filter", help="List available image filters")
    pflt.set_defaults(func=cmd_filter)

    return parser


def main(argv=None):
    """CLI entry point."""
    parser = build_cli()
    raw_argv = argv if argv is not None else sys.argv[1:]
    args = parser.parse_args(raw_argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(),
                                       logging.WARNING))
    explicit = _detect_explicit_args(parser, raw_argv)
    if hasattr(args, "config") and args.config:
        args = _apply_config_file(args, explicit=explicit)
    if hasattr(args, "preset"):
        args = _apply_preset(args)
    args.func(args)