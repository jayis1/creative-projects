#!/usr/bin/env python3
"""Backward-compatible shim for the legacy single-file ``kenken.py``.

All functionality has been refactored into the :mod:`kenken_solver` package.
This thin wrapper re-exports the public API so that existing code using
``from kenken import ...`` continues to work.

New code should import from ``kenken_solver`` directly.
"""

from __future__ import annotations

import sys
import os

# Ensure the package directory is importable when this file is run directly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kenken_solver.cage import Cage, VALID_OPS  # noqa: E402,F401
from kenken_solver.puzzle import KenKenPuzzle  # noqa: E402,F401
from kenken_solver.types import Cell  # noqa: E402,F401
from kenken_solver.solver import KenKenSolver  # noqa: E402,F401
from kenken_solver.generator import KenKenGenerator  # noqa: E402,F401
from kenken_solver.analyzer import PuzzleAnalyzer  # noqa: E402,F401
from kenken_solver.render import (  # noqa: E402,F401
    render_puzzle,
    render_solution,
    render_cage_map,
    render_solved_puzzle,
)
from kenken_solver.config import GenerationConfig  # noqa: E402,F401
from kenken_solver.cli import main  # noqa: E402,F401

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
    "GenerationConfig",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())