"""
maze_solver — A comprehensive maze generation, solving, and analysis toolkit.

This package provides multiple generation algorithms, solving algorithms,
rendering (ASCII, PNG, SVG), serialization, benchmarking, and analysis
capabilities for grid-based mazes.

Modules
-------
core        — Cell, Direction, Maze data structures
generators  — Maze generation algorithms
solvers     — Pathfinding algorithms
renderers   — ASCII, PNG, SVG rendering
analysis    — Statistics, difficulty scoring, maze comparison
io_utils    — JSON/TOML/YAML serialization, config loading
cli         — Command-line interface
"""

from .core import Cell, Direction, Maze, HEURISTICS
from .generators import GENERATOR_NAMES
from .solvers import SOLVER_NAMES
from .renderers import render_ascii, write_png, write_svg
from .analysis import analyze_maze, difficulty_score, compare_mazes

__version__ = "2.0.0"
__all__ = [
    "Cell",
    "Direction",
    "Maze",
    "HEURISTICS",
    "GENERATOR_NAMES",
    "SOLVER_NAMES",
    "render_ascii",
    "write_png",
    "write_svg",
    "analyze_maze",
    "difficulty_score",
    "compare_mazes",
    "__version__",
]