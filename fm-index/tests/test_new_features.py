"""Tests for new FMIndex features (backend, batch, memory estimation)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fmindex import FMIndex


def test_wavelet_matrix_backend():
    idx = FMIndex("mississippi", backend="wavelet_matrix")
    assert idx.backend == "wavelet_matrix"
    assert idx.count("iss") == 2
    assert idx.locate("iss") == [1, 4]


def test_wavelet_tree_backend():
    idx = FMIndex("mississippi", backend="wavelet_tree")
    assert idx.backend == "wavelet_tree"
    assert idx.count("iss") == 2


def test_invalid_backend():
    with pytest.raises(ValueError):
        FMIndex("abc", backend="invalid")


def test_backend_parity():
    """Both backends should produce identical results."""
    text = "abracadabra"
    idx_tree = FMIndex(text, backend="wavelet_tree")
    idx_matrix = FMIndex(text, backend="wavelet_matrix")
    for pat in ["a", "b", "ab", "ra", "cad", "abra", "xyz"]:
        assert idx_tree.count(pat) == idx_matrix.count(pat)
        assert idx_tree.locate(pat) == idx_matrix.locate(pat)


def test_batch_locate():
    idx = FMIndex("mississippi")
    results = idx.batch_locate(["iss", "ss", "xyz"])
    assert results["iss"] == [1, 4]
    assert results["ss"] == [2, 5]
    assert results["xyz"] == []


def test_batch_locate_dedup():
    idx = FMIndex("mississippi")
    results = idx.batch_locate(["iss", "iss", "iss"])
    assert results["iss"] == [1, 4]


def test_batch_locate_non_str():
    idx = FMIndex("abc")
    with pytest.raises(TypeError):
        idx.batch_locate([123])


def test_first_occurrence():
    idx = FMIndex("mississippi")
    assert idx.first_occurrence("iss") == 1
    assert idx.first_occurrence("ss") == 2
    assert idx.first_occurrence("xyz") is None


def test_last_occurrence():
    idx = FMIndex("mississippi")
    assert idx.last_occurrence("iss") == 4
    assert idx.last_occurrence("ss") == 5
    assert idx.last_occurrence("xyz") is None


def test_estimate_memory_bytes():
    idx = FMIndex("mississippi")
    mem = idx.estimate_memory_bytes()
    assert mem > 0
    assert isinstance(mem, int)


def test_estimate_memory_scales():
    idx1 = FMIndex("ab")
    idx2 = FMIndex("ab" * 100)
    assert idx2.estimate_memory_bytes() > idx1.estimate_memory_bytes()


def test_count_non_str():
    idx = FMIndex("abc")
    with pytest.raises(TypeError):
        idx.count(123)


def test_repr_includes_backend():
    idx = FMIndex("abc", backend="wavelet_matrix")
    r = repr(idx)
    assert "wavelet_matrix" in r