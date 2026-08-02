"""Test suite for the matrix_decomp package."""

from __future__ import annotations

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp import (
    Matrix,
    zeros,
    identity,
    transpose,
    matmul,
    is_square,
    trace,
    frobenius_norm,
    lu_decompose,
    lu_solve,
    lu_inverse,
    determinant,
    forward_sub,
    back_sub,
    cholesky,
    cholesky_solve,
    is_symmetric,
    is_spd,
    qr_householder,
    qr_solve,
    classical_gram_schmidt,
    modified_gram_schmidt,
    svd,
    svd_reconstruct,
    pseudo_inverse,
    rank,
    condition_number,
    qr_algorithm,
    eigen_decomposition,
    jacobi_eigen,
    power_iteration,
    least_squares,
    least_norm,
    linear_fit,
)


def approx(a, b, tol=1e-7):
    return abs(a - b) < tol


def vec_approx(a, b, tol=1e-6):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def mat_approx(A, B, tol=1e-6):
    return all(approx(A[i][j], B[i][j], tol) for i in range(len(A)) for j in range(len(A[0])))


# ---------------------------------------------------------------------------
# Matrix utilities
# ---------------------------------------------------------------------------
def test_identity():
    I = identity(3)
    assert I.data == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def test_transpose():
    A = Matrix([[1, 2, 3], [4, 5, 6]])
    At = transpose(A)
    assert At.data == [[1, 4], [2, 5], [3, 6]]


def test_matmul():
    A = Matrix([[1, 2], [3, 4]])
    B = Matrix([[5, 6], [7, 8]])
    C = matmul(A, B)
    assert C.data == [[19, 22], [43, 50]]


def test_matmul_identity():
    A = Matrix([[1, 2], [3, 4]])
    I = identity(2)
    assert matmul(A, I).approx_equal(A)


def test_is_square():
    assert is_square(Matrix([[1, 2], [3, 4]]))
    assert not is_square(Matrix([[1, 2, 3], [4, 5, 6]]))


def test_trace():
    assert approx(trace(Matrix([[1, 2], [3, 4]])), 5.0)


def test_frobenius_norm():
    assert approx(frobenius_norm(Matrix([[3, 0], [0, 4]])), 5.0)


# ---------------------------------------------------------------------------
# LU decomposition
# ---------------------------------------------------------------------------
def test_lu_decompose():
    A = Matrix([[4, 3], [6, 3]])
    L, U, perm, sign = lu_decompose(A)
    # PA = LU  =>  perm = [1, 0]
    P = Matrix([[0, 1], [1, 0]])
    PA = matmul(P, A)
    LU = matmul(L, U)
    assert PA.approx_equal(LU)


def test_lu_solve():
    A = Matrix([[2, 1], [1, 3]])
    b = [5, 10]
    x = lu_solve(A, b)
    assert vec_approx(x, [1.0, 3.0])


def test_lu_solve_3x3():
    A = Matrix([[3, 2, 1], [2, 3, 2], [1, 2, 4]])
    b = [6, 7, 7]
    x = lu_solve(A, b)
    assert vec_approx(x, [1.0, 1.0, 1.0])


def test_determinant():
    assert approx(determinant(Matrix([[1, 2], [3, 4]])), -2.0)


def test_determinant_3x3():
    A = Matrix([[6, 1, 1], [4, -2, 5], [2, 8, 7]])
    assert approx(determinant(A), -306.0)


def test_lu_inverse():
    A = Matrix([[4, 7], [2, 6]])
    inv = lu_inverse(A)
    prod = matmul(A, inv)
    assert prod.approx_equal(identity(2))


def test_forward_sub():
    L = Matrix([[2, 0], [1, 3]])
    y = forward_sub(L, [4, 5])
    assert vec_approx(y, [2.0, 1.0])


def test_back_sub():
    U = Matrix([[2, 3], [0, 4]])
    x = back_sub(U, [8, 4])
    # 4y = 4 => y = 1; 2x + 3 = 8 => x = 2.5
    assert vec_approx(x, [2.5, 1.0])


# ---------------------------------------------------------------------------
# Cholesky
# ---------------------------------------------------------------------------
def test_cholesky():
    A = Matrix([[4, 2], [2, 3]])
    L = cholesky(A)
    LLt = matmul(L, transpose(L))
    assert LLt.approx_equal(A)


def test_cholesky_solve():
    A = Matrix([[4, 2], [2, 3]])
    b = [10, 7]
    x = cholesky_solve(A, b)
    assert vec_approx(x, [2.0, 1.0])


def test_is_symmetric():
    assert is_symmetric(Matrix([[1, 2], [2, 3]]))
    assert not is_symmetric(Matrix([[1, 2], [3, 4]]))


def test_is_spd():
    assert is_spd(Matrix([[4, 2], [2, 3]]))
    assert not is_spd(Matrix([[1, 2], [3, 4]]))  # not symmetric
    assert not is_spd(Matrix([[-1, 0], [0, -1]]))  # not positive definite


