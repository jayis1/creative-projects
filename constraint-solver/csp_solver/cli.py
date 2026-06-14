"""
CLI entry point for the CSP solver.

Provides a command-line interface for solving various CSP problems
including Sudoku, N-Queens, graph coloring, cryptarithms, Latin
squares, magic squares, job shop scheduling, and more.

Supports configuration files, verbose output, JSON export, and
strategy comparison.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from .csp import CSP, Variable, Constraint
from .solver import CSPSolver, SolveResult, compare_strategies
from .problems import (
    sudoku_csp,
    generate_sudoku,
    n_queens_csp,
    graph_coloring_csp,
    cryptarithm_csp,
    latin_square_csp,
    magic_square_csp,
    format_sudoku_solution,
    format_queens_solution,
    format_cryptarithm_solution,
    format_latin_square,
    format_magic_square,
    AUSTRALIA_EDGES,
    US_REGIONS_EDGES,
)
from .problems_extra import (
    job_shop_csp,
    format_schedule,
    graph_csp_from_edges,
)
from .config import SolverConfig
from .logging_utils import SolverProgress, setup_logging
from .visualization import (
    render_sudoku,
    render_queens,
    render_graph_coloring,
    render_cryptarithm,
    render_latin_square,
    render_magic_square,
)
from .serialization import save_csp, save_solution, export_csp, export_solution

logger = logging.getLogger("csp_solver")


def parse_grid(grid_str: str) -> list:
    """Parse a flat 81-character string into a 9x9 grid.

    The string should contain digits 0-9 where 0 represents an empty cell.
    Whitespace and dots are treated as 0 (empty).
    """
    cleaned = grid_str.replace(" ", "").replace(".", "0")
    if len(cleaned) != 81:
        raise ValueError(f"Expected 81 characters, got {len(cleaned)}")
    digits = [int(c) for c in cleaned]
    return [digits[i*9:(i+1)*9] for i in range(9)]


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="csp-solver",
        description="Constraint Satisfaction Problem Solver — solve Sudoku, N-Queens, "
                    "graph coloring, cryptarithms, Latin squares, magic squares, and more.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Solve a hard Sudoku
  csp-solver sudoku --grid "100007090030020008009600500005300900010080002600004000300000010040000007007000300"

  # Generate and solve a random Sudoku
  csp-solver sudoku --generate --difficulty hard --seed 42

  # Solve 8-Queens with verbose output
  csp-solver queens --n 8 -vv

  # Count all 8-Queens solutions
  csp-solver queens --n 8 --count

  # Solve cryptarithm with JSON output
  csp-solver cryptarithm --words SEND MORE --result MONEY --json

  # Solve with a config file
  csp-solver queens --n 8 --config my_config.json

  # Compare strategies
  csp-solver queens --n 8 --compare

  # Solve job shop scheduling
  csp-solver schedule --jobs "J1:3:R1,J2:2:R1,J3:4:R2" --horizon 10

  # Disable heuristics for comparison
  csp-solver sudoku --no-mac --no-mrv --no-lcv
        """,
    )

    # Global options
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG)",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to a JSON/TOML config file for solver settings",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Path to save solution as JSON",
    )
    parser.add_argument(
        "--export-csp", type=str, default=None,
        help="Path to export the CSP definition as JSON",
    )

    subparsers = parser.add_subparsers(dest="problem", help="Problem type to solve")

    # Sudoku subcommand
    sudoku_p = subparsers.add_parser("sudoku", help="Solve a Sudoku puzzle")
    sudoku_p.add_argument("--grid", type=str, default=None,
                          help="Sudoku grid as 81-char string (0=empty)")
    sudoku_p.add_argument("--generate", action="store_true",
                          help="Generate a random Sudoku puzzle")
    sudoku_p.add_argument("--difficulty", type=str, default="medium",
                          choices=["easy", "medium", "hard"],
                          help="Sudoku difficulty (default: medium)")
    sudoku_p.add_argument("--seed", type=int, default=None,
                          help="Random seed for Sudoku generation")

    # Queens subcommand
    queens_p = subparsers.add_parser("queens", help="Solve N-Queens problem")
    queens_p.add_argument("--n", type=int, default=8,
                          help="Board size (default: 8)")
    queens_p.add_argument("--count", action="store_true",
                          help="Count all solutions")

    # Coloring subcommand
    color_p = subparsers.add_parser("coloring", help="Solve graph coloring")
    color_p.add_argument("--colors", type=int, default=3,
                         help="Number of colors (default: 3)")
    color_p.add_argument("--map", type=str, default="australia",
                         choices=["australia", "us"],
                         help="Map to color (default: australia)")

    # Cryptarithm subcommand
    crypto_p = subparsers.add_parser("cryptarithm", help="Solve cryptarithm puzzle")
    crypto_p.add_argument("--words", nargs="+", default=None,
                          help="Addend words (e.g., SEND MORE)")
    crypto_p.add_argument("--result", type=str, default=None,
                          help="Result word (e.g., MONEY)")

    # Latin square subcommand
    latin_p = subparsers.add_parser("latin", help="Solve Latin Square")
    latin_p.add_argument("--n", type=int, default=5,
                         help="Square size (default: 5)")

    # Magic square subcommand
    magic_p = subparsers.add_parser("magic", help="Solve Magic Square")
    magic_p.add_argument("--n", type=int, default=3,
                         help="Square size (default: 3)")

    # Schedule subcommand
    sched_p = subparsers.add_parser("schedule", help="Solve job shop scheduling")
    sched_p.add_argument("--jobs", type=str, required=True,
                         help="Jobs as 'name:duration:resource,...' "
                              "(e.g., 'J1:3:R1,J2:2:R1,J3:4:R2')")

    # Solver options (applied to all subcommands)
    for p in [sudoku_p, queens_p, color_p, crypto_p, latin_p, magic_p, sched_p]:
        p.add_argument("--no-mac", action="store_true",
                        help="Disable MAC (use basic backtracking)")
        p.add_argument("--no-mrv", action="store_true",
                        help="Disable MRV heuristic")
        p.add_argument("--no-lcv", action="store_true",
                        help="Disable LCV heuristic")
        p.add_argument("--timeout", type=float, default=None,
                        help="Timeout in seconds")
        p.add_argument("--json", action="store_true",
                        help="Output result as JSON")
        p.add_argument("--compare", action="store_true",
                        help="Compare solving strategies")
        p.add_argument("--pretty", action="store_true",
                        help="Use pretty rendering (box drawing)")

    return parser


