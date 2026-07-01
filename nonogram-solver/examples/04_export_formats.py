"""
Example: Exporting puzzles to various formats.

Shows PNG, SVG, HTML, and JSON export.
"""
from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.io import PuzzleIO
from nonogram.renderer import Renderer

# Solve the heart puzzle.
board = Board([[1], [3], [5], [3], [1]], [[1], [3], [5], [3], [1]])
Solver().solve(board)

# Export to JSON.
PuzzleIO.save_json(board, "heart_solved.json")
print("Saved JSON: heart_solved.json")

# Export to NON format.
PuzzleIO.save_non(board, "heart_solved.non")
print("Saved NON: heart_solved.non")

# Export to PNG.
PuzzleIO.save_png(board, "heart.png", cell_size=30)
print("Saved PNG: heart.png")

# Export to SVG.
PuzzleIO.save_svg(board, "heart.svg", cell_size=30)
print("Saved SVG: heart.svg")

# Export to HTML.
html = Renderer.html(board, title="Heart Puzzle")
with open("heart.html", "w") as f:
    f.write(html)
print("Saved HTML: heart.html")

# ANSI colored output.
print("\nANSI colored:")
print(Renderer.ansi(board))