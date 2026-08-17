"""Tensor-product NURBS surfaces."""

from __future__ import annotations

import math
from typing import Sequence, List, Tuple

from .bspline import find_span, basis_functions, basis_functions_derivatives
from .knot_vector import validate_knot_vector
from .exceptions import InvalidWeight, InvalidControlPoint


class NURBSSurface:
    """A tensor-product NURBS surface.

    Parameters
    ----------
    degree_u, degree_v : int
        Degrees in each parametric direction.
    knots_u, knots_v : sequence[float]
        Knot vectors.
    control_points : 2-D sequence
        ``control_points[i][j]`` is the (x, y, z) coordinate of the
        control point at row *i* (u-direction), column *j* (v-direction).
    weights : 2-D sequence or None
        Optional weight grid matching the control-point grid.
    """

    def __init__(
        self,
        degree_u: int,
        degree_v: int,
        knots_u: Sequence[float],
        knots_v: Sequence[float],
        control_points: Sequence[Sequence[Sequence[float]]],
        weights: Sequence[Sequence[float]] | None = None,
    ):
        if degree_u < 0 or degree_v < 0:
            raise ValueError("degrees must be non-negative")
        self.degree_u = int(degree_u)
        self.degree_v = int(degree_v)
        self.knots_u = [float(k) for k in knots_u]
        self.knots_v = [float(k) for k in knots_v]
        self.control_points = [
            [list(map(float, cp)) for cp in row] for row in control_points
        ]
        if not self.control_points or not self.control_points[0]:
            raise InvalidControlPoint("need at least a 1x1 control grid")
        self.nu = len(self.control_points) - 1
        self.nv = len(self.control_points[0]) - 1
        # Verify all rows have the same number of columns.
        for row in self.control_points:
            if len(row) != self.nv + 1:
                raise InvalidControlPoint(
                    "all rows must have the same number of columns"
                )
        self.dim = len(self.control_points[0][0])
        for row in self.control_points:
            for cp in row:
                if len(cp) != self.dim:
                    raise InvalidControlPoint(
                        "all control points must have the same dimension"
                    )
        validate_knot_vector(self.knots_u, self.nu, self.degree_u)
        validate_knot_vector(self.knots_v, self.nv, self.degree_v)

        if weights is None:
            self.weights = [[1.0] * (self.nv + 1) for _ in range(self.nu + 1)]
        else:
            self.weights = [[float(w) for w in row] for row in weights]
            if len(self.weights) != self.nu + 1 or any(
                len(r) != self.nv + 1 for r in self.weights
            ):
                raise InvalidWeight("weight grid shape must match control points")
            for row in self.weights:
                for w in row:
                    if w <= 0:
                        raise InvalidWeight("weights must be positive")

    def evaluate(self, u: float, v: float) -> List[float]:
        span_u = find_span(self.nu, self.degree_u, u, self.knots_u)
        span_v = find_span(self.nv, self.degree_v, v, self.knots_v)
        Nu = basis_functions(span_u, u, self.degree_u, self.knots_u)
        Nv = basis_functions(span_v, v, self.degree_v, self.knots_v)
        pu, pv = self.degree_u, self.degree_v
        dim = self.dim
        numer = [0.0] * dim
        denom = 0.0
        for j in range(pu + 1):
            iu = span_u - pu + j
            for k in range(pv + 1):
                iv = span_v - pv + k
                wN = Nu[j] * Nv[k] * self.weights[iu][iv]
                denom += wN
                for d in range(dim):
                    numer[d] += wN * self.control_points[iu][iv][d]
        if denom == 0.0:
            return [0.0] * dim
        return [x / denom for x in numer]

    def derivative(self, u: float, v: float, du: int = 1, dv: int = 0) -> List[float]:
        """Partial derivative ``d^{du+dv}S/du^{du}dv^{dv}``.

        Only first-order partials are implemented via the homogeneous
        quotient rule (higher orders fall back to numeric differences).
        """
        if du == 0 and dv == 0:
            return self.evaluate(u, v)
        if (du <= 1 and dv <= 1) and not (du == 1 and dv == 1):
            return self._first_partial(u, v, du, dv)
        # Higher-order / mixed: numeric fallback.
        h = 1e-6
        pt0 = self.evaluate(u, v)
        if du >= 1 and dv >= 1:
            pu1 = self.derivative(u + h, v, du - 1, dv)
            pu0 = self.derivative(u - h, v, du - 1, dv)
            return [(a - b) / (2 * h) for a, b in zip(pu1, pu0)]
        if du >= 1:
            p1 = self.derivative(u + h, v, du - 1, dv)
            p0 = self.derivative(u - h, v, du - 1, dv)
            return [(a - b) / (2 * h) for a, b in zip(p1, p0)]
        # dv >= 1
        p1 = self.derivative(u, v + h, du, dv - 1)
        p0 = self.derivative(u, v - h, du, dv - 1)
        return [(a - b) / (2 * h) for a, b in zip(p1, p0)]

    def _first_partial(self, u: float, v: float, du: int, dv: int) -> List[float]:
        span_u = find_span(self.nu, self.degree_u, u, self.knots_u)
        span_v = find_span(self.nv, self.degree_v, v, self.knots_v)
        Nu = basis_functions_derivatives(
            span_u, u, self.degree_u, du, self.knots_u
        )
        Nv = basis_functions_derivatives(
            span_v, v, self.degree_v, dv, self.knots_v
        )
        pu, pv = self.degree_u, self.degree_v
        dim = self.dim
        numer = [0.0] * dim
        denom = 0.0
        for j in range(pu + 1):
            iu = span_u - pu + j
            for k in range(pv + 1):
                iv = span_v - pv + k
                wN = Nu[du][j] * Nv[dv][k] * self.weights[iu][iv]
                denom += wN
                for d in range(dim):
                    numer[d] += wN * self.control_points[iu][iv][d]
        # Quotient rule with denominator of plain evaluation.
        S = self.evaluate(u, v)
        w0 = 0.0
        Nu0 = basis_functions(span_u, u, self.degree_u, self.knots_u)
        Nv0 = basis_functions(span_v, v, self.degree_v, self.knots_v)
        for j in range(pu + 1):
            iu = span_u - pu + j
            for k in range(pv + 1):
                iv = span_v - pv + k
                w0 += Nu0[j] * Nv0[k] * self.weights[iu][iv]
        if w0 == 0:
            return [0.0] * dim
        return [(numer[d] - S[d] * denom) / w0 for d in range(dim)]

    def normal(self, u: float, v: float) -> List[float]:
        """Surface normal (unit) at (u, v) via cross product of partials."""
        du = self._first_partial(u, v, 1, 0)
        dv = self._first_partial(u, v, 0, 1)
        n = [
            du[1] * dv[2] - du[2] * dv[1],
            du[2] * dv[0] - du[0] * dv[2],
            du[0] * dv[1] - du[1] * dv[0],
        ]
        norm = math.sqrt(sum(x * x for x in n))
        if norm < 1e-14:
            return [0.0, 0.0, 0.0]
        return [x / norm for x in n]

    @property
    def parameter_range(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return (
            (self.knots_u[self.degree_u], self.knots_u[self.nu + 1]),
            (self.knots_v[self.degree_v], self.knots_v[self.nv + 1]),
        )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"NURBSSurface(deg=({self.degree_u},{self.degree_v}), "
            f"size=({self.nu+1}x{self.nv+1}), dim={self.dim})"
        )