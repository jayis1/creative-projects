"""CLI entry point for the CSP solver."""

import argparse
import json
import sys
import time

from .csp import CSP, Variable, Constraint
from .solver import CSPSolver, SolveResult
from .problems import (
    sudoku_csp,
    n_queens_csp,
    graph_coloring_csp,
    cryptarithm_csp,
    format_sudoku_solution,
    format_queens_solution,
    format_cryptarithm_solution,
)


def parse_grid(grid_str: str) -> list:
    """Parse a flat 81-character string into a 9x9 grid."""
    if len(grid_str) != 81:
        raise ValueError(f"Expected 81 characters, got {len(grid_str)}")
    digits = [int(c) for c in grid_str]
    return [digits[i*9:(i+1)*9] for i in range(9)]


def main():
    parser = argparse.ArgumentParser(
        description="Constraint Satisfaction Problem Solver"
    )
    parser.add_argument(
        "problem",
        choices=["sudoku", "queens", "coloring", "cryptarithm"],
        help="Type of problem to solve",
    )
    parser.add_argument("--grid", type=str, default=None,
                        help="Sudoku grid as 81-char string (0=empty)")
    parser.add_argument("--n", type=int, default=8,
                        help="Board size for N-Queens (default: 8)")
    parser.add_argument("--colors", type=int, default=3,
                        help="Number of colors for graph coloring (default: 3)")
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

    args = parser.parse_args()

    # Build the CSP
    if args.problem == "sudoku":
        if args.grid:
            grid = parse_grid(args.grid)
        else:
            # Hard puzzle (AI Escargot - one of the hardest known)
            grid_str = (
                "100007090030020008009600500005300900010080002600004000"
                "300000010040000007007000300"
            )
            grid = parse_grid(grid_str)
        csp = sudoku_csp(grid)
    elif args.problem == "queens":
        csp = n_queens_csp(args.n)
    elif args.problem == "coloring":
        # Default: Australia map coloring
        edges = [
            ("WA", "NT"), ("WA", "SA"), ("NT", "SA"),
            ("NT", "Q"), ("SA", "Q"), ("SA", "NSW"),
            ("SA", "V"), ("Q", "NSW"), ("NSW", "V"),
        ]
        csp = graph_coloring_csp(edges, args.colors)
    elif args.problem == "cryptarithm":
        if not args.words or not args.result:
            # Default: SEND + MORE = MONEY
            args.words = ["SEND", "MORE"]
            args.result = "MONEY"
        csp = cryptarithm_csp(args.words, args.result)

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
            "elapsed": elapsed,
        }
        if result.stats:
            output["stats"] = {
                "assignments_tried": result.stats.assignments_tried,
                "backtracks": result.stats.backtracks,
            }
        print(json.dumps(output, indent=2))
    else:
        print(f"Problem: {args.problem}")
        print(f"Satisfiable: {result.is_satisfiable}")
        print(f"Method: {result.method}")
        print(f"Time: {elapsed:.4f}s")
        if result.stats:
            print(f"Assignments tried: {result.stats.assignments_tried}")
            print(f"Backtracks: {result.stats.backtracks}")

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
            else:
                for var in sorted(result.assignment):
                    print(f"  {var} = {result.assignment[var]}")


if __name__ == "__main__":
    main()