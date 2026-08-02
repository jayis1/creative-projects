"""Eigenvalue / eigenvector computation.

Three algorithms are provided:

* :func:`qr_algorithm` -- the unshifted QR algorithm: repeatedly form
  ``A_k = R_k Q_k`` where ``A_k = Q_k R_k``.  ``A_k`` converges to upper
  triangular (Schur) form, whose diagonal holds the eigenvalues.
* :func:`jacobi_eigen` -- the classical Jacobi eigenvalue algorithm for
  symmetric matrices, which sweeps through off-diagonal entries applying
  Givens rotations to zero them out.  Returns eigenvalues and eigenvectors.
* :func:`power_iteration` -- the simplest iterative eigensolver: find the
  dominant eigenvalue / eigenvector pair via repeated multiplication.
* :func:`eigen_decomposition` -- a convenience wrapper that returns
  eigenvalues and (optionally) eigenvectors for symmetric matrices.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from .matrix import EPS, Matrix, _to_data, identity, matmul
from .qr import qr_householder
from .lu import SingularMatrixError


def qr_algorithm(a, max_iter: int = 1000, tol: float = 1e-12, shift: bool = True) -> List[float]:
    """QR algorithm to find eigenvalues of a square matrix.

    When ``shift=True`` (default) the **Wilkinson shift** is applied: after
    each QR step the bottom-right diagonal element is used as a shift,
    dramatically accelerating convergence to the smallest eigenvalue.  For
    symmetric matrices the unshifted version already converges reasonably
    fast, but the shifted variant converges cubically.

    For symmetric matrices this converges to a diagonal matrix whose
    diagonal entries are the eigenvalues.  For general matrices it
    converges to upper-triangular (Schur) form; eigenvalues are on the
    diagonal.  Real matrices with complex eigenvalues are not handled
    (complex arithmetic is out of scope for this module).

    Returns
    -------
    list[float]
        The eigenvalues (sorted by descending absolute value).
    """
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("qr_algorithm requires a square matrix")

    Ak = [row[:] for row in d]
    for iteration in range(max_iter):
        # Deflation: if the bottom-left off-diagonal is tiny, shrink the
        # active sub-matrix.
        active = n
        while active > 1 and abs(Ak[active - 1][active - 2]) < tol * (abs(Ak[active - 2][active - 2]) + abs(Ak[active - 1][active - 1]) + EPS):
            active -= 1
        if active <= 1:
            break

        # Optional Wilkinson shift on the trailing 2x2 block.
        shift_val = 0.0
        if shift and active >= 2:
            a_ = Ak[active - 2][active - 2]
            b_ = Ak[active - 2][active - 1]
            c_ = Ak[active - 1][active - 2]
            d_ = Ak[active - 1][active - 1]
            # Wilkinson shift: eigenvalue of trailing 2x2 closest to d_.
            tr = a_ + d_
            det = a_ * d_ - b_ * c_
            disc = (tr * tr / 4.0 - det) ** 0.5
            lam1 = tr / 2.0 + disc
            lam2 = tr / 2.0 - disc
            shift_val = lam1 if abs(lam1 - d_) < abs(lam2 - d_) else lam2

        # Apply shift to the active sub-matrix.
        work = [row[:active] for row in Ak[:active]]
        if shift and shift_val != 0.0:
            for i in range(active):
                work[i][i] -= shift_val

        Q, R = qr_householder(work)
        # RQ (on the active block).
        rq = matmul(R, Q).data
        # Unshift.
        if shift and shift_val != 0.0:
            for i in range(active):
                rq[i][i] += shift_val
        # Write back.
        for i in range(active):
            for j in range(active):
                Ak[i][j] = rq[i][j]

        # Check convergence of the active block off-diagonal mass.
        off = 0.0
        for i in range(active):
            for j in range(i):
                off += Ak[i][j] * Ak[i][j] + Ak[j][i] * Ak[j][i]
        if off < tol * tol:
            break

    evals = [Ak[i][i] for i in range(n)]
    evals.sort(key=lambda x: -abs(x))
    return evals


def tridiagonalize(a) -> Matrix:
    """Reduce a symmetric matrix to tridiagonal form via Householder reflections.

    Returns a tridiagonal matrix ``T`` such that ``T = Q^T A Q`` for some
    orthogonal ``Q``.  ``T`` has the same eigenvalues as ``A``.
    """
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("tridiagonalize requires a square matrix")
    A = [row[:] for row in d]
    for k in range(n - 2):
        # Householder vector to zero out A[k+2:, k].
        x = [A[i][k] for i in range(k + 1, n)]
        normx = math.sqrt(sum(v * v for v in x))
        if normx < EPS:
            continue
        alpha = -normx if x[0] >= 0 else normx
        v = x[:]
        v[0] -= alpha
        vnorm = math.sqrt(sum(c * c for c in v))
        if vnorm < EPS:
            continue
        v = [c / vnorm for c in v]
        # Apply H = I - 2 v v^T from both sides: A' = H A H.
        # Compute p = A v (lower-right block).
        p = [0.0] * (n - k - 1)
        for i in range(n - k - 1):
            for j in range(n - k - 1):
                p[i] += A[k + 1 + i][k + 1 + j] * v[j]
        # K = 2 v^T p / 2 ... use beta = v^T p
        beta = sum(v[i] * p[i] for i in range(len(v)))
        # q = p - beta v
        q = [p[i] - beta * v[i] for i in range(len(v))]
        # A' = A - v q^T - q v^T  (on the lower-right block)
        for i in range(n - k - 1):
            for j in range(n - k - 1):
                A[k + 1 + i][k + 1 + j] -= 2.0 * (v[i] * q[j] + q[i] * v[j])
        # Zero out the column/row below k+1 explicitly.
        for i in range(k + 2, n):
            A[k][i] = 0.0
            A[i][k] = 0.0
        # Keep A[k+1][k] as alpha.
        A[k + 1][k] = alpha
        A[k][k + 1] = alpha
    return Matrix(A)


def jacobi_eigen(a, max_iter: int = 100, tol: float = 1e-14) -> Tuple[List[float], Matrix]:
    """Classical Jacobi eigenvalue algorithm for symmetric matrices.

    Returns ``(eigenvalues, eigenvectors)`` where ``eigenvalues`` are sorted
    in descending order and ``eigenvectors`` is a matrix whose columns are the
    corresponding eigenvectors.
    """
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("jacobi_eigen requires a square matrix")
    # Symmetrize to guard against tiny asymmetry.
    A = [[(d[i][j] + d[j][i]) / 2.0 for j in range(n)] for i in range(n)]
    V = identity(n).data  # eigenvector accumulator

    for _ in range(max_iter):
        # Find largest off-diagonal entry.
        p, q = 0, 1
        max_off = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(A[i][j]) > max_off:
                    max_off = abs(A[i][j])
                    p, q = i, j
        if max_off < tol:
            break
        # Compute rotation angle.
        app = A[p][p]
        aqq = A[q][q]
        apq = A[p][q]
        if abs(app - aqq) < EPS:
            theta = math.pi / 4.0
        else:
            theta = 0.5 * math.atan2(2.0 * apq, app - aqq)
        c = math.cos(theta)
        s = math.sin(theta)
        # Apply rotation J^T A J.
        for i in range(n):
            if i != p and i != q:
                aip = A[i][p]
                aiq = A[i][q]
                A[i][p] = c * aip + s * aiq
                A[p][i] = A[i][p]
                A[i][q] = -s * aip + c * aiq
                A[q][i] = A[i][q]
        A[p][p] = c * c * app + 2.0 * s * c * apq + s * s * aqq
        A[q][q] = s * s * app - 2.0 * s * c * apq + c * c * aqq
        A[p][q] = 0.0
        A[q][p] = 0.0
        # Update eigenvectors V = V J.
        for i in range(n):
            vip = V[i][p]
            viq = V[i][q]
            V[i][p] = c * vip + s * viq
            V[i][q] = -s * vip + c * viq

    evals = [A[i][i] for i in range(n)]
    # Sort descending by eigenvalue.
    order = sorted(range(n), key=lambda i: -evals[i])
    evals_sorted = [evals[i] for i in order]
    Vsorted = [[V[i][order[k]] for k in range(n)] for i in range(n)]
    return evals_sorted, Matrix(Vsorted)


def eigen_decomposition(a, vectors: bool = True) -> Tuple[List[float], Matrix | None]:
    """Return eigenvalues (and eigenvectors for symmetric matrices)."""
    # Use Jacobi for symmetric matrices (always symmetric here, since the
    # full non-symmetric eigenproblem with eigenvectors requires more
    # machinery).  If the caller only wants values, use the QR algorithm.
    d = _to_data(a)
    n = len(d)
    symmetric = all(abs(d[i][j] - d[j][i]) < 1e-9 for i in range(n) for j in range(n))
    if vectors and symmetric:
        return jacobi_eigen(a)[:2]  # already (vals, vecs)
    if vectors and not symmetric:
        # Fall back to QR algorithm for values only; eigenvectors for
        # non-symmetric matrices are not supported in v1.
        return qr_algorithm(a), None
    return qr_algorithm(a), None


def power_iteration(a, max_iter: int = 1000, tol: float = 1e-12) -> Tuple[float, List[float]]:
    """Dominant eigenvalue / eigenvector via power iteration.

    Returns ``(eigenvalue, eigenvector)`` for the eigenvalue of largest
    magnitude.  The vector is normalized to unit Euclidean length.
    """
    d = _to_data(a)
    n = len(d)
    if n != len(d[0]):
        raise ValueError("power_iteration requires a square matrix")
    # Initial guess: all ones, normalized.
    v = [1.0 / math.sqrt(n)] * n
    eigenvalue = 0.0
    for _ in range(max_iter):
        w = [sum(d[i][j] * v[j] for j in range(n)) for i in range(n)]
        nrm = math.sqrt(sum(x * x for x in w))
        if nrm < EPS:
            return 0.0, v
        v_new = [x / nrm for x in w]
        # Rayleigh quotient.
        Av = [sum(d[i][j] * v_new[j] for j in range(n)) for i in range(n)]
        new_eval = sum(v_new[i] * Av[i] for i in range(n))
        if abs(new_eval - eigenvalue) < tol:
            eigenvalue = new_eval
            v = v_new
            break
        eigenvalue = new_eval
        v = v_new
    return eigenvalue, v