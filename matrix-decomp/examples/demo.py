#!/usr/bin/env python3
"""Example: solving a linear system and computing a Cholesky factorization."""

from matrix_decomp import (
    Matrix,
    lu_decompose,
    lu_solve,
    cholesky,
    qr_householder,
    svd,
    jacobi_eigen,
    least_squares,
    linear_fit,
)


def main() -> None:
    # --- Linear system via LU ---
    A = Matrix([[4.0, 3.0], [6.0, 3.0]])
    b = [10.0, 12.0]
    x = lu_solve(A, b)
    print("LU solve A x = b:")
    print("  A =", A.data)
    print("  b =", b)
    print("  x =", x, "(expected [1, 2])")

    L, U, perm, sign = lu_decompose(A)
    print("  L =", L.data)
    print("  U =", U.data)
    print("  perm =", perm, "sign =", sign)

    # --- Cholesky on an SPD matrix ---
    S = Matrix([[4.0, 2.0], [2.0, 3.0]])
    Lc = cholesky(S)
    print("\nCholesky of", S.data)
    print("  L =", Lc.data)

    # --- QR ---
    Q, R = qr_householder(Matrix([[1.0, 1.0], [1.0, 0.0], [0.0, 1.0]]))
    print("\nQR of a 3x2 matrix:")
    print("  Q =", Q.data)
    print("  R =", R.data)

    # --- SVD ---
    U, Svals, Vt = svd(Matrix([[1.0, 0.0], [0.0, 2.0]]))
    print("\nSVD of diag(1,2):")
    print("  U =", U.data)
    print("  S =", Svals)
    print("  Vt =", Vt.data)

    # --- Eigenvalues (Jacobi, symmetric) ---
    vals, V = jacobi_eigen(Matrix([[2.0, 1.0], [1.0, 2.0]]))
    print("\nEigenvalues of [[2,1],[1,2]]:", vals, "(expected [3, 1])")

    # --- Least squares / linear fit ---
    xs = [0.0, 1.0, 2.0, 3.0, 4.0]
    ys = [1.0, 3.0, 5.0, 7.0, 9.0]  # y = 2x + 1
    slope, intercept, r2 = linear_fit(xs, ys)
    print(f"\nLinear fit: slope={slope}, intercept={intercept}, R^2={r2}")

    # Over-determined least squares
    A_ls = [[1.0, x] for x in xs]
    coeffs = least_squares(A_ls, ys)
    print("Least-squares coeffs (intercept, slope):", coeffs)


if __name__ == "__main__":
    main()