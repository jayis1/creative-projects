"""Orbit traps for the Fractal Explorer."""
from __future__ import annotations

import math


class OrbitTrap:
    """Base class for orbit-trap colouring.

    Subclasses implement :meth:`distance` which returns the (squared)
    distance from a point to the trap; the minimum over the orbit is used.
    """

    def distance(self, z: complex) -> float:
        raise NotImplementedError


class PointTrap(OrbitTrap):
    """Trap at a single complex point."""

    def __init__(self, point=0 + 0j):
        self.point = complex(point)

    def distance(self, z):
        d = z - self.point
        return d.real * d.real + d.imag * d.imag


class LineTrap(OrbitTrap):
    """Trap at an infinite line through the origin at a given angle (radians)."""

    def __init__(self, angle=0.0):
        self.angle = float(angle)

    def distance(self, z):
        return (z.real * math.sin(self.angle) -
                z.imag * math.cos(self.angle)) ** 2


class CircleTrap(OrbitTrap):
    """Trap at a circle of given radius centred at the origin."""

    def __init__(self, radius=1.0):
        self.radius = float(radius)

    def distance(self, z):
        d = abs(z) - self.radius
        return d * d


class CrossTrap(OrbitTrap):
    """Trap at the union of the real and imaginary axes (cross shape)."""

    def distance(self, z):
        return min(z.real * z.real, z.imag * z.imag)


class StripeTrap(OrbitTrap):
    """Trap based on angular stripes — distance from horizontal/vertical axis bands.

    Produces radiating stripe patterns.
    """

    def __init__(self, count=12, width=0.5):
        self.count = int(count)
        self.width = float(width)

    def distance(self, z):
        if z == 0:
            return 0.0
        angle = math.atan2(z.imag, z.real)
        mod = (angle / (2 * math.pi) * self.count) % 1.0
        return min(mod, 1.0 - mod) ** 2


class SpiralTrap(OrbitTrap):
    """Spiral trap — distance from an Archimedean spiral."""

    def __init__(self, tightness=0.3):
        self.tightness = float(tightness)

    def distance(self, z):
        if z == 0:
            return 0.0
        r = abs(z)
        theta = math.atan2(z.imag, z.real)
        # distance to nearest spiral arm
        target_r = self.tightness * theta
        d = r - target_r
        return d * d


TRAPS = {
    "point": PointTrap,
    "line": LineTrap,
    "circle": CircleTrap,
    "cross": CrossTrap,
    "stripe": StripeTrap,
    "spiral": SpiralTrap,
}


def make_trap(name: str, **kw):
    """Construct an orbit trap by name."""
    if name not in TRAPS:
        raise ValueError(f"Unknown trap {name!r}; options: {list(TRAPS)}")
    return TRAPS[name](**kw)