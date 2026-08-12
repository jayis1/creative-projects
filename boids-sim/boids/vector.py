"""2D vector math for boids — minimal, allocation-friendly."""

from __future__ import annotations
import math
from typing import Iterable


class Vector2:
    """Simple mutable 2D vector with common operations."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    # --- factory methods ---
    @classmethod
    def from_angle(cls, angle: float, length: float = 1.0) -> "Vector2":
        return cls(math.cos(angle) * length, math.sin(angle) * length)

    @classmethod
    def random(cls, min_val: float = 0.0, max_val: float = 1.0) -> "Vector2":
        import random as _r
        return cls(_r.uniform(min_val, max_val), _r.uniform(min_val, max_val))

    @classmethod
    def random_unit(cls) -> "Vector2":
        import random as _r
        angle = _r.uniform(0, math.tau)
        return cls(math.cos(angle), math.sin(angle))

    # --- properties ---
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    @property
    def angle(self) -> float:
        return math.atan2(self.y, self.x)

    def copy(self) -> "Vector2":
        return Vector2(self.x, self.y)

    # --- in-place arithmetic (avoids allocation) ---
    def add(self, other: "Vector2") -> "Vector2":
        self.x += other.x
        self.y += other.y
        return self

    def sub(self, other: "Vector2") -> "Vector2":
        self.x -= other.x
        self.y -= other.y
        return self

    def scale(self, s: float) -> "Vector2":
        self.x *= s
        self.y *= s
        return self

    def limit(self, max_len: float) -> "Vector2":
        """Scale this vector so its length does not exceed max_len (in-place)."""
        sq = self.x * self.x + self.y * self.y
        if sq > max_len * max_len:
            factor = max_len / math.sqrt(sq)
            self.x *= factor
            self.y *= factor
        return self

    def set_length(self, length: float) -> "Vector2":
        """Scale this vector to exactly *length* (in-place)."""
        sq = self.x * self.x + self.y * self.y
        if sq > 1e-12:
            factor = length / math.sqrt(sq)
            self.x *= factor
            self.y *= factor
        return self

    def normalize(self) -> "Vector2":
        sq = self.x * self.x + self.y * self.y
        if sq > 1e-12:
            factor = 1.0 / math.sqrt(sq)
            self.x *= factor
            self.y *= factor
        return self

    # --- functional operations (return new vectors) ---
    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, s: float) -> "Vector2":
        return Vector2(self.x * s, self.y * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float) -> "Vector2":
        return Vector2(self.x / s, self.y / s)

    def __neg__(self) -> "Vector2":
        return Vector2(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self) -> str:
        return f"Vector2({self.x:.3f}, {self.y:.3f})"

    # --- static helpers ---
    @staticmethod
    def dist(a: "Vector2", b: "Vector2") -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def dist_sq(a: "Vector2", b: "Vector2") -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        return dx * dx + dy * dy

    @staticmethod
    def angle_between(a: "Vector2", b: "Vector2") -> float:
        """Angle (radians) between two vectors."""
        dot = a.x * b.x + a.y * b.y
        la = a.length()
        lb = b.length()
        if la < 1e-12 or lb < 1e-12:
            return 0.0
        cos_v = max(-1.0, min(1.0, dot / (la * lb)))
        return math.acos(cos_v)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, t: Iterable[float]) -> "Vector2":
        items = list(t)
        return cls(items[0], items[1])