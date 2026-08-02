"""Tests for the CSR sparse matrix module."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp import Matrix
from matrix_decomp.sparse import CSRMatrix


def test_from_dense():
    A = CSRMatrix.from_dense([[0, 0, 1], [2, 0, 0], [0, 3, 0]])
    assert A.nnz == 3
    assert A.rows == 3
    assert A.cols == 3
    assert A.shape_tuple() == (3, 3)
    assert A.density == 3 / 9


def test_matvec():
    A = CSRMatrix.from_dense([[0, 0, 1], [2, 0, 0], [0, 3, 0]])
    y = A.matvec([1, 1, 1])
    assert y == [1, 2, 3]


def test_get():
    A = CSRMatrix.from_dense([[0, 0, 5], [2, 0, 0], [0, 3, 0]])
    assert A.get(0, 2) == 5
    assert A.get(0, 0) == 0
    assert A.get(1, 0) == 2


def test_get_out_of_bounds():
    A = CSRMatrix.from_dense([[0, 0, 1], [2, 0, 0]])
    try:
        A.get(5, 0)
        assert False
    except IndexError:
        pass


def test_transpose():
    A = CSRMatrix.from_dense([[1, 0], [0, 2], [3, 0]])
    At = A.transpose()
    assert At.rows == 2 and At.cols == 3
    # Transpose of [[1,0],[0,2],[3,0]] is [[1,0,3],[0,2,0]]
    assert At.to_dense().data == [[1.0, 0.0, 3.0], [0.0, 2.0, 0.0]]


def test_to_dense():
    A = CSRMatrix.from_dense([[0, 2], [3, 0]])
    D = A.to_dense()
    assert isinstance(D, Matrix)
    assert D.data == [[0.0, 2.0], [3.0, 0.0]]


def test_from_coo():
    coords = [(0, 1, 5.0), (1, 0, 3.0), (0, 1, 1.0)]  # duplicate (0,1) should sum
    A = CSRMatrix.from_coo(coords, (2, 2))
    D = A.to_dense()
    assert D.data == [[0.0, 6.0], [3.0, 0.0]]


def test_from_coo_out_of_bounds():
    try:
        CSRMatrix.from_coo([(0, 5, 1.0)], (2, 2))
        assert False
    except ValueError:
        pass


def test_matmul():
    A = CSRMatrix.from_dense([[1, 0], [0, 0]])
    B = CSRMatrix.from_dense([[0, 2], [3, 0]])
    C = A.matmul(B)
    # [[1,0],[0,0]] @ [[0,2],[3,0]] = [[0,2],[0,0]]
    assert C.to_dense().data == [[0.0, 2.0], [0.0, 0.0]]


def test_matmul_shape_mismatch():
    A = CSRMatrix.from_dense([[1, 0, 0]])
    B = CSRMatrix.from_dense([[1, 0], [0, 1]])
    try:
        A.matmul(B)
        assert False
    except ValueError:
        pass


def test_iteration():
    A = CSRMatrix.from_dense([[0, 2], [3, 0]])
    entries = list(A)
    assert entries == [(0, 1, 2.0), (1, 0, 3.0)]


def test_invalid_indptr():
    try:
        CSRMatrix([1.0], [0], [0, 0], (2, 2))  # indptr[-1] != len(data)
        assert False
    except ValueError:
        pass


def test_repr():
    A = CSRMatrix.from_dense([[0, 1], [0, 0]])
    assert "CSRMatrix" in repr(A)
    assert "nnz=1" in repr(A)


def test_tolerance_filter():
    # With a tolerance, tiny entries should be dropped.
    A = CSRMatrix.from_dense([[0, 1e-20], [1, 0]], tol=1e-15)
    assert A.nnz == 1  # only the 1 remains


def test_dense_vs_sparse_matvec():
    from matrix_decomp import matvec as dense_matvec

    dense = [[1, 0, 2], [0, 3, 0], [4, 0, 5]]
    sparse = CSRMatrix.from_dense(dense)
    x = [1, 1, 1]
    assert sparse.matvec(x) == dense_matvec(Matrix(dense), x)