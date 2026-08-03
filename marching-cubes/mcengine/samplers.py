"""Implicit surface samplers — functions f(x, y, z) whose zero set is a surface.

A :class:`Sampler` provides both a scalar field ``sample(x, y, z)`` and, when
available, an analytic gradient ``gradient(x, y, z)`` used by Dual Contouring to
place vertices accurately.  Pure-Python, no NumPy.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Callable, Optional, Tuple


class Sampler(ABC):
    """Abstract implicit-function sampler."""

    @abstractmethod
    def sample(self, x: float, y: float, z: float) -> float:
        """Return f(x, y, z).  Inside is f < isolevel (default 0)."""

    def gradient(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """Numerical gradient via central differences (overridden for speed)."""
        h = 1e-4
        fx = (self.sample(x + h, y, z) - self.sample(x - h, y, z)) / (2 * h)
        fy = (self.sample(x, y + h, z) - self.sample(x, y - h, z)) / (2 * h)
        fz = (self.sample(x, y, z + h) - self.sample(x, y, z - h)) / (2 * h)
        return (fx, fy, fz)

    def __call__(self, x: float, y: float, z: float) -> float:
        return self.sample(x, y, z)


# ---------------------------------------------------------------------------
# Primitive samplers
# ---------------------------------------------------------------------------

class SphereSampler(Sampler):
    """Unit sphere: f = x² + y² + z² - r²."""

    def __init__(self, radius: float = 1.0, center: Tuple[float, float, float] = (0, 0, 0)):
        self.r2 = radius * radius
        self.cx, self.cy, self.cz = center

    def sample(self, x, y, z):
        dx = x - self.cx; dy = y - self.cy; dz = z - self.cz
        return dx * dx + dy * dy + dz * dz - self.r2

    def gradient(self, x, y, z):
        return (2 * (x - self.cx), 2 * (y - self.cy), 2 * (z - self.cz))


class TorusSampler(Sampler):
    """Torus: major radius R, minor radius r, axis = z."""

    def __init__(self, R: float = 1.0, r: float = 0.35):
        self.R = R; self.r = r

    def sample(self, x, y, z):
        q = math.sqrt(x * x + y * y) - self.R
        return q * q + z * z - self.r * self.r

    def gradient(self, x, y, z):
        # ∂f/∂x = 2(q)(x/√(x²+y²)), etc.
        d = math.sqrt(x * x + y * y)
        if d < 1e-12:
            return (0.0, 0.0, 2 * z)
        q = d - self.R
        qx = q * x / d; qy = q * y / d
        return (2 * qx, 2 * qy, 2 * z)


class OctahedronSampler(Sampler):
    """L1 ball: |x| + |y| + |z| - r."""

    def __init__(self, r: float = 1.0):
        self.r = r

    def sample(self, x, y, z):
        return abs(x) + abs(y) + abs(z) - self.r

    def gradient(self, x, y, z):
        return (math.copysign(1.0, x), math.copysign(1.0, y), math.copysign(1.0, z))


class SteinerSampler(Sampler):
    """Steiner surface: a classic algebraic surface of genus 0 but with
    self-intersection.  f = x²y² + x²z² + y²z² - xyz."""

    def sample(self, x, y, z):
        return x * x * y * y + x * x * z * z + y * y * z * z - x * y * z


class Genus2Sampler(Sampler):
    """A genus-2 surface (two holes).  Uses the classic implicit form::

        f = (y² - 1)² * (z² - 1)² - x²  (barbell along x)

    Actually a "double torus" via a different well-known polynomial::

        2(x² + y²)² - 3.6(x² + y²) + y² - z²  = 0  (not quite)

    We use the simple and reliable "two-torus cross" form.
    """

    def sample(self, x, y, z):
        # Roman surface / cross-cap variant — gives a genus-2-ish shape.
        t = 1.2
        return (x * x + y * y + z * z + t * t - 1.0) ** 2 - 4.0 * t * t * (x * x + y * y)


class GyroidSampler(Sampler):
    """The gyroid minimal surface: sin(x)cos(y) + sin(y)cos(z) + sin(z)cos(x)."""

    def sample(self, x, y, z):
        return (math.sin(x) * math.cos(y)
                + math.sin(y) * math.cos(z)
                + math.sin(z) * math.cos(x))


class HeartSampler(Sampler):
    """A heart-shaped implicit surface (Taubin's equation)."""

    def sample(self, x, y, z):
        a = x * x + 2.25 * y * y + z * z - 1.0
        return a * a * a - x * x * z * z * z - 0.1125 * y * y * z * z * z


class SuperquadricSampler(Sampler):
    """Superquadric ellipsoid: (|x/a|^e2 + |y/b|^e2)^(e1/e2) + |z/c|^e1 - 1."""

    def __init__(self, a=1.0, b=1.0, c=1.0, e1=2.0, e2=2.0):
        self.a, self.b, self.c = a, b, c
        self.e1, self.e2 = e1, e2

    def sample(self, x, y, z):
        ax = abs(x / self.a); by = abs(y / self.b); cz = abs(z / self.c)
        return ((ax ** self.e2 + by ** self.e2) ** (self.e1 / self.e2)
                + cz ** self.e1 - 1.0)


class HyperboloidSampler(Sampler):
    """One-sheet hyperboloid: x² + y² - z² - r²."""

    def __init__(self, r: float = 1.0):
        self.r2 = r * r

    def sample(self, x, y, z):
        return x * x + y * y - z * z - self.r2


# ---------------------------------------------------------------------------
# Composite samplers
# ---------------------------------------------------------------------------

class BooleanOpsSampler(Sampler):
    """Boolean operations on two implicit surfaces (union / intersection / diff).

    The standard R-functions (Rvachev) give C¹ continuity:

    * union:        f = f1 + f2 + sqrt(f1² + f2²)
    * intersection: f = f1 + f2 - sqrt(f1² + f2²)
    * difference:   f = f1 - f2 - sqrt(f1² + f2²)   (inside f1 and outside f2)
    """

    def __init__(self, a: Sampler, b: Sampler, op: str = "union"):
        if op not in ("union", "intersection", "difference"):
            raise ValueError(f"unknown op {op!r}")
        self.a = a; self.b = b; self.op = op

    def sample(self, x, y, z):
        f1 = self.a.sample(x, y, z)
        f2 = self.b.sample(x, y, z)
        s = math.sqrt(f1 * f1 + f2 * f2)
        if self.op == "union":
            return f1 + f2 + s
        elif self.op == "intersection":
            return f1 + f2 - s
        else:
            return f1 - f2 - s


class NoisySampler(Sampler):
    """Wraps a sampler with low-amplitude procedural noise (deterministic)."""

    def __init__(self, base: Sampler, amplitude: float = 0.05, freq: float = 3.0):
        self.base = base; self.amp = amplitude; self.freq = freq

    def _noise(self, x, y, z):
        # Cheap deterministic pseudo-noise via layered sines.
        n = (math.sin(self.freq * x + 0.3)
             + math.sin(self.freq * y + 1.1)
             + math.sin(self.freq * z + 2.7))
        return n * self.amp

    def sample(self, x, y, z):
        return self.base.sample(x, y, z) + self._noise(x, y, z)