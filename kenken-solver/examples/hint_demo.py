#!/usr/bin/env python3
"""Example: Use hints to progressively solve a puzzle.

Demonstrates the hint system for interactive puzzle solving.

Usage:
    python3 examples/hint_demo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenken_solver import KenKenGenerator, KenKenSolver


def main() -> None:
    gen = KenKenGenerator(size=5, seed=123)
    puzzle = gen.generate()
    solver = KenKenSolver(puzzle)

    print("Generated a 5x5 KenKen puzzle.")
    print(f"Number of cages: {len(puzzle.cages)}")
    print()

    # Start with an empty grid and progressively fill it using hints
    known = {}
    print("Progressively filling the puzzle using hints:\n")

    for step in range(25):  # 5x5 = 25 cells
        hints = solver.get_hint(known, num=1)
        if not hints:
            print("No more hints available (puzzle may be unsolvable with current state).")
            break
        cell, val = hints[0]
        known[cell] = val
        print(f"  Step {step + 1}: Cell ({cell[0]},{cell[1]}) = {val}")

    # Display the final grid
    print(f"\nFilled {len(known)} cells:")
    n = puzzle.size
    for r in range(n):
        row = [str(known.get((r, c), ".")) for c in range(n)]
        print("  " + " ".join(row))

    # Verify it's a complete solution
    assert len(known) == n * n, "Could not fill all cells!"
    # Check Latin square property
    for r in range(n):
        row_vals = sorted(known[(r, c)] for c in range(n))
        assert row_vals == list(range(1, n + 1)), f"Row {r} invalid"
    for c in range(n):
        col_vals = sorted(known[(r, c)] for r in range(n))
        assert col_vals == list(range(1, n + 1)), f"Col {c} invalid"
    print("\n✓ All cells filled correctly — valid solution!")


if __name__ == "__main__":
    main()