"""
L-System Renderer — A formal grammar-based generative art engine.

Implements Lindenmayer Systems (L-systems) with:
  - Parametric L-systems (rules with parameters)
  - Stochastic L-systems (probabilistic rule selection)
  - Context-sensitive L-systems
  - Multiple rendering backends (SVG, ASCII, terminal)
  - Built-in presets for classic fractals and plant models
  - Custom color mapping, gradients, and styling
  - Turtle graphics interpretation with 2D extensions
  - JSON import/export of L-system definitions
  - SVG animation (growth animation) support
  - Perturbation/noise for organic variation
  - Batch rendering of all presets
  - String statistics and analysis
  - Iteration-by-iteration growth tracking
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union


def _escape_xml(text: str) -> str:
    """Escape XML special characters in a string."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------

class RenderBackend(Enum):
    SVG = auto()
    ASCII = auto()
    TERMINAL = auto()


class ColorMode(Enum):
    """Determines how segments are colored."""
    DEPTH = auto()       # Color by turtle stack depth
    POSITION = auto()   # Color by normalized position (gradient)
    SEGMENT_INDEX = auto()  # Color by segment order (rainbow)
    SINGLE = auto()     # Single color for all segments


@dataclass
class TurtleState:
    """Snapshot of the turtle's state for push/pop operations."""
    x: float = 0.0
    y: float = 0.0
    angle: float = 90.0  # degrees; 0 = right, 90 = up
    step_size: float = 5.0
    angle_increment: float = 25.0
    line_width: float = 1.0
    color: str = "#000000"
    depth: int = 0


@dataclass
class Segment:
    """A single line segment produced by the turtle interpreter."""
    x1: float
    y1: float
    x2: float
    y2: float
    color: str = "#000000"
    width: float = 1.0
    depth: int = 0
    segment_index: int = 0  # Order index for color modes


@dataclass
class LSystemRule:
    """A single production rule.

    Attributes:
        predecessor: The symbol this rule replaces (e.g. 'F').
        successor: The replacement string (e.g. 'F+F--F+F').
        condition: Optional Python expression that must evaluate to True
                    for the rule to apply (parametric L-systems).
        probability: Weight for stochastic rule selection (default 1.0).
        left_context: Left context for context-sensitive rules.
        right_context: Right context for context-sensitive rules.
    """
    predecessor: str
    successor: str
    condition: Optional[str] = None
    probability: float = 1.0
    left_context: Optional[str] = None
    right_context: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        d = {
            "predecessor": self.predecessor,
            "successor": self.successor,
        }
        if self.condition is not None:
            d["condition"] = self.condition
        if self.probability != 1.0:
            d["probability"] = self.probability
        if self.left_context is not None:
            d["left_context"] = self.left_context
        if self.right_context is not None:
            d["right_context"] = self.right_context
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LSystemRule":
        """Deserialize from dictionary."""
        return cls(
            predecessor=d["predecessor"],
            successor=d["successor"],
            condition=d.get("condition"),
            probability=d.get("probability", 1.0),
            left_context=d.get("left_context"),
            right_context=d.get("right_context"),
        )


@dataclass
class LSystemDefinition:
    """Complete definition of an L-system.

    Attributes:
        name: Human-readable name.
        axiom: The initial string / starting state.
        rules: List of production rules.
        angle: Default turning angle in degrees.
        step_size: Default forward step length.
        iterations: Default number of iterations to apply.
        line_width: Default line width for rendering.
        colors: Optional mapping from depth -> color string.
        color_mode: How to assign colors to segments.
        gradient: Optional (start_color, end_color) for position/segment gradients.
        perturbation: Std deviation of random angle perturbation in degrees (0 = none).
        step_perturbation: Std deviation of random step size perturbation (0 = none).
        background: Background color for rendering.
    """
    name: str
    axiom: str
    rules: List[LSystemRule]
    angle: float = 25.0
    step_size: float = 5.0
    iterations: int = 4
    line_width: float = 1.0
    colors: Dict[int, str] = field(default_factory=dict)
    color_mode: str = "depth"  # "depth", "position", "segment_index", "single"
    gradient: Optional[Tuple[str, str]] = None  # (start_color, end_color)
    perturbation: float = 0.0
    step_perturbation: float = 0.0
    background: str = "#ffffff"

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        d = {
            "name": self.name,
            "axiom": self.axiom,
            "rules": [r.to_dict() for r in self.rules],
            "angle": self.angle,
            "step_size": self.step_size,
            "iterations": self.iterations,
            "line_width": self.line_width,
        }
        if self.colors:
            # JSON keys must be strings
            d["colors"] = {str(k): v for k, v in self.colors.items()}
        d["color_mode"] = self.color_mode
        if self.gradient:
            d["gradient"] = list(self.gradient)
        if self.perturbation != 0.0:
            d["perturbation"] = self.perturbation
        if self.step_perturbation != 0.0:
            d["step_perturbation"] = self.step_perturbation
        if self.background != "#ffffff":
            d["background"] = self.background
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LSystemDefinition":
        """Deserialize from dictionary."""
        colors_raw = d.get("colors", {})
        colors = {int(k): v for k, v in colors_raw.items()} if colors_raw else {}
        gradient_raw = d.get("gradient")
        gradient = tuple(gradient_raw) if gradient_raw else None
        return cls(
            name=d["name"],
            axiom=d["axiom"],
            rules=[LSystemRule.from_dict(r) for r in d.get("rules", [])],
            angle=d.get("angle", 25.0),
            step_size=d.get("step_size", 5.0),
            iterations=d.get("iterations", 4),
            line_width=d.get("line_width", 1.0),
            colors=colors,
            color_mode=d.get("color_mode", "depth"),
            gradient=gradient,
            perturbation=d.get("perturbation", 0.0),
            step_perturbation=d.get("step_perturbation", 0.0),
            background=d.get("background", "#ffffff"),
        )

    def to_json(self, path: str) -> None:
        """Save definition to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json(cls, path: str) -> "LSystemDefinition":
        """Load definition from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Color utilities
