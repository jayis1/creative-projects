"""Command-line interface for the mcengine isosurface toolkit.

Usage examples::

    mcengine render --algorithm mc --sampler sphere --resolution 32 --output sphere.obj
    mcengine render --algorithm dc --sampler torus --res 48 --output torus.stl --format stl
    mcengine render --sampler gyroid --res 64 --bounds -3,3 -o gyroid.ply --format ply-binary
    mcengine info --input sphere.obj
    mcengine list-samplers
    mcengine compare --sampler sphere --res 32
"""

from __future__ import annotations

import argparse
import json
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
        raise ValueError(f"unknown sampler '{name}'.  Use --list-samplers to see options.")
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


EXPORTERS = {
    "obj": write_obj,
    "off": write_off,
    "ply-ascii": write_ply_ascii,
    "ply-binary": write_ply_binary,
    "stl-ascii": write_stl_ascii,
    "stl-binary": write_stl_binary,
    "gltf": write_gltf_minimal,
}


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

    d = analyze_mesh(mesh)
    print(d.summary())

    if args.preview:
        print("\nASCII preview:")
        print(render_ascii_preview(mesh, width=args.preview_width, height=args.preview_height))

    fmt = args.format or _detect_format(args.output)
    if fmt not in EXPORTERS:
        print(f"Error: unknown format '{fmt}'", file=sys.stderr)
        sys.exit(1)
    EXPORTERS[fmt](mesh, args.output)
    print(f"\nExported {mesh.num_faces} faces to {args.output} ({fmt})")


def cmd_info(args):
    """Read a mesh file and print diagnostics."""
    # Simple OBJ reader
    verts, faces = [], []
    with open(args.input) as f:
        for line in f:
            if line.startswith("v "):
                parts = line.split()
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith("f "):
                parts = line.split()[1:]
                # handle v//vn format
                idx = [int(p.split("/")[0]) - 1 for p in parts[:3]]
                faces.append(tuple(idx))
    from .mesh import Mesh
    mesh = Mesh(vertices=verts, faces=faces)
    d = analyze_mesh(mesh)
    print(d.summary())


def cmd_list_samplers(args):
    """List available samplers."""
    print("Available samplers:")
    for name, (desc, _) in SAMPLERS.items():
        print(f"  {name:20s}  {desc}")


def cmd_compare(args):
    """Compare all three algorithms on the same sampler."""
    sampler_base = _make_sampler(args.sampler, args)
    bounds = _parse_bounds(args.bounds)
    res = args.resolution

    print(f"{'Algorithm':20s} {'Vertices':>10s} {'Faces':>10s} {'Watertight':>12s} {'χ':>5s} {'Area':>12s}")
    print("-" * 75)
    for name, cls in [("MarchingCubes", MarchingCubes), ("MarchingTetrahedra", MarchingTetrahedra), ("DualContouring", DualContouring)]:
        # Each algorithm needs its own sampler instance (they cache field)
        from .samplers import Sampler
        sampler = type(sampler_base)(**{} ) if not hasattr(sampler_base, 'r2') else type(sampler_base)()
        # Just create fresh
        sampler = _make_sampler(args.sampler, args)
        algo = cls(sampler=sampler, bounds=bounds, resolution=(res, res, res), isolevel=args.isolevel)
        mesh = algo.run()
        d = analyze_mesh(mesh)
        chi = d.euler_characteristic
        wt = "yes" if d.is_watertight else "no"
        print(f"{name:20s} {mesh.num_vertices:10d} {mesh.num_faces:10d} {wt:>12s} {chi:5d} {d.surface_area:12.4f}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mcengine",
        description="Isosurface extraction toolkit (Marching Cubes, Marching Tetrahedra, Dual Contouring)",
    )
    sub = parser.add_subparsers(dest="command")

    # render
    p = sub.add_parser("render", help="Extract isosurface and export mesh")
    p.add_argument("--algorithm", "-a", choices=["mc", "mt", "dc"], default="mc", help="Meshing algorithm")
    p.add_argument("--sampler", "-s", default="sphere", help="Implicit surface name")
    p.add_argument("--resolution", "--res", type=int, default=32, help="Grid resolution per axis")
    p.add_argument("--bounds", "-b", default="-1.5,1.5", help="Bounds as 'lo,hi' or 'x0,y0,z0,x1,y1,z1'")
    p.add_argument("--isolevel", "-i", type=float, default=0.0, help="Isovalue")
    p.add_argument("--output", "-o", required=True, help="Output file path")
    p.add_argument("--format", "-f", choices=list(EXPORTERS.keys()), default=None, help="Output format (auto-detect from extension if omitted)")
    p.add_argument("--preview", action="store_true", help="Print ASCII preview")
    p.add_argument("--preview-width", type=int, default=60)
    p.add_argument("--preview-height", type=int, default=20)
    p.add_argument("--no-clamp", action="store_true", help="DC: don't clamp vertices to cells")
    # sampler params
    p.add_argument("--sphere-radius", type=float, default=1.0)
    p.add_argument("--torus-R", type=float, default=1.0)
    p.add_argument("--torus-r", type=float, default=0.35)
    p.add_argument("--octa-r", type=float, default=1.0)
    p.add_argument("--sq-e1", type=float, default=2.0, help="Superquadric e1")
    p.add_argument("--sq-e2", type=float, default=2.0, help="Superquadric e2")
    p.add_argument("--hyp-r", type=float, default=1.0)
    p.set_defaults(func=cmd_render)

    # info
    p = sub.add_parser("info", help="Print mesh diagnostics from an OBJ file")
    p.add_argument("--input", "-i", required=True, help="OBJ file path")
    p.set_defaults(func=cmd_info)

    # list-samplers
    p = sub.add_parser("list-samplers", help="List available implicit surfaces")
    p.set_defaults(func=cmd_list_samplers)

    # compare
    p = sub.add_parser("compare", help="Compare all 3 algorithms on the same surface")
    p.add_argument("--sampler", "-s", default="sphere")
    p.add_argument("--resolution", "--res", type=int, default=24)
    p.add_argument("--bounds", "-b", default="-1.5,1.5")
    p.add_argument("--isolevel", "-i", type=float, default=0.0)
    p.add_argument("--sphere-radius", type=float, default=1.0)
    p.add_argument("--torus-R", type=float, default=1.0)
    p.add_argument("--torus-r", type=float, default=0.35)
    p.add_argument("--octa-r", type=float, default=1.0)
    p.add_argument("--sq-e1", type=float, default=2.0)
    p.add_argument("--sq-e2", type=float, default=2.0)
    p.add_argument("--hyp-r", type=float, default=1.0)
    p.set_defaults(func=cmd_compare)

    return parser


def main(argv: Optional[List[str]] = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()