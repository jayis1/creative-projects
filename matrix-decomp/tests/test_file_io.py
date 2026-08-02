"""Tests for the file I/O module (CSV / JSON read/write)."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp import Matrix
from matrix_decomp.file_io import save_csv, load_csv, save_json, load_json, parse_matrix_string


def test_csv_roundtrip():
    A = Matrix([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        path = f.name
    try:
        save_csv(A, path)
        B = load_csv(path)
        assert B.rows == 2 and B.cols == 3
        for i in range(2):
            for j in range(3):
                assert abs(B[i][j] - A[i][j]) < 1e-10
    finally:
        os.unlink(path)


def test_csv_whitespace_delimited():
    content = "1 2 3\n4 5 6\n"
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        B = load_csv(path)
        assert B.data == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    finally:
        os.unlink(path)


def test_csv_semicolon_delimited():
    content = "1;2;3\n4;5;6\n"
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        B = load_csv(path)
        assert B.data == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    finally:
        os.unlink(path)


def test_csv_skip_header():
    content = "a,b,c\n1,2,3\n4,5,6\n"
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        B = load_csv(path, skip_header=True)
        assert B.data == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    finally:
        os.unlink(path)


def test_csv_empty_file_raises():
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        f.write("")
        path = f.name
    try:
        load_csv(path)
        assert False
    except ValueError:
        pass
    finally:
        os.unlink(path)


def test_json_bare_array_roundtrip():
    A = Matrix([[1.0, 2.0], [3.0, 4.0]])
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        path = f.name
    try:
        save_json(A, path)
        with open(path) as fh:
            obj = json.load(fh)
        assert obj == [[1.0, 2.0], [3.0, 4.0]]
        B = load_json(path)
        assert B.data == A.data
    finally:
        os.unlink(path)


def test_json_wrapper_roundtrip():
    A = Matrix([[1.0, 2.0], [3.0, 4.0]])
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        path = f.name
    try:
        save_json(A, path, wrapper=True)
        B = load_json(path)
        assert B.data == A.data
    finally:
        os.unlink(path)


def test_json_invalid_raises():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write('{"foo": 42}')
        path = f.name
    try:
        load_json(path)
        assert False
    except ValueError:
        pass
    finally:
        os.unlink(path)


def test_parse_matrix_string_json():
    M = parse_matrix_string('[[1,2],[3,4]]')
    assert M.data == [[1.0, 2.0], [3.0, 4.0]]


def test_parse_matrix_string_semicolon():
    M = parse_matrix_string("1 2 3 ; 4 5 6")
    assert M.data == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]


def test_parse_matrix_string_comma():
    M = parse_matrix_string("1,2\n3,4")
    assert M.data == [[1.0, 2.0], [3.0, 4.0]]


def test_parse_matrix_string_empty_raises():
    try:
        parse_matrix_string("   ")
        assert False
    except ValueError:
        pass