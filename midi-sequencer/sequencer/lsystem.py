"""L-System pattern generation for evolving rhythmic/melodic patterns."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from sequencer.patterns import Pattern, Step
from sequencer.scales import scale_notes


# L-System rules for musical patterns
# Each symbol maps to a musical action:
#   A-G = scale degree 1-7 (with octave shifts)
#   R = rest
#   H = hold (tie to next note)
#   + = transpose up one scale degree
#   - = transpose down one scale degree
#   U = octave up
#   D = octave down

PRESETS = {
    "cantor": {
        "axiom": "A",
        "rules": {"A": "A+R-A-R+A"},
        "angle": 1,
    },
    "fibonacci_melody": {
        "axiom": "A",
        "rules": {"A": "AB", "B": "A"},
        "angle": 1,
    },
    "tree_rhythm": {
        "axiom": "X",
        "rules": {"X": "A+RX-RXR-R+X+", "R": "RR"},
        "angle": 1,
    },
    "koch_snowflake": {
        "axiom": "A",
        "rules": {"A": "A+A-R-R+A+A"},
        "angle": 1,
    },
    "serpinski_melody": {
        "axiom": "A",
        "rules": {"A": "R+A+R+A+R", "R": "A-R-A-R-A"},
        "angle": 1,
    },
}


def _expand_lsystem(axiom: str, rules: Dict[str, str], iterations: int) -> str:
    """Expand an L-System string for the given number of iterations.

    Args:
        axiom: Starting string
        rules: Dict mapping symbols to their replacements
        iterations: Number of expansion iterations

    Returns:
        Expanded string
    """
    current = axiom
    for _ in range(iterations):
        next_str = []
        for char in current:
            next_str.append(rules.get(char, char))
        current = "".join(next_str)
        # Limit growth to prevent explosion
        if len(current) > 2048:
            break
    return current


def lsystem_pattern(
    preset: Optional[str] = None,
    axiom: Optional[str] = None,
    rules: Optional[Dict[str, str]] = None,
    iterations: int = 3,
    root: str = "C",
    scale: str = "major",
    octave: int = 4,
    velocity: int = 100,
) -> Pattern:
    """Generate a pattern from an L-System.

    Args:
        preset: Name of a preset L-System (or provide axiom/rules manually)
        axiom: Starting string (overrides preset)
        rules: Expansion rules (overrides preset)
        iterations: Number of expansion iterations
        root: Root note for the scale
        scale: Scale name
        octave: Starting octave
        velocity: Default velocity

    Returns:
        A Pattern generated from the L-System
    """
    if preset and preset in PRESETS:
        p = PRESETS[preset]
        axiom = axiom or p["axiom"]
        rules = rules or p["rules"]

    if axiom is None:
        axiom = "A"
    if rules is None:
        rules = {"A": "A+R-A-R+A"}

    expanded = _expand_lsystem(axiom, rules, iterations)
    notes = scale_notes(root, scale, 3, octave)

    # Interpret the expanded string
    steps = []
    current_degree = 0  # Index into scale notes
    current_octave = 0   # Octave offset

    for char in expanded:
        if char in "ABCDEFG":
            degree = ord(char) - ord('A')  # 0-6
            idx = current_degree + degree
            idx = idx % len(notes)
            note = notes[idx] + current_octave * 12
            note = max(0, min(127, note))
            steps.append(Step(notes=[note], velocity=velocity, gate=0.8))
            current_degree = degree
        elif char == 'R':
            steps.append(Step())  # Rest
        elif char == 'H':
            # Hold — mark previous step as tied
            if steps and steps[-1].notes:
                steps[-1].tie = True
                steps[-1].gate = 1.0
        elif char == '+':
            current_degree = (current_degree + 1) % len(notes)
            if current_degree == 0:
                current_octave += 1
        elif char == '-':
            current_degree = (current_degree - 1) % len(notes)
            if current_degree == len(notes) - 1:
                current_octave -= 1
        elif char == 'U':
            current_octave += 1
        elif char == 'D':
            current_octave -= 1
        # Ignore unknown symbols (they're structural)

    if not steps:
        steps = [Step()]

    return Pattern(name=f"lsystem_{preset or 'custom'}", steps=steps, length=len(steps))