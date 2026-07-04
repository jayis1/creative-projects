"""2D vector utilities (pure Python, no external deps).

A lightweight 2-vector class with all operations the physics engine needs.
Keeping it dependency-free makes the engine portable and easy to embed.
"""

from __future__ import annotations

import math
from typing import Iterable, Tuple

__all__ = ["Vec2"]


class Vec2:
    """Immutable 2D vector with operator overloading.

    All arithmetic operations return *new* Vec2 instances; the object is
    treated as a value type.  Equality is exact (no epsilon) — use
    :meth:`almost_eq` when comparing floating results.
    """

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = float(x)
        self.y = float(y)

    # ------------------------------------------------------------------ #
    # construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def from_angle(cls, angle: float, length: float = 1.0) -> "Vec2":
        """Unit vector rotated by *angle* radians, scaled by *length*."""
        return cls(math.cos(angle) * length, math.sin(angle) * length)

    @classmethod
    def zero(cls) -> "Vec2":
        return cls(0.0, 0.0)

    # ------------------------------------------------------------------ #
    # basic algebra
    # ------------------------------------------------------------------ #
    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        s = float(scalar)
        return Vec2(self.x * s, self.y * s)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> "Vec2":
        s = float(scalar)
        if s == 0.0:
            raise ZeroDivisionError("cannot divide Vec2 by zero")
        return Vec2(self.x / s, self.y / s)

    def __neg__(self) -> "Vec2":
        return Vec2(-self.x, -self.y)

    def __pos__(self) -> "Vec2":
        return Vec2(self.x, self.y)

    # ------------------------------------------------------------------ #
    # products
    # ------------------------------------------------------------------ #
    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: "Vec2") -> float:
        """2D scalar cross product: ``self.x*other.y - self.y*other.x``."""
        return self.x * other.y - self.y * other.x

    def cross_scalar(self, s: float) -> "Vec2":
        """Cross of a scalar (z-axis) with this vector: ``(s*self.y, -s*self.x)``."""
        return Vec2(-s * self.y, s * self.x)

    # ------------------------------------------------------------------ #
    # geometry
    # ------------------------------------------------------------------ #
    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalize(self) -> "Vec2":
        ln = self.length()
        if ln == 0.0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / ln, self.y / ln)

    def perpendicular(self) -> "Vec2":
        """Left-hand perpendicular ``(−y, x)``."""
        return Vec2(-self.y, self.x)

    def rotate(self, angle: float) -> "Vec2":
        c, s = math.cos(angle), math.sin(angle)
        return Vec2(self.x * c - self.y * s, self.x * s + self.y * c)

    def angle(self) -> float:
        return math.atan2(self.y, self.x)

    # ------------------------------------------------------------------ #
    # comparison / repr
    # ------------------------------------------------------------------ #
    def almost_eq(self, other: "Vec2", eps: float = 1e-9) -> bool:
        return abs(self.x - other.x) <= eps and abs(self.y - other.y) <= eps

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vec2):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self) -> str:
        return f"Vec2({self.x!r}, {self.y!r})"

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @staticmethod
    def axis_y() -> "Vec2":
        return Vec2(0.0, 1.0)

    @staticmethod
    def axis_x() -> "Vec2":
        return Vec2(1.0, 0.0)