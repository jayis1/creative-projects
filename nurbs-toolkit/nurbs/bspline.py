"""Core B-spline basis functions and curve evaluation.

Implements the Cox–de Boor recursion for basis function evaluation
and the derivative formula from *The NURBS Book* (Piegl & Tiller).
"""

from __future__ import annotations

import math
from typing import Sequence, List, Tuple

from .knot_vector import validate_knot_vector


def find_span(n: int, p: int, u: float, U: Sequence[float]) -> int:
    """Determine the knot span index for parameter *u*.

    Parameters
    ----------
    n : int
        Highest control-point index (i.e. ``len(P)-1``).
    p : int
        Degree.
    u : float
        Parameter value.
    U : sequence[float]
        Knot vector.

    Returns
    -------
    int
        Span index *k* such that ``U[k] <= u < U[k+1]`` (or ``n`` when
        ``u == U[-1]``).
    """
    if u >= U[n + 1]:  # special case: u at the very end
        # Find the last index where U[i] < U[m] (i.e. last distinct knot
        # before the maximum), but clamp to a valid span.
        # Standard NURBS-Book algorithm:
        return n
    if u <= U[p]:
        return p
    low = p
    high = n + 1
    mid = (low + high) // 2
    while u < U[mid] or u >= U[mid + 1]:
        if u < U[mid]:
            high = mid
        else:
            low = mid
        mid = (low + high) // 2
    return mid


def basis_functions(
    span: int, u: float, p: int, U: Sequence[float]
) -> List[float]:
    """Compute the non-zero B-spline basis functions ``N_{span-p,..,span}``.

    Uses the Cox–de Boor recursion.  Returns a list of length ``p+1``.
    """
    N: List[float] = [0.0] * (p + 1)
    left: List[float] = [0.0] * (p + 1)
    right: List[float] = [0.0] * (p + 1)
    N[0] = 1.0
    for j in range(1, p + 1):
        left[j] = u - U[span + 1 - j]
        right[j] = U[span + j] - u
        saved = 0.0
        for r in range(j):
            temp = N[r] / (right[r + 1] + left[j - r])
            N[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
        N[j] = saved
    return N


def basis_functions_derivatives(
    span: int,
    u: float,
    p: int,
    n_derivatives: int,
    U: Sequence[float],
) -> List[List[float]]:
    """Compute basis functions and their derivatives up to *n_derivatives*.

    Returns a 2-D list ``ders[k][j]`` = k-th derivative of
    ``N_{span-p+j}`` evaluated at *u*.

    Implements Algorithm A2.3 from *The NURBS Book*.
    """
    if n_derivatives < 0:
        raise ValueError("n_derivatives must be >= 0")
    ndu = [[0.0] * (p + 1) for _ in range(p + 1)]
    ndu[0][0] = 1.0
    left = [0.0] * (p + 1)
    right = [0.0] * (p + 1)
    for j in range(1, p + 1):
        left[j] = u - U[span + 1 - j]
        right[j] = U[span + j] - u
        saved = 0.0
        for r in range(j):
            ndu[j][r] = right[r + 1] + left[j - r]
            temp = ndu[r][j - 1] / ndu[j][r]
            ndu[r][j] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
        ndu[j][j] = saved

    ders = [[0.0] * (p + 1) for _ in range(min(n_derivatives, p) + 1)]
    for j in range(p + 1):
        ders[0][j] = ndu[j][p]

    # Compute derivatives.
    a = [[0.0] * (p + 1) for _ in range(2)]
    for r in range(p + 1):
        s1 = 0
        s2 = 1
        a[0][0] = 1.0
        for k in range(1, n_derivatives + 1):
            d = 0.0
            rk = r - k
            pk = p - k
            if r >= k:
                a[s2][0] = a[s1][0] / ndu[pk + 1][rk]
                d = a[s2][0] * ndu[rk][pk]
            if rk >= -1:
                j1 = 1
            else:
                j1 = -rk
            if r - 1 <= pk:
                j2 = k - 1
            else:
                j2 = p - r
            for j in range(j1, j2 + 1):
                a[s2][j] = (a[s1][j] - a[s1][j - 1]) / ndu[pk + 1][rk + j]
                d += a[s2][j] * ndu[rk + j][pk]
            if r <= pk:
                a[s2][k] = -a[s1][k - 1] / ndu[pk + 1][r]
                d += a[s2][k] * ndu[r][pk]
            ders[k][r] = d
            s1, s2 = s2, s1  # swap rows

    # Multiply through by factorials.
    r = p
    for k in range(1, n_derivatives + 1):
        for j in range(p + 1):
            ders[k][j] *= r
        r *= (p - k)
    return ders


class BSplineBasis:
    """A reusable B-spline basis function set.

    Encapsulates a degree and knot vector so basis functions can be
    evaluated repeatedly without re-passing them.
    """

    def __init__(self, degree: int, knots: Sequence[float]):
        if degree < 0:
            raise ValueError("degree must be non-negative")
        self.degree = int(degree)
        self.knots = list(float(k) for k in knots)
        # n = m - p - 1 where m = len(knots) - 1; but the knot vector
        # has m + 1 elements, so n = len(knots) - p - 2.
        self.n = len(self.knots) - self.degree - 2
        validate_knot_vector(self.knots, self.n, self.degree)

    @property
    def num_control_points(self) -> int:
        return self.n + 1

    def span(self, u: float) -> int:
        return find_span(self.n, self.degree, u, self.knots)

    def evaluate(self, u: float) -> List[float]:
        """Return all *non-zero* basis functions at *u* (length ``p+1``)."""
        s = self.span(u)
        return basis_functions(s, u, self.degree, self.knots)

    def evaluate_all(self, u: float) -> List[float]:
        """Return the full basis vector ``N_0..N_n`` at *u*."""
        s = self.span(u)
        nz = basis_functions(s, u, self.degree, self.knots)
        full = [0.0] * (self.n + 1)
        for j, val in enumerate(nz):
            full[s - self.degree + j] = val
        return full

    def derivatives(self, u: float, order: int) -> List[List[float]]:
        """Return derivatives of non-zero basis functions up to *order*."""
        s = self.span(u)
        return basis_functions_derivatives(
            s, u, self.degree, order, self.knots
        )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"BSplineBasis(degree={self.degree}, "
            f"num_cp={self.num_control_points}, knots={self.knots})"
        )


