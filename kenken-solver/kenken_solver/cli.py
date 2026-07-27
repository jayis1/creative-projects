"""Command-line interface for the KenKen engine.

Provides the following subcommands:

* ``generate`` — generate a new puzzle
* ``solve``     — solve a puzzle from a file
* ``verify``    — verify a puzzle has a unique solution
* ``analyze``   — analyze puzzle difficulty and properties
* ``batch``     — batch-generate multiple puzzles
* ``hint``      — get hints for a partially solved puzzle
* ``interactive`` — interactive solving session

Global options
--------------

``--verbose`` / ``-v``
    Enable debug-level logging.
``--quiet`` / ``-q``
    Suppress all output except errors.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional

from kenken_solver.analyzer import PuzzleAnalyzer
from kenken_solver.config import GenerationConfig
from kenken_solver.generator import KenKenGenerator
from kenken_solver.puzzle import KenKenPuzzle
from kenken_solver.render import (
    render_cage_map,
    render_puzzle,
    render_solved_puzzle,
    render_solution,
)
from kenken_solver.solver import KenKenSolver
from kenken_solver.types import Cell

logger = logging.getLogger("kenken_solver")


def _setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure logging based on verbosity flags."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def _load_puzzle(path: str) -> KenKenPuzzle:
    """Load a puzzle from a JSON or text file (auto-detected by content)."""
    with open(path) as f:
        content = f.read()
    if content.strip().startswith("{"):
        return KenKenPuzzle.from_json(content)
    return KenKenPuzzle.from_text(content)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="kenken",
        description="KenKen puzzle generator, solver, and verifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Generate a 5x5 puzzle
  kenken generate --size 5

  # Generate a hard 6x6 puzzle with seed
  kenken generate --size 6 --difficulty hard --seed 42

  # Generate from a config file
  kenken generate --config puzzle_config.json

  # Solve a puzzle from a JSON file
  kenken solve --input puzzle.json

  # Generate and immediately solve
  kenken generate --size 4 --solve

  # Verify a puzzle has a unique solution
  kenken verify --input puzzle.json

  # Analyze puzzle difficulty
  kenken analyze --input puzzle.json

  # Batch generate 10 puzzles
  kenken batch --size 5 --count 10 --output-dir puzzles/

  # Get a hint for a partially solved puzzle
  kenken hint --input puzzle.json --cells 0,0=3 1,1=2

  # Interactive solving mode
  kenken interactive --input puzzle.json
""",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress non-error output"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # -- generate --
    gen = sub.add_parser("generate", help="Generate a new KenKen puzzle")
    gen.add_argument(
        "--size", type=int, default=5, help="Grid size (default 5)"
    )
    gen.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default="medium",
    )
    gen.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    gen.add_argument(
        "--max-cage-size", type=int, default=4, help="Maximum cage size"
    )
    gen.add_argument(
        "--no-singletons",
        action="store_true",
        help="Avoid single-cell cages",
    )
    gen.add_argument(
        "--solve", action="store_true", help="Also print the solution"
    )
    gen.add_argument(
        "--output", "-o", type=str, default=None, help="Write puzzle to file"
    )
    gen.add_argument(
        "--format",
        choices=["grid", "json", "text", "both"],
        default="grid",
    )
    gen.add_argument(
        "--config",
        type=str,
        default=None,
        help="Load generation parameters from a JSON/YAML config file",
    )
    gen.add_argument(
        "--max-attempts", type=int, default=100,
        help="Maximum generation attempts before giving up",
    )

    # -- solve --
    sol = sub.add_parser("solve", help="Solve a puzzle from JSON or text")
    sol.add_argument(
        "--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)"
    )
    sol.add_argument(
        "--all", action="store_true", help="Find all solutions"
    )
    sol.add_argument(
        "--stats", action="store_true", help="Print solver statistics"
    )
    sol.add_argument(
        "--max-solutions", type=int, default=None,
        help="Maximum solutions to find (default 1, or 999999 with --all)",
    )

    # -- verify --
    ver = sub.add_parser(
        "verify", help="Verify a puzzle has a unique solution"
    )
    ver.add_argument(
        "--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)"
    )

    # -- analyze --
    ana = sub.add_parser(
        "analyze", help="Analyze puzzle difficulty and properties"
    )
    ana.add_argument(
        "--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)"
    )

    # -- batch --
    bat = sub.add_parser("batch", help="Batch generate multiple puzzles")
    bat.add_argument("--size", type=int, default=5)
    bat.add_argument(
        "--count", type=int, default=10, help="Number of puzzles to generate"
    )
    bat.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default="medium",
    )
    bat.add_argument("--seed", type=int, default=None)
    bat.add_argument(
        "--output-dir", "-o", type=str, required=True,
        help="Output directory",
    )
    bat.add_argument(
        "--format", choices=["json", "text"], default="json"
    )
    bat.add_argument(
        "--no-singletons", action="store_true", help="Avoid single-cell cages"
    )
    bat.add_argument(
        "--max-cage-size", type=int, default=4, help="Maximum cage size"
    )

    # -- hint --
    hnt = sub.add_parser(
        "hint", help="Get hints for a partially solved puzzle"
    )
    hnt.add_argument(
        "--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)"
    )
    hnt.add_argument(
        "--cells", nargs="*",
        default=[], help="Pre-filled cells as R,C=V pairs",
    )
    hnt.add_argument(
        "--num", type=int, default=1, help="Number of hints to return"
    )

    # -- interactive --
    inter = sub.add_parser(
        "interactive", help="Interactive solving session"
    )
    inter.add_argument(
        "--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)"
    )

    return parser


