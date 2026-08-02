"""Iterative linear solvers.

Classical stationary iterations (Jacobi, Gauss-Seidel, SOR) and the
Krylov-subspace method **Conjugate Gradient** (for SPD systems).  These
complement the direct solvers in :mod:`matrix_decomp.lu` and
:mod:`matrix_decomp.qr` — iterative methods are preferred for large,
sparse, or structured systems where an explicit factorization is too
expensive.

All solvers accept either a dense :class:`~matrix_decomp.matrix.Matrix`
or a :class:`~matrix_decomp.sparse.CSRMatrix`.  Each returns the solution
vector and a :class:`SolveResult` with convergence diagnostics.

Example
-------

>>> from matrix_decomp import Matrix
>>> from matrix_decomp.iterative import jacobi_solve
>>> A = Matrix([[4.0, 1.0], [1.0, 3.0]])
>>> result = jacobi_solve(A, [1.0, 2.0])
>>> result.x
[0.0909..., 0.6363...]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Sequence, Tuple

from .matrix import EPS, Matrix, _to_data
from .sparse import CSRMatrix

# Type alias for anything we can do a matrix-vector product with.
MatLike = "Matrix | CSRMatrix"

# Sentinel residual before the loop (overwritten in first iteration).
_residual: float = 0.0


def _matvec(A, x: Sequence[float]) -> List[float]:
    """Dispatch matvec for dense ``Matrix`` or ``CSRMatrix``."""
    if isinstance(A, CSRMatrix):
        return A.matvec(x)
    d = _to_data(A)
    n = len(d)
    m = len(d[0])
    if len(x) != m:
        raise ValueError("matvec: dimension mismatch")
    return [sum(d[i][j] * x[j] for j in range(m)) for i in range(n)]


def _shape(A) -> Tuple[int, int]:
    if isinstance(A, CSRMatrix):
        return A.shape_tuple()
    d = _to_data(A)
    return (len(d), len(d[0]) if d else 0)


def _diag(A) -> List[float]:
    if isinstance(A, CSRMatrix):
        return [A.get(i, i) for i in range(A.rows)]
    d = _to_data(A)
    return [d[i][i] for i in range(min(len(d), len(d[0])))]


@dataclass
class SolveResult:
    """Result of an iterative solve."""

    x: List[float]
    iterations: int
    residual: float
    converged: bool
    method: str
    history: List[float] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "converged" if self.converged else "NOT converged"
        return (
            f"SolveResult(method={self.method!r}, {status}, "
            f"iters={self.iterations}, residual={self.residual:.2e})"
        )


# ---------------------------------------------------------------------------
# Jacobi
# ---------------------------------------------------------------------------
def jacobi_solve(
    A: MatLike,
    b: Sequence[float],
    x0: Sequence[float] | None = None,
    max_iter: int = 1000,
    tol: float = 1e-10,
) -> SolveResult:
    """Jacobi iteration: ``x_i^{(k+1)} = (b_i - sum_{j!=i} A_ij x_j^{(k)}) / A_ii``.

    Converges for strictly or irreducibly diagonally dominant matrices.
    """
    rows, cols = _shape(A)
    if rows != cols:
        raise ValueError("Jacobi requires a square matrix")
    if len(b) != rows:
        raise ValueError("b length must match matrix dimension")
    diag = _diag(A)
    if any(abs(d) < EPS for d in diag):
        raise ValueError("Jacobi: zero on diagonal (matrix not strictly diagonally dominant)")

    x = list(x0) if x0 is not None else [0.0] * rows
    history: List[float] = []
    residual: float = float("inf")
    for k in range(max_iter):
        x_new = [0.0] * rows
        Ax = _matvec(A, x)
        for i in range(rows):
            x_new[i] = (b[i] - Ax[i] + diag[i] * x[i]) / diag[i]
        residual = math.sqrt(sum((Ax[j] - b[j]) ** 2 for j in range(rows)))
        history.append(residual)
        diff = math.sqrt(sum((x_new[i] - x[i]) ** 2 for i in range(rows)))
        x = x_new
        if residual < tol:
            return SolveResult(x, k + 1, residual, True, "jacobi", history)
    return SolveResult(x, max_iter, residual, False, "jacobi", history)


# ---------------------------------------------------------------------------
# Gauss-Seidel
# ---------------------------------------------------------------------------
def gauss_seidel_solve(
    A: MatLike,
    b: Sequence[float],
    x0: Sequence[float] | None = None,
    max_iter: int = 1000,
    tol: float = 1e-10,
) -> SolveResult:
    """Gauss-Seidel iteration — uses updated values immediately within each sweep.

    Roughly twice as fast to converge as Jacobi for the same system.
    """
    rows, cols = _shape(A)
    if rows != cols:
        raise ValueError("Gauss-Seidel requires a square matrix")
    if len(b) != rows:
        raise ValueError("b length must match matrix dimension")
    diag = _diag(A)
    if any(abs(d) < EPS for d in diag):
        raise ValueError("Gauss-Seidel: zero on diagonal")

    x = list(x0) if x0 is not None else [0.0] * rows
    dense = None if isinstance(A, CSRMatrix) else _to_data(A)
    history: List[float] = []
    residual: float = float("inf")
    for k in range(max_iter):
        if dense is not None:
            for i in range(rows):
                s = b[i]
                for j in range(rows):
                    if j != i:
                        s -= dense[i][j] * x[j]
                x[i] = s / diag[i]
        else:
            for i in range(rows):
                s = b[i]
                for idx in range(A.indptr[i], A.indptr[i + 1]):  # type: ignore[union-attr]
                    col = A.indices[idx]  # type: ignore[union-attr]
                    if col != i:
                        s -= A.data[idx] * x[col]  # type: ignore[union-attr]
                x[i] = s / diag[i]
        residual = math.sqrt(sum((bi - xi) ** 2 for bi, xi in zip(_matvec(A, x), b)))
        history.append(residual)
        if residual < tol:
            return SolveResult(x, k + 1, residual, True, "gauss_seidel", history)
    return SolveResult(x, max_iter, residual, False, "gauss_seidel", history)


# ---------------------------------------------------------------------------
# SOR (Successive Over-Relaxation)
# ---------------------------------------------------------------------------
def sor_solve(
    A: MatLike,
    b: Sequence[float],
    omega: float = 1.0,
    x0: Sequence[float] | None = None,
    max_iter: int = 1000,
    tol: float = 1e-10,
) -> SolveResult:
    """SOR: weighted average of Gauss-Seidel update and previous iterate.

    ``omega=1`` recovers Gauss-Seidel; ``omega < 1`` is under-relaxation;
    ``omega > 1`` is over-relaxation (typically 1 < omega < 2 for SPD).
    """
    if not (0.0 < omega < 2.0):
        raise ValueError("omega must be in (0, 2) for convergence")
    rows, cols = _shape(A)
    if rows != cols:
        raise ValueError("SOR requires a square matrix")
    if len(b) != rows:
        raise ValueError("b length must match matrix dimension")
    diag = _diag(A)
    if any(abs(d) < EPS for d in diag):
        raise ValueError("SOR: zero on diagonal")

    x = list(x0) if x0 is not None else [0.0] * rows
    dense = None if isinstance(A, CSRMatrix) else _to_data(A)
    history: List[float] = []
    residual: float = float("inf")
    for k in range(max_iter):
        if dense is not None:
            for i in range(rows):
                s = b[i]
                for j in range(rows):
                    if j != i:
                        s -= dense[i][j] * x[j]
                gs = s / diag[i]
                x[i] = (1 - omega) * x[i] + omega * gs
        else:
            for i in range(rows):
                s = b[i]
                for idx in range(A.indptr[i], A.indptr[i + 1]):  # type: ignore[union-attr]
                    col = A.indices[idx]  # type: ignore[union-attr]
                    if col != i:
                        s -= A.data[idx] * x[col]  # type: ignore[union-attr]
                gs = s / diag[i]
                x[i] = (1 - omega) * x[i] + omega * gs
        residual = math.sqrt(sum((bi - xi) ** 2 for bi, xi in zip(_matvec(A, x), b)))
        history.append(residual)
        if residual < tol:
            return SolveResult(x, k + 1, residual, True, "sor", history)
    return SolveResult(x, max_iter, residual, False, "sor", history)


# ---------------------------------------------------------------------------
# Conjugate Gradient
# ---------------------------------------------------------------------------
def conjugate_gradient(
    A: MatLike,
    b: Sequence[float],
    x0: Sequence[float] | None = None,
    max_iter: int = 1000,
    tol: float = 1e-10,
) -> SolveResult:
    """Conjugate Gradient method for SPD systems.

    Minimizes ``f(x) = 1/2 x^T A x - b^T x`` using A-conjugate search
    directions.  For an ``n x n`` SPD matrix, CG converges in at most
    ``n`` steps in exact arithmetic.
    """
    rows, cols = _shape(A)
    if rows != cols:
        raise ValueError("CG requires a square matrix")
    if len(b) != rows:
        raise ValueError("b length must match matrix dimension")

    x = list(x0) if x0 is not None else [0.0] * rows
    r = [b[i] - val for i, val in enumerate(_matvec(A, x))]
    p = list(r)
    rs_old = sum(ri * ri for ri in r)
    history: List[float] = []
    residual: float = math.sqrt(rs_old)

    for k in range(max_iter):
        Ap = _matvec(A, p)
        denom = sum(p[i] * Ap[i] for i in range(rows))
        if abs(denom) < EPS:
            # A is not SPD (or p is zero); bail.
            residual = math.sqrt(rs_old)
            history.append(residual)
            return SolveResult(x, k, residual, residual < tol, "cg", history)
        alpha = rs_old / denom
        for i in range(rows):
            x[i] += alpha * p[i]
            r[i] -= alpha * Ap[i]
        rs_new = sum(ri * ri for ri in r)
        residual = math.sqrt(rs_new)
        history.append(residual)
        if residual < tol:
            return SolveResult(x, k + 1, residual, True, "cg", history)
        beta = rs_new / rs_old
        for i in range(rows):
            p[i] = r[i] + beta * p[i]
        rs_old = rs_new

    return SolveResult(x, max_iter, residual, False, "cg", history)