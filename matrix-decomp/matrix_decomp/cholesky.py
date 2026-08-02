"""Cholesky decomposition for symmetric positive-definite (SPD) matrices.

The Cholesky factorization of an SPD matrix ``A`` is::

    A = L L^T

where ``L`` is lower-triangular with positive diagonal entries.  Linear
systems ``A x = b`` are then solved by two triangular solves:

    L y = b   (forward substitution)
    L^T x = y (back substitution)
"""

from __future__ import annotations

from typing import List, Sequence

from .matrix import EPS, Matrix, _to_data, transpose
from .lu import SingularMatrixError, forward_sub, back_sub


def is_symmetric(a, tol: float = 1e-9) -> bool:
    """Check whether a matrix is symmetric within ``tol``."""
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        return False
    for i in range(n):
        for j in range(i + 1, n):
            if abs(d[i][j] - d[j][i]) > tol:
                return False
    return True


def is_spd(a, tol: float = 1e-9) -> bool:
    """Return True if ``a`` is symmetric positive-definite.

    Attempts a Cholesky decomposition; SPD matrices have one.
    """
    if not is_symmetric(a, tol):
        return False
    try:
        cholesky(a)
    except (ValueError, SingularMatrixError):
        return False
    return True


def cholesky(a) -> Matrix:
    """Compute the Cholesky factorization ``A = L L^T``.

    Parameters
    ----------
    a : matrix-like
        A symmetric positive-definite matrix.

    Returns
    -------
    Matrix
        Lower-triangular ``L`` with positive diagonal such that
        ``L @ L.T == A``.

    Raises
    ------
    ValueError
        If ``a`` is not square.
    ValueError
        If ``a`` is not symmetric (within tolerance).
    SingularMatrixError
        If a negative or zero pivot is encountered (matrix is not positive
        definite).
    """
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("Cholesky requires a square matrix")
    if not is_symmetric(d, tol=1e-9):
        raise ValueError("Cholesky requires a symmetric matrix")

    L: List[List[float]] = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1):
            s = d[i][j]
            for k in range(j):
                s -= L[i][k] * L[j][k]
            if i == j:
                if s <= 0.0:
                    raise SingularMatrixError(
                        "Matrix is not positive definite "
                        f"(non-positive pivot at ({i},{j}))"
                    )
                L[i][j] = s ** 0.5
            else:
                if abs(L[j][j]) < EPS:
                    raise SingularMatrixError("Zero diagonal in Cholesky factor")
                L[i][j] = s / L[j][j]
    return Matrix(L)


def cholesky_solve(a, b: Sequence[float]) -> List[float]:
    """Solve ``A x = b`` for an SPD matrix ``A`` using Cholesky."""
    L = cholesky(a)
    y = forward_sub(L, b)
    # Solve L^T x = y  -- back substitution on the transpose (upper-triangular).
    Lt = transpose(L)
    x = back_sub(Lt, y)
    return x