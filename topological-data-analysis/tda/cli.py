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
  stats     — Show per-dimension statistics table
  batch     — Process multiple point clouds and output features
  kernel    — Compute persistence kernel matrix between diagram files
  config    — Generate or validate a configuration file
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import List, Optional, Sequence

from . import (
    VietorisRipsComplex,
    WeightedRipsComplex,
    CechComplex,
    AlphaComplex,
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
    diagram_statistics,
    statistics_table,
    vectorize,
    pss_kernel,
    pwg_kernel,
    fisher_kernel,
    kernel_matrix,
)
from .io import diagrams_to_json, diagrams_from_json, save_diagrams
from .diagram import PersistenceDiagram
from .curves import landscape_norm
from .config import load_config, save_config, validate_config, DEFAULT_CONFIG
from .exceptions import TDAError, FileFormatError
from .logging_config import get_logger

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

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


def _parse_grid(path: str):
    """Load a grid (for sublevel filtration) from a JSON file."""
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Complex builder factory (used by compute and batch)
# ---------------------------------------------------------------------------

def _build_complex(args, points=None, grid=None):
    """Create and build the appropriate complex based on args."""
    if points is None and grid is None:
        points = _parse_points(args.input)

    cpx_type = getattr(args, "complex", "rips")

    if cpx_type == "rips":
        builder = VietorisRipsComplex(
            points,
            max_scale=args.max_scale,
            max_dimension=args.max_dimension,
        )
    elif cpx_type == "weighted":
        if not args.weights:
            raise TDAError("--weights required for weighted complex")
        weights = _parse_weights(args.weights)
        if len(weights) != len(points):
            raise TDAError(
                f"{len(weights)} weights for {len(points)} points"
            )
        builder = WeightedRipsComplex(
            points, weights,
            max_scale=args.max_scale,
            max_dimension=args.max_dimension,
        )
    elif cpx_type == "cech":
        builder = CechComplex(
            points,
            epsilon=args.max_scale / 2.0,
            max_dimension=args.max_dimension,
        )
    elif cpx_type == "alpha":
        builder = AlphaComplex(
            points,
            alpha=args.max_scale / 2.0,
            max_dimension=args.max_dimension,
        )
    elif cpx_type == "sublevel":
        if grid is None:
            raise TDAError("--grid required for sublevel complex")
        builder = SublevelFiltration(grid, max_dimension=args.max_dimension)
    else:
        raise TDAError(f"Unknown complex type: {cpx_type}")

    return builder.build()


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_compute(args: argparse.Namespace) -> int:
    """Compute persistent homology of a point cloud or grid."""
    points = None
    grid = None
    if args.complex == "sublevel":
        if not args.grid:
            print("Error: --grid required for sublevel complex", file=sys.stderr)
            return 1
        grid = _parse_grid(args.grid)
    else:
        points = _parse_points(args.input)

    try:
        tree = _build_complex(args, points=points, grid=grid)
    except TDAError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

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


