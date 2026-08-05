"""
Command-line interface for the TDA toolkit.

Subcommands:
  compute   — Compute persistent homology of a point cloud
  distance  — Compute bottleneck, Hausdorff, or Wasserstein distance
  landscape — Compute persistence landscapes
  betti     — Compute Betti curves
  image     — Compute persistence images
  plot      — ASCII scatter plot of persistence diagrams
  info      — Show summary info about a diagram file
  compare   — Compare two diagrams with multiple metrics
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Sequence

from . import (
    VietorisRipsComplex,
    WeightedRipsComplex,
    CechComplex,
    SublevelFiltration,
    compute_persistence,
    diagrams_from_persistence,
    bottleneck_distance,
    hausdorff_distance,
    wasserstein_distance,
    betti_curve,
    persistence_landscape,
    persistence_image,
    image_to_ascii,
    plot_diagram_ascii,
    barcode_string,
)
from .io import diagrams_to_json, diagrams_from_json, save_diagrams
from .diagram import PersistenceDiagram
from .curves import landscape_norm


def _parse_points(path: str) -> List[Sequence[float]]:
    """Load a point cloud from a JSON or CSV file.

    JSON format: [[x, y, ...], [x, y, ...], ...]
    CSV format: comma-separated coordinates, one point per line.
    """
    if path.endswith(".json"):
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected a list of points in {path}")
        result = []
        for pt in data:
            if not isinstance(pt, (list, tuple)):
                raise ValueError(f"Each point must be a list, got {type(pt)}")
            result.append(tuple(float(c) for c in pt))
        return result
    else:
        pts: List[Sequence[float]] = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                coords = [float(x) for x in parts]
                pts.append(tuple(coords))
        return pts


def _parse_weights(path: str) -> List[float]:
    """Load vertex weights from a JSON file (list of floats)."""
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Weights file must be a JSON list of numbers")
    return [float(w) for w in data]


def cmd_compute(args: argparse.Namespace) -> int:
    """Compute persistent homology of a point cloud."""
    points = _parse_points(args.input)

    if args.complex == "rips":
        builder = VietorisRipsComplex(
            points,
            max_scale=args.max_scale,
            max_dimension=args.max_dimension,
        )
    elif args.complex == "weighted":
        if not args.weights:
            print("Error: --weights required for weighted complex", file=sys.stderr)
            return 1
        weights = _parse_weights(args.weights)
        if len(weights) != len(points):
            print(f"Error: {len(weights)} weights for {len(points)} points",
                  file=sys.stderr)
            return 1
        builder = WeightedRipsComplex(
            points, weights,
            max_scale=args.max_scale,
            max_dimension=args.max_dimension,
        )
    elif args.complex == "cech":
        builder = CechComplex(
            points,
            epsilon=args.max_scale / 2.0,
            max_dimension=args.max_dimension,
        )
    else:
        print(f"Unknown complex type: {args.complex}", file=sys.stderr)
        return 1

    tree = builder.build()
    persistence = compute_persistence(
        tree,
        max_dimension=args.max_dimension,
        min_persistence=args.min_persistence,
    )
    diagrams = diagrams_from_persistence(persistence)

    if args.format == "json":
        print(diagrams_to_json(diagrams))
    elif args.format == "barcode":
        print(barcode_string(diagrams))
    elif args.format == "plot":
        print(plot_diagram_ascii(diagrams))
    elif args.format == "summary":
        for dim in sorted(diagrams):
            diag = diagrams[dim]
            print(f"H{dim}: {diag.num_features} features "
                  f"({diag.num_essential} essential), "
                  f"max persistence = {diag.max_persistence:.4f}")

    if args.output:
        save_diagrams(diagrams, args.output)

    return 0


def cmd_distance(args: argparse.Namespace) -> int:
    """Compute bottleneck, Hausdorff, or Wasserstein distance between two diagrams."""
    d1 = diagrams_from_json(open(args.file1).read())
    d2 = diagrams_from_json(open(args.file2).read())

    dim = args.dimension
    if dim not in d1 or dim not in d2:
        print(f"Dimension {dim} not found in one or both diagrams", file=sys.stderr)
        return 1

    if args.metric == "bottleneck":
        dist = bottleneck_distance(d1[dim], d2[dim])
    elif args.metric == "hausdorff":
        dist = hausdorff_distance(d1[dim], d2[dim])
    elif args.metric == "wasserstein":
        dist = wasserstein_distance(d1[dim], d2[dim], p=args.p)
    else:
        print(f"Unknown metric: {args.metric}", file=sys.stderr)
        return 1

    print(f"{args.metric}_distance(H{dim}) = {dist:.6f}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare two diagrams with all available metrics."""
    d1 = diagrams_from_json(open(args.file1).read())
    d2 = diagrams_from_json(open(args.file2).read())

    dims = sorted(set(d1.keys()) | set(d2.keys()))
    for dim in dims:
        if dim not in d1 or dim not in d2:
            print(f"H{dim}: (missing in one diagram)")
            continue
        bn = bottleneck_distance(d1[dim], d2[dim])
        hs = hausdorff_distance(d1[dim], d2[dim])
        w1 = wasserstein_distance(d1[dim], d2[dim], p=1.0)
        w2 = wasserstein_distance(d1[dim], d2[dim], p=2.0)
        print(f"H{dim}:")
        print(f"  bottleneck  = {bn:.6f}")
        print(f"  hausdorff   = {hs:.6f}")
        print(f"  wasserstein1= {w1:.6f}")
        print(f"  wasserstein2= {w2:.6f}")
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