# ---------------------------------------------------------------------------

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert a hex color string to an (R, G, B) tuple.

    Handles both '#RRGGBB' and 'RRGGBB' formats.
    Returns (0, 0, 0) for unparseable input.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (0, 0, 0)
    try:
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
    except ValueError:
        return (0, 0, 0)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert an (R, G, B) tuple to a hex color string."""
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def lerp_color(color1: str, color2: str, t: float) -> str:
    """Linearly interpolate between two hex colors.

    Args:
        color1: Start color in '#RRGGBB' format.
        color2: End color in '#RRGGBB' format.
        t: Interpolation factor (0.0 = color1, 1.0 = color2).

    Returns:
        Interpolated color in '#RRGGBB' format.
    """
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return rgb_to_hex(r, g, b)


def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """Convert HSL (h in [0,360], s,l in [0,1]) to RGB (0-255 each)."""
    h = h % 360
    s = max(0.0, min(1.0, s))
    l = max(0.0, min(1.0, l))
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def rainbow_color(index: int, total: int) -> str:
    """Generate a rainbow color for a segment index."""
    if total <= 0:
        return "#ffffff"
    hue = (index / total) * 360
    r, g, b = hsl_to_rgb(hue, 0.85, 0.55)
    return rgb_to_hex(r, g, b)


# ---------------------------------------------------------------------------
# L-system engine (string rewriting)
# ---------------------------------------------------------------------------

class LSystemEngine:
    """Core engine that performs L-system string rewriting.

    Supports:
      - Deterministic rules
      - Stochastic rules (probability weights)
      - Context-sensitive rules (left/right context matching)
      - Parametric rules (conditions evaluated as Python expressions)
    """

    def __init__(self, definition: LSystemDefinition, seed: Optional[int] = None):
        self.definition = definition
        self.rng = random.Random(seed)
        self._param_context: Dict[str, Any] = {}

    def _build_rule_map(self) -> Dict[str, List[LSystemRule]]:
        """Index rules by predecessor symbol for O(1) lookup."""
        rule_map: Dict[str, List[LSystemRule]] = defaultdict(list)
        for rule in self.definition.rules:
            rule_map[rule.predecessor].append(rule)
        return rule_map

    def _match_context(
        self, rule: LSystemRule, symbol: str, string: str, pos: int
    ) -> bool:
        """Check left and right context for context-sensitive rules.

        Context matching ignores bracket symbols [] when scanning for neighbors,
        matching the standard L-system context-sensitive semantics.
        """
        if rule.left_context is not None:
            # Walk left skipping brackets
            depth = 0
            chars_matched = 0
            i = pos - 1
            left_str = ""
            while i >= 0 and chars_matched < len(rule.left_context):
                ch = string[i]
                if ch == "]":
                    depth += 1
                elif ch == "[":
                    depth -= 1
                    if depth < 0:
                        depth = 0
                elif depth == 0:
                    left_str = ch + left_str
                    chars_matched += 1
                i -= 1
            if left_str != rule.left_context:
                return False

        if rule.right_context is not None:
            depth = 0
            chars_matched = 0
            i = pos + 1
            right_str = ""
            while i < len(string) and chars_matched < len(rule.right_context):
                ch = string[i]
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth < 0:
                        depth = 0
                elif depth == 0:
                    right_str += ch
                    chars_matched += 1
                i += 1
            if right_str != rule.right_context:
                return False

        return True

    def _evaluate_condition(self, rule: LSystemRule) -> bool:
        """Evaluate a parametric rule's condition safely."""
        if rule.condition is None:
            return True
        try:
            # Restricted eval: only allow basic math operations
            safe_builtins = {
                "abs": abs, "min": min, "max": max,
                "int": int, "float": float, "round": round,
            }
            return bool(eval(rule.condition, {"__builtins__": safe_builtins}, self._param_context))
        except Exception:
            return False

    def _select_rule(
        self, rules: List[LSystemRule], symbol: str, string: str, pos: int
    ) -> Optional[LSystemRule]:
        """Select the appropriate rule for a symbol, considering context,
        conditions, and probability."""
        matching: List[LSystemRule] = []
        for rule in rules:
            if not self._match_context(rule, symbol, string, pos):
                continue
            if not self._evaluate_condition(rule):
                continue
            matching.append(rule)

        if not matching:
            return None
        if len(matching) == 1:
            return matching[0]

        # Stochastic selection using weighted sampling
        total_weight = sum(r.probability for r in matching)
        if total_weight <= 0:
            return matching[0]
        roll = self.rng.uniform(0, total_weight)
        cumulative = 0.0
        for rule in matching:
            cumulative += rule.probability
            if roll <= cumulative:
                return rule
        return matching[-1]

    def iterate(self, iterations: Optional[int] = None) -> str:
        """Apply production rules for the given number of iterations.

        Returns the produced string.
        """
        n = iterations if iterations is not None else self.definition.iterations
        if n < 0:
            raise ValueError(f"Iterations must be non-negative, got {n}")
        if n > 50:
            # Safety guard: warn about potentially huge strings
            estimated_length = len(self.definition.axiom) * (max(len(r.successor) for r in self.definition.rules) if self.definition.rules else 2) ** n
            if estimated_length > 10_000_000:
                raise ValueError(
                    f"Iteration {n} would produce an estimated {estimated_length:,} characters. "
                    f"Reduce iterations or use a simpler L-system."
                )

        current = self.definition.axiom
        rule_map = self._build_rule_map()

        for _ in range(n):
            next_str_parts: List[str] = []
            for pos, symbol in enumerate(current):
                if symbol in rule_map:
                    rule = self._select_rule(
                        rule_map[symbol], symbol, current, pos
                    )
                    if rule is not None:
                        next_str_parts.append(rule.successor)
                    else:
                        next_str_parts.append(symbol)
                else:
                    next_str_parts.append(symbol)
            current = "".join(next_str_parts)

        return current

    def iterate_steps(self, iterations: Optional[int] = None) -> List[str]:
        """Apply production rules, returning the string at each iteration step.

        Useful for growth animations and debugging.
        """
        n = iterations if iterations is not None else self.definition.iterations
        if n < 0:
            raise ValueError(f"Iterations must be non-negative, got {n}")

        results = [self.definition.axiom]
        current = self.definition.axiom
        rule_map = self._build_rule_map()

        for _ in range(n):
            next_str_parts: List[str] = []
            for pos, symbol in enumerate(current):
                if symbol in rule_map:
                    rule = self._select_rule(
                        rule_map[symbol], symbol, current, pos
                    )
                    if rule is not None:
                        next_str_parts.append(rule.successor)
                    else:
                        next_str_parts.append(symbol)
                else:
                    next_str_parts.append(symbol)
            current = "".join(next_str_parts)
            results.append(current)

        return results

    @staticmethod
    def analyze(lstring: str) -> Dict[str, Any]:
        """Analyze an L-system string and return statistics."""
        if not lstring:
            return {"length": 0, "symbols": {}, "draw_symbols": 0, "unique_symbols": 0}

        symbol_counts: Dict[str, int] = defaultdict(int)
        draw_symbols = 0
        for ch in lstring:
            symbol_counts[ch] += 1
            if ch in ("F", "G"):
                draw_symbols += 1

        return {
            "length": len(lstring),
            "symbols": dict(symbol_counts),
            "draw_symbols": draw_symbols,
            "unique_symbols": len(symbol_counts),
        }