def cmd_stats(args: argparse.Namespace) -> int:
    """Show per-dimension statistics table for a diagram file."""
    diagrams = diagrams_from_json(open(args.input).read())
    print(statistics_table(diagrams))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Process multiple point clouds from a JSON file (list of lists of
    points) and output features."""
    from .batch import BatchProcessor

    with open(args.input) as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Error: batch input must be a JSON list of point clouds", file=sys.stderr)
        return 1

    point_clouds = data

    bp = BatchProcessor(
        point_clouds,
        max_scale=args.max_scale,
        max_dimension=args.max_dimension,
        min_persistence=args.min_persistence,
    )

    if args.output_format == "stats":
        results = bp.run_with_stats()
        print(json.dumps(results, indent=2, default=str))
    elif args.output_format == "vectors":
        vectors = bp.run_with_vectors(max_features=args.max_features)
        print(json.dumps(vectors, indent=2))
    else:  # diagrams
        results = bp.run()
        all_diagrams = []
        for diag_dict in results:
            for dim in sorted(diag_dict):
                all_diagrams.append(diag_dict[dim].to_dict())
        print(json.dumps({"diagrams": all_diagrams}, indent=2))

    return 0


def cmd_kernel(args: argparse.Namespace) -> int:
    """Compute persistence kernel matrix between diagram files."""
    import os

    files = args.files
    if len(files) < 2:
        print("Error: need at least two diagram files", file=sys.stderr)
        return 1

    # Load all diagrams (first dimension found in each file).
    diagrams: List[PersistenceDiagram] = []
    for fpath in files:
        d = diagrams_from_json(open(fpath).read())
        if not d:
            print(f"Warning: no diagrams in {fpath}, skipping", file=sys.stderr)
            continue
        # Use the dimension specified by --dimension, or the first available.
        if args.dimension is not None and args.dimension in d:
            diagrams.append(d[args.dimension])
        else:
            # Use first dimension.
            first_dim = sorted(d.keys())[0]
            diagrams.append(d[first_dim])

    if len(diagrams) < 2:
        print("Error: need at least two valid diagrams", file=sys.stderr)
        return 1

    if args.kernel == "pss":
        K = kernel_matrix(diagrams, pss_kernel, sigma=args.sigma)
    elif args.kernel == "pwg":
        K = kernel_matrix(diagrams, pwg_kernel, sigma=args.sigma)
    elif args.kernel == "fisher":
        K = kernel_matrix(diagrams, fisher_kernel, sigma=args.sigma, beta=args.beta)
    else:
        print(f"Unknown kernel: {args.kernel}", file=sys.stderr)
        return 1

    # Print kernel matrix.
    print("Kernel matrix:")
    header = "        " + "  ".join(
        os.path.basename(f)[:8] for f in files[:len(diagrams)]
    )
    print(header)
    for i, row in enumerate(K):
        label = os.path.basename(files[i])[:8]
        print(f"{label:>8}  " + "  ".join(f"{v:8.4f}" for v in row))

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"kernel": args.kernel, "matrix": K}, f, indent=2)

    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Generate or validate a configuration file."""
    if args.action == "generate":
        cfg = dict(DEFAULT_CONFIG)
        save_config(cfg, args.output or "tda_config.json")
        print(f"Default config written to {args.output or 'tda_config.json'}")
        return 0
    elif args.action == "validate":
        try:
            cfg = load_config(args.file)
            validate_config(cfg)
            print("Configuration is valid.")
            print(json.dumps(cfg, indent=2, default=str))
            return 0
        except (FileFormatError, Exception) as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            return 1
    return 1


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tda",
        description="Topological Data Analysis toolkit (v3.0)",
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose (debug) logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # compute
    p = sub.add_parser("compute", help="Compute persistent homology of a point cloud")
    p.add_argument("input", help="Input point cloud (JSON or CSV)")
    p.add_argument("--complex", choices=["rips", "weighted", "cech", "alpha", "sublevel"],
                   default="rips", help="Complex type")
    p.add_argument("--weights", help="Weights JSON file (for weighted complex)")
    p.add_argument("--grid", help="Grid JSON file (for sublevel complex)")
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

    # stats
    p = sub.add_parser("stats", help="Show per-dimension statistics table")
    p.add_argument("input", help="Diagram JSON file")
    p.set_defaults(func=cmd_stats)

    # batch
    p = sub.add_parser("batch", help="Process multiple point clouds")
    p.add_argument("input", help="JSON file containing list of point clouds")
    p.add_argument("--max-scale", type=float, default=float("inf"))
    p.add_argument("--max-dimension", "-d", type=int, default=1)
    p.add_argument("--min-persistence", type=float, default=0.0)
    p.add_argument("--output-format", choices=["diagrams", "stats", "vectors"],
                   default="stats", help="Output format")
    p.add_argument("--max-features", type=int, default=50,
                   help="Max features per dimension (for vectors)")
    p.set_defaults(func=cmd_batch)

    # kernel
    p = sub.add_parser("kernel", help="Compute persistence kernel matrix")
    p.add_argument("files", nargs="+", help="Diagram JSON files")
    p.add_argument("--kernel", choices=["pss", "pwg", "fisher"],
                   default="pss", help="Kernel type")
    p.add_argument("--dimension", "-d", type=int, default=None,
                   help="Homology dimension (default: first available)")
    p.add_argument("--sigma", type=float, default=1.0, help="Gaussian bandwidth")
    p.add_argument("--beta", type=float, default=1.0,
                   help="Fisher beta parameter")
    p.add_argument("--output", "-o", help="Save kernel matrix as JSON")
    p.set_defaults(func=cmd_kernel)

    # config
    p = sub.add_parser("config", help="Generate or validate a config file")
    p.add_argument("action", choices=["generate", "validate"],
                   help="Generate default config or validate existing")
    p.add_argument("--file", "-f", help="Config file to validate")
    p.add_argument("--output", "-o", help="Output file for generated config")
    p.set_defaults(func=cmd_config)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    # Strip the global --verbose before subcommand parsing.
    if argv is None:
        argv = sys.argv[1:]

    # Handle --verbose as a pre-flag.
    verbose = False
    clean_argv = []
    i = 0
    while i < len(argv):
        if argv[i] in ("--verbose", "-v"):
            verbose = True
        else:
            clean_argv.append(argv[i])
        i += 1

    args = parser.parse_args(clean_argv)

    # Configure logging level.
    log = get_logger(verbose=verbose)
    if verbose:
        log.setLevel(logging.DEBUG)

    try:
        return args.func(args)
    except TDAError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"File not found: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())