def cmd_image(args: argparse.Namespace) -> int:
    """Compute persistence images from a diagram file."""
    diagrams = diagrams_from_json(open(args.input).read())
    dim = args.dimension
    if dim not in diagrams:
        print(f"Dimension {dim} not found", file=sys.stderr)
        return 1

    img, b_range, p_range = persistence_image(
        diagrams[dim],
        resolution=args.resolution,
        sigma=args.sigma,
    )

    print(f"Persistence image H{dim}: {len(img)}x{len(img[0])} pixels")
    print(f"  birth range:        [{b_range[0]:.4f}, {b_range[1]:.4f}]")
    print(f"  persistence range:  [{p_range[0]:.4f}, {p_range[1]:.4f}]")
    print()
    print(image_to_ascii(img, width=args.width))

    if args.output:
        with open(args.output, "w") as f:
            json.dump({
                "dimension": dim,
                "birth_range": list(b_range),
                "persistence_range": list(p_range),
                "image": img,
            }, f, indent=2)

    return 0


def cmd_plot(args: argparse.Namespace) -> int:
    """ASCII scatter plot of persistence diagrams."""
    diagrams = diagrams_from_json(open(args.input).read())
    dims = [int(d) for d in args.dims.split(",")] if args.dims else None
    print(plot_diagram_ascii(diagrams, width=args.width, height=args.height,
                             dims=dims))
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
    p.add_argument("--complex", choices=["rips", "weighted", "cech"],
                   default="rips", help="Complex type")
    p.add_argument("--weights", help="Weights JSON file (for weighted complex)")
    p.add_argument("--max-scale", type=float, default=float("inf"),
                   help="Maximum filtration scale (epsilon)")
    p.add_argument("--max-dimension", "-d", type=int, default=1,
                   help="Maximum homology dimension")
    p.add_argument("--min-persistence", type=float, default=0.0,
                   help="Filter features with persistence below this threshold")
    p.add_argument("--format", choices=["json", "barcode", "summary", "plot"],
                   default="summary")
    p.add_argument("--output", "-o", help="Save diagrams to JSON file")
    p.set_defaults(func=cmd_compute)

    # distance
    p = sub.add_parser("distance", help="Compute distance between two diagrams")
    p.add_argument("file1", help="First diagram JSON")
    p.add_argument("file2", help="Second diagram JSON")
    p.add_argument("--metric", choices=["bottleneck", "hausdorff", "wasserstein"],
                   default="bottleneck")
    p.add_argument("--dimension", "-d", type=int, default=0)
    p.add_argument("--p", type=float, default=2.0,
                   help="Wasserstein order (for wasserstein metric)")
    p.set_defaults(func=cmd_distance)

    # compare
    p = sub.add_parser("compare", help="Compare two diagrams with all metrics")
    p.add_argument("file1", help="First diagram JSON")
    p.add_argument("file2", help="Second diagram JSON")
    p.set_defaults(func=cmd_compare)

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

    # image
    p = sub.add_parser("image", help="Compute persistence images")
    p.add_argument("input", help="Diagram JSON file")
    p.add_argument("--dimension", "-d", type=int, default=0)
    p.add_argument("--resolution", "-r", type=int, default=50)
    p.add_argument("--sigma", type=float, default=1.0, help="Gaussian bandwidth")
    p.add_argument("--width", type=int, default=50, help="ASCII render width")
    p.add_argument("--output", "-o", help="Save image as JSON")
    p.set_defaults(func=cmd_image)

    # plot
    p = sub.add_parser("plot", help="ASCII scatter plot of persistence diagrams")
    p.add_argument("input", help="Diagram JSON file")
    p.add_argument("--dims", help="Comma-separated dimensions to plot")
    p.add_argument("--width", type=int, default=60)
    p.add_argument("--height", type=int, default=30)
    p.set_defaults(func=cmd_plot)

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