"""Least-squares and least-norm solvers, plus simple linear regression.

* :func:`least_squares` -- solve ``min ||A x - b||`` for tall/rectangular A
  via QR decomposition.
* :func:`least_norm` -- solve ``min ||x||`` subject to ``A x = b`` for
  wide/under-determined systems via the pseudo-inverse.
* :func:`linear_fit` -- simple (single-variable) linear regression returning
  slope, intercept and R^2.
"""

from __future__ import annotations

from typing import List, Sequence

from .matrix import Matrix, _to_data, transpose
from .qr import qr_solve
from .svd import pseudo_inverse
from .lu import lu_solve


def least_squares(a, b: Sequence[float]) -> List[float]:
    """Solve the least-squares problem ``min ||A x - b||_2``.

    Works for ``m >= n`` (over-determined or square).  Uses QR when A is
    tall and LU when A is square.
    """
    d = _to_data(a)
    m, n = len(d), len(d[0])
    if len(b) != m:
        raise ValueError("least_squares: b length must match A rows")
    if m >= n:
        return qr_solve(a, b)
    # Under-determined: fall back to least-norm solution.
    return least_norm(a, b)


def least_norm(a, b: Sequence[float]) -> List[float]:
    """Minimum-norm solution ``x = A^+ b`` of an under-determined system.

    Uses the Moore-Penrose pseudo-inverse.
    """
    d = _to_data(a)
    m, n = len(d), len(d[0])
    if len(b) != m:
        raise ValueError("least_norm: b length must match A rows")
    Aplus = pseudo_inverse(a)
    # x = A^+ b
    return [sum(Aplus[i][j] * b[j] for j in range(m)) for i in range(n)]


def linear_fit(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float, float]:
    """Simple linear regression ``y = a + b x``.

    Returns ``(slope, intercept, r_squared)``.
    """
    n = len(xs)
    if n != len(ys):
        raise ValueError("linear_fit: xs and ys must have equal length")
    if n < 2:
        raise ValueError("linear_fit: need at least 2 points")
    # Build the design matrix [1, x] and solve least squares.
    A = [[1.0, xs[i]] for i in range(n)]
    coeffs = least_squares(A, list(ys))
    intercept, slope = coeffs[0], coeffs[1]
    # R^2
    y_mean = sum(ys) / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((ys[i] - (intercept + slope * xs[i])) ** 2 for i in range(n))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return slope, intercept, r2