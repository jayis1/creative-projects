"""
Example: Generating random nonogram puzzles.

Shows how to create puzzles of various sizes and difficulties.
"""
from nonogram.board import Board, Cell
from nonogram.generator import Generator
from nonogram.solver import Solver

# Generate a small easy puzzle.
gen = Generator(seed=42)
easy = gen.generate_easy(5)
print("Easy 5x5 puzzle:")
print(f"  Row clues: {easy.row_clues}")
print(f"  Col clues: {easy.col_clues}")
print(f"  Solution:\n{easy.render()}")
print()

# Generate a medium puzzle.
medium = gen.generate_medium(10)
print(f"Medium 10x10 puzzle generated: {medium.width}x{medium.height}")
print(f"  Unique: {Solver().is_unique(Board(medium.row_clues, medium.col_clues))}")
print()

# Generate a hard puzzle.
gen2 = Generator(seed=100)
hard = gen2.generate_hard(15)
print(f"Hard 15x15 puzzle generated: {hard.width}x{hard.height}")
print(f"  Unique: {Solver().is_unique(Board(hard.row_clues, hard.col_clues))}")

# Generate without uniqueness check (faster).
gen3 = Generator(seed=7)
fast = gen3.generate(8, 8, density=0.6, unique=False)
print(f"\nFast 8x8 (no uniqueness check): {fast.width}x{fast.height}")
print(f"  Solution:\n{fast.render()}")