# ---------------------------------------------------------------------------
# Turtle interpreter
# ---------------------------------------------------------------------------

class TurtleInterpreter:
    """Interprets an L-system string using turtle graphics.

    Standard symbol meanings:
      F, G   — Move forward and draw
      f      — Move forward without drawing
      +      — Turn left by angle_increment
      -      — Turn right by angle_increment
      [      — Push state onto stack
      ]      — Pop state from stack
      |      — Reverse direction (turn 180°)
      #      — Increment line width
      !      — Decrement line width
      (      — Decrease step size by factor
      )      — Increase step size by factor
      <      — Divide step size by 2
      >      — Multiply step size by 2
    """

    def __init__(
        self,
        angle: float = 25.0,
        step_size: float = 5.0,
        line_width: float = 1.0,
        colors: Optional[Dict[int, str]] = None,
        perturbation: float = 0.0,
        step_perturbation: float = 0.0,
        seed: Optional[int] = None,
    ):
        self.initial_angle = angle
        self.initial_step_size = step_size
        self.initial_line_width = line_width
        self.colors = colors or {}
        self.perturbation = perturbation
        self.step_perturbation = step_perturbation
        self.rng = random.Random(seed)

    def interpret(self, lstring: str) -> List[Segment]:
        """Interpret an L-system string and return a list of line segments."""
        state = TurtleState(
            x=0.0,
            y=0.0,
            angle=90.0,  # Start pointing up
            step_size=self.initial_step_size,
            angle_increment=self.initial_angle,
            line_width=self.initial_line_width,
            color=self.colors.get(0, "#2d5016"),
            depth=0,
        )
        stack: List[TurtleState] = []
        segments: List[Segment] = []
        step_factor = 0.7  # For ( and ) symbols
        seg_index = 0

        for ch in lstring:
            if ch in ("F", "G"):
                # Apply perturbation to angle and step for organic feel
                angle_pert = 0.0
                step_pert_factor = 1.0
                if self.perturbation > 0:
                    angle_pert = self.rng.gauss(0, self.perturbation)
                if self.step_perturbation > 0:
                    step_pert_factor = 1.0 + self.rng.gauss(0, self.step_perturbation)
                    step_pert_factor = max(0.5, min(1.5, step_pert_factor))

                actual_angle = state.angle + angle_pert
                actual_step = state.step_size * step_pert_factor

                rad = math.radians(actual_angle)
                new_x = state.x + actual_step * math.cos(rad)
                new_y = state.y + actual_step * math.sin(rad)

                color = self.colors.get(state.depth, state.color)
                segments.append(
                    Segment(
                        x1=state.x,
                        y1=state.y,
                        x2=new_x,
                        y2=new_y,
                        color=color,
                        width=state.line_width,
                        depth=state.depth,
                        segment_index=seg_index,
                    )
                )
                seg_index += 1
                state.x = new_x
                state.y = new_y

            elif ch == "f":
                # Move forward without drawing
                rad = math.radians(state.angle)
                state.x += state.step_size * math.cos(rad)
                state.y += state.step_size * math.sin(rad)

            elif ch == "+":
                state.angle += state.angle_increment

            elif ch == "-":
                state.angle -= state.angle_increment

            elif ch == "|":
                state.angle += 180.0

            elif ch == "[":
                stack.append(copy.deepcopy(state))
                state.depth += 1
                # Gradually thin branches and shrink step
                state.line_width = max(0.3, state.line_width * 0.7)
                state.step_size *= 0.75
                color = self.colors.get(state.depth, state.color)
                state.color = color

            elif ch == "]":
                if stack:
                    state = stack.pop()

            elif ch == "#":
                state.line_width += 1.0

            elif ch == "!":
                state.line_width = max(0.1, state.line_width - 1.0)

            elif ch == "<":
                state.step_size /= 2.0

            elif ch == ">":
                state.step_size *= 2.0

            elif ch == "(":
                state.step_size *= step_factor

            elif ch == ")":
                state.step_size /= step_factor

        return segments


