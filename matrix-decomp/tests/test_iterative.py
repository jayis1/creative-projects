"""Tests for the iterative solvers (Jacobi, Gauss-Seidel, SOR, CG)."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp import Matrix, lu_solve
from matrix_decomp.iterative import (
    jacobi_solve,
    gauss_seidel_solve,
    sor_solve,
    conjugate_gradient,
)
from matrix_decomp.sparse import CSRMatrix


def _vec_approx(a, b, tol=1e-6):
    return all(abs(x - y) < tol for x, y in zip(a, b))


# A strictly diagonally dominant SPD matrix
_A = Matrix([[10.0, -1.0, 2.0], [-1.0, 11.0, -1.0], [2.0, -1.0, 10.0]])
_b = [12.0, -3.0, 7.0]
_expected = lu_solve(_A, _b)  # ground-truth from direct solve


def test_jacobi_converges():
    r = jacobi_solve(_A, _b, max_iter=500, tol=1e-12)
    assert r.converged
    assert r.iterations < 100
    assert _vec_approx(r.x, _expected, tol=1e-6)


def test_gauss_seidel_converges():
    r = gauss_seidel_solve(_A, _b, max_iter=500, tol=1e-12)
    assert r.converged
    assert r.iterations > 0
    assert _vec_approx(r.x, _expected, tol=1e-6)


def test_gauss_seidel_faster_than_jacobi():
    r_j = jacobi_solve(_A, _b, max_iter=500, tol=1e-12)
    r_gs = gauss_seidel_solve(_A, _b, max_iter=500, tol=1e-12)
    assert r_gs.iterations <= r_j.iterations


def test_sor_omega_one_matches_gauss_seidel():
    r_sor = sor_solve(_A, _b, omega=1.0, max_iter=500, tol=1e-12)
    r_gs = gauss_seidel_solve(_A, _b, max_iter=500, tol=1e-12)
    assert r_sor.converged
    assert _vec_approx(r_sor.x, r_gs.x, tol=1e-8)


def test_sor_over_relaxation():
    r = sor_solve(_A, _b, omega=1.5, max_iter=500, tol=1e-12)
    assert r.converged
    assert _vec_approx(r.x, _expected, tol=1e-6)


def test_sor_invalid_omega():
    try:
        sor_solve(_A, _b, omega=2.5)
        assert False
    except ValueError:
        pass
    try:
        sor_solve(_A, _b, omega=0.0)
        assert False
    except ValueError:
        pass


def test_conjugate_gradient_spd():
    A = Matrix([[4.0, 1.0], [1.0, 3.0]])
    b = [1.0, 2.0]
    expected = lu_solve(A, b)
    r = conjugate_gradient(A, b, tol=1e-14)
    assert r.converged
    assert r.iterations <= 2  # at most n steps for SPD
    assert _vec_approx(r.x, expected, tol=1e-6)


def test_conjugate_gradient_3x3():
    r = conjugate_gradient(_A, _b, tol=1e-14)
    assert r.converged
    assert _vec_approx(r.x, _expected, tol=1e-6)


def test_jacobi_with_csr():
    A_csr = CSRMatrix.from_dense([[10.0, -1.0, 0.0], [-1.0, 10.0, -2.0], [0.0, -2.0, 10.0]])
    b = [9.0, 7.0, 6.0]
    expected = lu_solve(A_csr.to_dense(), b)
    r = jacobi_solve(A_csr, b, tol=1e-12)
    assert r.converged
    assert _vec_approx(r.x, expected, tol=1e-6)


def test_cg_with_csr():
    A_csr = CSRMatrix.from_dense([[4.0, 1.0], [1.0, 3.0]])
    b = [1.0, 2.0]
    expected = lu_solve(A_csr.to_dense(), b)
    r = conjugate_gradient(A_csr, b, tol=1e-14)
    assert r.converged
    assert _vec_approx(r.x, expected, tol=1e-6)


def test_gauss_seidel_with_csr():
    A_csr = CSRMatrix.from_dense([[10.0, 1.0], [1.0, 10.0]])
    b = [11.0, 11.0]
    expected = lu_solve(A_csr.to_dense(), b)
    r = gauss_seidel_solve(A_csr, b, tol=1e-12)
    assert r.converged
    assert _vec_approx(r.x, expected, tol=1e-6)


def test_jacobi_non_square_raises():
    try:
        jacobi_solve(Matrix([[1, 2], [3, 4], [5, 6]]), [1, 2, 3])
        assert False
    except ValueError:
        pass


def test_jacobi_zero_diagonal_raises():
    try:
        jacobi_solve(Matrix([[0, 1], [1, 0]]), [1, 2], max_iter=10)
        assert False
    except ValueError:
        pass


def test_residual_decreases_jacobi():
    r = jacobi_solve(_A, _b, max_iter=200, tol=1e-14)
    # History should be monotonically decreasing (roughly).
    for i in range(1, len(r.history)):
        assert r.history[i] <= r.history[i - 1] + 1e-12  # allow tiny wiggle


def test_solve_result_repr():
    r = jacobi_solve(_A, _b, max_iter=5, tol=1e-20)
    s = repr(r)
    assert "SolveResult" in s
    assert "jacobi" in s


def test_sor_matches_expected():
    r = sor_solve(_A, _b, omega=1.0, max_iter=500, tol=1e-12)
    assert _vec_approx(r.x, _expected, tol=1e-6)