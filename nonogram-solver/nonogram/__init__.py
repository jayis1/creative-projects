"""
Nonogram solver, generator, and player.

A nonogram is a logic puzzle where cells in a grid are filled or left blank
based on clues given for each row and column. This package provides:

- ``Solver`` — constraint propagation + backtracking line solver
- ``Generator`` — random puzzle generator with unique-solution check
- ``Player`` — interactive CLI player
- ``Board`` — the core grid data structure with clue representation
- ``LineSolver`` — efficient per-line solver using overlap + constraint propagation
- CLI interface via ``python -m nonogram.cli``
"""

from nonogram.board import Board, Cell
from nonogram.line_solver import LineSolver
from nonogram.solver import Solver
from nonogram.generator import Generator
from nonogram.player import Player

__version__ = "1.0.0"
__all__ = [
    "Board",
    "Cell",
    "LineSolver",
    "Solver",
    "Generator",
    "Player",
]