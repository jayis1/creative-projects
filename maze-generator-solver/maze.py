"""
Backward-compatibility wrapper for the original ``maze.py`` interface.

This module re-exports all public symbols from the :mod:`maze_solver`
package so that existing code using ``from maze import Maze`` continues
to work.  New code should import from :mod:`maze_solver` directly.
"""

from __future__ import annotations

# Re-export everything from the package.
from maze_solver.core import (
    Cell,
    Direction,
    Maze,
    _ALL_DIRECTIONS,
)
from maze_solver.heuristics import (
    HEURISTICS,
    HeuristicFn,
    chebyshev_distance,
    euclidean_distance,
    manhattan_distance,
)
from maze_solver.renderers import (
    _write_png_file as _write_png,
    render_ascii as _render,
)
from maze_solver.analysis import analyze_maze, compare_mazes, difficulty_score
from maze_solver.generators import GENERATOR_NAMES
from maze_solver.solvers import SOLVER_NAMES

__all__ = [
    "Cell",
    "Direction",
    "Maze",
    "HEURISTICS",
    "HeuristicFn",
    "manhattan_distance",
    "euclidean_distance",
    "chebyshev_distance",
    "analyze_maze",
    "compare_mazes",
    "difficulty_score",
    "GENERATOR_NAMES",
    "SOLVER_NAMES",
]


def main() -> None:
    """CLI entry point (delegates to maze_solver.cli)."""
    from maze_solver.cli import main as _main

    _main()


if __name__ == "__main__":
    main()