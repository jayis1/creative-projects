"""LU decomposition with partial pivoting (PA = LU).

Implements the textbook Doolittle/Crout-style Gaussian elimination with row
pivoting, plus linear-system solving, determinant computation and matrix
inverse via forward/back substitution.

The factorization of a square matrix ``A`` is::

    P A = L U

where ``P`` is a permutation matrix, ``L`` is unit lower-triangular, and
``U`` is upper-triangular.  Linear systems ``A x = b`` are then solved as
``L y = P b`` (forward substitution) and ``U x = y`` (back substitution).
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .matrix import EPS, Matrix, _to_data, identity, matmul, zeros


class SingularMatrixError(ValueError):
    """Raised when a matrix is (numerically) singular."""


def lu_decompose(a) -> Tuple[Matrix, Matrix, List[int], int]:
    """LU decomposition with partial pivoting.

    Returns ``(L, U, perm, sign)`` where:

    * ``L`` is unit lower-triangular,
    * ``U`` is upper-triangular,
    * ``perm`` is the row-permutation list such that ``P @ A == L @ U``
      where ``P`` is the permutation matrix with ``P[perm[i], i] = 1``,
    * ``sign`` is ``+1`` or ``-1`` (the sign of the permutation determinant,
      needed for determinant computation).

    Raises
    ------
    ValueError
        If ``A`` is not square.
    SingularMatrixError
        If a zero pivot is encountered (matrix is numerically singular).
    """
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("LU decomposition requires a square matrix")

    # Work on a copy so we don't mutate the caller's matrix.
    U: List[List[float]] = [row[:] for row in d]
    L: List[List[float]] = [[0.0] * n for _ in range(n)]
    perm: List[int] = list(range(n))
    sign = 1

    for k in range(n):
        # --- Partial pivoting: find the largest-magnitude entry in column k,
        #     rows k..n-1.
        pivot_row = k
        pivot_val = abs(U[k][k])
        for i in range(k + 1, n):
            if abs(U[i][k]) > pivot_val:
                pivot_val = abs(U[i][k])
                pivot_row = i

        if pivot_val < EPS:
            raise SingularMatrixError(
                f"Matrix is singular: zero pivot at column {k}"
            )

        # Swap rows in U and perm, track sign.
        if pivot_row != k:
            U[k], U[pivot_row] = U[pivot_row], U[k]
            perm[k], perm[pivot_row] = perm[pivot_row], perm[k]
            sign = -sign
            # Swap already-computed lower-triangular entries to the left of k.
            for j in range(k):
                L[k][j], L[pivot_row][j] = L[pivot_row][j], L[k][j]

        # Eliminate below.
        pivot = U[k][k]
        for i in range(k + 1, n):
            factor = U[i][k] / pivot
            L[i][k] = factor
            for j in range(k, n):
                U[i][j] -= factor * U[k][j]

    # Unit diagonal of L.
    for i in range(n):
        L[i][i] = 1.0

    return Matrix(L), Matrix(U), perm, sign


def _permute(perm: Sequence[int], b: Sequence[float]) -> List[float]:
    """Apply row permutation: ``Pb[i] = b[perm[i]]``."""
    return [b[p] for p in perm]


def forward_sub(L: Matrix, b: Sequence[float]) -> List[float]:
    """Solve ``L y = b`` where ``L`` is lower-triangular (unit or general)."""
    d = L.data if isinstance(L, Matrix) else _to_data(L)
    n = len(d)
    if len(b) != n:
        raise ValueError("forward_sub: dimension mismatch")
    y = [0.0] * n
    for i in range(n):
        s = b[i]
        for j in range(i):
            s -= d[i][j] * y[j]
        diag = d[i][i]
        if abs(diag) < EPS:
            raise SingularMatrixError("forward_sub: zero diagonal entry")
        y[i] = s / diag
    return y


def back_sub(U: Matrix, y: Sequence[float]) -> List[float]:
    """Solve ``U x = y`` where ``U`` is upper-triangular."""
    d = U.data if isinstance(U, Matrix) else _to_data(U)
    n = len(d)
    if len(y) != n:
        raise ValueError("back_sub: dimension mismatch")
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = y[i]
        for j in range(i + 1, n):
            s -= d[i][j] * x[j]
        diag = d[i][i]
        if abs(diag) < EPS:
            raise SingularMatrixError("back_sub: zero diagonal entry")
        x[i] = s / diag
    return x


def lu_solve(a, b: Sequence[float]) -> List[float]:
    """Solve ``A x = b`` via LU decomposition with partial pivoting."""
    L, U, perm, _ = lu_decompose(a)
    pb = _permute(perm, b)
    y = forward_sub(L, pb)
    x = back_sub(U, y)
    return x


def lu_inverse(a) -> Matrix:
    """Compute the inverse of a square, non-singular matrix via LU."""
    L, U, perm, _ = lu_decompose(a)
    n = L.rows
    inv_cols: List[List[float]] = []
    for col in range(n):
        e = [1.0 if i == col else 0.0 for i in range(n)]
        # Permute the identity column, then solve.
        pe = _permute(perm, e)
        y = forward_sub(L, pe)
        x = back_sub(U, y)
        inv_cols.append(x)
    # inv_cols is column-major; transpose to row-major.
    return Matrix([[inv_cols[j][i] for j in range(n)] for i in range(n)])


def determinant(a) -> float:
    """Determinant of a square matrix via LU.

    Uses ``det(A) = sign * prod(diag(U))``.
    """
    _, U, _, sign = lu_decompose(a)
    det = float(sign)
    for i in range(U.rows):
        det *= U[i][i]
    return det