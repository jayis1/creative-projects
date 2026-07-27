"""KenKen puzzle engine — generator, solver, verifier, analyzer, and hint system.

KenKen (also known as KenDoku, Calcudoku, or Mathdoku) is an arithmetical-logic
puzzle invented by Japanese mathematics teacher Tetsuya Miyamoto in 2004.

An *n × n* grid must be filled so that:

1. Each **row** contains the numbers 1–*n* exactly once (Latin square constraint).
2. Each **column** contains the numbers 1–*n* exactly once.
3. The grid is divided into **cages** — contiguous groups of cells, each with a
   target number and an operator (``+``, ``-``, ``*``, ``/``, or ``=`` for
   single-cell cages). The numbers in each cage must combine via the operator
   to produce the target.

This package provides:

* :class:`~kenken_solver.cage.Cage`               — a cage (cells, operator, target).
* :class:`~kenken_solver.puzzle.KenKenPuzzle`       — immutable puzzle representation.
* :class:`~kenken_solver.solver.KenKenSolver`       — backtracking solver with
  constraint propagation, MRV heuristic, forward checking, and naked-single
  propagation.
* :class:`~kenken_solver.generator.KenKenGenerator` — generates puzzles with
  guaranteed unique solutions.
* :class:`~kenken_solver.analyzer.PuzzleAnalyzer`   — analyzes difficulty and properties.
* :mod:`kenken_solver.render`                       — ASCII rendering utilities.
* :mod:`kenken_solver.cli`                           — command-line interface.
"""

from __future__ import annotations

from kenken_solver.cage import Cage, VALID_OPS
from kenken_solver.puzzle import KenKenPuzzle
from kenken_solver.types import Cell
from kenken_solver.solver import KenKenSolver
from kenken_solver.generator import KenKenGenerator
from kenken_solver.analyzer import PuzzleAnalyzer
from kenken_solver.render import (
    render_puzzle,
    render_solution,
    render_cage_map,
    render_solved_puzzle,
)
from kenken_solver.cli import main

__version__ = "3.0.0"

__all__ = [
    "Cage",
    "VALID_OPS",
    "KenKenPuzzle",
    "Cell",
    "KenKenSolver",
    "KenKenGenerator",
    "PuzzleAnalyzer",
    "render_puzzle",
    "render_solution",
    "render_cage_map",
    "render_solved_puzzle",
    "main",
    "__version__",
]