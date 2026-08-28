"""Sokoban solver package."""

from .analysis import assignment_lower_bound, render_explain_overlay
from .config import RuntimeConfig, load_config
from .io import LevelEntry, load_level_text, parse_level_pack
from .levels import BUILTIN_LEVELS, get_level, list_levels
from .models import Board, SolveResult, SolutionStep, Stats
from .parser import parse_level
from .solver import SokobanSolver, solve_level_pack

__all__ = [
    "BUILTIN_LEVELS",
    "Board",
    "LevelEntry",
    "RuntimeConfig",
    "SolveResult",
    "SolutionStep",
    "Stats",
    "SokobanSolver",
    "assignment_lower_bound",
    "get_level",
    "list_levels",
    "load_config",
    "load_level_text",
    "parse_level",
    "parse_level_pack",
    "render_explain_overlay",
    "solve_level_pack",
]