# -- command handlers --------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    """Handle the ``generate`` subcommand."""
    if args.config:
        cfg = GenerationConfig.from_file(args.config)
        # CLI args override config file values
        if args.size != 5:
            cfg.size = args.size
        if args.difficulty != "medium":
            cfg.difficulty = args.difficulty
        if args.seed is not None:
            cfg.seed = args.seed
        if args.max_cage_size != 4:
            cfg.max_cage_size = args.max_cage_size
        if args.no_singletons:
            cfg.allow_singletons = False
    else:
        cfg = GenerationConfig(
            size=args.size,
            difficulty=args.difficulty,
            seed=args.seed,
            max_cage_size=args.max_cage_size,
            allow_singletons=not args.no_singletons,
            max_attempts=args.max_attempts,
            format=args.format,
            output=args.output,
        )

    gen_obj = KenKenGenerator(
        size=cfg.size,
        seed=cfg.seed,
        max_cage_size=cfg.max_cage_size,
        difficulty=cfg.difficulty,
        allow_singletons=cfg.allow_singletons,
    )
    puzzle = gen_obj.generate(max_attempts=cfg.max_attempts)

    if cfg.format in ("grid", "both"):
        print(render_puzzle(puzzle))
        print()
    if cfg.format == "text":
        print(puzzle.to_text())
    if cfg.format in ("json", "both"):
        print(puzzle.to_json())
    if cfg.output:
        with open(cfg.output, "w") as f:
            f.write(puzzle.to_json())
        print(f"Puzzle written to {cfg.output}", file=sys.stderr)
    if args.solve:
        solver = KenKenSolver(puzzle)
        grid = solver.solve_grid()
        if grid:
            print("Solution:")
            print(render_solved_puzzle(puzzle, grid))
        else:
            print("No solution found.")
    return 0


