"""Command-line interface for the mcengine isosurface toolkit.

Usage examples::

    mcengine render --algorithm mc --sampler sphere --resolution 32 --output sphere.obj
    mcengine render --algorithm dc --sampler torus --res 48 --output torus.stl --format stl
    mcengine render --sampler gyroid --res 64 --bounds -3,3 -o gyroid.ply --format ply-binary
    mcengine info --input sphere.obj
    mcengine list-samplers
    mcengine list-presets
    mcengine compare --sampler sphere --res 32
    mcengine batch --config render_jobs.json
    mcengine preset gyroid --output gyroid.stl
    mcengine subdivide --input sphere.obj --iterations 2 --output sphere_sub.obj
    mcengine transform --input mesh.obj --rotate-z 1.57 --output rotated.obj
    mcengine convert --input sphere.obj --output sphere.stl --format stl-binary
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import List, Optional, Tuple

from . import (
    MarchingCubes, MarchingTetrahedra, DualContouring,
    SphereSampler, TorusSampler, OctahedronSampler, SteinerSampler,
    Genus2Sampler, GyroidSampler, HeartSampler, SuperquadricSampler,
    HyperboloidSampler, NoisySampler, BooleanOpsSampler,
    analyze_mesh, write_obj, write_off, write_ply_ascii, write_ply_binary,
    write_stl_ascii, write_stl_binary, write_gltf_minimal,
)
from .ascii_preview import render_ascii_preview
from .samplers import Sampler
from .simplify import simplify_mesh
from .subdivision import subdivide_n
from .transforms import (
    translate, scale, rotate_x, rotate_y, rotate_z, mirror,
    normalize_size, center, merge_meshes,
)
from .mesh_io import read_mesh, read_obj
from .batch import render_job, render_config, render_preset, EXPORTERS
from .config import SAMPLER_CLASSES, PRESETS, list_presets, get_preset, normalize_job
from .logging_util import get_logger, set_log_level


# ---------------------------------------------------------------------------
# Sampler registry
# ---------------------------------------------------------------------------
SAMPLERS = {
    "sphere": ("Unit sphere", SphereSampler),
    "torus": ("Torus (R=1, r=0.35)", TorusSampler),
    "octahedron": ("L1 octahedron", OctahedronSampler),
    "steiner": ("Steiner surface", SteinerSampler),
    "genus2": ("Genus-2 surface", Genus2Sampler),
    "gyroid": ("Gyroid minimal surface", GyroidSampler),
    "heart": ("Heart (Taubin)", HeartSampler),
    "superquadric": ("Superquadric ellipsoid", SuperquadricSampler),
    "hyperboloid": ("One-sheet hyperboloid", HyperboloidSampler),
}


def _parse_bounds(s: str) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Parse a bounds string like '-1.5,1.5' or '-1.5,-1.5,-1.5,1.5,1.5,1.5'."""
    parts = [float(x) for x in s.split(",")]
    if len(parts) == 2:
        lo, hi = parts
        return ((lo, lo, lo), (hi, hi, hi))
    elif len(parts) == 6:
        return ((parts[0], parts[1], parts[2]), (parts[3], parts[4], parts[5]))
    else:
        raise ValueError(f"bounds must be 2 or 6 comma-separated values, got {len(parts)}")


def _make_sampler(name: str, args) -> Sampler:
    if name not in SAMPLERS:
        raise ValueError(f"unknown sampler '{name}'.  Use 'list-samplers' to see options.")
    cls = SAMPLERS[name][1]
    if name == "sphere":
        return cls(radius=args.sphere_radius)
    if name == "torus":
        return cls(R=args.torus_R, r=args.torus_r)
    if name == "octahedron":
        return cls(r=args.octa_r)
    if name == "superquadric":
        return cls(e1=args.sq_e1, e2=args.sq_e2)
    if name == "hyperboloid":
        return cls(r=args.hyp_r)
    return cls()