# ---------------------------------------------------------------------------
# Color post-processing
# ---------------------------------------------------------------------------

class ColorPostProcessor:
    """Applies color modes to segments after interpretation."""

    @staticmethod
    def apply(
        segments: List[Segment],
        color_mode: str = "depth",
        colors: Optional[Dict[int, str]] = None,
        gradient: Optional[Tuple[str, str]] = None,
    ) -> List[Segment]:
        """Apply the specified color mode to all segments."""
        if not segments:
            return segments

        colors = colors or {}

        if color_mode == "single":
            base_color = colors.get(0, "#2d5016")
            for seg in segments:
                seg.color = base_color

        elif color_mode == "depth":
            for seg in segments:
                seg.color = colors.get(seg.depth, seg.color)

        elif color_mode == "position":
            if gradient:
                # Color based on normalized Y position (bottom=start, top=end)
                ys = []
                for seg in segments:
                    ys.extend([seg.y1, seg.y2])
                if ys:
                    min_y = min(ys)
                    max_y = max(ys)
                    y_range = max_y - min_y if max_y != min_y else 1.0
                    for seg in segments:
                        mid_y = (seg.y1 + seg.y2) / 2
                        t = (mid_y - min_y) / y_range
                        seg.color = lerp_color(gradient[0], gradient[1], t)
            else:
                # Default: use depth colors
                for seg in segments:
                    seg.color = colors.get(seg.depth, seg.color)

        elif color_mode == "segment_index":
            total = len(segments)
            for seg in segments:
                seg.color = rainbow_color(seg.segment_index, total)

        return segments


# ---------------------------------------------------------------------------
# Rendering backends
# ---------------------------------------------------------------------------

