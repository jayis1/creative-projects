"""Singular Value Decomposition (SVD) and derived routines.

The SVD of a matrix ``A`` (m x n, m >= n) is::

    A = U S V^T

where ``U`` is m x n with orthonormal columns, ``S`` is a diagonal n-vector of
singular values, and ``V`` is n x n orthogonal.  We compute it via the
eigen-decomposition of the smaller of ``A^T A`` and ``A A^T`` -- the Jacobi
eigenvalue algorithm is used on the symmetric ``n x n`` matrix ``A^T A``.

Also provides:

* :func:`svd_reconstruct` -- rebuild ``A`` from its factors.
* :func:`pseudo_inverse` -- Moore-Penrose pseudo-inverse ``A^+``.
* :func:`rank` -- numerical rank via singular-value threshold.
* :func:`condition_number` -- ratio of largest to smallest singular value.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from .matrix import EPS, Matrix, _to_data, identity, matmul, transpose
from .eigen import jacobi_eigen


def svd(a, tol: float = 1e-10) -> Tuple[Matrix, List[float], Matrix]:
    """Singular Value Decomposition ``A = U S V^T``.

    Parameters
    ----------
    a : matrix-like
        A matrix with ``m >= n`` (tall or square).  Wide matrices are handled
        by transposing.

    Returns
    -------
    (U, S, Vt)
        ``U`` is m x n with orthonormal columns, ``S`` is a list of n singular
        values (descending), and ``Vt`` is the transpose of ``V`` (n x n
        orthogonal).  Together ``U @ diag(S) @ Vt`` reconstructs ``A``.
    """
    d = _to_data(a)
    m = len(d)
    n = len(d[0])
    transposed = False
    if m < n:
        # Work on A^T to satisfy m >= n, then swap results.
        d = [[d[i][j] for i in range(m)] for j in range(n)]
        m, n = n, m
        transposed = True

    AtA = matmul(transpose(d), d).data  # n x n
    evals, V = jacobi_eigen(AtA)  # V columns are eigenvectors of A^T A

    # Singular values are sqrt of eigenvalues; guard against tiny negatives.
    svals = [math.sqrt(e) if e > 0 else 0.0 for e in evals]

    # U columns: u_i = A v_i / s_i  (for s_i > 0)
    Vmat = V.data
    U = [[0.0] * n for _ in range(m)]
    for k in range(n):
        vk = [Vmat[i][k] for i in range(n)]
        # u_k = A v_k
        uk = [sum(d[i][j] * vk[j] for j in range(n)) for i in range(m)]
        s = svals[k]
        if s > tol:
            for i in range(m):
                U[i][k] = uk[i] / s
        else:
            # For zero singular values, leave column zero; we will orthonormalize
            # later via Gram-Schmidt against existing columns.
            pass

    # Orthonormalize columns of U that came from zero singular values, to
    # ensure U has orthonormal columns even in rank-deficient cases.
    # Use a simple modified Gram-Schmidt pass.
    for k in range(n):
        if svals[k] <= tol:
            # Fill with a standard basis vector, then orthogonalize.
            col = [1.0 if i == k else 0.0 for i in range(m)]
            for j in range(n):
                if j == k:
                    continue
                uj = [U[i][j] for i in range(m)]
                proj = sum(col[i] * uj[i] for i in range(m))
                col = [col[i] - proj * uj[i] for i in range(m)]
            nrm = math.sqrt(sum(x * x for x in col))
            if nrm > EPS:
                col = [x / nrm for x in col]
            for i in range(m):
                U[i][k] = col[i]

    Vt = [[Vmat[i][j] for i in range(n)] for j in range(n)]  # transpose of V

    if transposed:
        # A^T = U S Vt  =>  A = (U S Vt)^T = Vt^T S U^T.
        # So the SVD of A is: U_A = Vt^T, S_A = S, Vt_A = U^T.
        return transpose(Matrix(Vt)), svals, transpose(Matrix(U))
    return Matrix(U), svals, Matrix(Vt)


def svd_reconstruct(U: Matrix, S: List[float], Vt: Matrix) -> Matrix:
    """Reconstruct ``A = U @ diag(S) @ Vt``."""
    m = U.rows
    n = Vt.cols
    out = [[0.0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            s = 0.0
            for k in range(len(S)):
                s += U[i][k] * S[k] * Vt[k][j]
            out[i][j] = s
    return Matrix(out)


def pseudo_inverse(a, tol: float = 1e-10) -> Matrix:
    """Moore-Penrose pseudo-inverse ``A^+ = V S^+ U^T``.

    For an ``m x n`` matrix ``A`` the pseudo-inverse is ``n x m``.
    """
    U, S, Vt = svd(a, tol=tol)
    # A = U S Vt  (U: m x k, S: k, Vt: k x n)  where k = len(S).
    # A^+ = V S^+ U^T  which is n x m.
    m_A = U.rows       # rows of A
    n_A = Vt.cols      # cols of A
    Vt_data = Vt.data
    U_data = U.data
    out = [[0.0] * m_A for _ in range(n_A)]
    for j in range(n_A):
        for i in range(m_A):
            s = 0.0
            for k in range(len(S)):
                if S[k] > tol:
                    # V[j,k] = Vt[k,j],  U^T[k,i] = U[i,k]
                    s += Vt_data[k][j] * (1.0 / S[k]) * U_data[i][k]
            out[j][i] = s
    return Matrix(out)


def rank(a, tol: float = 1e-9) -> int:
    """Numerical rank: count of singular values above ``tol``."""
    _, S, _ = svd(a, tol=tol)
    return sum(1 for s in S if s > tol)


def condition_number(a) -> float:
    """Ratio of largest to smallest non-zero singular value."""
    _, S, _ = svd(a)
    s_max = max(S) if S else 0.0
    s_min = min((s for s in S if s > 1e-15), default=0.0)
    if s_min == 0.0:
        return float("inf")
    return s_max / s_min