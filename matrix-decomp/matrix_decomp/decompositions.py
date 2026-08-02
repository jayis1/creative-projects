"""Additional matrix decompositions and related utilities.

Provides:

* :func:`schur_decomposition` — Schur decomposition for symmetric matrices
  (which reduces to the spectral decomposition).  Returns ``A = Q T Q^T``
  where ``T`` is (block) upper-triangular and ``Q`` is orthogonal.
* :func:`spectral_decomposition` — for a symmetric matrix ``A``, returns
  ``(eigenvalues, eigenvectors)`` such that ``A = V diag(eigenvalues) V^T``.
* :func:`polar_decomposition` — ``A = Q P`` where ``Q`` is orthogonal and
  ``P`` is symmetric positive-semidefinite.  Computed via SVD.
* :func:`lu_complete_pivot` — LU with *complete* (row + column) pivoting,
  more numerically stable than partial pivoting for pathological matrices.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from .matrix import EPS, Matrix, _to_data, identity, matmul, transpose
from .eigen import jacobi_eigen
from .svd import svd
from .lu import SingularMatrixError, forward_sub, back_sub


def spectral_decomposition(a) -> Tuple[List[float], Matrix]:
    """Spectral decomposition of a symmetric matrix: ``A = V diag(λ) V^T``.

    Returns ``(eigenvalues, V)`` where eigenvalues are in descending order
    and ``V`` columns are orthonormal eigenvectors.  Uses the Jacobi
    algorithm.
    """
    return jacobi_eigen(a)


def schur_decomposition(a) -> Tuple[Matrix, Matrix]:
    """Schur decomposition of a symmetric matrix: ``A = Q T Q^T``.

    For symmetric matrices the Schur form ``T`` is diagonal (containing
    the eigenvalues) and ``Q`` is orthogonal.  Returns ``(Q, T)``.

    Raises
    ------
    ValueError
        If ``a`` is not symmetric.
    """
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("schur_decomposition requires a square matrix")
    for i in range(n):
        for j in range(i + 1, n):
            if abs(d[i][j] - d[j][i]) > 1e-9:
                raise ValueError("schur_decomposition requires a symmetric matrix")
    evals, V = jacobi_eigen(a)
    T = [[evals[i] if i == j else 0.0 for j in range(n)] for i in range(n)]
    return V, Matrix(T)


def polar_decomposition(a) -> Tuple[Matrix, Matrix]:
    """Polar decomposition ``A = Q P`` where ``Q`` is orthogonal and ``P``
    is symmetric positive-semidefinite.

    Computed via SVD: ``A = U S V^T``, then ``Q = U V^T`` and ``P = V S V^T``.
    For full-rank square matrices, ``Q`` is the nearest orthogonal matrix
    to ``A`` (in the Frobenius norm).
    """
    d = _to_data(a)
    m, n = len(d), len(d[0])
    if m != n:
        raise ValueError("polar_decomposition requires a square matrix")
    U, S, Vt = svd(a)
    # A = U S Vt  where Vt = V^T.
    # Q = U V^T = U * Vt   (Vt IS V^T)
    Q = matmul(U, Vt)
    # P = V S V^T = Vt^T S Vt
    V = transpose(Vt)
    Sdiag = [[S[i] if i == j else 0.0 for j in range(n)] for i in range(n)]
    P = matmul(matmul(V, Sdiag), Vt)
    return Q, P


def lu_complete_pivot(a) -> Tuple[Matrix, Matrix, List[int], List[int], int]:
    """LU decomposition with **complete pivoting** (``PAQ = LU``).

    Complete pivoting searches the entire trailing sub-matrix for the
    largest element and swaps both rows and columns.  This is more
    stable than partial pivoting for matrices that are pathologically
    nearly-singular.

    Returns ``(L, U, row_perm, col_perm, sign)`` such that
    ``P @ A @ Q == L @ U`` where ``P`` permutes rows by ``row_perm`` and
    ``Q`` permutes columns by ``col_perm``.
    """
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("lu_complete_pivot requires a square matrix")
    U: List[List[float]] = [row[:] for row in d]
    L: List[List[float]] = [[0.0] * n for _ in range(n)]
    row_perm = list(range(n))
    col_perm = list(range(n))
    sign = 1

    for k in range(n):
        # Find the largest-magnitude entry in the trailing sub-matrix.
        pivot_row, pivot_col = k, k
        pivot_val = abs(U[k][k])
        for i in range(k, n):
            for j in range(k, n):
                if abs(U[i][j]) > pivot_val:
                    pivot_val = abs(U[i][j])
                    pivot_row, pivot_col = i, j

        if pivot_val < EPS:
            raise SingularMatrixError(
                f"Matrix is singular: zero pivot at step {k}"
            )

        # Row swap.
        if pivot_row != k:
            U[k], U[pivot_row] = U[pivot_row], U[k]
            row_perm[k], row_perm[pivot_row] = row_perm[pivot_row], row_perm[k]
            sign = -sign
            for j in range(k):
                L[k][j], L[pivot_row][j] = L[pivot_row][j], L[k][j]
        # Column swap.
        if pivot_col != k:
            for i in range(n):
                U[i][k], U[i][pivot_col] = U[i][pivot_col], U[i][k]
            col_perm[k], col_perm[pivot_col] = col_perm[pivot_col], col_perm[k]
            sign = -sign

        pivot = U[k][k]
        for i in range(k + 1, n):
            factor = U[i][k] / pivot
            L[i][k] = factor
            for j in range(k, n):
                U[i][j] -= factor * U[k][j]

    for i in range(n):
        L[i][i] = 1.0
    return Matrix(L), Matrix(U), row_perm, col_perm, sign