def _detect_format(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    fmt_map = {
        ".obj": "obj", ".off": "off", ".ply": "ply-binary",
        ".stl": "stl-binary", ".gltf": "gltf",
    }
    return fmt_map.get(ext, "obj")


def _export_mesh(mesh, output: str, fmt: Optional[str] = None):
    """Export mesh to file, auto-detecting format if needed."""
    fmt = fmt or _detect_format(output)
    if fmt not in EXPORTERS:
        print(f"Error: unknown format '{fmt}'", file=sys.stderr)
        sys.exit(1)
    EXPORTERS[fmt](mesh, output)
    return fmt


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_render(args):
    """Run an algorithm and export the mesh."""
    sampler = _make_sampler(args.sampler, args)
    bounds = _parse_bounds(args.bounds)
    res = (args.resolution, args.resolution, args.resolution) if isinstance(args.resolution, int) else args.resolution

    algo_map = {
        "mc": MarchingCubes,
        "mt": MarchingTetrahedra,
        "dc": DualContouring,
    }
    algo_cls = algo_map[args.algorithm]

    kwargs = dict(sampler=sampler, bounds=bounds, resolution=res, isolevel=args.isolevel)
    if args.algorithm == "dc":
        kwargs["clamp_to_cell"] = not args.no_clamp

    print(f"Running {args.algorithm.upper()} on '{args.sampler}' at {res}...")
    algo = algo_cls(**kwargs)
    mesh = algo.run()

    # Post-processing: simplify
    if args.simplify and args.simplify < mesh.num_faces:
        print(f"Simplifying to ~{args.simplify} faces...")
        mesh = simplify_mesh(mesh, target_faces=args.simplify)

    # Post-processing: subdivide
    if args.subdivide and args.subdivide > 0:
        print(f"Subdividing {args.subdivide}x...")
        mesh = subdivide_n(mesh, args.subdivide)

    d = analyze_mesh(mesh)
    print(d.summary())

    if args.preview:
        print("\nASCII preview:")
        print(render_ascii_preview(mesh, width=args.preview_width, height=args.preview_height))

    fmt = _export_mesh(mesh, args.output, args.format)
    print(f"\nExported {mesh.num_faces} faces to {args.output} ({fmt})")


def cmd_info(args):
    """Read a mesh file and print diagnostics."""
    mesh = read_mesh(args.input)
    d = analyze_mesh(mesh)
    print(d.summary())
    if args.preview:
        print()
        print(render_ascii_preview(mesh, width=args.preview_width, height=args.preview_height))


def cmd_list_samplers(args):
    """List available samplers."""
    print("Available samplers:")
    for name, (desc, _) in SAMPLERS.items():
        print(f"  {name:20s}  {desc}")


def cmd_list_presets(args):
    """List available presets."""
    print("Available presets:")
    for name in list_presets():
        preset = get_preset(name)
        print(f"  {name:20s}  algo={preset['algorithm']}  sampler={preset['sampler']}  "
              f"res={preset['resolution']}")


def cmd_compare(args):
    """Compare all three algorithms on the same sampler."""
    bounds = _parse_bounds(args.bounds)
    res = args.resolution

    print(f"{'Algorithm':20s} {'Vertices':>10s} {'Faces':>10s} {'Watertight':>12s} {'χ':>5s} {'Area':>12s}")
    print("-" * 75)
    for name, cls in [("MarchingCubes", MarchingCubes), ("MarchingTetrahedra", MarchingTetrahedra), ("DualContouring", DualContouring)]:
        sampler = _make_sampler(args.sampler, args)
        algo = cls(sampler=sampler, bounds=bounds, resolution=(res, res, res), isolevel=args.isolevel)
        mesh = algo.run()
        d = analyze_mesh(mesh)
        chi = d.euler_characteristic
        wt = "yes" if d.is_watertight else "no"
        print(f"{name:20s} {mesh.num_vertices:10d} {mesh.num_faces:10d} {wt:>12s} {chi:5d} {d.surface_area:12.4f}")


def cmd_batch(args):
    """Run multiple render jobs from a config file."""
    set_log_level("INFO")
    results = render_config(args.config)
    print(f"\nCompleted {len(results)} jobs:")
    for r in results:
        d = r["diagnostics"]
        print(f"  {r['name']:20s}  V={d.num_vertices:6d}  F={d.num_faces:6d}  "
              f"χ={d.euler_characteristic:4d}  watertight={d.is_watertight}  "
              f"({r['elapsed']:.2f}s)")
        if r.get("output"):
            print(f"    -> {r['output']}")
        if r.get("preview") and args.preview:
            print()
            print(r["preview"])


def cmd_preset(args):
    """Render using a built-in preset."""
    result = render_preset(args.preset, output=args.output, preview=args.preview)
    d = result["diagnostics"]
    print(f"Preset '{args.preset}':")
    print(d.summary())
    if args.output:
        print(f"Exported to {args.output}")
    if result.get("preview"):
        print()
        print(result["preview"])


def cmd_subdivide(args):
    """Subdivide a mesh file using Loop subdivision."""
    mesh = read_mesh(args.input)
    print(f"Input: V={mesh.num_vertices}, F={mesh.num_faces}")
    mesh = subdivide_n(mesh, args.iterations)
    print(f"After {args.iterations}x subdivision: V={mesh.num_vertices}, F={mesh.num_faces}")
    d = analyze_mesh(mesh)
    print(d.summary())
    _export_mesh(mesh, args.output, args.format)
    print(f"Exported to {args.output}")


def cmd_transform(args):
    """Apply geometric transformations to a mesh file."""
    mesh = read_mesh(args.input)
    print(f"Input: V={mesh.num_vertices}, F={mesh.num_faces}")

    if args.translate:
        parts = [float(x) for x in args.translate.split(",")]
        mesh = translate(mesh, *parts)
    if args.scale:
        s = float(args.scale)
        mesh = scale(mesh, s, s, s)
    if args.rotate_x is not None:
        mesh = rotate_x(mesh, args.rotate_x)
    if args.rotate_y is not None:
        mesh = rotate_y(mesh, args.rotate_y)
    if args.rotate_z is not None:
        mesh = rotate_z(mesh, args.rotate_z)
    if args.mirror:
        mesh = mirror(mesh, args.mirror)
    if args.center:
        mesh = center(mesh)
    if args.normalize:
        mesh = normalize_size(mesh, args.normalize)

    d = analyze_mesh(mesh)
    print(d.summary())
    _export_mesh(mesh, args.output, args.format)
    print(f"Exported to {args.output}")


def cmd_convert(args):
    """Convert a mesh file from one format to another."""
    mesh = read_mesh(args.input)
    fmt = _export_mesh(mesh, args.output, args.format)
    d = analyze_mesh(mesh)
    print(f"Converted: {args.input} -> {args.output} ({fmt})")
    print(f"  V={d.num_vertices}, F={d.num_faces}")


def cmd_simplify(args):
    """Simplify a mesh file using edge-collapse."""
    mesh = read_mesh(args.input)
    print(f"Input: V={mesh.num_vertices}, F={mesh.num_faces}")
    mesh = simplify_mesh(mesh, target_faces=args.target, max_error=args.max_error)
    print(f"Simplified: V={mesh.num_vertices}, F={mesh.num_faces}")
    d = analyze_mesh(mesh)
    print(d.summary())
    _export_mesh(mesh, args.output, args.format)
    print(f"Exported to {args.output}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _add_sampler_params(parser):
    """Add common sampler parameter arguments to a parser."""
    parser.add_argument("--sphere-radius", type=float, default=1.0)
    parser.add_argument("--torus-R", type=float, default=1.0)
    parser.add_argument("--torus-r", type=float, default=0.35)
    parser.add_argument("--octa-r", type=float, default=1.0)
    parser.add_argument("--sq-e1", type=float, default=2.0, help="Superquadric e1")
    parser.add_argument("--sq-e2", type=float, default=2.0, help="Superquadric e2")
    parser.add_argument("--hyp-r", type=float, default=1.0)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mcengine",
        description="Isosurface extraction toolkit (Marching Cubes, Marching Tetrahedra, Dual Contouring)",
        epilog="Run 'mcengine <command> --help' for command-specific options.",
    )
    sub = parser.add_subparsers(dest="command")

    # render
    p = sub.add_parser("render", help="Extract isosurface and export mesh",
                       description="Run a meshing algorithm on a built-in sampler and export the result.")
    p.add_argument("--algorithm", "-a", choices=["mc", "mt", "dc"], default="mc", help="Meshing algorithm (default: mc)")
    p.add_argument("--sampler", "-s", default="sphere", help="Implicit surface name (use 'list-samplers' to see)")
    p.add_argument("--resolution", "--res", type=int, default=32, help="Grid resolution per axis (default: 32)")
    p.add_argument("--bounds", "-b", default="-1.5,1.5", help="Bounds: 'lo,hi' or 'x0,y0,z0,x1,y1,z1'")
    p.add_argument("--isolevel", "-i", type=float, default=0.0, help="Isovalue (default: 0.0)")
    p.add_argument("--output", "-o", required=True, help="Output file path")
    p.add_argument("--format", "-f", choices=list(EXPORTERS.keys()), default=None,
                   help="Output format (auto-detect from extension if omitted)")
    p.add_argument("--preview", action="store_true", help="Print ASCII preview")
    p.add_argument("--preview-width", type=int, default=60)
    p.add_argument("--preview-height", type=int, default=20)
    p.add_argument("--no-clamp", action="store_true", help="DC: don't clamp vertices to cells")
    p.add_argument("--simplify", type=int, default=0, help="Simplify to target face count")
    p.add_argument("--subdivide", type=int, default=0, help="Loop subdivision iterations")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    _add_sampler_params(p)
    p.set_defaults(func=cmd_render)

    # info
    p = sub.add_parser("info", help="Print mesh diagnostics from a file",
                       description="Read a mesh file (OBJ/OFF/PLY/STL) and print diagnostics.")
    p.add_argument("--input", "-i", required=True, help="Input mesh file path")
    p.add_argument("--preview", action="store_true", help="Print ASCII preview")
    p.add_argument("--preview-width", type=int, default=60)
    p.add_argument("--preview-height", type=int, default=20)
    p.set_defaults(func=cmd_info)

    # list-samplers
    p = sub.add_parser("list-samplers", help="List available implicit surfaces")
    p.set_defaults(func=cmd_list_samplers)

    # list-presets
    p = sub.add_parser("list-presets", help="List available render presets")
    p.set_defaults(func=cmd_list_presets)

    # compare
    p = sub.add_parser("compare", help="Compare all 3 algorithms on the same surface",
                       description="Run MC, MT, and DC on the same sampler and print a comparison table.")
    p.add_argument("--sampler", "-s", default="sphere")
    p.add_argument("--resolution", "--res", type=int, default=24)
    p.add_argument("--bounds", "-b", default="-1.5,1.5")
    p.add_argument("--isolevel", "-i", type=float, default=0.0)
    _add_sampler_params(p)
    p.set_defaults(func=cmd_compare)

    # batch
    p = sub.add_parser("batch", help="Run multiple jobs from a config file",
                       description="Load a JSON/TOML config file and execute all render jobs.")
    p.add_argument("--config", "-c", required=True, help="Config file path (JSON or TOML)")
    p.add_argument("--preview", action="store_true", help="Show previews for each job")
    p.set_defaults(func=cmd_batch)

    # preset
    p = sub.add_parser("preset", help="Render using a built-in preset",
                       description="Render a mesh using a named preset configuration.")
    p.add_argument("preset", help="Preset name (use 'list-presets' to see options)")
    p.add_argument("--output", "-o", default=None, help="Output file path")
    p.add_argument("--preview", action="store_true", help="Print ASCII preview")
    p.set_defaults(func=cmd_preset)

    # subdivide
    p = sub.add_parser("subdivide", help="Subdivide a mesh using Loop subdivision",
                       description="Read a mesh, apply Loop subdivision, and export.")
    p.add_argument("--input", "-i", required=True, help="Input mesh file")
    p.add_argument("--output", "-o", required=True, help="Output mesh file")
    p.add_argument("--iterations", "-n", type=int, default=1, help="Subdivision iterations (default: 1)")
    p.add_argument("--format", "-f", choices=list(EXPORTERS.keys()), default=None)
    p.set_defaults(func=cmd_subdivide)

    # transform
    p = sub.add_parser("transform", help="Apply geometric transformations to a mesh",
                       description="Read a mesh, apply transforms (translate/scale/rotate/mirror), and export.")
    p.add_argument("--input", "-i", required=True, help="Input mesh file")
    p.add_argument("--output", "-o", required=True, help="Output mesh file")
    p.add_argument("--translate", "-t", default=None, help="Translate: 'dx,dy,dz'")
    p.add_argument("--scale", "-s", type=float, default=None, help="Uniform scale factor")
    p.add_argument("--rotate-x", type=float, default=None, help="Rotate around X (radians)")
    p.add_argument("--rotate-y", type=float, default=None, help="Rotate around Y (radians)")
    p.add_argument("--rotate-z", type=float, default=None, help="Rotate around Z (radians)")
    p.add_argument("--mirror", default=None, choices=["x", "y", "z"], help="Mirror across plane")
    p.add_argument("--center", action="store_true", help="Center at origin")
    p.add_argument("--normalize", type=float, default=None, help="Normalize to target max dimension")
    p.add_argument("--format", "-f", choices=list(EXPORTERS.keys()), default=None)
    p.set_defaults(func=cmd_transform)

    # convert
    p = sub.add_parser("convert", help="Convert mesh between file formats",
                       description="Read a mesh in one format and write it in another.")
    p.add_argument("--input", "-i", required=True, help="Input mesh file")
    p.add_argument("--output", "-o", required=True, help="Output mesh file")
    p.add_argument("--format", "-f", choices=list(EXPORTERS.keys()), default=None)
    p.set_defaults(func=cmd_convert)

    # simplify
    p = sub.add_parser("simplify", help="Simplify a mesh using edge-collapse",
                       description="Reduce triangle count while preserving topology.")
    p.add_argument("--input", "-i", required=True, help="Input mesh file")
    p.add_argument("--output", "-o", required=True, help="Output mesh file")
    p.add_argument("--target", "-t", type=int, default=500, help="Target face count (default: 500)")
    p.add_argument("--max-error", type=float, default=0.15, help="Max normal deviation (radians)")
    p.add_argument("--format", "-f", choices=list(EXPORTERS.keys()), default=None)
    p.set_defaults(func=cmd_simplify)

    return parser


def main(argv: Optional[List[str]] = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, "verbose") and args.verbose:
        set_log_level("DEBUG")

    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"Error: file not found: {e.filename}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()