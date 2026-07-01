"""
Nonogram solver, generator, and player.

A nonogram is a logic puzzle where cells in a grid are filled or left blank
based on clues given for each row and column. This package provides:

- ``Board`` — the core grid data structure with clue representation
- ``Cell`` — three-state cell enum (UNKNOWN / EMPTY / FILLED)
- ``LineSolver`` — efficient per-line solver using overlap + constraint propagation
- ``Solver`` — full-board solver: constraint propagation + backtracking with MRV
- ``Generator`` — random puzzle generator with unique-solution check
- ``Player`` — interactive CLI player with hints
- ``PuzzleIO`` — file I/O (JSON, NON text format, PNG, SVG)
- ``Renderer`` — ANSI and HTML renderers
- ``DifficultyAnalyzer`` — puzzle difficulty grading
- ``presets`` — curated puzzle collection
- CLI interface via ``python -m nonogram.cli``
"""

from nonogram.board import Board, Cell
from nonogram.line_solver import LineSolver
from nonogram.solver import Solver, SolveResult
from nonogram.generator import Generator
from nonogram.player import Player
from nonogram.io import PuzzleIO
from nonogram.renderer import Renderer
from nonogram.analyzer import DifficultyAnalyzer
from nonogram.presets import PRESETS, get_preset, list_presets

__version__ = "2.0.0"
__all__ = [
    "Board",
    "Cell",
    "LineSolver",
    "Solver",
    "SolveResult",
    "Generator",
    "Player",
    "PuzzleIO",
    "Renderer",
    "DifficultyAnalyzer",
    "PRESETS",
    "get_preset",
    "list_presets",
]