"""QR decomposition and orthogonalization routines.

Provides:

* :func:`qr_householder` -- QR via Householder reflections (numerically
  stable, the production-grade algorithm).
* :func:`qr_solve` -- least-squares / least-norm solve via QR.
* :func:`classical_gram_schmidt` and :func:`modified_gram_schmidt` --
  the two textbook Gram-Schmidt variants (classical is numerically poor,
  modified is good and also yields a QR decomposition).
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .matrix import EPS, Matrix, _to_data, identity, matmul, matvec, transpose


def _vec_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _vec_sub(a: List[float], b: List[float]) -> List[float]:
    return [a[i] - b[i] for i in range(len(a))]


def _vec_dot(a: List[float], b: List[float]) -> float:
    return sum(a[i] * b[i] for i in range(len(a)))


def _vec_scale(v: List[float], s: float) -> List[float]:
    return [x * s for x in v]


def qr_householder(a) -> Tuple[Matrix, Matrix]:
    """QR decomposition via Householder reflections.

    Returns ``(Q, R)`` such that ``A == Q @ R`` where ``Q`` is orthogonal
    (``Q^T Q == I``) and ``R`` is upper-triangular.  Works for rectangular
    matrices (``m >= n``); for ``m < n`` the factorization still proceeds
    but ``R`` is upper-trapezoidal.
    """
    d = _to_data(a)
    m = len(d)
    n = len(d[0])
    # R starts as a copy of A; we accumulate Householder transforms into Q.
    R: List[List[float]] = [row[:] for row in d]
    Q: List[List[float]] = identity(m).data

    steps = min(m - 1, n)
    # When m == n we also want the last pivot to zero nothing, but we still
    # apply it to make R's diagonal positive when convenient.  Standard
    # convention: iterate over min(m, n).
    for k in range(min(m, n)):
        # Householder vector for column k, rows k..m-1.
        x = [R[i][k] for i in range(k, m)]
        normx = _vec_norm(x)
        if normx < EPS:
            continue
        # Choose sign to avoid cancellation: alpha = -sign(x0) * ||x||.
        alpha = -normx if x[0] >= 0 else normx
        # v = x - alpha * e1
        v = x[:]
        v[0] -= alpha
        vnorm = _vec_norm(v)
        if vnorm < EPS:
            continue
        v = _vec_scale(v, 1.0 / vnorm)  # normalized Householder vector

        # Apply H = I - 2 v v^T to R rows k..m-1, columns k..n-1.
        for j in range(k, n):
            col = [R[i][j] for i in range(k, m)]
            dot = 2.0 * _vec_dot(v, col)
            for i in range(k, m):
                R[i][j] -= dot * v[i - k]

        # Apply H to Q: Q = Q H  (accumulate from the right).
        for j in range(m):
            row = [Q[j][i] for i in range(k, m)]
            dot = 2.0 * _vec_dot(v, row)
            for i in range(k, m):
                Q[j][i] -= dot * v[i - k]

    return Matrix(Q), Matrix(R)


def qr_solve(a, b: Sequence[float]) -> List[float]:
    """Solve the least-squares problem ``min ||A x - b||`` via QR.

    For a tall/rectangular ``A`` (``m >= n``) this gives the least-squares
    solution.  For a square non-singular ``A`` it gives the exact solution.
    """
    Q, R = qr_householder(a)
    m, n = Q.rows, R.cols
    if len(b) != m:
        raise ValueError("qr_solve: b length must match A rows")
    # Compute Q^T b.
    qtb = [sum(Q[i][k] * b[i] for i in range(m)) for k in range(n)]
    # Back-substitute R x = Q^T b using the top n x n block of R.
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = qtb[i]
        for j in range(i + 1, n):
            s -= R[i][j] * x[j]
        diag = R[i][i]
        if abs(diag) < EPS:
            from .lu import SingularMatrixError
            raise SingularMatrixError("qr_solve: R is singular")
        x[i] = s / diag
    return x


def classical_gram_schmidt(a) -> Tuple[Matrix, Matrix]:
    """Classical Gram-Schmidt QR.

    Numerically unstable; provided for comparison / teaching.
    """
    d = _to_data(a)
    m = len(d)
    n = len(d[0])
    Q = [[0.0] * n for _ in range(m)]
    R = [[0.0] * n for _ in range(n)]
    for j in range(n):
        # a_j (the j-th column of A).
        aj = [d[i][j] for i in range(m)]
        for i in range(j):
            qi = [Q[r][i] for r in range(m)]
            R[i][j] = _vec_dot(qi, aj)
            aj = [aj[r] - R[i][j] * qi[r] for r in range(m)]
        nrm = _vec_norm(aj)
        if nrm < EPS:
            R[j][j] = 0.0
            # leave Q column as zeros (linearly dependent)
            continue
        R[j][j] = nrm
        for r in range(m):
            Q[r][j] = aj[r] / nrm
    return Matrix(Q), Matrix(R)


def modified_gram_schmidt(a) -> Tuple[Matrix, Matrix]:
    """Modified Gram-Schmidt QR -- numerically stable variant."""
    d = _to_data(a)
    m = len(d)
    n = len(d[0])
    # V holds working columns; we orthogonalize in place.
    V = [[d[i][j] for j in range(n)] for i in range(m)]
    Q = [[0.0] * n for _ in range(m)]
    R = [[0.0] * n for _ in range(n)]
    for j in range(n):
        vj = [V[i][j] for i in range(m)]
        nrm = _vec_norm(vj)
        if nrm < EPS:
            R[j][j] = 0.0
            continue
        R[j][j] = nrm
        for i in range(m):
            Q[i][j] = vj[i] / nrm
        qj = [Q[i][j] for i in range(m)]
        # Subtract projections from remaining columns.
        for k in range(j + 1, n):
            vk = [V[i][k] for i in range(m)]
            R[j][k] = _vec_dot(qj, vk)
            for i in range(m):
                V[i][k] = vk[i] - R[j][k] * qj[i]
    return Matrix(Q), Matrix(R)