class BSplineCurve:
    """A B-spline curve in arbitrary dimension."""

    def __init__(
        self,
        degree: int,
        knots: Sequence[float],
        control_points: Sequence[Sequence[float]],
    ):
        self.degree = int(degree)
        self.knots = [float(k) for k in knots]
        self.control_points = [list(map(float, cp)) for cp in control_points]
        self.n = len(self.control_points) - 1
        validate_knot_vector(self.knots, self.n, self.degree)
        if self.n < self.degree:
            raise ValueError("Too few control points for this degree")
        self.dim = len(self.control_points[0]) if self.control_points else 0

    # -- evaluation --------------------------------------------------
    def evaluate(self, u: float) -> List[float]:
        """Evaluate the curve at parameter *u*."""
        span = find_span(self.n, self.degree, u, self.knots)
        N = basis_functions(span, u, self.degree, self.knots)
        cp = self.control_points
        p = self.degree
        dim = self.dim
        point = [0.0] * dim
        for j in range(p + 1):
            idx = span - p + j
            w = N[j]
            for d in range(dim):
                point[d] += w * cp[idx][d]
        return point

    def derivative(self, u: float, order: int = 1) -> List[float]:
        """Compute the *order*-th parametric derivative at *u*."""
        span = find_span(self.n, self.degree, u, self.knots)
        ders = basis_functions_derivatives(
            span, u, self.degree, order, self.knots
        )
        p = self.degree
        dim = self.dim
        result = [0.0] * dim
        for j in range(p + 1):
            idx = span - p + j
            for d in range(dim):
                result[d] += ders[order][j] * self.control_points[idx][d]
        return result

    def tangent(self, u: float) -> List[float]:
        """Unit tangent vector at *u*."""
        d = self.derivative(u, 1)
        norm = math.sqrt(sum(x * x for x in d)) or 1.0
        return [x / norm for x in d]

    def normal(self, u: float, up: Sequence[float] = (0.0, 0.0, 1.0)) -> List[float]:
        """Return a normal vector in 3-D (cross of tangent with *up*)."""
        if self.dim != 3:
            raise ValueError("normal() requires a 3-D curve")
        t = self.tangent(u)
        n = [
            t[1] * up[2] - t[2] * up[1],
            t[2] * up[0] - t[0] * up[2],
            t[0] * up[1] - t[1] * up[0],
        ]
        norm = math.sqrt(sum(x * x for x in n))
        if norm < 1e-14:
            return [0.0, 0.0, 0.0]
        return [x / norm for x in n]

    # -- helpers -----------------------------------------------------
    @property
    def parameter_range(self) -> Tuple[float, float]:
        return (self.knots[self.degree], self.knots[self.n + 1])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"BSplineCurve(degree={self.degree}, "
            f"n={self.n}, dim={self.dim}, "
            f"range={self.parameter_range})"
        )