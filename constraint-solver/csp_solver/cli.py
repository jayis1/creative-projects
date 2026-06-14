"""
CLI entry point for the CSP solver.

Provides a command-line interface for solving various CSP problems
including Sudoku, N-Queens, graph coloring, cryptarithms, Latin
squares, and magic squares.
"""

import argparse
import json
import sys
import time

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


def parse_grid(grid_str: str) -> list:
    """Parse a flat 81-character string into a 9x9 grid.

    The string should contain digits 0-9 where 0 represents an empty cell.
    Whitespace and dots are treated as 0 (empty).
    """
    # Remove whitespace and dots
    cleaned = grid_str.replace(" ", "").replace(".", "0")
    if len(cleaned) != 81:
        raise ValueError(f"Expected 81 characters, got {len(cleaned)}")
    digits = [int(c) for c in cleaned]
    return [digits[i*9:(i+1)*9] for i in range(9)]


def main():
    parser = argparse.ArgumentParser(
        description="Constraint Satisfaction Problem Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Solve a hard Sudoku
  python -m csp_solver sudoku --grid "100007090030020008..."

  # Generate and solve a random Sudoku
  python -m csp_solver sudoku --generate --difficulty hard

  # Solve 8-Queens
  python -m csp_solver queens --n 8

  # Count all 8-Queens solutions
  python -m csp_solver queens --n 8 --count

  # Solve cryptarithm
  python -m csp_solver cryptarithm --words SEND MORE --result MONEY

  # Solve Latin Square
  python -m csp_solver latin --n 5

  # Solve Magic Square
  python -m csp_solver magic --n 3

  # Compare strategies on N-Queens
  python -m csp_solver queens --n 8 --compare
        """,
    )
    parser.add_argument(
        "problem",
        choices=["sudoku", "queens", "coloring", "cryptarithm", "latin", "magic"],
        help="Type of problem to solve",
    )
    parser.add_argument("--grid", type=str, default=None,
                        help="Sudoku grid as 81-char string (0=empty, '.'=empty)")
    parser.add_argument("--generate", action="store_true",
                        help="Generate a random Sudoku puzzle")
    parser.add_argument("--difficulty", type=str, default="medium",
                        choices=["easy", "medium", "hard"],
                        help="Sudoku difficulty (default: medium)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for Sudoku generation")
    parser.add_argument("--n", type=int, default=8,
                        help="Board size for N-Queens/Latin Square/Magic Square (default: 8)")
    parser.add_argument("--colors", type=int, default=3,
                        help="Number of colors for graph coloring (default: 3)")
    parser.add_argument("--map", type=str, default="australia",
                        choices=["australia", "us"],
                        help="Map for graph coloring (default: australia)")
    parser.add_argument("--words", nargs="+", default=None,
                        help="Addend words for cryptarithm")
    parser.add_argument("--result", type=str, default=None,
                        help="Result word for cryptarithm")
    parser.add_argument("--no-mac", action="store_true",
                        help="Disable MAC (use basic backtracking)")
    parser.add_argument("--no-mrv", action="store_true",
                        help="Disable MRV heuristic")
    parser.add_argument("--no-lcv", action="store_true",
                        help="Disable LCV heuristic")
    parser.add_argument("--timeout", type=float, default=None,
                        help="Timeout in seconds")
    parser.add_argument("--json", action="store_true",
                        help="Output result as JSON")
    parser.add_argument("--count", action="store_true",
                        help="Count all solutions (N-Queens)")
    parser.add_argument("--compare", action="store_true",
                        help="Compare solving strategies")

    args = parser.parse_args()

    # Build the CSP
    csp = None
    problem_label = args.problem
    extra_info = {}

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
            # Hard puzzle (AI Escargot)
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
            for i, sol in enumerate(solutions[:5]):  # Show first 5
                print(f"\nSolution {i+1}:")
                print(format_queens_solution(sol, args.n))
            if len(solutions) > 5:
                print(f"... and {len(solutions) - 5} more")
            return

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

    # Compare strategies if requested
    if args.compare:
        print(f"Comparing strategies on {args.problem} (n={args.n})...")
        results = compare_strategies(csp, timeout=args.timeout or 30)
        print(f"\n{'Strategy':<25} {'Time':>10} {'Assignments':>12} {'Backtracks':>12} {'Found':>6}")
        print("-" * 70)
        for r in results:
            t = f"{r['time'][0]:.4f}s" if r['time'] else "N/A"
            a = str(r['assignments']) if r['assignments'] else "N/A"
            b = str(r['backtracks']) if r['backtracks'] else "N/A"
            f = "Yes" if r['satisfiable'] else "No"
            print(f"{r['strategy']:<25} {t:>10} {a:>12} {b:>12} {f:>6}")
        return

    # Solve
    solver = CSPSolver(
        use_mrv=not args.no_mrv,
        use_lcv=not args.no_lcv,
        use_mac=not args.no_mac,
        timeout=args.timeout,
    )

    start = time.time()
    result = solver.solve(csp)
    elapsed = time.time() - start

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
            if args.problem == "sudoku":
                print(format_sudoku_solution(result.assignment))
            elif args.problem == "queens":
                print(format_queens_solution(result.assignment, args.n))
            elif args.problem == "cryptarithm":
                print(format_cryptarithm_solution(
                    result.assignment, args.words, args.result
                ))
            elif args.problem == "latin":
                print(format_latin_square(result.assignment, args.n))
            elif args.problem == "magic":
                print(format_magic_square(result.assignment, args.n))
            else:
                for var in sorted(result.assignment):
                    print(f"  {var} = {result.assignment[var]}")


if __name__ == "__main__":
    main()