"""vec.py — 3D vector math for the ray tracer.

Pure-Python small vector type used by the geometry / shading code so the
tracer is easy to read and reason about.  All operations return *new* Vec3
instances (vectors are immutable by convention) which keeps the math readable
and avoids aliasing bugs.
"""

from __future__ import annotations

import math
from typing import Tuple

__all__ = ["Vec3"]


class Vec3:
    """An immutable 3-component vector with operator overloading."""

    __slots__ = ("x", "y", "z")
    _zero: "Vec3 | None" = None

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        object.__setattr__(self, "x", float(x))
        object.__setattr__(self, "y", float(y))
        object.__setattr__(self, "z", float(z))

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def zero(cls) -> "Vec3":
        if cls._zero is None:
            cls._zero = cls(0.0, 0.0, 0.0)
        return cls._zero

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float]) -> "Vec3":
        return cls(t[0], t[1], t[2])

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    # ------------------------------------------------------------------ #
    # Arithmetic
    # ------------------------------------------------------------------ #
    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, s: float | int | "Vec3") -> "Vec3":
        if isinstance(s, Vec3):
            return Vec3(self.x * s.x, self.y * s.y, self.z * s.z)
        return Vec3(self.x * s, self.y * s, self.z * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float | int) -> "Vec3":
        if s == 0:
            raise ZeroDivisionError("Vec3 division by zero")
        return Vec3(self.x / s, self.y / s, self.z / s)

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    def __eq__(self, other: object) -> bool:  # noqa: D401
        if not isinstance(other, Vec3):
            return NotImplemented
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))

    # ------------------------------------------------------------------ #
    # Vector ops
    # ------------------------------------------------------------------ #
    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalized(self) -> "Vec3":
        n = self.length()
        if n == 0.0:
            raise ValueError("Cannot normalize a zero-length vector")
        return Vec3(self.x / n, self.y / n, self.z / n)

    def reflect(self, normal: "Vec3") -> "Vec3":
        """Reflect *self* about *normal* (which must be unit length)."""
        return self - normal * (2.0 * self.dot(normal))

    def refract(self, normal: "Vec3", eta: float) -> "Vec3":
        """Snell refraction.  Returns the transmitted direction.

        Uses the common formulation:  ``k = ((n·I) + eta*(n·I - n·I)) ...``
        implemented with the Fresnel-safe ``k`` computation.  ``eta`` is the
        ratio n1/n2 of the incident / transmitted medium.
        """
        cos_i = -self.dot(normal)
        sin_t2 = eta * eta * (1.0 - cos_i * cos_i)
        if sin_t2 > 1.0:
            # Total internal reflection — caller should detect & reflect.
            return self.reflect(normal)
        cos_t = math.sqrt(1.0 - sin_t2)
        return self * eta + normal * (eta * cos_i - cos_t)

    def lerp(self, other: "Vec3", t: float) -> "Vec3":
        t = max(0.0, min(1.0, t))
        return Vec3(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t,
            self.z + (other.z - self.z) * t,
        )

    def component_min(self) -> float:
        return min(self.x, self.y, self.z)

    def component_max(self) -> float:
        return max(self.x, self.y, self.z)

    def clamp(self, lo: float = 0.0, hi: float = 1.0) -> "Vec3":
        return Vec3(
            max(lo, min(hi, self.x)),
            max(lo, min(hi, self.y)),
            max(lo, min(hi, self.z)),
        )

    def __repr__(self) -> str:
        return f"Vec3({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z