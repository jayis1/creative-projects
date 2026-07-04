"""2x2 matrix utilities used by the rigid-body engine.

The physics solver needs to assemble and invert 2x2 effective-mass matrices
for each contact / joint constraint.  A tiny dedicated matrix type keeps that
code readable and dependency-free.
"""

from __future__ import annotations

import math
from typing import List, Tuple

__all__ = ["Mat22", "solve_2x2"]


class Mat22:
    """Immutable 2x2 matrix stored row-major.

    ``m[[a, b], [c, d]]`` corresponds to ``Mat22(a, b, c, d)`` with::

            | a  b |
            | c  d |
    """

    __slots__ = ("a", "b", "c", "d")

    def __init__(self, a: float, b: float, c: float, d: float) -> None:
        self.a = float(a)
        self.b = float(b)
        self.c = float(c)
        self.d = float(d)

    # ------------------------------------------------------------------ #
    # factories
    # ------------------------------------------------------------------ #
    @classmethod
    def identity(cls) -> "Mat22":
        return cls(1.0, 0.0, 0.0, 1.0)

    @classmethod
    def rotation(cls, angle: float) -> "Mat22":
        c, s = math.cos(angle), math.sin(angle)
        return cls(c, -s, s, c)

    # ------------------------------------------------------------------ #
    # ops
    # ------------------------------------------------------------------ #
    def multiply_vec(self, x: float, y: float) -> Tuple[float, float]:
        """Return M @ (x, y)."""
        return (self.a * x + self.b * y, self.c * x + self.d * y)

    def transpose_multiply_vec(self, x: float, y: float) -> Tuple[float, float]:
        """Return M^T @ (x, y)."""
        return (self.a * x + self.c * y, self.b * x + self.d * y)

    def determinant(self) -> float:
        return self.a * self.d - self.b * self.c

    def inverse(self) -> "Mat22":
        det = self.determinant()
        if det == 0.0:
            raise ZeroDivisionError("matrix is singular")
        inv_det = 1.0 / det
        return Mat22(
            self.d * inv_det,
            -self.b * inv_det,
            -self.c * inv_det,
            self.a * inv_det,
        )

    def __repr__(self) -> str:
        return f"Mat22({self.a}, {self.b}, {self.c}, {self.d})"


def solve_2x2(
    a: float, b: float, c: float, d: float, x: float, y: float
) -> Tuple[float, float]:
    """Solve ``[[a,b],[c,d]] @ (s,t) = (x,y)`` via Cramer's rule.

    Returns ``(s, t)``.  Raises :class:`ZeroDivisionError` if the matrix is
    singular.
    """
    det = a * d - b * c
    if det == 0.0:
        raise ZeroDivisionError("singular system")
    inv = 1.0 / det
    return ((d * x - b * y) * inv, (-c * x + a * y) * inv)