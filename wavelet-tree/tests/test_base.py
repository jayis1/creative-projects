"""Tests for the WaveletBase abstract base class and its default methods."""

import pytest
import random

from wavelet_tree import WaveletTree, WaveletMatrix, HuffmanWaveletTree, HuffmanWaveletMatrix
from wavelet_tree.base import WaveletBase


SEQUENCES = [
    "abracadabra",
    "mississippi",
    "hello world",
    "abcdefg",
    "a",
    "aaaaaaaaaa",
    "ab",
]

for seed in range(10):
    random.seed(seed)
    length = random.randint(1, 100)
    sigma = random.randint(1, 15)
    seq = "".join(chr(ord("a") + random.randint(0, sigma - 1)) for _ in range(length))
    SEQUENCES.append(seq)

ALL_STRUCTURES = [
    WaveletTree,
    WaveletMatrix,
    HuffmanWaveletTree,
    HuffmanWaveletMatrix,
]


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_isinstance(cls, seq):
    """All structures should be instances of WaveletBase."""
    wt = cls(seq)
    assert isinstance(wt, WaveletBase)


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_getitem(cls, seq):
    """__getitem__ should match access."""
    if not seq:
        return
    wt = cls(seq)
    for i in range(len(seq)):
        assert wt[i] == seq[i]


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_negative_index(cls, seq):
    """Negative indexing should work like Python lists."""
    if not seq:
        return
    wt = cls(seq)
    for i in range(len(seq)):
        assert wt[-len(seq) + i] == seq[i]
    assert wt[-1] == seq[-1]


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
def test_index_out_of_range(cls):
    """Indexing out of range should raise IndexError."""
    wt = cls("abc")
    with pytest.raises(IndexError):
        _ = wt[5]
    with pytest.raises(IndexError):
        _ = wt[-10]


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_iter(cls, seq):
    """Iteration should yield all symbols in order."""
    if not seq:
        return
    wt = cls(seq)
    assert list(wt) == list(seq)


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_reversed(cls, seq):
    """__reversed__ should yield symbols in reverse order."""
    if not seq:
        return
    wt = cls(seq)
    assert list(reversed(wt)) == list(reversed(seq))


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_contains(cls, seq):
    """__contains__ should check alphabet membership."""
    wt = cls(seq)
    for c in set(seq):
        assert c in wt
    assert "z" not in wt
    assert "1" not in wt


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_count(cls, seq):
    """count() should return total occurrences of a symbol."""
    wt = cls(seq)
    for c in set(seq):
        assert wt.count(c) == seq.count(c)
    assert wt.count("z") == 0


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_index(cls, seq):
    """index() should return the first occurrence position."""
    if not seq:
        return
    wt = cls(seq)
    for c in set(seq):
        expected = seq.index(c)
        assert wt.index(c) == expected


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_index_with_start(cls, seq):
    """index() with start should find first occurrence at or after start."""
    if not seq:
        return
    wt = cls(seq)
    for c in set(seq):
        for start in range(len(seq)):
            try:
                expected = seq.index(c, start)
            except ValueError:
                expected = -1
            assert wt.index(c, start) == expected


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_positions(cls, seq):
    """positions() should return all positions of a symbol."""
    if not seq:
        return
    wt = cls(seq)
    for c in set(seq):
        expected = [i for i, ch in enumerate(seq) if ch == c]
        assert wt.positions(c) == expected


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_to_list(cls, seq):
    """to_list() should reconstruct the sequence."""
    if not seq:
        return
    wt = cls(seq)
    assert wt.to_list() == list(seq)


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_equality(cls, seq):
    """Two structures over the same sequence should be equal."""
    wt1 = cls(seq)
    wt2 = cls(seq)
    assert wt1 == wt2


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
def test_inequality(cls):
    """Structures over different sequences should not be equal."""
    wt1 = cls("abc")
    wt2 = cls("abd")
    assert wt1 != wt2


def test_equality_different_structures():
    """Different structure types over the same sequence should be equal."""
    seq = "abracadabra"
    wt = WaveletTree(seq)
    wm = WaveletMatrix(seq)
    assert wt == wm


def test_inequality_different_lengths():
    """Structures of different lengths should not be equal."""
    wt1 = WaveletTree("abc")
    wt2 = WaveletTree("abcd")
    assert wt1 != wt2


@pytest.mark.parametrize("cls", ALL_STRUCTURES)
@pytest.mark.parametrize("seq", SEQUENCES)
def test_hash(cls, seq):
    """Hash should be consistent and based on content."""
    if not seq:
        return
    wt1 = cls(seq)
    wt2 = cls(seq)
    assert hash(wt1) == hash(wt2)


def test_cannot_instantiate_abc():
    """Cannot instantiate WaveletBase directly."""
    with pytest.raises(TypeError):
        WaveletBase()