"""Curve fitting via least-squares approximation.

Given a set of data points, fit a B-spline curve of specified degree
with a chosen number of control points by solving the normal equations
of the least-squares problem.
"""

from __future__ import annotations

from typing import Sequence, List, Tuple, Optional

from .bspline import BSplineCurve, find_span, basis_functions
from .knot_vector import generate_clamped_uniform_knot_vector


def _chord_length_parameters(
    points: Sequence[Sequence[float]],
) -> List[float]:
    """Compute chord-length parameterization for *points* in [0, 1]."""
    if len(points) < 2:
        return [0.0]
    dists: List[float] = [0.0]
    for i in range(1, len(points)):
        d = sum(
            (points[i][k] - points[i - 1][k]) ** 2
            for k in range(len(points[0]))
        ) ** 0.5
        dists.append(dists[-1] + d)
    total = dists[-1] if dists[-1] > 0 else 1.0
    return [d / total for d in dists]


def fit_bspline_curve(
    points: Sequence[Sequence[float]],
    degree: int,
    num_control_points: int,
    parameters: Sequence[float] | None = None,
    knots: Sequence[float] | None = None,
) -> BSplineCurve:
    """Fit a B-spline curve to *points* via least squares.

    Parameters
    ----------
    points : sequence
        Data points to fit (each a list/tuple of floats).
    degree : int
        Spline degree.
    num_control_points : int
        Number of control points (>= degree + 1).
    parameters : sequence, optional
        Parameter values for each data point.  If None, chord-length
        parameterization is used.
    knots : sequence, optional
        Knot vector.  If None, a clamped uniform knot vector is
        generated and the interior knots are positioned by averaging.

    Returns
    -------
    BSplineCurve
        Fitted curve.
    """
    m = len(points)
    if m < 2:
        raise ValueError("Need at least 2 points to fit")
    if num_control_points < degree + 1:
        raise ValueError("num_control_points must be >= degree + 1")
    if num_control_points > m:
        raise ValueError("num_control_points cannot exceed number of data points")

    n = num_control_points - 1
    dim = len(points[0])

    if parameters is None:
        parameters = _chord_length_parameters(points)
    params = list(parameters)
    # Scale parameters to [0, n - degree + 1] to match clamped knot vector range.
    knot_end = n - degree + 1
    params = [p * knot_end for p in params]

    if knots is None:
        U = generate_clamped_uniform_knot_vector(n, degree)
        # Reposition interior knots via averaging (NURBS Book Eq. 9.68).
        d = (m + 1) // (n - degree + 1) if (n - degree + 1) > 0 else 1
        j = degree + 1
        for i in range(1, n - degree + 1):
            start = (i - 1) * d
            end = i * d
            avg = sum(params[start:end + 1]) / (end - start + 1)
            U[j] = avg
            j += 1
    else:
        U = list(knots)

    # Build basis matrix N (m x (n+1)) and solve normal equations.
    # N^T N P = N^T Q
    Nmat = [[0.0] * (n + 1) for _ in range(m)]
    for i in range(m):
        u = params[i]
        span = find_span(n, degree, u, U)
        basis = basis_functions(span, u, degree, U)
        for j in range(degree + 1):
            Nmat[i][span - degree + j] = basis[j]

    # Compute N^T N (size (n+1) x (n+1)) and N^T Q (size (n+1) x dim).
    NtN = [[0.0] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for jcol in range(n + 1):
            s = 0.0
            for k in range(m):
                s += Nmat[k][i] * Nmat[k][jcol]
            NtN[i][jcol] = s

    NtQ = [[0.0] * dim for _ in range(n + 1)]
    for i in range(n + 1):
        for d in range(dim):
            s = 0.0
            for k in range(m):
                s += Nmat[k][i] * points[k][d]
            NtQ[i][d] = s

    # Solve NtN * P = NtQ via Gaussian elimination with partial pivoting.
    control_points = _solve_linear_system(NtN, NtQ, n + 1, dim)
    return BSplineCurve(degree, U, control_points)


def _solve_linear_system(
    A: List[List[float]],
    B: List[List[float]],
    n: int,
    dim: int,
) -> List[List[float]]:
    """Solve ``A X = B`` via Gaussian elimination with partial pivoting.

    ``A`` is n×n, ``B`` is n×dim, returns X (n×dim).
    """
    # Augment A with B.
    M = [list(A[i]) + list(B[i]) for i in range(n)]

    for col in range(n):
        # Pivot.
        pivot = col
        max_val = abs(M[col][col])
        for r in range(col + 1, n):
            if abs(M[r][col]) > max_val:
                max_val = abs(M[r][col])
                pivot = r
        if max_val < 1e-14:
            raise ValueError("Singular matrix in least-squares fit")
        M[col], M[pivot] = M[pivot], M[col]

        # Eliminate.
        for r in range(n):
            if r == col:
                continue
            factor = M[r][col] / M[col][col]
            for c in range(col, n + dim):
                M[r][c] -= factor * M[col][c]

    # Back-substitute.
    X = [[0.0] * dim for _ in range(n)]
    for i in range(n):
        for d in range(dim):
            X[i][d] = M[i][n + d] / M[i][i]
    return X