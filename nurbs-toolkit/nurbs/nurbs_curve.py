"""NURBS curves — rational B-splines with weights.

A NURBS curve is the projective image of a B-spline in homogeneous
coordinates.  Each control point ``P_i`` has an associated weight
``w_i > 0``.
"""

from __future__ import annotations

import math
from typing import Sequence, List, Tuple

from .bspline import find_span, basis_functions, basis_functions_derivatives


class NURBSCurve:
    """A NURBS curve in arbitrary dimension (typically 2-D or 3-D)."""

    def __init__(
        self,
        degree: int,
        knots: Sequence[float],
        control_points: Sequence[Sequence[float]],
        weights: Sequence[float] | None = None,
    ):
        self.degree = int(degree)
        self.knots = [float(k) for k in knots]
        self.control_points = [list(map(float, cp)) for cp in control_points]
        self.n = len(self.control_points) - 1
        if weights is None:
            self.weights = [1.0] * (self.n + 1)
        else:
            if len(weights) != self.n + 1:
                raise ValueError("weights length must match control points")
            self.weights = [float(w) for w in weights]
            for w in self.weights:
                if w <= 0:
                    raise ValueError("weights must be positive")
        self.dim = len(self.control_points[0]) if self.control_points else 0

    # -- evaluation --------------------------------------------------
    def evaluate(self, u: float) -> List[float]:
        span = find_span(self.n, self.degree, u, self.knots)
        N = basis_functions(span, u, self.degree, self.knots)
        p = self.degree
        dim = self.dim
        numer = [0.0] * dim
        denom = 0.0
        for j in range(p + 1):
            idx = span - p + j
            wN = N[j] * self.weights[idx]
            denom += wN
            for d in range(dim):
                numer[d] += wN * self.control_points[idx][d]
        if denom == 0.0:
            return [0.0] * dim
        return [v / denom for v in numer]

    def derivative(self, u: float, order: int = 1) -> List[float]:
        """NURBS derivative via quotient rule on homogeneous coordinates."""
        if order == 0:
            return self.evaluate(u)
        # Compute derivatives of numerator A(u) and denominator w(u).
        span = find_span(self.n, self.degree, u, self.knots)
        ders = basis_functions_derivatives(
            span, u, self.degree, order, self.knots
        )
        p = self.degree
        dim = self.dim
        Aders = [[0.0] * dim for _ in range(order + 1)]
        wders = [0.0] * (order + 1)
        for j in range(p + 1):
            idx = span - p + j
            w = self.weights[idx]
            for k in range(order + 1):
                wders[k] += ders[k][j] * w
                for d in range(dim):
                    Aders[k][d] += ders[k][j] * w * self.control_points[idx][d]
        # A'(u) = (w * C')'  =>  C' = (A' - w' C) / w
        # General formula (NURBS Book Eq. 4.14–4.15):
        # C^(k) = ( A^(k) - sum_{i=1}^{k} C^(k-i) * w^(i) ) / w
        CK = [[0.0] * dim for _ in range(order + 1)]
        for k in range(order + 1):
            v = list(Aders[k])
            for i in range(1, k + 1):
                wi = wders[i]
                for d in range(dim):
                    v[d] -= wi * CK[k - i][d]
            for d in range(dim):
                CK[k][d] = v[d] / wders[0] if wders[0] != 0 else 0.0
        return CK[order]

    def tangent(self, u: float) -> List[float]:
        d = self.derivative(u, 1)
        norm = math.sqrt(sum(x * x for x in d)) or 1.0
        return [x / norm for x in d]

    # -- helpers -----------------------------------------------------
    @property
    def parameter_range(self) -> Tuple[float, float]:
        return (self.knots[self.degree], self.knots[self.n + 1])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"NURBSCurve(degree={self.degree}, n={self.n}, "
            f"dim={self.dim}, range={self.parameter_range})"
        )