"""
Command-line interface for the TDA toolkit.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Sequence

from . import (
    VietorisRipsComplex,
    compute_persistence,
    diagrams_from_persistence,
    bottleneck_distance,
    hausdorff_distance,
    betti_curve,
    persistence_landscape,
    barcode_string,
)
from .io import diagrams_to_json, diagrams_from_json
from .diagram import PersistenceDiagram


def _parse_points(path: str) -> List[Sequence[float]]:
    """Load a point cloud from a JSON or CSV file.

    JSON format: [[x, y, ...], [x, y, ...], ...]
    CSV format: comma-separated coordinates, one point per line.
    """
    if path.endswith(".json"):
        with open(path) as f:
            data = json.load(f)
        return [tuple(float(c) for c in pt) for pt in data]
    else:
        pts: List[Sequence[float]] = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                coords = [float(x) for x in line.split(",")]
                pts.append(tuple(coords))
        return pts


def cmd_compute(args: argparse.Namespace) -> int:
    """Compute persistent homology of a point cloud."""
    points = _parse_points(args.input)
    vr = VietorisRipsComplex(
        points,
        max_scale=args.max_scale,
        max_dimension=args.max_dimension,
    )
    tree = vr.build()
    persistence = compute_persistence(tree, max_dimension=args.max_dimension)
    diagrams = diagrams_from_persistence(persistence)

    if args.format == "json":
        print(diagrams_to_json(diagrams))
    elif args.format == "barcode":
        print(barcode_string(diagrams))
    elif args.format == "summary":
        for dim in sorted(diagrams):
            diag = diagrams[dim]
            print(f"H{dim}: {diag.num_features} features "
                  f"({diag.num_essential} essential), "
                  f"max persistence = {diag.max_persistence:.4f}")

    if args.output:
        from .io import save_diagrams
        save_diagrams(diagrams, args.output)

    return 0


def cmd_distance(args: argparse.Namespace) -> int:
    """Compute bottleneck or Hausdorff distance between two diagrams."""
    d1 = diagrams_from_json(open(args.file1).read())
    d2 = diagrams_from_json(open(args.file2).read())

    dim = args.dimension
    if dim not in d1 or dim not in d2:
        print(f"Dimension {dim} not found in one or both diagrams", file=sys.stderr)
        return 1

    if args.metric == "bottleneck":
        dist = bottleneck_distance(d1[dim], d2[dim])
    else:
        dist = hausdorff_distance(d1[dim], d2[dim])

    print(f"{args.metric}_distance(H{dim}) = {dist:.6f}")
    return 0


def cmd_landscape(args: argparse.Namespace) -> int:
    """Compute persistence landscapes from a diagram file."""
    diagrams = diagrams_from_json(open(args.input).read())
    dim = args.dimension
    if dim not in diagrams:
        print(f"Dimension {dim} not found", file=sys.stderr)
        return 1

    landscapes = persistence_landscape(
        diagrams[dim],
        resolution=args.resolution,
        max_functions=args.num_functions,
    )

    from .curves import landscape_norm

    for k, landscape in enumerate(landscapes, 1):
        norm = landscape_norm(landscape, p=args.norm)
        print(f"Λ_{k}: L^{args.norm} norm = {norm:.6f}")
        if args.verbose:
            for t, v in landscape[:10]:
                print(f"  t={t:.4f}: {v:.4f}")
            if len(landscape) > 10:
                print(f"  ... ({len(landscape)} points total)")

    return 0


def cmd_betti(args: argparse.Namespace) -> int:
    """Compute Betti curves from a diagram file."""
    diagrams = diagrams_from_json(open(args.input).read())
    curves = betti_curve(diagrams, resolution=args.resolution)
    for dim in sorted(curves):
        print(f"H{dim}:")
        for t, b in curves[dim]:
            print(f"  t={t:.4f}: β={b}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show summary info about a diagram file."""
    diagrams = diagrams_from_json(open(args.input).read())
    print(f"Persistence diagrams: {len(diagrams)} dimensions")
    for dim in sorted(diagrams):
        diag = diagrams[dim]
        print(f"  H{dim}: {diag.num_features} features, "
              f"{diag.num_essential} essential, "
              f"max persistence = {diag.max_persistence:.4f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tda",
        description="Topological Data Analysis toolkit",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # compute
    p = sub.add_parser("compute", help="Compute persistent homology of a point cloud")
    p.add_argument("input", help="Input point cloud (JSON or CSV)")
    p.add_argument("--max-scale", type=float, default=float("inf"),
                   help="Maximum filtration scale (epsilon)")
    p.add_argument("--max-dimension", "-d", type=int, default=1,
                   help="Maximum homology dimension")
    p.add_argument("--format", choices=["json", "barcode", "summary"],
                   default="summary")
    p.add_argument("--output", "-o", help="Save diagrams to JSON file")
    p.set_defaults(func=cmd_compute)

    # distance
    p = sub.add_parser("distance", help="Compute distance between two diagrams")
    p.add_argument("file1", help="First diagram JSON")
    p.add_argument("file2", help="Second diagram JSON")
    p.add_argument("--metric", choices=["bottleneck", "hausdorff"],
                   default="bottleneck")
    p.add_argument("--dimension", "-d", type=int, default=0)
    p.set_defaults(func=cmd_distance)

    # landscape
    p = sub.add_parser("landscape", help="Compute persistence landscapes")
    p.add_argument("input", help="Diagram JSON file")
    p.add_argument("--dimension", "-d", type=int, default=0)
    p.add_argument("--resolution", "-r", type=int, default=100)
    p.add_argument("--num-functions", "-k", type=int, default=5)
    p.add_argument("--norm", type=int, default=2, help="L^p norm order (0=sup)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.set_defaults(func=cmd_landscape)

    # betti
    p = sub.add_parser("betti", help="Compute Betti curves")
    p.add_argument("input", help="Diagram JSON file")
    p.add_argument("--resolution", "-r", type=int, default=100)
    p.set_defaults(func=cmd_betti)

    # info
    p = sub.add_parser("info", help="Show info about a diagram file")
    p.add_argument("input", help="Diagram JSON file")
    p.set_defaults(func=cmd_info)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())