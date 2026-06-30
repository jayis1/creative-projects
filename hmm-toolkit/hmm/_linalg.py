"""Minimal linear-algebra helpers for the Gaussian HMM module.

Pure-Python implementations of determinant and matrix inverse via
Gaussian elimination with partial pivoting.  Intended for small matrices
(typically D ≤ 10) used as covariance matrices.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple


def det(mat: Sequence[Sequence[float]]) -> float:
    """Compute the determinant of a square matrix via Gaussian elimination."""
    n = len(mat)
    if n == 0:
        return 1.0
    # copy
    a = [list(row) for row in mat]
    d = 1.0
    for col in range(n):
        # partial pivot
        pivot = col
        for r in range(col + 1, n):
            if abs(a[r][col]) > abs(a[pivot][col]):
                pivot = r
        if abs(a[pivot][col]) < 1e-300:
            return 0.0
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            d = -d
        d *= a[col][col]
        for r in range(col + 1, n):
            factor = a[r][col] / a[col][col]
            for c in range(col, n):
                a[r][c] -= factor * a[col][c]
    return d


def inv(mat: Sequence[Sequence[float]]) -> List[List[float]]:
    """Compute the inverse of a square matrix via Gauss-Jordan elimination."""
    n = len(mat)
    if n == 0:
        return []
    # augmented [A | I]
    aug: List[List[float]] = []
    for i in range(n):
        row = list(mat[i]) + [1.0 if j == i else 0.0 for j in range(n)]
        aug.append(row)
    for col in range(n):
        pivot = col
        for r in range(col + 1, n):
            if abs(aug[r][col]) > abs(aug[pivot][col]):
                pivot = r
        if abs(aug[pivot][col]) < 1e-300:
            raise ValueError("Matrix is singular and cannot be inverted")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        piv = aug[col][col]
        for c in range(2 * n):
            aug[col][c] /= piv
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            for c in range(2 * n):
                aug[r][c] -= factor * aug[col][c]
    return [row[n:] for row in aug]


def add_ridge(mat: Sequence[Sequence[float]], ridge: float) -> List[List[float]]:
    """Add ``ridge * I`` to a square matrix (regularisation)."""
    n = len(mat)
    out = [list(row) for row in mat]
    for i in range(n):
        out[i][i] += ridge
    return out


def matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> List[List[float]]:
    """Matrix multiplication."""
    rows_a, cols_a = len(a), len(a[0])
    cols_b = len(b[0])
    result = [[0.0] * cols_b for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            s = 0.0
            for k in range(cols_a):
                s += a[i][k] * b[k][j]
            result[i][j] = s
    return result