"""Surface fitting via least-squares approximation.

Given a grid of data points, fit a tensor-product B-spline surface
of specified degrees with a chosen number of control points by
solving the normal equations in each parametric direction.
"""

from __future__ import annotations

from typing import Sequence, List, Tuple, Optional

from .bspline import BSplineCurve, find_span, basis_functions
from .nurbs_surface import NURBSSurface
from .knot_vector import generate_clamped_uniform_knot_vector
from .exceptions import NURBSError


def _chord_length_params_1d(
    points: Sequence[Sequence[float]],
) -> List[float]:
    """Compute chord-length parameters in [0, 1] for a list of points."""
    n = len(points)
    if n < 2:
        return [0.0]
    dists: List[float] = [0.0]
    for i in range(1, n):
        d = sum(
            (points[i][k] - points[i - 1][k]) ** 2
            for k in range(len(points[0]))
        ) ** 0.5
        dists.append(dists[-1] + d)
    total = dists[-1] if dists[-1] > 0 else 1.0
    return [d / total for d in dists]


def fit_bspline_surface(
    points: Sequence[Sequence[Sequence[float]]],
    degree_u: int,
    degree_v: int,
    num_ctrl_u: int,
    num_ctrl_v: int,
) -> NURBSSurface:
    """Fit a B-spline surface to a grid of points via least squares.

    Parameters
    ----------
    points : 2-D grid of 3-D points
        ``points[i][j]`` is the data point at row *i*, column *j*.
    degree_u, degree_v : int
        Spline degrees in each direction.
    num_ctrl_u, num_ctrl_v : int
        Number of control points in each direction.

    Returns
    -------
    NURBSSurface
        Fitted surface (all weights = 1).
    """
    m_u = len(points)
    m_v = len(points[0]) if m_u > 0 else 0
    if m_u < 2 or m_v < 2:
        raise NURBSError("Need at least a 2x2 grid of points to fit a surface")
    if num_ctrl_u < degree_u + 1 or num_ctrl_v < degree_v + 1:
        raise NURBSError("num_ctrl must be >= degree + 1 in each direction")
    if num_ctrl_u > m_u or num_ctrl_v > m_v:
        raise NURBSError("num_ctrl cannot exceed number of data points in that direction")

    dim = len(points[0][0])
    n_u = num_ctrl_u - 1
    n_v = num_ctrl_v - 1

    # Parameterize each direction.
    # Use the first row / column for chord-length params.
    row_0 = [points[0][j] for j in range(m_v)]
    col_0 = [points[i][0] for i in range(m_u)]
    params_v = _chord_length_params_1d(row_0)
    params_u = _chord_length_params_1d(col_0)

    # Scale to knot-vector range.
    end_u = n_u - degree_u + 1
    end_v = n_v - degree_v + 1
    params_u = [p * end_u for p in params_u]
    params_v = [p * end_v for p in params_v]

    # Knot vectors.
    U_u = generate_clamped_uniform_knot_vector(n_u, degree_u)
    U_v = generate_clamped_uniform_knot_vector(n_v, degree_v)

    # Build basis matrices.
    # N_u: m_u x (n_u+1)
    N_u = [[0.0] * (n_u + 1) for _ in range(m_u)]
    for i in range(m_u):
        u = params_u[i]
        span = find_span(n_u, degree_u, u, U_u)
        basis = basis_functions(span, u, degree_u, U_u)
        for j in range(degree_u + 1):
            N_u[i][span - degree_u + j] = basis[j]

    # N_v: m_v x (n_v+1)
    N_v = [[0.0] * (n_v + 1) for _ in range(m_v)]
    for j in range(m_v):
        v = params_v[j]
        span = find_span(n_v, degree_v, v, U_v)
        basis = basis_functions(span, v, degree_v, U_v)
        for k in range(degree_v + 1):
            N_v[j][span - degree_v + k] = basis[k]

    # Solve: P = (N_u^T N_u)^{-1} N_u^T  Q  N_v  (N_v^T N_v)^{-1}
    # where Q is the m_u x m_v x dim data grid.
    # Step 1: Solve N_u^T N_u R = N_u^T Q  (for each v column, each dim)
    NtuNtu = _matmul_transpose(N_u, m_u, n_u + 1)
    NtvNtv = _matmul_transpose(N_v, m_v, n_v + 1)

    # N_u^T Q: (n_u+1) x m_v x dim
    NtuQ = [[[0.0] * dim for _ in range(m_v)] for _ in range(n_u + 1)]
    for i in range(n_u + 1):
        for j in range(m_v):
            for d in range(dim):
                s = 0.0
                for k in range(m_u):
                    s += N_u[k][i] * points[k][j][d]
                NtuQ[i][j][d] = s

    # Solve NtuNtu R = NtuQ for R: (n_u+1) x m_v x dim
    R = _solve_multi(NtuNtu, NtuQ, n_u + 1, m_v, dim)

    # Now solve R N_v^T = ... => R N_v (N_v^T N_v)^{-1}
    # P = R N_v (N_v^T N_v)^{-1}
    # First compute R N_v^T: (n_u+1) x (n_v+1) x dim
    RNvT = [[[0.0] * dim for _ in range(n_v + 1)] for _ in range(n_u + 1)]
    for i in range(n_u + 1):
        for j in range(n_v + 1):
            for d in range(dim):
                s = 0.0
                for k in range(m_v):
                    s += R[i][k][d] * N_v[k][j]
                RNvT[i][j][d] = s

    # Solve NtvNtv^T P^T = RNvT^T for each row, then transpose.
    # P[i][j] = solution of NtvNtv P_row = RNvT_row for each i
    P = [[[0.0] * dim for _ in range(n_v + 1)] for _ in range(n_u + 1)]
    for i in range(n_u + 1):
        # Build RHS: (n_v+1) x dim
        rhs = [[RNvT[i][j][d] for d in range(dim)] for j in range(n_v + 1)]
        sol = _solve_linear(NtvNtv, rhs, n_v + 1, dim)
        for j in range(n_v + 1):
            for d in range(dim):
                P[i][j][d] = sol[j][d]

    return NURBSSurface(degree_u, degree_v, U_u, U_v, P)


