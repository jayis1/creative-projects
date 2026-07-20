#!/usr/bin/env python3
"""Command-line interface for the TSP solver.

Usage examples::

    # Solve a 50-city instance with Christofides + 2-opt refinement
    tsp-solver --algo christofides --refine two_opt -n 50 --seed 42

    # Load a TSPLIB file and solve optimally
    tsp-solver --load instance.tsp --algo held_karp

    # Benchmark all algorithms
    tsp-solver --benchmark -n 15 --seed 42 --csv results.csv

    # Use a config file
    tsp-solver --config config.yaml --json

    # List algorithms by category
    tsp-solver --list --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

from .instance import generate_instance, load_tsplib
from .solver import solve, list_algorithms, list_algorithms_by_category
from .viz import ascii_plot
from .config import SolverConfig, default_config_path
from .logging_util import configure_logging, get_logger

_log = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Solve TSP instances with various algorithms.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Available algorithms: " + ", ".join(list_algorithms()),
    )
    parser.add_argument("--algo", default=None,
                        help="Algorithm name (default: nearest_neighbor)")
    parser.add_argument("--refine", default=None,
                        help="Local search refinement: two_opt|three_opt|or_opt")
    parser.add_argument("-n", "--n", type=int, default=None,
                        help="Number of cities (for random instance)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed")
    parser.add_argument("--grid", type=int, default=None,
                        help="Coordinate grid size")
    parser.add_argument("--distribution", default=None,
                        choices=["uniform", "cluster"],
                        help="Coordinate distribution for random instances")
    parser.add_argument("--load", default=None,
                        help="Load a TSPLIB-style .tsp file instead of random")
    parser.add_argument("--save", default=None,
                        help="Save the instance to a TSPLIB file")
    parser.add_argument("--compare", action="store_true", default=False,
                        help="Run all algorithms and compare")
    parser.add_argument("--list", action="store_true", default=False,
                        help="List all available algorithms")
    parser.add_argument("--list-categories", action="store_true", default=False,
                        help="List algorithms grouped by category")
    parser.add_argument("--json", action="store_true", default=False,
                        help="Output results as JSON")
    parser.add_argument("--csv", default=None, metavar="FILE",
                        help="Export benchmark results to a CSV file")
    parser.add_argument("--plot", action="store_true", default=False,
                        help="Print ASCII visualization of the tour")
    parser.add_argument("--benchmark", action="store_true", default=False,
                        help="Run BenchmarkSuite with quality ratios")
    parser.add_argument("--config", default=None, metavar="FILE",
                        help="Load configuration from a YAML or JSON file")
    parser.add_argument("--log-level", default=None,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity")
    parser.add_argument("--log-file", default=None, metavar="FILE",
                        help="Write logs to this file")
    parser.add_argument("--verbose", "-v", action="store_true", default=False,
                        help="Shorthand for --log-level INFO")
    parser.add_argument("--max-iter", type=int, default=None,
                        help="Max iterations for iterative algorithms")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Load config: explicit --config, or auto-discover default
    if args.config:
        try:
            cfg = SolverConfig.from_file(args.config)
        except (FileNotFoundError, ValueError, ImportError) as exc:
            print(f"Error loading config: {exc}", file=sys.stderr)
            return 2
    else:
        auto = default_config_path()
        if auto:
            _log.info("Auto-discovered config: %s", auto)
            try:
                cfg = SolverConfig.from_file(auto)
            except Exception:  # noqa: BLE001
                cfg = SolverConfig()
        else:
            cfg = SolverConfig()

    # Merge CLI args over config
    if args.algo:
        cfg.algorithm = args.algo
    if args.refine:
        cfg.refine = args.refine
    if args.n is not None:
        cfg.n = args.n
    if args.seed is not None:
        cfg.seed = args.seed
    if args.grid is not None:
        cfg.grid = args.grid
    if args.load:
        cfg.load = args.load
    if args.json:
        cfg.output = "json"
    if args.plot:
        cfg.plot = True
    if args.benchmark:
        cfg.benchmark = True
    if args.compare:
        cfg.compare = True
    if args.list:
        cfg.list_algos = True
    if args.verbose:
        cfg.log_level = "INFO"
    if args.log_level:
        cfg.log_level = args.log_level
    if args.log_file:
        cfg.log_file = args.log_file
    if args.max_iter:
        cfg.max_iter = args.max_iter

    configure_logging(cfg.log_level, cfg.log_file)

    if args.list or args.list_categories:
        if args.list_categories:
            cats = list_algorithms_by_category()
            for cat, algos in cats.items():
                print(f"\n{cat}:")
                for a in algos:
                    print(f"  {a}")
        else:
            for name in list_algorithms():
                print(name)
        return 0

    # Load or generate instance
    if cfg.load:
        try:
            instance = load_tsplib(cfg.load)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error loading TSPLIB file: {exc}", file=sys.stderr)
            return 2
    else:
        instance = generate_instance(
            cfg.n, seed=cfg.seed, grid=cfg.grid,
            distribution=args.distribution or "uniform",
        )

    # Save instance if requested
    if args.save:
        from .instance import save_tsplib
        save_tsplib(instance, args.save)
        print(f"Instance saved to {args.save}")

    if cfg.benchmark:
        from .benchmark import BenchmarkSuite
        suite = BenchmarkSuite()
        suite.run(instance, seed=cfg.seed)
        if cfg.output == "json":
            print(suite.to_json())
        else:
            print(suite.summary())
            best = suite.best()
            if best:
                print(f"\nBest: {best.algorithm} (length={best.length:.2f})")
        if args.csv:
            suite.to_csv(args.csv)
            print(f"CSV exported to {args.csv}", file=sys.stderr)
        return 0

    if cfg.compare:
        results = {}
        for algo in list_algorithms():
            try:
                t0 = time.perf_counter()
                tour = solve(instance, algo, seed=cfg.seed)
                elapsed = time.perf_counter() - t0
                results[algo] = {"length": round(tour.length, 2), "time_s": round(elapsed, 4)}
            except Exception as exc:  # noqa: BLE001
                results[algo] = {"error": str(exc)}
        if cfg.output == "json":
            print(json.dumps(results, indent=2))
        else:
            print(f"{'Algorithm':<28} {'Length':>12} {'Time(s)':>10}")
            print("-" * 54)
            for algo, data in results.items():
                if "error" in data:
                    print(f"{algo:<28} {'ERROR':>12} {data['error'][:30]}")
                else:
                    print(f"{algo:<28} {data['length']:>12.2f} {data['time_s']:>10.4f}")
        return 0

    # Single solve
    algo_kwargs = dict(cfg.algorithm_params.get(cfg.algorithm, {}))
    if cfg.max_iter and cfg.algorithm in (
        "simulated_annealing", "iterated_local_search", "lin_kernighan",
    ):
        algo_kwargs.setdefault("max_iter", cfg.max_iter)

    t0 = time.perf_counter()
    try:
        tour = solve(instance, cfg.algorithm, refine=cfg.refine, seed=cfg.seed, **algo_kwargs)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    elapsed = time.perf_counter() - t0

    if cfg.output == "json":
        print(json.dumps({
            "algorithm": cfg.algorithm,
            "refine": cfg.refine,
            "n": instance.n,
            "length": tour.length,
            "time_s": elapsed,
            "tour": list(tour.order),
        }, indent=2))
    else:
        print(f"Algorithm : {cfg.algorithm}")
        if cfg.refine:
            print(f"Refine    : {cfg.refine}")
        print(f"Instance  : {instance.name}")
        print(f"Cities    : {instance.n}")
        print(f"Length    : {tour.length:.4f}")
        print(f"Time(s)   : {elapsed:.4f}")
        print(f"Tour      : {list(tour.order)}")
    if cfg.plot:
        print()
        print(ascii_plot(instance, tour))
    return 0


if __name__ == "__main__":
    sys.exit(main())