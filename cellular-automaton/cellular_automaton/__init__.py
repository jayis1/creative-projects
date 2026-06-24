"""Cellular Automaton Simulator — 1D & 2D CA engine from scratch."""

from .engine import CellularAutomaton, StepResult
from .rules import Rule, ElementaryRule, GameOfLifeRule, CustomRule, RULES
from .patterns import PATTERNS, get_pattern, place_pattern, parse_rle
from .visualizer import render_ascii, render_svg, render_ppm

__all__ = [
    "CellularAutomaton",
    "StepResult",
    "Rule",
    "ElementaryRule",
    "GameOfLifeRule",
    "CustomRule",
    "RULES",
    "PATTERNS",
    "get_pattern",
    "place_pattern",
    "parse_rle",
    "render_ascii",
    "render_svg",
    "render_ppm",
]

__version__ = "1.0.0"