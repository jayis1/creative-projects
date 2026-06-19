"""Minimal immutable 2-D vector helpers used throughout nbody-sim.

Implemented as plain floats stored in tuples for cheap copies; the module
exposes convenience functions so callers can stay free of attribute noise.
All operations are pure (no mutation), which keeps the integrator code clear.
"""

from __future__ import annotations

import math
from typing import Tuple

Vec2 = Tuple[float, float]


def add(a: Vec2, b: Vec2) -> Vec2:
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Vec2, b: Vec2) -> Vec2:
    return (a[0] - b[0], a[1] - b[1])


def scale(a: Vec2, s: float) -> Vec2:
    return (a[0] * s, a[1] * s)


def dot(a: Vec2, b: Vec2) -> float:
    return a[0] * b[0] + a[1] * b[1]


def length(a: Vec2) -> float:
    return math.hypot(a[0], a[1])


def length_sq(a: Vec2) -> float:
    return a[0] * a[0] + a[1] * a[1]


def dist(a: Vec2, b: Vec2) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dist_sq(a: Vec2, b: Vec2) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def normalize(a: Vec2) -> Vec2:
    n = math.hypot(a[0], a[1])
    if n == 0.0:
        return (0.0, 0.0)
    return (a[0] / n, a[1] / n)


__all__ = [
    "Vec2",
    "add", "sub", "scale", "dot",
    "length", "length_sq", "dist", "dist_sq", "normalize",
]