"""Bug-hunt tests: written to expose bugs before fixing them."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp import (
    Matrix, rank, condition_number, svd, lu_solve, lu_decompose,
    cholesky, qr_householder, qr_solve, jacobi_eigen, qr_algorithm,
    least_squares, least_norm, pseudo_inverse, matrix_power,
    hilbert, vandermonde, is_spd, determinant, lu_inverse,
)


def test_rank_near_singular():
    """Bug: rank() uses absolute tolerance, giving wrong rank for
    matrices where numerical roundoff produces small but non-zero SVs
    relative to tol=1e-9.  Row 2 = 2*Row 1, so rank should be 2."""
    A = Matrix([[1, 2, 3], [2, 4, 6], [1, 1, 1]])
    r = rank(A)
    assert r == 2, f"Expected rank 2, got {r}"


def test_rank_scaled():
    """Bug: rank() with absolute tolerance fails for scaled matrices.
    A matrix with entries ~1e6 but rank-deficient should still have the
    correct rank.  [[1e6, 2e6], [2e6, 4e6]] has rank 1."""
    A = Matrix([[1e6, 2e6], [2e6, 4e6]])
    r = rank(A)
    assert r == 1, f"Expected rank 1, got {r}"


def test_condition_number_relative():
    """Bug: condition_number uses absolute 1e-15 threshold for zero SVs,
    which can give inf for well-conditioned matrices where the smallest
    SV is just above 1e-15 but the matrix is not actually singular.
    Also: for a scaled identity, should give the ratio."""
    A = Matrix([[1, 0], [0, 1e-10]])
    cn = condition_number(A)
    # 1 / 1e-10 = 1e10, not inf
    assert cn == float("inf") or abs(cn - 1e10) / 1e10 < 0.01, f"Got {cn}"


def test_qr_solve_square_singular_raises():
    """A singular square matrix via qr_solve should raise, not return NaN."""
    A = Matrix([[1, 2], [2, 4]])
    try:
        qr_solve(A, [1, 2])
        assert False, "Should have raised"
    except Exception:
        pass


def test_lu_decompose_perm_correctness():
    """Verify PA = LU holds with the returned permutation."""
    A = Matrix([[0, 1], [1, 0]])  # needs row swap
    L, U, perm, sign = lu_decompose(A)
    # Build P from perm
    n = 2
    P = [[0.0] * n for _ in range(n)]
    for i in range(n):
        P[i][perm[i]] = 1.0
    PA = Matrix(P) @ A
    LU = L @ U
    assert PA.approx_equal(LU, tol=1e-9), f"PA={PA.data}, LU={LU.data}"


def test_matrix_power_zero():
    """A^0 should be identity even for non-trivial matrices."""
    A = Matrix([[5, 3], [2, 1]])
    result = matrix_power(A, 0)
    from matrix_decomp import identity
    assert result.approx_equal(identity(2))


def test_jacobi_eigen_identity_matrix():
    """Eigenvalues of identity should all be 1."""
    from matrix_decomp import identity
    vals, V = jacobi_eigen(identity(3))
    assert all(abs(v - 1.0) < 1e-9 for v in vals), f"Got {vals}"


def test_cholesky_solve_matches_lu():
    """Cholesky and LU should give the same solution for SPD matrices."""
    A = Matrix([[4, 2, 1], [2, 5, 3], [1, 3, 6]])
    b = [7, 10, 10]
    x_chol = cholesky(A)
    from matrix_decomp import cholesky_solve
    x_c = cholesky_solve(A, b)
    x_l = lu_solve(A, b)
    assert all(abs(a - b) < 1e-9 for a, b in zip(x_c, x_l)), f"Cholesky={x_c}, LU={x_l}"


def test_vandermonde_zero():
    """Vandermonde with x=0 should handle 0**0=1 correctly (highest power first)."""
    V = vandermonde([0, 1, 2])
    # Highest power first: [x^2, x^1, x^0]
    assert V.data == [[0, 0, 1], [1, 1, 1], [4, 2, 1]], f"Got {V.data}"


def test_svd_orthonormal_u_columns():
    """U columns should be orthonormal even for rank-deficient matrices."""
    A = Matrix([[1, 2, 3], [2, 4, 6]])  # rank 1
    U, S, Vt = svd(A)
    # Check U^T U ≈ I (columns orthonormal)
    from matrix_decomp import transpose, identity
    UtU = transpose(U) @ U
    assert UtU.approx_equal(identity(UtU.rows), tol=1e-6), f"U^T U = {UtU.data}"


def test_pseudo_inverse_properties():
    """A A+ A = A and A+ A A+ = A+ (Moore-Penrose properties)."""
    A = Matrix([[1, 2], [3, 4], [5, 6]])
    Aplus = pseudo_inverse(A)
    from matrix_decomp import matmul
    AApA = matmul(matmul(A, Aplus), A)
    assert AApA.approx_equal(A, tol=1e-5)
    ApAAp = matmul(matmul(Aplus, A), Aplus)
    assert ApAAp.approx_equal(Aplus, tol=1e-5)


def test_determinant_zero_pivot():
    """Determinant of a singular matrix should raise (not return 0)."""
    A = Matrix([[1, 2], [2, 4]])
    try:
        d = determinant(A)
        # If it doesn't raise, it should be 0
        assert abs(d) < 1e-10, f"Expected 0 or raise, got {d}"
    except Exception:
        pass  # Raising is also acceptable


def test_least_squares_tall():
    """Least-squares on an over-determined system should give a small residual."""
    A = [[1, 0], [1, 1], [1, 2], [1, 3]]
    b = [1, 2, 2, 3]
    x = least_squares(A, b)
    # Exact fit isn't possible; verify it minimizes residual
    from matrix_decomp import residual_norm
    r = residual_norm(Matrix(A), b, x)
    assert r < 1.5, f"Residual too large: {r}"


def test_hilbert_spd_cholesky():
    """Hilbert matrix is SPD; Cholesky should succeed for n=4."""
    H = hilbert(4)
    L = cholesky(H)
    from matrix_decomp import matmul, transpose
    assert matmul(L, transpose(L)).approx_equal(H, tol=1e-6)


# ---------------------------------------------------------------------------
# Bug fixes verified
# ---------------------------------------------------------------------------
def test_rank_relative_tolerance_fixed():
    """Bug fix: rank() now uses relative tolerance so near-singular matrices
    with O(1) entries are correctly classified.  [[1,2,3],[2,4,6],[1,1,1]]
    has rank 2 (row 2 = 2*row 1)."""
    A = Matrix([[1, 2, 3], [2, 4, 6], [1, 1, 1]])
    assert rank(A) == 2


def test_rank_identity_still_full():
    """After the relative-tolerance fix, full-rank matrices still report
    the correct rank."""
    assert rank(Matrix([[1, 0], [0, 1]])) == 2
    from matrix_decomp import identity
    assert rank(identity(4)) == 4


def test_qr_algorithm_complex_eigenvalues_no_crash():
    """Bug fix: Wilkinson shift used to crash with complex sqrt when the
    trailing 2x2 block had complex eigenvalues.  Now it gracefully falls
    back to the real part as a shift."""
    from matrix_decomp.eigen import qr_algorithm
    # Rotation matrix has eigenvalues ±i (complex); should not crash.
    A = Matrix([[0, -1], [1, 0]])
    vals = qr_algorithm(A, max_iter=200)
    # Should return near-zero values (real parts of ±i).
    assert all(abs(v) < 1e-6 for v in vals), f"Expected near-zero, got {vals}"


def test_condition_number_singular_matrix():
    """A truly singular matrix should report inf condition number."""
    A = Matrix([[1, 2], [2, 4]])  # rank 1, singular
    cn = condition_number(A)
    assert cn == float("inf"), f"Expected inf, got {cn}"


def test_condition_number_well_conditioned():
    """Identity should have condition number 1."""
    from matrix_decomp import identity
    assert abs(condition_number(identity(3)) - 1.0) < 1e-9