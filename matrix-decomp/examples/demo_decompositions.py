#!/usr/bin/env python3
"""Example: Schur and Polar decompositions.

Demonstrates decomposing a symmetric matrix via the Schur decomposition
(A = Q T Q^T) and a general square matrix via the polar decomposition
(A = Q P).
"""

from matrix_decomp import Matrix, matmul, transpose, identity
from matrix_decomp.decompositions import schur_decomposition, polar_decomposition


def main() -> None:
    # ---- Schur decomposition (symmetric matrix) ----
    A = Matrix([
        [4.0, 1.0, 2.0],
        [1.0, 5.0, 3.0],
        [2.0, 3.0, 6.0],
    ])
    print("=== Schur Decomposition (A = Q T Q^T) ===")
    print(f"A =")
    print(A)

    Q, T = schur_decomposition(A)
    print(f"\nQ (orthogonal) =")
    print(Q)
    print(f"\nT (diagonal, eigenvalues) =")
    print(T)

    # Verify Q T Q^T = A.
    recon = matmul(matmul(Q, T), transpose(Q))
    print(f"\nQ T Q^T =")
    print(recon)
    assert recon.approx_equal(A, tol=1e-6), "Reconstruction failed!"
    print("  ✓ Q T Q^T ≈ A")

    # Verify Q is orthogonal.
    QtQ = matmul(transpose(Q), Q)
    assert QtQ.approx_equal(identity(3), tol=1e-6), "Q not orthogonal!"
    print("  ✓ Q^T Q ≈ I")

    # ---- Polar decomposition ----
    print("\n=== Polar Decomposition (A = Q P) ===")
    B = Matrix([
        [3.0, 1.0, 0.0],
        [1.0, 2.0, 1.0],
        [0.0, 1.0, 1.0],
    ])
    print(f"B =")
    print(B)

    Qp, P = polar_decomposition(B)
    print(f"\nQ (orthogonal) =")
    print(Qp)
    print(f"\nP (symmetric PSD) =")
    print(P)

    # Verify Q P = B.
    recon2 = matmul(Qp, P)
    print(f"\nQ P =")
    print(recon2)
    assert recon2.approx_equal(B, tol=1e-5), "Polar reconstruction failed!"
    print("  ✓ Q P ≈ B")

    # Verify Q is orthogonal.
    assert matmul(transpose(Qp), Qp).approx_equal(identity(3), tol=1e-5)
    print("  ✓ Q^T Q ≈ I")


if __name__ == "__main__":
    main()