class SVGRenderer:
    """Renders segments to an SVG file.

    Supports:
      - Auto-scaling and centering
      - Configurable background, margins
      - Optional SVG animation (progressive draw)
      - Title and metadata
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 800,
        background: str = "#ffffff",
        margin: float = 20.0,
        title: str = "",
    ):
        self.width = width
        self.height = height
        self.background = background
        self.margin = margin
        self.title = title

    def _compute_bounds(self, segments: List[Segment]) -> Tuple[float, float, float, float]:
        """Compute the bounding box of all segments."""
        if not segments:
            return (0, 0, 100, 100)
        xs = []
        ys = []
        for seg in segments:
            xs.extend([seg.x1, seg.x2])
            ys.extend([seg.y1, seg.y2])
        return min(xs), min(ys), max(xs), max(ys)

    def render(
        self,
        segments: List[Segment],
        output_path: str,
        animate: bool = False,
        animation_duration: float = 5.0,
    ) -> str:
        """Render segments to an SVG file.

        Args:
            segments: List of Segment objects to render.
            output_path: Path to write the SVG file.
            animate: If True, add SVG animation that draws segments progressively.
            animation_duration: Duration of animation in seconds (if animate=True).

        Returns:
            Path to the output file.
        """
        if not segments:
            # Write empty SVG
            lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}">',
                f'<rect width="{self.width}" height="{self.height}" fill="{self.background}"/>',
                '</svg>',
            ]
            with open(output_path, "w") as f:
                f.write("\n".join(lines))
            return output_path

        min_x, min_y, max_x, max_y = self._compute_bounds(segments)
        data_w = max_x - min_x or 1.0
        data_h = max_y - min_y or 1.0

        # Scale to fit within the SVG viewport with margins
        avail_w = self.width - 2 * self.margin
        avail_h = self.height - 2 * self.margin
        scale = min(avail_w / data_w, avail_h / data_h)

        # Center the drawing
        offset_x = self.margin + (avail_w - data_w * scale) / 2
        offset_y = self.margin + (avail_h - data_h * scale) / 2

        lines: List[str] = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">'
        )
        if self.title:
            lines.append(f"<title>{_escape_xml(self.title)}</title>")
            lines.append(f"<desc>{_escape_xml('Generated by lsystem-renderer-q4m7')}</desc>")

        lines.append(
            f'<rect width="{self.width}" height="{self.height}" '
            f'fill="{self.background}"/>'
        )

        # Group segments by (color, width) for compact but accurate SVG
        if not animate:
            # Group by (color, rounded_width) to avoid float grouping issues
            style_groups: Dict[Tuple[str, float], List[Segment]] = defaultdict(list)
            for seg in segments:
                # Round width to 2 decimal places for grouping
                key = (seg.color, round(seg.width, 2))
                style_groups[key].append(seg)

            for (color, width), group in style_groups.items():
                path_parts = []
                for seg in group:
                    sx1 = (seg.x1 - min_x) * scale + offset_x
                    sy1 = self.height - ((seg.y1 - min_y) * scale + offset_y)
                    sx2 = (seg.x2 - min_x) * scale + offset_x
                    sy2 = self.height - ((seg.y2 - min_y) * scale + offset_y)
                    path_parts.append(f"M{sx1:.2f},{sy1:.2f} L{sx2:.2f},{sy2:.2f}")
                path_d = " ".join(path_parts)
                lines.append(
                    f'<path d="{path_d}" stroke="{color}" '
                    f'stroke-width="{width:.2f}" fill="none" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>'
                )
        else:
            # Animated: each segment appears progressively
            total = len(segments)
            delay_per_seg = animation_duration / total
            for i, seg in enumerate(segments):
                sx1 = (seg.x1 - min_x) * scale + offset_x
                sy1 = self.height - ((seg.y1 - min_y) * scale + offset_y)
                sx2 = (seg.x2 - min_x) * scale + offset_x
                sy2 = self.height - ((seg.y2 - min_y) * scale + offset_y)
                begin = f"{i * delay_per_seg:.3f}s"
                dur = f"{delay_per_seg * 3:.3f}s"
                lines.append(
                    f'<line x1="{sx1:.3f}" y1="{sy1:.3f}" '
                    f'x2="{sx2:.3f}" y2="{sy2:.3f}" '
                    f'stroke="{seg.color}" stroke-width="{seg.width:.2f}" '
                    f'stroke-linecap="round" opacity="0">'
                    f'<animate attributeName="opacity" from="0" to="1" '
                    f'begin="{begin}" dur="{dur}" fill="freeze"/>'
                    f'</line>'
                )

        lines.append("</svg>")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return output_path


class ASCIIRenderer:
    """Renders segments to ASCII art using a character grid.

    Supports directional characters (|, -, /, \\) for better-looking output.
    """

    CHAR_MAP = {
        (0, 1): "|",
        (0, -1): "|",
        (1, 0): "-",
        (-1, 0): "-",
        (1, 1): "\\",
        (-1, -1): "\\",
        (1, -1): "/",
        (-1, 1): "/",
    }

    def __init__(self, width: int = 80, height: int = 40):
        self.width = width
        self.height = height

    def render(self, segments: List[Segment], output_path: Optional[str] = None) -> str:
        """Render segments to ASCII art string."""
        if not segments:
            return ""

        # Compute bounds
        xs = []
        ys = []
        for seg in segments:
            xs.extend([seg.x1, seg.x2])
            ys.extend([seg.y1, seg.y2])

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        data_w = max_x - min_x or 1.0
        data_h = max_y - min_y or 1.0

        # Create grid
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]

        scale_x = (self.width - 1) / data_w if data_w > 0 else 1
        scale_y = (self.height - 1) / data_h if data_h > 0 else 1
        scale = min(scale_x, scale_y)

        for seg in segments:
            x1 = int((seg.x1 - min_x) * scale)
            y1 = int((seg.y1 - min_y) * scale)
            x2 = int((seg.x2 - min_x) * scale)
            y2 = int((seg.y2 - min_y) * scale)

            # Bresenham-like rasterization
            dx = x2 - x1
            dy = y2 - y1
            steps = max(abs(dx), abs(dy), 1)

            # Determine direction character
            if steps > 0:
                ndx = dx / steps
                ndy = dy / steps
                # Snap to nearest direction
                key = (
                    round(ndx) if abs(ndx) > 0.3 else 0,
                    round(ndy) if abs(ndy) > 0.3 else 0,
                )
                char = self.CHAR_MAP.get(key, "*")
            else:
                char = "*"

            for i in range(steps + 1):
                t = i / steps
                px = int(x1 + dx * t)
                py = int(y1 + dy * t)
                if 0 <= px < self.width and 0 <= py < self.height:
                    grid[py][px] = char

        # Flip grid vertically (y increases upward in math, downward in text)
        lines = ["".join(row) for row in reversed(grid)]
        result = "\n".join(lines)

        if output_path:
            with open(output_path, "w") as f:
                f.write(result)

        return result


# ---------------------------------------------------------------------------
# Preset L-systems
# ---------------------------------------------------------------------------

PRESETS: Dict[str, LSystemDefinition] = {
    "koch_curve": LSystemDefinition(
        name="Koch Curve",
        axiom="F",
        rules=[LSystemRule("F", "F+F--F+F")],
        angle=60.0,
        step_size=3.0,
        iterations=4,
        line_width=1.0,
    ),
    "koch_snowflake": LSystemDefinition(
        name="Koch Snowflake",
        axiom="F--F--F",
        rules=[LSystemRule("F", "F+F--F+F")],
        angle=60.0,
        step_size=3.0,
        iterations=4,
        line_width=1.0,
    ),
    "sierpinski_triangle": LSystemDefinition(
        name="Sierpiński Triangle",
        axiom="F-G-G",
        rules=[
            LSystemRule("F", "F-G+F+G-F"),
            LSystemRule("G", "GG"),
        ],
        angle=120.0,
        step_size=3.0,
        iterations=6,
        line_width=1.0,
    ),
    "dragon_curve": LSystemDefinition(
        name="Dragon Curve",
        axiom="F",
        rules=[
            LSystemRule("F", "F+G"),
            LSystemRule("G", "F-G"),
        ],
        angle=90.0,
        step_size=5.0,
        iterations=12,
        line_width=1.0,
        color_mode="segment_index",
    ),
    "hilbert_curve": LSystemDefinition(
        name="Hilbert Curve",
        axiom="A",
        rules=[
            LSystemRule("A", "-BF+AFA+FB-"),
            LSystemRule("B", "+AF-BFB-FA+"),
        ],
        angle=90.0,
        step_size=5.0,
        iterations=5,
        line_width=1.0,
        color_mode="segment_index",
    ),
    "plant_simple": LSystemDefinition(
        name="Simple Plant",
        axiom="F",
        rules=[LSystemRule("F", "F[+F]F[-F]F")],
        angle=25.7,
        step_size=4.0,
        iterations=5,
        line_width=1.0,
        colors={
            0: "#5a3e1b",
            1: "#3d6b2e",
            2: "#4a8c3a",
            3: "#6bb55a",
            4: "#8dd77a",
            5: "#a8f08a",
        },
    ),
    "plant_stochastic": LSystemDefinition(
        name="Stochastic Plant",
        axiom="F",
        rules=[
            LSystemRule("F", "F[+F]F[-F]F", probability=0.5),
            LSystemRule("F", "F[+F]F", probability=0.25),
            LSystemRule("F", "F[-F]F", probability=0.25),
        ],
        angle=25.7,
        step_size=4.0,
        iterations=5,
        line_width=1.5,
        colors={
            0: "#5a3e1b",
            1: "#3d6b2e",
            2: "#4a8c3a",
            3: "#6bb55a",
            4: "#8dd77a",
            5: "#a8f08a",
        },
    ),
    "tree_bushy": LSystemDefinition(
        name="Bushy Tree",
        axiom="F",
        rules=[LSystemRule("F", "FF+[+F-F-F]-[-F+F+F]")],
        angle=22.5,
        step_size=4.0,
        iterations=4,
        line_width=1.5,
        colors={
            0: "#4a2f0a",
            1: "#5a3e1b",
            2: "#3d6b2e",
            3: "#5a9e3a",
            4: "#7abf5a",
            5: "#a8f08a",
        },
    ),
    "penrose_tiles": LSystemDefinition(
        name="Penrose Tiles",
        axiom="[7]++[7]++[7]++[7]++[7]",
        rules=[
            LSystemRule("6", "81++91----71[-81----61]++"),
            LSystemRule("7", "+81--91[---61--71]"),
            LSystemRule("8", "-61++71[+++81++91]-"),
            LSystemRule("9", "--81+++61[+91+++71]--71"),
        ],
        angle=36.0,
        step_size=4.0,
        iterations=4,
        line_width=0.8,
    ),
    "levy_c_curve": LSystemDefinition(
        name="Lévy C Curve",
        axiom="F",
        rules=[LSystemRule("F", "+F--F+")],
        angle=45.0,
        step_size=3.0,
        iterations=14,
        line_width=1.0,
        color_mode="segment_index",
    ),
    "gosper_curve": LSystemDefinition(
        name="Gosper Curve (Flowsnake)",
        axiom="A",
        rules=[
            LSystemRule("A", "A-B--B+A++AA+B-"),
            LSystemRule("B", "+A-BB--B-A++A+B"),
        ],
        angle=60.0,
        step_size=4.0,
        iterations=4,
        line_width=1.0,
        color_mode="segment_index",
    ),
    "fractal_tree": LSystemDefinition(
        name="Fractal Tree",
        axiom="X",
        rules=[
            LSystemRule("X", "F+[[X]-X]-F[-FX]+X"),
            LSystemRule("F", "FF"),
        ],
        angle=25.0,
        step_size=4.0,
        iterations=6,
        line_width=1.5,
        colors={
            0: "#5a3e1b",
            1: "#4a6e2e",
            2: "#3d8c3a",
            3: "#5aae5a",
            4: "#7acf6a",
            5: "#9aef8a",
            6: "#baffaa",
        },
    ),
    "barnsley_fern": LSystemDefinition(
        name="Barnsley Fern (approximation)",
        axiom="X",
        rules=[
            LSystemRule("X", "F+[[X]-X]-F[-FX]+X"),
            LSystemRule("F", "FF"),
        ],
        angle=25.0,
        step_size=3.0,
        iterations=5,
        line_width=1.0,
        colors={
            0: "#1a5c1a",
            1: "#228b22",
            2: "#32cd32",
            3: "#7cfc00",
            4: "#adff2f",
        },
    ),
    "cantor_dust": LSystemDefinition(
        name="Cantor Dust",
        axiom="F",
        rules=[
            LSystemRule("F", "FfF"),
            LSystemRule("f", "fff"),
        ],
        angle=0.0,
        step_size=5.0,
        iterations=4,
        line_width=2.0,
        color_mode="single",
    ),
}


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

class LSystemRenderer:
    """High-level API for rendering L-systems.

    Usage:
        renderer = LSystemRenderer()
        renderer.render("koch_snowflake", iterations=4, backend="svg",
                        output="koch.svg")
    """

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed

    def render(
        self,
        preset_or_definition: Union[str, LSystemDefinition],
        iterations: Optional[int] = None,
        backend: Union[str, RenderBackend] = RenderBackend.SVG,
        output: str = "output.svg",
        width: int = 800,
        height: int = 800,
        background: Optional[str] = None,
        margin: float = 20.0,
        animate: bool = False,
        animation_duration: float = 5.0,
    ) -> str:
        """Render an L-system to the specified backend.

        Args:
            preset_or_definition: Either a preset name (str) or an
                LSystemDefinition instance.
            iterations: Override the default iteration count.
            backend: Rendering backend ('svg', 'ascii', or RenderBackend enum).
            output: Output file path.
            width: Canvas width (for SVG).
            height: Canvas height (for SVG).
            background: Background color (overrides definition).
            margin: Margin around the drawing (for SVG).
            animate: If True and backend=SVG, generate animation.
            animation_duration: Duration of animation in seconds.

        Returns:
            Path to the output file.
        """
        if isinstance(backend, str):
            backend = RenderBackend[backend.upper()]

        # Resolve definition
        if isinstance(preset_or_definition, str):
            if preset_or_definition not in PRESETS:
                available = ", ".join(sorted(PRESETS.keys()))
                raise ValueError(
                    f"Unknown preset '{preset_or_definition}'. "
                    f"Available presets: {available}"
                )
            definition = copy.deepcopy(PRESETS[preset_or_definition])
        else:
            definition = copy.deepcopy(preset_or_definition)

        # Override background if provided
        if background is not None:
            definition.background = background

        # Generate string
        engine = LSystemEngine(definition, seed=self.seed)
        lstring = engine.iterate(iterations)

        # Interpret with turtle
        interpreter = TurtleInterpreter(
            angle=definition.angle,
            step_size=definition.step_size,
            line_width=definition.line_width,
            colors=definition.colors,
            perturbation=definition.perturbation,
            step_perturbation=definition.step_perturbation,
            seed=self.seed,
        )
        segments = interpreter.interpret(lstring)

        # Apply color post-processing
        segments = ColorPostProcessor.apply(
            segments,
            color_mode=definition.color_mode,
            colors=definition.colors,
            gradient=definition.gradient,
        )

        # Render
        if backend == RenderBackend.SVG:
            renderer = SVGRenderer(
                width=width,
                height=height,
                background=definition.background,
                margin=margin,
                title=definition.name,
            )
            return renderer.render(segments, output, animate=animate,
                                   animation_duration=animation_duration)
        elif backend == RenderBackend.ASCII:
            renderer = ASCIIRenderer(
                width=min(width // 8, 120),
                height=min(height // 16, 60)
            )
            result = renderer.render(segments)
            actual_output = output
            if not actual_output.endswith(".txt"):
                # Replace extension or append .txt
                if "." in os.path.basename(actual_output):
                    actual_output = actual_output.rsplit(".", 1)[0] + ".txt"
                else:
                    actual_output += ".txt"
            with open(actual_output, "w") as f:
                f.write(result)
            return actual_output
        elif backend == RenderBackend.TERMINAL:
            renderer = ASCIIRenderer(width=80, height=40)
            result = renderer.render(segments)
            print(result)
            return output
        else:
            raise ValueError(f"Unsupported backend: {backend}")

    def render_all_presets(
        self,
        output_dir: str = ".",
        iterations: Optional[int] = None,
        backend: str = "svg",
        width: int = 800,
        height: int = 800,
    ) -> Dict[str, str]:
        """Render all presets to files in the given directory.

        Returns a dict mapping preset name -> output file path.
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        for name in self.list_presets():
            definition = self.get_preset(name)
            ext = "svg" if backend == "svg" else "txt"
            output_path = os.path.join(output_dir, f"{name}.{ext}")
            try:
                path = self.render(
                    definition,
                    iterations=iterations,
                    backend=backend,
                    output=output_path,
                    width=width,
                    height=height,
                )
                results[name] = path
            except Exception as e:
                results[name] = f"ERROR: {e}"
        return results

    def animate_growth(
        self,
        preset_or_definition: Union[str, LSystemDefinition],
        output_dir: str = ".",
        iterations: Optional[int] = None,
        width: int = 800,
        height: int = 800,
    ) -> List[str]:
        """Render each iteration step as a separate SVG file.

        Creates files named step_0.svg, step_1.svg, etc.
        Useful for creating growth animations.

        Returns list of output file paths.
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        if isinstance(preset_or_definition, str):
            definition = self.get_preset(preset_or_definition)
        else:
            definition = copy.deepcopy(preset_or_definition)

        engine = LSystemEngine(definition, seed=self.seed)
        steps = engine.iterate_steps(iterations)

        paths = []
        for i, lstring in enumerate(steps):
            interpreter = TurtleInterpreter(
                angle=definition.angle,
                step_size=definition.step_size,
                line_width=definition.line_width,
                colors=definition.colors,
                perturbation=definition.perturbation,
                step_perturbation=definition.step_perturbation,
                seed=self.seed,
            )
            segments = interpreter.interpret(lstring)
            segments = ColorPostProcessor.apply(
                segments,
                color_mode=definition.color_mode,
                colors=definition.colors,
                gradient=definition.gradient,
            )

            svg_renderer = SVGRenderer(
                width=width, height=height,
                background=definition.background,
                title=f"{definition.name} — Step {i}",
            )
            path = os.path.join(output_dir, f"step_{i}.svg")
            svg_renderer.render(segments, path)
            paths.append(path)

        return paths

    def list_presets(self) -> List[str]:
        """Return a list of available preset names."""
        return list(PRESETS.keys())

    def get_preset(self, name: str) -> LSystemDefinition:
        """Return a copy of a preset definition."""
        if name not in PRESETS:
            available = ", ".join(sorted(PRESETS.keys()))
            raise ValueError(f"Unknown preset '{name}'. Available: {available}")
        return copy.deepcopy(PRESETS[name])


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def main():
    """Command-line interface for the L-system renderer."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="L-System Renderer — Generate fractals and plant-like structures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Render Koch snowflake
  python3 lsystem.py --preset koch_snowflake -i 4 -o koch.svg

  # Render a stochastic plant with a specific seed
  python3 lsystem.py --preset plant_stochastic -i 5 --seed 42 -o plant.svg

  # Render to ASCII
  python3 lsystem.py --preset dragon_curve -i 10 --backend ascii -o dragon.txt

  # Render all presets
  python3 lsystem.py --render-all -d ./output

  # Animate growth steps
  python3 lsystem.py --preset koch_snowflake --animate -d ./growth

  # List available presets
  python3 lsystem.py --list-presets

  # Custom L-system (Sierpinski arrowhead)
  python3 lsystem.py --axiom "A" --rule "A->B-A-B" --rule "B->A+B+A" --angle 60 -i 7 -o custom.svg

  # Load from JSON definition
  python3 lsystem.py --load definition.json -o output.svg
        """,
    )

    parser.add_argument(
        "--preset", "-p",
        help="Preset L-system name to render",
    )
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=None,
        help="Number of iterations (default: use preset default)",
    )
    parser.add_argument(
        "--backend", "-b",
        choices=["svg", "ascii", "terminal"],
        default="svg",
        help="Rendering backend (default: svg)",
    )
    parser.add_argument(
        "--output", "-o",
        default="output.svg",
        help="Output file path (default: output.svg)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1000,
        help="SVG canvas width (default: 1000)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1000,
        help="SVG canvas height (default: 1000)",
    )
    parser.add_argument(
        "--background",
        default=None,
        help="Background color (overrides preset default)",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed for stochastic L-systems",
    )
    parser.add_argument(
        "--list-presets", "-l",
        action="store_true",
        help="List available presets and exit",
    )
    parser.add_argument(
        "--axiom",
        help="Custom axiom (overrides preset)",
    )
    parser.add_argument(
        "--rule",
        action="append",
        help="Custom rule in format 'PREDECESSOR->SUCCESSOR' (can be repeated)",
    )
    parser.add_argument(
        "--angle",
        type=float,
        default=None,
        help="Custom angle in degrees (overrides preset)",
    )
    parser.add_argument(
        "--step-size",
        type=float,
        default=None,
        help="Custom step size (overrides preset)",
    )
    parser.add_argument(
        "--line-width",
        type=float,
        default=None,
        help="Custom line width (overrides preset)",
    )
    parser.add_argument(
        "--color-mode",
        choices=["depth", "position", "segment_index", "single"],
        default=None,
        help="Color mode for rendering",
    )
    parser.add_argument(
        "--gradient",
        help="Gradient colors as 'start_color,end_color' (e.g. '#ff0000,#0000ff')",
    )
    parser.add_argument(
        "--perturbation",
        type=float,
        default=None,
        help="Angle perturbation (std dev in degrees) for organic variation",
    )
    parser.add_argument(
        "--render-all",
        action="store_true",
        help="Render all presets to output directory",
    )
    parser.add_argument(
        "--animate",
        action="store_true",
        help="Generate SVG animation (progressive draw)",
    )
    parser.add_argument(
        "--animate-steps",
        action="store_true",
        help="Render each iteration step as a separate SVG file",
    )
    parser.add_argument(
        "--directory", "-d",
        default=".",
        help="Output directory for --render-all and --animate-steps",
    )
    parser.add_argument(
        "--load",
        help="Load L-system definition from a JSON file",
    )
    parser.add_argument(
        "--save",
        help="Save the resolved L-system definition to a JSON file (don't render)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print string statistics without rendering",
    )

    args = parser.parse_args()

    renderer = LSystemRenderer(seed=args.seed)

    if args.list_presets:
        print("Available presets:")
        for name in renderer.list_presets():
            preset = PRESETS[name]
            print(f"  {name:25s} — {preset.name}")
        return

    # Render all presets — no definition needed
    if args.render_all:
        results = renderer.render_all_presets(
            output_dir=args.directory,
            iterations=args.iterations,
            backend=args.backend,
            width=args.width,
            height=args.height,
        )
        print("Rendered all presets:")
        for name, path in results.items():
            print(f"  {name}: {path}")
        return

    # Load from JSON or build definition
    if args.load:
        definition = LSystemDefinition.from_json(args.load)
    elif args.preset:
        definition = renderer.get_preset(args.preset)
    elif args.axiom:
        definition = LSystemDefinition(
            name="Custom",
            axiom=args.axiom,
            rules=[],
            angle=args.angle or 90.0,
            step_size=args.step_size or 5.0,
            iterations=4,
            line_width=args.line_width or 1.0,
        )
    else:
        parser.error("One of --preset, --axiom, or --load is required "
                     "(unless using --list-presets or --render-all)")

    # Apply CLI overrides
    if args.angle is not None:
        definition.angle = args.angle
    if args.step_size is not None:
        definition.step_size = args.step_size
    if args.line_width is not None:
        definition.line_width = args.line_width
    if args.color_mode is not None:
        definition.color_mode = args.color_mode
    if args.gradient is not None:
        parts = args.gradient.split(",")
        if len(parts) == 2:
            definition.gradient = (parts[0].strip(), parts[1].strip())
    if args.perturbation is not None:
        definition.perturbation = args.perturbation
    if args.background is not None:
        definition.background = args.background

    # Add custom rules
    if args.rule:
        for rule_str in args.rule:
            sep = "->" if "->" in rule_str else "="
            parts = rule_str.split(sep, 1)
            if len(parts) != 2:
                print(f"Invalid rule format: {rule_str}", file=sys.stderr)
                sys.exit(1)
            definition.rules.append(
                LSystemRule(predecessor=parts[0].strip(), successor=parts[1].strip())
            )

    # Save definition if requested
    if args.save:
        definition.to_json(args.save)
        print(f"Definition saved to: {args.save}")
        return

    # Stats mode
    if args.stats:
        engine = LSystemEngine(definition, seed=args.seed)
        lstring = engine.iterate(args.iterations)
        stats = LSystemEngine.analyze(lstring)
        print(f"L-System: {definition.name}")
        print(f"  Axiom: {definition.axiom[:60]}{'...' if len(definition.axiom) > 60 else ''}")
        print(f"  String length: {stats['length']:,}")
        print(f"  Drawing symbols (F/G): {stats['draw_symbols']:,}")
        print(f"  Unique symbols: {stats['unique_symbols']}")
        print(f"  Symbol breakdown:")
        # Sort by count descending
        for sym, count in sorted(stats['symbols'].items(), key=lambda x: -x[1])[:15]:
            pct = 100 * count / stats['length'] if stats['length'] > 0 else 0
            print(f"    '{sym}': {count:,} ({pct:.1f}%)")
        if stats['length'] > 15 * 1000:
            print("  (showing top 15 symbols)")
        return

    # Animate steps
    if args.animate_steps:
        paths = renderer.animate_growth(
            definition,
            output_dir=args.directory,
            iterations=args.iterations,
            width=args.width,
            height=args.height,
        )
        print(f"Generated {len(paths)} step files:")
        for path in paths:
            print(f"  {path}")
        return

    # Normal render
    output = args.output
    if args.backend == "ascii" and not output.endswith(".txt"):
        output = output.rsplit(".", 1)[0] + ".txt" if "." in output else output + ".txt"
    elif args.backend == "svg" and not output.endswith(".svg"):
        output += ".svg"

    result = renderer.render(
        definition,
        iterations=args.iterations,
        backend=args.backend,
        output=output,
        width=args.width,
        height=args.height,
        background=args.background,
        animate=args.animate,
    )
    print(f"Output written to: {result}")

    # Print brief stats
    engine = LSystemEngine(definition, seed=args.seed)
    lstring = engine.iterate(args.iterations)
    stats = LSystemEngine.analyze(lstring)
    print(f"Segments: {stats['draw_symbols']:,} | String length: {stats['length']:,}")


if __name__ == "__main__":
    main()