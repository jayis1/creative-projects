#!/usr/bin/env python3
"""Example: Sparse (CSR) matrix operations.

Demonstrates constructing a CSR matrix from dense and COO format,
matrix-vector and matrix-matrix multiplication, transpose, and
converting back to dense.
"""

from matrix_decomp.sparse import CSRMatrix
from matrix_decomp import Matrix


def main() -> None:
    # Build from dense.
    dense = [
        [0, 0, 3, 0, 0],
        [0, 0, 0, 4, 0],
        [0, 5, 0, 0, 0],
        [6, 0, 0, 0, 0],
        [0, 0, 0, 0, 7],
    ]
    A = CSRMatrix.from_dense(dense)
    print(f"A: {A}")
    print(f"  nnz = {A.nnz}, density = {A.density:.2%}")

    # Iterate over non-zero entries.
    print("\n  Non-zero entries:")
    for i, j, v in A:
        print(f"    ({i}, {j}) = {v}")

    # Matrix-vector product.
    x = [1, 1, 1, 1, 1]
    y = A.matvec(x)
    print(f"\n  A @ {x} = {y}")

    # Transpose.
    At = A.transpose()
    print(f"\n  A^T: {At}")
    print(f"  A^T dense:")
    print(At.to_dense())

    # Build from COO (coordinate) triples.
    coords = [
        (0, 0, 1.0), (0, 2, 2.0),
        (1, 1, 3.0),
        (2, 0, 4.0), (2, 2, 5.0),
    ]
    B = CSRMatrix.from_coo(coords, (3, 3))
    print(f"\nB (from COO): {B}")
    print(f"  B dense:")
    print(B.to_dense())

    # Matrix-matrix product.
    C = A.matmul(A.transpose())
    print(f"\nA @ A^T: {C}")
    print(f"  dense:")
    print(C.to_dense())

    # Sparse vs dense comparison.
    dense_A = Matrix(dense)
    from matrix_decomp import matvec as dense_matvec
    assert A.matvec(x) == dense_matvec(dense_A, x), "Mismatch!"
    print("\n  ✓ Sparse matvec matches dense matvec")


if __name__ == "__main__":
    main()