def parse_jobs(jobs_str: str) -> dict:
    """Parse a jobs string like 'J1:3:R1,J2:2:R1' into a dict."""
    jobs = {}
    for part in jobs_str.split(","):
        part = part.strip()
        if not part:
            continue
        fields = part.split(":")
        if len(fields) != 3:
            raise ValueError(f"Invalid job spec: {part!r} (expected name:duration:resource)")
        name = fields[0].strip()
        duration = int(fields[1].strip())
        resource = fields[2].strip()
        jobs[name] = (duration, resource)
    return jobs


def setup_from_args(args) -> CSPSolver:
    """Create a CSPSolver from parsed CLI arguments."""
    # Load config file if specified
    config = None
    if args.config:
        config = SolverConfig.from_file(args.config)

    # Build solver kwargs, CLI overrides config
    kwargs = {}
    if config:
        kwargs = {
            "use_mrv": config.use_mrv,
            "use_degree": config.use_degree,
            "use_lcv": config.use_lcv,
            "use_forward_check": config.use_forward_check,
            "use_mac": config.use_mac,
            "preprocess_ac3": config.preprocess_ac3,
            "timeout": config.timeout,
        }

    # CLI flags override config
    kwargs["use_mrv"] = not getattr(args, "no_mrv", False) if hasattr(args, "no_mrv") else kwargs.get("use_mrv", True)
    kwargs["use_lcv"] = not getattr(args, "no_lcv", False) if hasattr(args, "no_lcv") else kwargs.get("use_lcv", True)
    kwargs["use_mac"] = not getattr(args, "no_mac", False) if hasattr(args, "no_mac") else kwargs.get("use_mac", True)
    if getattr(args, "timeout", None) is not None:
        kwargs["timeout"] = args.timeout

    return CSPSolver(**kwargs)


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command line arguments. Uses sys.argv if None.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Setup logging from verbosity
    if args.verbose >= 2:
        setup_logging("DEBUG")
    elif args.verbose >= 1:
        setup_logging("INFO")
    else:
        setup_logging("WARNING")

    if not args.problem:
        parser.print_help()
        return 1

    # Build the CSP and problem metadata
    csp = None
    problem_label = args.problem
    extra_info = {}

    try:
        if args.problem == "sudoku":
            if args.generate:
                puzzle, solution = generate_sudoku(args.difficulty, args.seed)
                csp = sudoku_csp(puzzle)
                extra_info["puzzle"] = format_sudoku_solution(
                    {f"R{i}C{j}": puzzle[i][j] or 0
                     for i in range(9) for j in range(9)}
                )
            elif args.grid:
                grid = parse_grid(args.grid)
                csp = sudoku_csp(grid)
            else:
                grid_str = (
                    "100007090030020008009600500005300900010080002600004000"
                    "300000010040000007007000300"
                )
                grid = parse_grid(grid_str)
                csp = sudoku_csp(grid)

        elif args.problem == "queens":
            csp = n_queens_csp(args.n)
            if args.count:
                solver = CSPSolver(use_mac=True, timeout=args.timeout or 120)
                solutions = solver.solve_all(csp, max_solutions=10000)
                print(f"N={args.n}: {len(solutions)} solutions found")
                for i, sol in enumerate(solutions[:5]):
                    print(f"\nSolution {i+1}:")
                    if getattr(args, "pretty", False):
                        print(render_queens(sol, args.n))
                    else:
                        print(format_queens_solution(sol, args.n))
                if len(solutions) > 5:
                    print(f"... and {len(solutions) - 5} more")
                return 0

        elif args.problem == "coloring":
            if args.map == "australia":
                edges = AUSTRALIA_EDGES
                extra_info["map"] = "Australia"
            else:
                edges = US_REGIONS_EDGES
                extra_info["map"] = "US Regions"
            csp = graph_coloring_csp(edges, args.colors)

        elif args.problem == "cryptarithm":
            if not args.words or not args.result:
                args.words = ["SEND", "MORE"]
                args.result = "MONEY"
            csp = cryptarithm_csp(args.words, args.result)
            extra_info["equation"] = " + ".join(args.words) + " = " + args.result

        elif args.problem == "latin":
            csp = latin_square_csp(args.n)

        elif args.problem == "magic":
            csp = magic_square_csp(args.n)

        elif args.problem == "schedule":
            jobs = parse_jobs(args.jobs)
            csp = job_shop_csp(jobs)
            extra_info["jobs"] = jobs

        else:
            print(f"Unknown problem type: {args.problem}", file=sys.stderr)
            return 1

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Export CSP if requested
    if args.export_csp:
        save_csp(csp, args.export_csp)
        print(f"CSP exported to {args.export_csp}")

    # Compare strategies if requested
    if args.compare:
        print(f"Comparing strategies on {args.problem}...")
        results = compare_strategies(csp, timeout=args.timeout or 30)
        print(f"\n{'Strategy':<25} {'Time':>10} {'Assignments':>12} {'Backtracks':>12} {'Found':>6}")
        print("-" * 70)
        for r in results:
            t = f"{r['time'][0]:.4f}s" if r['time'] else "N/A"
            a = str(r['assignments']) if r['assignments'] else "N/A"
            b = str(r['backtracks']) if r['backtracks'] else "N/A"
            f = "Yes" if r['satisfiable'] else "No"
            print(f"{r['strategy']:<25} {t:>10} {a:>12} {b:>12} {f:>6}")
        return 0

    # Solve
    solver = setup_from_args(args)
    logger.info("Solving %s with method: %s", problem_label, solver._method_string())

    start = time.time()
    result = solver.solve(csp)
    elapsed = time.time() - start

    # Output results
    if args.json:
        output = {
            "problem": args.problem,
            "satisfiable": result.is_satisfiable,
            "assignment": result.assignment,
            "method": result.method,
            "elapsed": round(elapsed, 4),
        }
        if result.stats:
            output["stats"] = result.stats.to_dict()
        print(json.dumps(output, indent=2))
    else:
        print(f"Problem: {problem_label}")
        if "map" in extra_info:
            print(f"Map: {extra_info['map']}")
        if "equation" in extra_info:
            print(f"Equation: {extra_info['equation']}")
        print(f"Satisfiable: {result.is_satisfiable}")
        print(f"Method: {result.method}")
        print(f"Time: {elapsed:.4f}s")
        if result.stats:
            print(f"Assignments tried: {result.stats.assignments_tried}")
            print(f"Backtracks: {result.stats.backtracks}")
            if result.stats.domain_prunes:
                print(f"Domain prunes: {result.stats.domain_prunes}")

        if result.assignment:
            print("\nSolution:")
            pretty = getattr(args, "pretty", False)
            if args.problem == "sudoku":
                renderer = render_sudoku if pretty else format_sudoku_solution
                print(renderer(result.assignment))
            elif args.problem == "queens":
                renderer = render_queens if pretty else format_queens_solution
                print(renderer(result.assignment, args.n))
            elif args.problem == "coloring":
                if pretty:
                    edges = AUSTRALIA_EDGES if args.map == "australia" else US_REGIONS_EDGES
                    print(render_graph_coloring(result.assignment, edges))
                else:
                    for var in sorted(result.assignment):
                        print(f"  {var} = {result.assignment[var]}")
            elif args.problem == "cryptarithm":
                renderer = render_cryptarithm if pretty else format_cryptarithm_solution
                if pretty:
                    print(renderer(result.assignment, args.words, args.result))
                else:
                    print(renderer(result.assignment, args.words, args.result))
            elif args.problem == "latin":
                renderer = render_latin_square if pretty else format_latin_square
                print(renderer(result.assignment, args.n))
            elif args.problem == "magic":
                renderer = render_magic_square if pretty else format_magic_square
                print(renderer(result.assignment, args.n))
            elif args.problem == "schedule":
                jobs = extra_info.get("jobs", {})
                print(format_schedule(result.assignment, jobs))
            else:
                for var in sorted(result.assignment):
                    print(f"  {var} = {result.assignment[var]}")

    # Save solution if requested
    if args.output:
        save_solution(
            result.assignment or {},
            args.output,
            stats=result.stats,
            method=result.method,
            problem_type=args.problem,
        )
        if not args.json:
            print(f"\nSolution saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())