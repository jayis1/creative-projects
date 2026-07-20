#!/usr/bin/env python3
"""Command-line interface for the TSP solver.

Usage:
    python cli.py --algo christofides --refine two_opt --n 50 --seed 42
    python cli.py --load instance.tsp --algo held_karp
    python cli.py --compare --n 30 --seed 1
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from .instance import generate_instance, load_tsplib
from .solver import solve, list_algorithms


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Solve TSP instances with various algorithms.")
    parser.add_argument("--algo", default="nearest_neighbor", help="Algorithm name")
    parser.add_argument("--refine", default=None, help="Local search refinement: two_opt|three_opt|or_opt")
    parser.add_argument("--n", type=int, default=20, help="Number of cities (for random instance)")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--grid", type=int, default=1000, help="Coordinate grid size")
    parser.add_argument("--load", default=None, help="Load a TSPLIB-style .tsp file instead of random")
    parser.add_argument("--compare", action="store_true", help="Run all algorithms and compare")
    parser.add_argument("--list", action="store_true", help="List all available algorithms")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args(argv)

    if args.list:
        for name in list_algorithms():
            print(name)
        return 0

    if args.load:
        instance = load_tsplib(args.load)
    else:
        instance = generate_instance(args.n, seed=args.seed, grid=args.grid)

    if args.compare:
        results = {}
        for algo in list_algorithms():
            try:
                t0 = time.perf_counter()
                tour = solve(instance, algo, seed=args.seed)
                elapsed = time.perf_counter() - t0
                results[algo] = {"length": round(tour.length, 2), "time_s": round(elapsed, 4)}
            except Exception as exc:
                results[algo] = {"error": str(exc)}
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"{'Algorithm':<25} {'Length':>12} {'Time(s)':>10}")
            print("-" * 50)
            for algo, data in results.items():
                if "error" in data:
                    print(f"{algo:<25} {'ERROR':>12} {data['error'][:30]}")
                else:
                    print(f"{algo:<25} {data['length']:>12.2f} {data['time_s']:>10.4f}")
        return 0

    t0 = time.perf_counter()
    tour = solve(instance, args.algo, refine=args.refine, seed=args.seed)
    elapsed = time.perf_counter() - t0
    if args.json:
        print(json.dumps({
            "algorithm": args.algo,
            "refine": args.refine,
            "n": instance.n,
            "length": tour.length,
            "time_s": elapsed,
            "tour": list(tour.order),
        }, indent=2))
    else:
        print(f"Algorithm : {args.algo}")
        if args.refine:
            print(f"Refine    : {args.refine}")
        print(f"Cities    : {instance.n}")
        print(f"Length    : {tour.length:.4f}")
        print(f"Time(s)   : {elapsed:.4f}")
        print(f"Tour      : {list(tour.order)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())