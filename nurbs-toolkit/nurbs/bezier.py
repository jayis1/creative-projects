"""Bezier curves — a special case of B-splines.

Provides de Casteljau evaluation and conversion to an equivalent
B-spline representation.
"""

from __future__ import annotations

import math
from typing import Sequence, List, Tuple

from .bspline import BSplineCurve


class BezierCurve:
    """A Bezier curve of degree ``len(control_points) - 1``."""

    def __init__(self, control_points: Sequence[Sequence[float]]):
        self.control_points = [list(map(float, cp)) for cp in control_points]
        if len(self.control_points) < 2:
            raise ValueError("Need at least 2 control points")
        self.degree = len(self.control_points) - 1
        self.dim = len(self.control_points[0])

    def evaluate(self, t: float) -> List[float]:
        """De Casteljau algorithm at parameter *t* in [0, 1]."""
        pts = [list(cp) for cp in self.control_points]
        n = self.degree
        for k in range(1, n + 1):
            for i in range(n - k + 1):
                for d in range(self.dim):
                    pts[i][d] = (1 - t) * pts[i][d] + t * pts[i + 1][d]
        return pts[0]

    def derivative(self, t: float, order: int = 1) -> List[float]:
        """Analytic derivative of a Bezier curve (hodograph)."""
        if order == 0:
            return self.evaluate(t)
        # Derivative control points: Q_i = n*(P_{i+1} - P_i)
        cp = self.control_points
        n = self.degree
        dim = self.dim
        q = [[n * (cp[i + 1][d] - cp[i][d]) for d in range(dim)]
             for i in range(n)]
        # Reduce degree by 1 per derivative order.
        sub = BezierCurve(q) if len(q) >= 2 else None
        if sub is None:
            # Constant derivative.
            return list(q[0]) if q else [0.0] * dim
        return sub.derivative(t, order - 1)

    def tangent(self, t: float) -> List[float]:
        d = self.derivative(t, 1)
        norm = math.sqrt(sum(x * x for x in d)) or 1.0
        return [x / norm for x in d]

    def elevate_degree(self) -> "BezierCurve":
        """Return a new Bezier curve of degree+1 representing the same curve."""
        n = self.degree
        cp = self.control_points
        dim = self.dim
        new_cp = [[0.0] * dim for _ in range(n + 2)]
        new_cp[0] = list(cp[0])
        new_cp[-1] = list(cp[-1])
        for i in range(1, n + 1):
            ratio = i / (n + 1)
            for d in range(dim):
                new_cp[i][d] = ratio * cp[i - 1][d] + (1 - ratio) * cp[i][d]
        return BezierCurve(new_cp)

    def subdivide(self, t: float = 0.5) -> Tuple["BezierCurve", "BezierCurve"]:
        """Subdivide at parameter *t* into two Bezier curves."""
        pts = [list(cp) for cp in self.control_points]
        n = self.degree
        left = [list(pts[0])]
        right = [list(pts[-1])]
        for k in range(1, n + 1):
            for i in range(n - k + 1):
                for d in range(self.dim):
                    pts[i][d] = (1 - t) * pts[i][d] + t * pts[i + 1][d]
            left.append(list(pts[0]))
            right.append(list(pts[n - k]))
        right.reverse()
        return BezierCurve(left), BezierCurve(right)

    def __repr__(self) -> str:  # pragma: no cover
        return f"BezierCurve(degree={self.degree}, dim={self.dim})"


def bezier_to_bspline(bezier: BezierCurve) -> BSplineCurve:
    """Convert a Bezier curve to an equivalent clamped B-spline."""
    from .knot_vector import generate_clamped_uniform_knot_vector

    n = bezier.degree
    p = bezier.degree
    knots = generate_clamped_uniform_knot_vector(n, p)
    return BSplineCurve(p, knots, bezier.control_points)