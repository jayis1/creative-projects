"""
Example: Solving a nonogram puzzle programmatically.

This example demonstrates the core API for creating, solving, and
analyzing nonogram puzzles.
"""
from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.analyzer import DifficultyAnalyzer

# Create a board from clues (the "heart" puzzle).
board = Board(
    row_clues=[[1], [3], [5], [3], [1]],
    col_clues=[[1], [3], [5], [3], [1]],
)

print("Puzzle (clues only):")
print(f"  Row clues: {board.row_clues}")
print(f"  Col clues: {board.col_clues}")
print()

# Solve it.
solver = Solver()
result = solver.solve(board)

if result.solved:
    print("Solution:")
    print(board.render())
    print(f"\nSolved in {result.iterations} iterations, "
          f"{result.backtracks} backtracks.")
else:
    print("No solution found!")

# Analyze difficulty.
analyzer = DifficultyAnalyzer()
info = analyzer.analyze(board)
print(f"\nDifficulty: {info['difficulty']} (score: {info['score']})")
print(f"Grid: {info['grid_size']}, filled ratio: {info['filled_ratio']}")

# Check uniqueness.
is_unique = solver.is_unique(Board([[1], [3], [5], [3], [1]],
                                    [[1], [3], [5], [3], [1]]))
print(f"Unique solution: {is_unique}")