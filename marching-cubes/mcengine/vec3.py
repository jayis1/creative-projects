"""Minimal 3-D vector helpers (pure Python, no NumPy)."""

from __future__ import annotations

import math
from typing import Iterable, Tuple


class Vec3(tuple):
    """An immutable 3-vector, subclasses ``tuple`` for cheap unpacking."""

    __slots__ = ()

    def __new__(cls, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> "Vec3":
        return tuple.__new__(cls, (float(x), float(y), float(z)))

    # --- accessors ---------------------------------------------------------
    @property
    def x(self) -> float: return self[0]

    @property
    def y(self) -> float: return self[1]

    @property
    def z(self) -> float: return self[2]

    # --- arithmetic --------------------------------------------------------
    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self[0] + other[0], self[1] + other[1], self[2] + other[2])

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self[0] - other[0], self[1] - other[1], self[2] - other[2])

    def __mul__(self, s: float) -> "Vec3":
        return Vec3(self[0] * s, self[1] * s, self[2] * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float) -> "Vec3":
        return Vec3(self[0] / s, self[1] / s, self[2] / s)

    def __neg__(self) -> "Vec3":
        return Vec3(-self[0], -self[1], -self[2])

    # --- geometry ----------------------------------------------------------
    def dot(self, other: "Vec3") -> float:
        return self[0] * other[0] + self[1] * other[1] + self[2] * other[2]

    def length(self) -> float:
        return math.sqrt(self[0] * self[0] + self[1] * self[1] + self[2] * self[2])

    def length_sq(self) -> float:
        return self[0] * self[0] + self[1] * self[1] + self[2] * self[2]

    def normalized(self) -> "Vec3":
        L = self.length()
        if L == 0.0:
            return Vec3(0.0, 0.0, 0.0)
        return Vec3(self[0] / L, self[1] / L, self[2] / L)


def dot(a: Iterable[float], b: Iterable[float]) -> float:
    """Dot product of two 3-vectors (accepts any 3-element iterable)."""
    ai = list(a); bi = list(b)
    return ai[0] * bi[0] + ai[1] * bi[1] + ai[2] * bi[2]


def cross(a: Iterable[float], b: Iterable[float]) -> Vec3:
    """Cross product ``a × b``."""
    ax, ay, az = a
    bx, by, bz = b
    return Vec3(ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)


def normalize(v: Iterable[float]) -> Vec3:
    """Return the unit vector of ``v`` (zero-safe)."""
    vx, vy, vz = v
    L = math.sqrt(vx * vx + vy * vy + vz * vz)
    if L == 0.0:
        return Vec3(0.0, 0.0, 0.0)
    return Vec3(vx / L, vy / L, vz / L)


def add(a, b) -> Vec3:
    return Vec3(a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b) -> Vec3:
    return Vec3(a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a, s: float) -> Vec3:
    return Vec3(a[0] * s, a[1] * s, a[2] * s)