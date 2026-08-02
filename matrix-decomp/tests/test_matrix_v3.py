"""Tests for the new Matrix class methods and operator overloads (v3.0)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp import Matrix, identity


def test_pow_operator():
    A = Matrix([[1, 1], [0, 1]])
    P3 = A ** 3
    assert P3.data == [[1, 3], [0, 1]]
    P0 = A ** 0
    assert P0.approx_equal(identity(2))


def test_truediv_operator():
    A = Matrix([[2.0, 4.0], [6.0, 8.0]])
    B = A / 2.0
    assert B.data == [[1.0, 2.0], [3.0, 4.0]]


def test_truediv_by_zero():
    A = Matrix([[1.0, 2.0]])
    try:
        A / 0.0
        assert False
    except ZeroDivisionError:
        pass


def test_iter_rows():
    A = Matrix([[1, 2], [3, 4]])
    rows = list(A)
    assert rows == [[1.0, 2.0], [3.0, 4.0]]


def test_contains():
    A = Matrix([[1, 2], [3, 4]])
    assert 3.0 in A
    assert 5.0 not in A


def test_to_list():
    A = Matrix([[1, 2], [3, 4]])
    lst = A.to_list()
    assert lst == [[1.0, 2.0], [3.0, 4.0]]
    # Ensure deep copy
    lst[0][0] = 99
    assert A[0][0] == 1.0


def test_flatten():
    A = Matrix([[1, 2], [3, 4]])
    assert A.flatten() == [1.0, 2.0, 3.0, 4.0]


def test_map():
    A = Matrix([[1.0, 2.0], [3.0, 4.0]])
    B = A.map(lambda x: x * x)
    assert B.data == [[1.0, 4.0], [9.0, 16.0]]


def test_is_symmetric_method():
    A = Matrix([[1, 2], [2, 3]])
    assert A.is_symmetric()
    B = Matrix([[1, 2], [3, 4]])
    assert not B.is_symmetric()
    C = Matrix([[1, 2, 3], [4, 5, 6]])
    assert not C.is_symmetric()  # non-square