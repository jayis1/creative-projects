#!/usr/bin/env python3
"""Example: Serialize and deserialize puzzles in JSON and text formats.

Demonstrates the round-trip serialization capabilities of the KenKen engine.

Usage:
    python3 examples/serialization.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenken_solver import KenKenGenerator, KenKenPuzzle, KenKenSolver, render_puzzle


def main() -> None:
    # Generate a puzzle
    gen = KenKenGenerator(size=4, seed=42)
    puzzle = gen.generate()
    print("Original puzzle:")
    print(render_puzzle(puzzle))
    print()

    # --- JSON round-trip ---
    json_str = puzzle.to_json()
    print("JSON output:")
    print(json_str[:200] + "..." if len(json_str) > 200 else json_str)
    print()

    puzzle_from_json = KenKenPuzzle.from_json(json_str)
    solver = KenKenSolver(puzzle_from_json)
    assert solver.solve_grid() is not None, "JSON round-trip failed!"
    print("✓ JSON round-trip: puzzle solves correctly")
    print()

    # --- Text format round-trip ---
    text = puzzle.to_text()
    print("Text format output:")
    print(text)
    puzzle_from_text = KenKenPuzzle.from_text(text)
    solver2 = KenKenSolver(puzzle_from_text)
    assert solver2.solve_grid() is not None, "Text round-trip failed!"
    print("✓ Text round-trip: puzzle solves correctly")
    print()

    # --- Text format with comments ---
    custom_text = """\
# A custom 3x3 KenKen puzzle
size: 3
# Row 0 cages
0,0 0,1 + 3
0,2 = 1
# Row 1 cages
1,0 1,1 + 5
1,2 = 1
# Row 2 cages
2,0 2,1 + 5
2,2 = 1
"""
    print("Custom text puzzle with comments:")
    custom_puzzle = KenKenPuzzle.from_text(custom_text)
    print(render_puzzle(custom_puzzle))
    solver3 = KenKenSolver(custom_puzzle)
    grid = solver3.solve_grid()
    if grid:
        print(f"Solution found: {grid}")
    else:
        print("No solution for custom puzzle")


if __name__ == "__main__":
    main()