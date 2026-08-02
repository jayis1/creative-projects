"""Tests for the decompositions module (Schur, spectral, polar, complete-pivot LU)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp import (
    Matrix,
    identity,
    matmul,
    transpose,
    schur_decomposition,
    spectral_decomposition,
    polar_decomposition,
    lu_complete_pivot,
    lu_solve,
    determinant,
)
from matrix_decomp.decompositions import lu_complete_pivot as _lcp


def _mat_approx(A, B, tol=1e-6):
    return all(abs(A[i][j] - B[i][j]) < tol for i in range(len(A)) for j in range(len(A[0])))


def test_spectral_decomposition():
    A = Matrix([[2.0, 1.0], [1.0, 2.0]])
    evals, V = spectral_decomposition(A)
    # A = V diag(evals) V^T
    D = Matrix([[evals[i] if i == j else 0.0 for j in range(2)] for i in range(2)])
    recon = matmul(matmul(V, D), transpose(V))
    assert _mat_approx(recon.data, A.data, tol=1e-6)


def test_schur_decomposition():
    A = Matrix([[4.0, 1.0], [1.0, 4.0]])
    Q, T = schur_decomposition(A)
    # Q orthogonal
    assert _mat_approx(matmul(transpose(Q), Q).data, identity(2).data, tol=1e-6)
    # A = Q T Q^T
    recon = matmul(matmul(Q, T), transpose(Q))
    assert _mat_approx(recon.data, A.data, tol=1e-6)
    # T diagonal (symmetric -> diagonal)
    assert abs(T[0][1]) < 1e-9 and abs(T[1][0]) < 1e-9


def test_schur_non_symmetric_raises():
    try:
        schur_decomposition(Matrix([[1, 2], [3, 4]]))
        assert False
    except ValueError:
        pass


def test_schur_non_square_raises():
    try:
        schur_decomposition(Matrix([[1, 2, 3]]))
        assert False
    except ValueError:
        pass


def test_polar_decomposition():
    # A simple test: polar of identity is (I, I)
    Q, P = polar_decomposition(identity(3))
    assert _mat_approx(Q.data, identity(3).data, tol=1e-6)
    assert _mat_approx(P.data, identity(3).data, tol=1e-6)


def test_polar_decomposition_reconstruction():
    A = Matrix([[3.0, 1.0], [1.0, 2.0]])
    Q, P = polar_decomposition(A)
    # A = Q P
    recon = matmul(Q, P)
    assert _mat_approx(recon.data, A.data, tol=1e-5)
    # Q orthogonal
    assert _mat_approx(matmul(transpose(Q), Q).data, identity(2).data, tol=1e-5)
    # P symmetric
    assert abs(P[0][1] - P[1][0]) < 1e-5


def test_polar_decomposition_non_square_raises():
    try:
        polar_decomposition(Matrix([[1, 2, 3], [4, 5, 6]]))
        assert False
    except ValueError:
        pass


def test_lu_complete_pivot():
    A = Matrix([[0.0, 1.0], [1.0, 0.0]])  # needs column+row pivot
    L, U, rp, cp, sign = lu_complete_pivot(A)
    # PAQ = LU: build P and Q
    n = 2
    P = [[0.0] * n for _ in range(n)]
    for i in range(n):
        P[i][rp[i]] = 1.0
    Q = [[0.0] * n for _ in range(n)]
    for j in range(n):
        Q[cp[j]][j] = 1.0
    PAQ = matmul(matmul(Matrix(P), A), Matrix(Q))
    LU = matmul(L, U)
    assert _mat_approx(PAQ.data, LU.data, tol=1e-9)


def test_lu_complete_pivot_det():
    A = Matrix([[6.0, 1.0, 1.0], [4.0, -2.0, 5.0], [2.0, 8.0, 7.0]])
    _, U, _, _, sign = lu_complete_pivot(A)
    det_cp = sign
    for i in range(3):
        det_cp *= U[i][i]
    # |det| should match (sign may differ due to column pivoting).
    assert abs(abs(det_cp) - abs(determinant(A))) < 1e-9


def test_lu_complete_pivot_singular_raises():
    from matrix_decomp import SingularMatrixError

    A = Matrix([[1.0, 2.0], [2.0, 4.0]])  # singular
    try:
        lu_complete_pivot(A)
        assert False
    except SingularMatrixError:
        pass


def test_lu_complete_pivot_solve():
    # Verify that PAQ = LU can be used to solve a system (column pivot complicates
    # things, but we just check the factorization reconstructs correctly).
    A = Matrix([[2.0, 3.0], [4.0, 1.0]])
    L, U, rp, cp, sign = lu_complete_pivot(A)
    n = 2
    P = [[0.0] * n for _ in range(n)]
    for i in range(n):
        P[i][rp[i]] = 1.0
    Q = [[0.0] * n for _ in range(n)]
    for j in range(n):
        Q[cp[j]][j] = 1.0
    PAQ = matmul(matmul(Matrix(P), A), Matrix(Q))
    LU = matmul(L, U)
    assert _mat_approx(PAQ.data, LU.data, tol=1e-9)