def cmd_solve(args: argparse.Namespace) -> int:
    """Handle the ``solve`` subcommand."""
    puzzle = _load_puzzle(args.input)
    if args.max_solutions is not None:
        max_sol = args.max_solutions
    elif args.all:
        max_sol = 999999
    else:
        max_sol = 1
    solver = KenKenSolver(puzzle, max_solutions=max_sol)
    solver.solve()
    if not solver.solutions:
        print("No solution found.")
        return 1
    for i, soln in enumerate(solver.solutions):
        grid = [
            [soln[(r, c)] for c in range(puzzle.size)]
            for r in range(puzzle.size)
        ]
        if args.all or max_sol > 1:
            print(f"Solution {i + 1}:")
        print(render_solution(grid))
    if args.stats:
        print(f"\nSolver stats: {solver.stats}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Handle the ``verify`` subcommand."""
    puzzle = _load_puzzle(args.input)
    solver = KenKenSolver(puzzle, max_solutions=2)
    solver.solve()
    if len(solver.solutions) == 1:
        print("UNIQUE — puzzle has exactly one solution.")
        return 0
    elif len(solver.solutions) == 0:
        print("UNSOLVABLE — puzzle has no solution.")
        return 1
    else:
        print(
            f"NOT UNIQUE — puzzle has at least {len(solver.solutions)} solutions."
        )
        return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handle the ``analyze`` subcommand."""
    puzzle = _load_puzzle(args.input)
    analyzer = PuzzleAnalyzer(puzzle)
    results = analyzer.analyze()
    print(json.dumps(results, indent=2))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Handle the ``batch`` subcommand."""
    os.makedirs(args.output_dir, exist_ok=True)
    stats = {"generated": 0, "failed": 0, "times": []}
    for i in range(args.count):
        seed = args.seed + i if args.seed is not None else None
        gen_obj = KenKenGenerator(
            size=args.size,
            seed=seed,
            difficulty=args.difficulty,
            max_cage_size=args.max_cage_size,
            allow_singletons=not args.no_singletons,
        )
        t0 = time.time()
        try:
            puzzle = gen_obj.generate()
        except RuntimeError:
            stats["failed"] += 1
            continue
        elapsed = time.time() - t0
        stats["times"].append(elapsed)
        stats["generated"] += 1
        ext = "json" if args.format == "json" else "txt"
        path = os.path.join(args.output_dir, f"puzzle_{i:03d}.{ext}")
        with open(path, "w") as f:
            if args.format == "json":
                f.write(puzzle.to_json())
            else:
                f.write(puzzle.to_text())
        if not args.quiet:
            print(f"  [{i + 1}/{args.count}] {path} ({elapsed:.3f}s)")
    print(
        f"Generated {stats['generated']}/{args.count} puzzles "
        f"({stats['failed']} failed)"
    )
    if stats["times"]:
        avg_t = sum(stats["times"]) / len(stats["times"])
        print(f"Average generation time: {avg_t:.3f}s")
        print(f"Total time: {sum(stats['times']):.3f}s")
    return 0


def cmd_hint(args: argparse.Namespace) -> int:
    """Handle the ``hint`` subcommand."""
    puzzle = _load_puzzle(args.input)
    partial: Dict[Cell, int] = {}
    for spec in args.cells:
        cell_str, val_str = spec.split("=")
        r_str, c_str = cell_str.split(",")
        partial[(int(r_str), int(c_str))] = int(val_str)
    solver = KenKenSolver(puzzle)
    try:
        hints = solver.get_hint(partial, num=args.num)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not hints:
        print(
            "No hints available (puzzle may be unsolvable with given cells)."
        )
        return 1
    for cell, val in hints:
        print(f"Cell ({cell[0]},{cell[1]}) = {val}")
    return 0


def cmd_interactive(args: argparse.Namespace) -> int:
    """Handle the ``interactive`` subcommand.

    Provides a simple interactive session where the user can fill in cells,
    get hints, check validity, and view the current grid state.
    """
    puzzle = _load_puzzle(args.input)
    solver = KenKenSolver(puzzle)
    n = puzzle.size

    # Solve once to have the solution available for hint/validation
    solution = solver.solve_grid()
    if solution is None:
        print("This puzzle has no solution!")
        return 1

    # Current user grid (0 = empty)
    grid: List[List[int]] = [[0] * n for _ in range(n)]

    print("=== KenKen Interactive Solver ===")
    print(f"Puzzle size: {n}x{n}")
    print()
    print(render_puzzle(puzzle))
    print()
    print("Commands:")
    print("  fill R C V    — fill cell (R,C) with value V")
    print("  clear R C     — clear cell (R,C)")
    print("  hint [N]      — get N hints (default 1)")
    print("  check         — check if current grid is valid")
    print("  show          — show the puzzle")
    print("  state         — show current grid state")
    print("  solution      — reveal the full solution")
    print("  quit / exit   — exit the session")
    print()

    while True:
        try:
            line = input("kenken> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("quit", "exit"):
            break
        elif cmd == "fill":
            if len(parts) != 4:
                print("Usage: fill R C V")
                continue
            try:
                r, c, v = int(parts[1]), int(parts[2]), int(parts[3])
            except ValueError:
                print("Invalid numbers")
                continue
            if not (0 <= r < n and 0 <= c < n and 1 <= v <= n):
                print(f"Values must be 1..{n}, rows/cols 0..{n - 1}")
                continue
            grid[r][c] = v
            print(f"Filled ({r},{c}) = {v}")
        elif cmd == "clear":
            if len(parts) != 3:
                print("Usage: clear R C")
                continue
            try:
                r, c = int(parts[1]), int(parts[2])
            except ValueError:
                print("Invalid numbers")
                continue
            if not (0 <= r < n and 0 <= c < n):
                print(f"Rows/cols must be 0..{n - 1}")
                continue
            grid[r][c] = 0
            print(f"Cleared ({r},{c})")
        elif cmd == "hint":
            num = 1
            if len(parts) > 1:
                try:
                    num = int(parts[1])
                except ValueError:
                    print("Usage: hint [N]")
                    continue
            partial = {
                (r, c): grid[r][c]
                for r in range(n)
                for c in range(n)
                if grid[r][c] != 0
            }
            try:
                hints = solver.get_hint(partial, num=num)
            except ValueError as e:
                print(f"Error: {e}")
                continue
            if not hints:
                print("No hints available (check for conflicts).")
            else:
                for cell, val in hints:
                    print(f"  Cell ({cell[0]},{cell[1]}) = {val}")
        elif cmd == "check":
            # Check row/col constraints
            errors = []
            for r in range(n):
                vals = [grid[r][c] for c in range(n) if grid[r][c] != 0]
                if len(vals) != len(set(vals)):
                    errors.append(f"Row {r} has duplicates")
            for c in range(n):
                vals = [grid[r][c] for r in range(n) if grid[r][c] != 0]
                if len(vals) != len(set(vals)):
                    errors.append(f"Col {c} has duplicates")
            # Check cage constraints
            assignment = {
                (r, c): grid[r][c]
                for r in range(n)
                for c in range(n)
                if grid[r][c] != 0
            }
            for cage in puzzle.cages:
                if not cage.satisfied(assignment):
                    errors.append(
                        f"Cage {cage.label} ({cage.op}{cage.target}) "
                        f"not satisfied"
                    )
            if errors:
                print("Issues found:")
                for e in errors:
                    print(f"  - {e}")
            else:
                print("No conflicts detected so far.")
        elif cmd == "show":
            print(render_puzzle(puzzle))
        elif cmd == "state":
            print("Current grid:")
            for r in range(n):
                row_str = " ".join(
                    str(grid[r][c]) if grid[r][c] != 0 else "." for c in range(n)
                )
                print(f"  {row_str}")
        elif cmd == "solution":
            print("Solution:")
            print(render_solved_puzzle(puzzle, solution))
        else:
            print(f"Unknown command: {cmd}")

    print("Goodbye!")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point.

    Returns the exit code (0 for success, non-zero for error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    _setup_logging(
        verbose=getattr(args, "verbose", False),
        quiet=getattr(args, "quiet", False),
    )

    handlers = {
        "generate": cmd_generate,
        "solve": cmd_solve,
        "verify": cmd_verify,
        "analyze": cmd_analyze,
        "batch": cmd_batch,
        "hint": cmd_hint,
        "interactive": cmd_interactive,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


__all__ = ["main", "build_parser"]