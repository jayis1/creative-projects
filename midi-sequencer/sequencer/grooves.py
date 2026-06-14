"""Groove templates and velocity curve utilities."""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from sequencer.patterns import Pattern, Step
import math
import copy


# Pre-defined groove templates — each is a list of (velocity_offset, timing_offset_ticks) per step
# Positive timing = late, negative = early
GROOVE_TEMPLATES: Dict[str, List[Tuple[int, int]]] = {
    "straight": [(0, 0)] * 16,
    "swing_16th": [
        (0, 0), (5, 15),   # swung 16th pairs
        (0, 0), (5, 15),
        (0, 0), (5, 15),
        (0, 0), (5, 15),
        (0, 0), (5, 15),
        (0, 0), (5, 15),
        (0, 0), (5, 15),
        (0, 0), (5, 15),
    ],
    "shuffle": [
        (0, 0), (10, 30),
        (-5, 0), (10, 30),
        (0, 0), (10, 30),
        (-5, 0), (10, 30),
        (0, 0), (10, 30),
        (-5, 0), (10, 30),
        (0, 0), (10, 30),
        (-5, 0), (10, 30),
    ],
    "dilla": [
        (5, 0), (-5, 20),
        (10, 0), (0, 25),
        (5, 0), (-10, 15),
        (10, 0), (5, 20),
        (0, 0), (-5, 25),
        (10, 0), (0, 15),
        (5, 0), (-5, 20),
        (10, 0), (0, 30),
    ],
    "bossa": [
        (10, 0), (0, 10),
        (5, 0), (0, 5),
        (10, 0), (0, 15),
        (5, 0), (0, 10),
        (10, 0), (0, 10),
        (5, 0), (0, 5),
        (10, 0), (0, 15),
        (5, 0), (0, 10),
    ],
    "reggae": [
        (0, 20), (0, 0),
        (5, 10), (0, 0),
        (0, 20), (0, 0),
        (5, 10), (0, 0),
        (0, 20), (0, 0),
        (5, 10), (0, 0),
        (0, 20), (0, 0),
        (5, 10), (0, 0),
    ],
}


def apply_groove(pattern: Pattern, groove_name: str, intensity: float = 1.0) -> Pattern:
    """Apply a groove template to a pattern.

    Args:
        pattern: The pattern to modify
        groove_name: Name of the groove template from GROOVE_TEMPLATES
        intensity: 0.0 = no effect, 1.0 = full groove effect

    Returns:
        A new Pattern with the groove applied
    """
    if groove_name not in GROOVE_TEMPLATES:
        raise ValueError(f"Unknown groove: {groove_name!r}. Choose from: {list(GROOVE_TEMPLATES)}")

    groove = GROOVE_TEMPLATES[groove_name]
    new_steps = []
    for i, step in enumerate(pattern.steps):
        new_step = copy.deepcopy(step)
        groove_idx = i % len(groove)
        vel_offset, timing_offset = groove[groove_idx]

        # Apply velocity offset
        new_step.velocity = max(1, min(127, new_step.velocity + int(vel_offset * intensity)))
        # Apply timing offset directly to the step (used during MIDI export)
        new_step.timing_offset = timing_offset * intensity
        new_steps.append(new_step)

    return Pattern(name=f"{pattern.name}_{groove_name}", steps=new_steps, length=pattern.length)


# Velocity curve generators
def velocity_crescendo(length: int, start_vel: int = 40, end_vel: int = 127) -> List[int]:
    """Generate a crescendo velocity curve."""
    return [int(start_vel + (end_vel - start_vel) * i / max(1, length - 1)) for i in range(length)]


def velocity_diminuendo(length: int, start_vel: int = 127, end_vel: int = 40) -> List[int]:
    """Generate a diminuendo velocity curve."""
    return velocity_crescendo(length, end_vel, start_vel)[::-1]


def velocity_swell(length: int, peak_vel: int = 127, base_vel: int = 40) -> List[int]:
    """Generate a swell (crescendo then diminuendo) velocity curve."""
    midpoint = length // 2
    up = velocity_crescendo(midpoint, base_vel, peak_vel)
    down = velocity_diminuendo(length - midpoint, peak_vel, base_vel)
    return up + down


def velocity_heartbeat(length: int, peak_vel: int = 120, base_vel: int = 60) -> List[int]:
    """Generate a heartbeat-like velocity curve (two peaks per cycle)."""
    velocities = []
    for i in range(length):
        phase = (i / length) * 2 * math.pi
        # Two peaks per cycle
        v = base_vel + (peak_vel - base_vel) * (0.5 + 0.3 * math.sin(phase) + 0.2 * math.sin(2 * phase))
        velocities.append(int(max(1, min(127, v))))
    return velocities


def velocity_random(length: int, low: int = 60, high: int = 120, seed: Optional[int] = None) -> List[int]:
    """Generate random velocities within a range."""
    import random
    if seed is not None:
        random.seed(seed)
    return [random.randint(low, high) for _ in range(length)]


VELOCITY_CURVES = {
    "crescendo": velocity_crescendo,
    "diminuendo": velocity_diminuendo,
    "swell": velocity_swell,
    "heartbeat": velocity_heartbeat,
    "random": velocity_random,
}


def apply_velocity_curve(pattern: Pattern, curve_name: str, **kwargs) -> Pattern:
    """Apply a velocity curve to a pattern.

    Args:
        pattern: The pattern to modify
        curve_name: Name of the velocity curve from VELOCITY_CURVES
        **kwargs: Additional arguments for the curve function

    Returns:
        A new Pattern with the velocity curve applied
    """
    if curve_name not in VELOCITY_CURVES:
        raise ValueError(f"Unknown curve: {curve_name!r}. Choose from: {list(VELOCITY_CURVES)}")

    curve_func = VELOCITY_CURVES[curve_name]
    velocities = curve_func(pattern.length, **kwargs)

    new_steps = []
    for i, step in enumerate(pattern.steps):
        new_step = copy.deepcopy(step)
        if step.notes:  # Only apply to steps that have notes
            new_step.velocity = velocities[i % len(velocities)]
        new_steps.append(new_step)

    return Pattern(name=f"{pattern.name}_{curve_name}", steps=new_steps, length=pattern.length)