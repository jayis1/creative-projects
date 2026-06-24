"""Cellular Automaton Simulator — 1D & 2D CA engine from scratch."""

from .engine import CellularAutomaton, StepResult, CAStats, Boundary
from .rules import (
    Rule, ElementaryRule, GameOfLifeRule, CustomRule, RULES,
    get_rule, parse_bx_sx_notation,
)
from .patterns import PATTERNS, get_pattern, place_pattern, parse_rle
from .visualizer import (
    render_ascii, render_svg, render_ppm, render_png, render_ansi,
    render_spacetime_ascii, render_spacetime_svg, render_animation_frames,
)
from .vectorized import (
    step_life_vectorized, step_elementary_vectorized, wolfram_rule_table,
)

__all__ = [
    "CellularAutomaton",
    "StepResult",
    "CAStats",
    "Boundary",
    "Rule",
    "ElementaryRule",
    "GameOfLifeRule",
    "CustomRule",
    "RULES",
    "get_rule",
    "parse_bx_sx_notation",
    "PATTERNS",
    "get_pattern",
    "place_pattern",
    "parse_rle",
    "render_ascii",
    "render_svg",
    "render_ppm",
    "render_png",
    "render_ansi",
    "render_spacetime_ascii",
    "render_spacetime_svg",
    "render_animation_frames",
    "step_life_vectorized",
    "step_elementary_vectorized",
    "wolfram_rule_table",
]

__version__ = "2.0.0"