def _matmul_transpose(N: List[List[float]], m: int, n: int) -> List[List[float]]:
    """Compute N^T N (n x n)."""
    result = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            s = 0.0
            for k in range(m):
                s += N[k][i] * N[k][j]
            result[i][j] = s
    return result


def _solve_multi(
    A: List[List[float]], B: List[List[List[float]]], n: int, m: int, dim: int
) -> List[List[List[float]]]:
    """Solve A X = B where B is n x m x dim, returning X (n x m x dim)."""
    # Gaussian elimination with partial pivoting on A.
    M = [list(A[i]) for i in range(n)]
    # Build augmented matrix: n x (n + m*dim)
    aug = [list(M[i]) + [B[i][j][d] for j in range(m) for d in range(dim)]
           for i in range(n)]
    for col in range(n):
        pivot = col
        max_val = abs(aug[col][col])
        for r in range(col + 1, n):
            if abs(aug[r][col]) > max_val:
                max_val = abs(aug[r][col])
                pivot = r
        if max_val < 1e-14:
            raise NURBSError("Singular matrix in surface fitting")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col] / aug[col][col]
            for c in range(col, n + m * dim):
                aug[r][c] -= factor * aug[col][c]
    X = [[[0.0] * dim for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for j in range(m):
            for d in range(dim):
                X[i][j][d] = aug[i][n + j * dim + d] / aug[i][i]
    return X


def _solve_linear(
    A: List[List[float]], B: List[List[float]], n: int, dim: int
) -> List[List[float]]:
    """Solve A X = B where A is n x n and B is n x dim."""
    M = [list(A[i]) + list(B[i]) for i in range(n)]
    for col in range(n):
        pivot = col
        max_val = abs(M[col][col])
        for r in range(col + 1, n):
            if abs(M[r][col]) > max_val:
                max_val = abs(M[r][col])
                pivot = r
        if max_val < 1e-14:
            raise NURBSError("Singular matrix in surface fitting")
        M[col], M[pivot] = M[pivot], M[col]
        for r in range(n):
            if r == col:
                continue
            factor = M[r][col] / M[col][col]
            for c in range(col, n + dim):
                M[r][c] -= factor * M[col][c]
    X = [[0.0] * dim for _ in range(n)]
    for i in range(n):
        for d in range(dim):
            X[i][d] = M[i][n + d] / M[i][i]
    return X