def test_cholesky_non_spd_raises():
    try:
        cholesky(Matrix([[1, 2], [3, 4]]))  # not symmetric
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# QR
# ---------------------------------------------------------------------------
def test_qr_householder_square():
    A = Matrix([[12, -51, 4], [6, 167, -68], [-4, 24, -41]])
    Q, R = qr_householder(A)
    QR = matmul(Q, R)
    assert QR.approx_equal(A, tol=1e-6)
    # Q should be orthogonal
    assert matmul(transpose(Q), Q).approx_equal(identity(3), tol=1e-6)


def test_qr_householder_rect():
    A = Matrix([[1, 1], [1, 0], [0, 1]])
    Q, R = qr_householder(A)
    QR = matmul(Q, R)
    assert QR.approx_equal(A, tol=1e-6)
    assert matmul(transpose(Q), Q).approx_equal(identity(3), tol=1e-6)


def test_qr_solve():
    A = Matrix([[1, 1], [1, -1], [2, 1]])
    b = [2, 0, 3]
    x = qr_solve(A, b)
    # Least-squares solution
    Ax = matmul(A, Matrix([[x[0]], [x[1]]]))
    residual = [Ax[i][0] - b[i] for i in range(3)]
    assert math.sqrt(sum(r * r for r in residual)) < 0.5


def test_modified_gram_schmidt():
    A = Matrix([[1, 1], [1, 0], [0, 1]])
    Q, R = modified_gram_schmidt(A)
    QR = matmul(Q, R)
    assert QR.approx_equal(A, tol=1e-6)
    # Columns of Q orthonormal
    QtQ = matmul(transpose(Q), Q)
    assert QtQ.approx_equal(identity(2), tol=1e-6)


# ---------------------------------------------------------------------------
# SVD
# ---------------------------------------------------------------------------
def test_svd_square():
    A = Matrix([[3, 0], [0, 2]])
    U, S, Vt = svd(A)
    recon = svd_reconstruct(U, S, Vt)
    assert recon.approx_equal(A, tol=1e-6)
    assert vec_approx(S, [3.0, 2.0], tol=1e-6)


def test_svd_rect():
    A = Matrix([[1, 2], [3, 4], [5, 6]])
    U, S, Vt = svd(A)
    recon = svd_reconstruct(U, S, Vt)
    assert recon.approx_equal(A, tol=1e-5)


def test_pseudo_inverse():
    A = Matrix([[1, 2], [3, 4], [5, 6]])
    Aplus = pseudo_inverse(A)
    # A A+ A = A
    AAp = matmul(A, Aplus)
    AApA = matmul(AAp, A)
    assert AApA.approx_equal(A, tol=1e-5)


def test_rank():
    assert rank(identity(3)) == 3
    A = Matrix([[1, 2], [2, 4]])  # rank 1
    assert rank(A) == 1


def test_condition_number():
    A = Matrix([[1, 0], [0, 1e6]])
    cn = condition_number(A)
    assert approx(cn, 1e6, tol=1.0)


# ---------------------------------------------------------------------------
# Eigen
# ---------------------------------------------------------------------------
def test_jacobi_eigen():
    A = Matrix([[2, 1], [1, 2]])
    vals, V = jacobi_eigen(A)
    assert vec_approx(vals, [3.0, 1.0])
    # Check A v = lambda v for each eigenvector
    for k in range(2):
        vk = [V[i][k] for i in range(2)]
        Avk = [sum(A[i][j] * vk[j] for j in range(2)) for i in range(2)]
        scaled = [vals[k] * vk[i] for i in range(2)]
        assert vec_approx(Avk, scaled, tol=1e-6)


def test_jacobi_eigen_3x3():
    A = Matrix([[4, 1, 0], [1, 4, 1], [0, 1, 4]])
    vals, _ = jacobi_eigen(A)
    # Eigenvalues of this tridiagonal matrix: 4 + sqrt(2), 4, 4 - sqrt(2)
    expected = sorted([4 + math.sqrt(2), 4.0, 4 - math.sqrt(2)], reverse=True)
    assert vec_approx(vals, expected, tol=1e-6)


def test_qr_algorithm_eigenvalues():
    A = Matrix([[2, 1], [1, 2]])
    vals = qr_algorithm(A)
    assert vec_approx(sorted(vals, reverse=True), [3.0, 1.0], tol=1e-4)


def test_power_iteration():
    A = Matrix([[3, 0], [0, 1]])
    eval, evec = power_iteration(A)
    assert approx(eval, 3.0, tol=1e-4)


# ---------------------------------------------------------------------------
# Least squares
# ---------------------------------------------------------------------------
def test_least_squares_overdetermined():
    A = [[1, 0], [1, 1], [1, 2], [1, 3]]
    b = [1, 2, 3, 4]
    x = least_squares(A, b)
    assert vec_approx(x, [1.0, 1.0], tol=1e-6)


def test_linear_fit():
    xs = [0, 1, 2, 3, 4]
    ys = [1, 3, 5, 7, 9]  # y = 2x + 1
    slope, intercept, r2 = linear_fit(xs, ys)
    assert approx(slope, 2.0, tol=1e-6)
    assert approx(intercept, 1.0, tol=1e-6)
    assert approx(r2, 1.0, tol=1e-6)


def test_least_norm():
    # Under-determined: x + y = 1
    A = Matrix([[1, 1]])
    b = [1]
    x = least_norm(A, b)
    # Minimum-norm solution: x = [0.5, 0.5]
    assert vec_approx(x, [0.5, 0.5], tol=1e-5)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))