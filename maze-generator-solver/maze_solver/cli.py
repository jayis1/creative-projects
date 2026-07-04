"""
Command-line interface for maze-generator-solver.

Provides a rich argparse-based CLI with subcommands for generating,
solving, benchmarking, analyzing, and exporting mazes.  Also supports
loading configuration files (JSON/TOML/YAML) for declarative maze
generation.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional, Tuple

from .analysis import analyze_maze, compare_mazes, difficulty_score
from .core import HEURISTICS, Maze
from .heuristics import HEURISTICS as HEURISTICS_MAP
from .io_utils import load_config, maze_from_config
from .renderers import render_ascii, render_distance_map, write_png, write_svg
from .generators import GENERATOR_NAMES
from .solvers import SOLVER_NAMES

logger = logging.getLogger("maze_solver")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="maze-solver",
        description=(
            "Maze Generator & Solver — generate and solve mazes with "
            "multiple algorithms, braid support, PNG/SVG export, "
            "analysis, difficulty scoring, and configuration files."
        ),
    )
    parser.add_argument(
        "-W", "--width", type=int, default=20,
        help="Maze width (default 20)",
    )
    parser.add_argument(
        "-H", "--height", type=int, default=10,
        help="Maze height (default 10)",
    )
    parser.add_argument(
        "-g", "--generator", default="recursive_backtracking",
        choices=GENERATOR_NAMES,
        help="Generation algorithm (default: recursive_backtracking)",
    )
    parser.add_argument(
        "-s", "--solver", default="bfs",
        choices=SOLVER_NAMES,
        help="Solving algorithm (default: bfs)",
    )
    parser.add_argument(
        "--heuristic", default="manhattan",
        choices=list(HEURISTICS_MAP.keys()),
        help="Heuristic for A*/greedy/IDA* solvers (default: manhattan)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--solve", action="store_true",
        help="Solve the maze and display the path",
    )
    parser.add_argument(
        "--analyze", action="store_true",
        help="Print maze analysis statistics",
    )
    parser.add_argument(
        "--braid", type=float, nargs="?", const=1.0, default=None,
        help="Braid the maze (remove dead ends). Optional probability 0-1",
    )
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Benchmark all solvers on this maze",
    )
    parser.add_argument(
        "--heatmap", action="store_true",
        help="Print a distance heatmap from the start cell",
    )
    parser.add_argument(
        "--save", metavar="FILE",
        help="Save the maze to a JSON file",
    )
    parser.add_argument(
        "--load", metavar="FILE",
        help="Load a maze from a JSON file (ignores -g)",
    )
    parser.add_argument(
        "--png", metavar="FILE",
        help="Export the maze as a PNG image",
    )
    parser.add_argument(
        "--svg", metavar="FILE",
        help="Export the maze as an SVG image",
    )
    parser.add_argument(
        "--no-display", action="store_true",
        help="Don't print the maze",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Check if the maze is a perfect maze (connected, no loops)",
    )
    parser.add_argument(
        "--config", metavar="FILE",
        help="Load maze configuration from a JSON/TOML/YAML file",
    )
    parser.add_argument(
        "--difficulty", action="store_true",
        help="Print the maze difficulty score (0-100)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Set up logging.
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # --- Maze creation ---
    if args.config:
        logger.debug("Loading config from %s", args.config)
        config = load_config(args.config)
        maze = maze_from_config(config)
        # Allow CLI args to override config for output-related options.
        if not args.solve and not args.analyze and not args.benchmark:
            args.solve = config.get("solve", False)
            args.analyze = config.get("analyze", False)
    elif args.load:
        logger.debug("Loading maze from %s", args.load)
        maze = Maze.load(args.load)
    else:
        logger.debug(
            "Creating maze %dx%d with generator=%s seed=%s",
            args.width, args.height, args.generator, args.seed,
        )
        maze = Maze(args.width, args.height, seed=args.seed)
        maze.generate(args.generator)

    # --- Braid ---
    if args.braid is not None:
        n_braided = maze.braid(args.braid)
        print(f"Braided {n_braided} dead ends (probability={args.braid})")

    # --- Validate ---
    if args.validate:
        perfect = maze.is_perfect()
        print(f"Perfect maze: {perfect}")

    # --- Solve ---
    solution = None
    if args.solve or args.analyze or args.benchmark or args.png or args.svg:
        solution = maze.solve(args.solver, heuristic=args.heuristic)

    # --- Display ---
    if not args.no_display:
        if args.heatmap:
            print("--- Distance Heatmap ---")
            print(render_distance_map(maze))
        elif args.solve and solution:
            print(render_ascii(maze, solution=solution))
            print(f"\nSolution length: {len(solution)} steps")
        else:
            print(render_ascii(maze))

    # --- Benchmark ---
    if args.benchmark:
        print("\n--- Solver Benchmark ---")
        results = maze.benchmark()
        print(f"{'Algorithm':<16} {'Found':<6} {'Length':<8} "
              f"{'Explored':<10} {'Time (ms)':<10}")
        print("-" * 52)
        for r in results:
            print(
                f"{r['algorithm']:<16} {str(r['found']):<6} "
                f"{r['path_length']:<8} {r['explored']:<10} "
                f"{r['time_ms']:<10}"
            )

    # --- Analysis ---
    if args.analyze:
        stats = analyze_maze(maze)
        print("\n--- Maze Analysis ---")
        for key, val in stats.items():
            print(f"  {key}: {val}")

    # --- Difficulty ---
    if args.difficulty:
        score = difficulty_score(maze)
        print(f"Difficulty score: {score:.2f}/100")

    # --- Save ---
    if args.save:
        maze.save(args.save)
        print(f"Maze saved to {args.save}")

    # --- PNG export ---
    if args.png:
        write_png(maze, args.png, solution=solution)
        print(f"Maze exported to {args.png}")

    # --- SVG export ---
    if args.svg:
        write_svg(maze, args.svg, solution=solution)
        print(f"Maze exported to {args.svg}")