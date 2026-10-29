"""Command-line polyomino exact-cover demonstration."""
import argparse
from tiling import TilingSolver, render

# Twenty monominoes provide a compact, deterministic demonstration.
PIECES = [[(0,0)] for _ in range(20)]

def main():
    parser = argparse.ArgumentParser(description="Find exact polyomino tilings with bit-mask Algorithm X.")
    parser.add_argument("--limit", type=int, default=1, help="maximum solutions to find")
    parser.add_argument("--demo", action="store_true", help="solve and print a 4x5 example")
    args = parser.parse_args()
    board = [(r,c) for r in range(4) for c in range(5)]
    solver = TilingSolver(board, PIECES)
    solutions = solver.solve(args.limit)
    print(f"solutions found: {len(solutions)}")
    if solutions:
        print(render(board, solutions[0]))
    return 0 if solutions else 1

if __name__ == "__main__":
    raise SystemExit(main())
