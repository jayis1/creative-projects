"""Cellular Automaton Simulator — 1D & 2D CA engine from scratch.

A comprehensive cellular automaton engine supporting:
    * 256 Wolfram elementary 1D rules
    * 15 Life-like 2D rule variants
    * Custom callable rules
    * Multi-state CAs (Wireworld, Brian's Brain, Forest Fire, Cyclic, Immigration)
    * Bxx/Sxx notation parser
    * 19 builtin patterns + RLE parser
    * 4 boundary conditions
    * NumPy-vectorized stepping
    * Spacetime diagrams, animation frames, JSON serialization
    * Run statistics with cycle detection
    * Analysis tools (Wolfram classification, entropy, density, sweeps)
    * Config files (JSON/YAML/TOML)
    * Multi-format rendering (ASCII/ANSI/SVG/PPM/PNG)
    * argparse CLI
"""

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

# Multi-state CAs (optional, requires numpy which is always installed).
from .multistate import (
    MultiStateRule, WireworldRule, BriansBrainRule, ForestFireRule,
    CyclicRule, ImmigrationRule,
    MULTISTATE_RULES, get_multistate_rule, is_multistate_rule,
)

# Analysis tools.
from .analysis import (
    WolframClassification, classify_elementary_rule,
    shannon_entropy, spacetime_entropy,
    DensityReport, density_over_time,
    SweepResult, parameter_sweep,
    hamming_distance, lyapunov_proxy, local_diversity,
)

# Config system.
from .config import CAConfig

__all__ = [
    # Engine
    "CellularAutomaton",
    "StepResult",
    "CAStats",
    "Boundary",
    # Rules
    "Rule",
    "ElementaryRule",
    "GameOfLifeRule",
    "CustomRule",
    "RULES",
    "get_rule",
    "parse_bx_sx_notation",
    # Multi-state rules
    "MultiStateRule",
    "WireworldRule",
    "BriansBrainRule",
    "ForestFireRule",
    "CyclicRule",
    "ImmigrationRule",
    "MULTISTATE_RULES",
    "get_multistate_rule",
    "is_multistate_rule",
    # Patterns
    "PATTERNS",
    "get_pattern",
    "place_pattern",
    "parse_rle",
    # Visualizers
    "render_ascii",
    "render_svg",
    "render_ppm",
    "render_png",
    "render_ansi",
    "render_spacetime_ascii",
    "render_spacetime_svg",
    "render_animation_frames",
    # Vectorized
    "step_life_vectorized",
    "step_elementary_vectorized",
    "wolfram_rule_table",
    # Analysis
    "WolframClassification",
    "classify_elementary_rule",
    "shannon_entropy",
    "spacetime_entropy",
    "DensityReport",
    "density_over_time",
    "SweepResult",
    "parameter_sweep",
    "hamming_distance",
    "lyapunov_proxy",
    "local_diversity",
    # Config
    "CAConfig",
]

__version__ = "3.0.0"