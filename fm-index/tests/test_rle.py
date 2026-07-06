"""Tests for RLE (run-length encoding) module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fmindex.rle import rle_encode, rle_decode, RLEString


def test_rle_encode_basic():
    assert rle_encode("aaabbc") == [('a', 3), ('b', 2), ('c', 1)]
    assert rle_encode("") == []
    assert rle_encode("a") == [('a', 1)]
    assert rle_encode("abc") == [('a', 1), ('b', 1), ('c', 1)]


def test_rle_decode_basic():
    assert rle_decode([('a', 3), ('b', 2), ('c', 1)]) == "aaabbc"
    assert rle_decode([]) == ""
    assert rle_decode([('x', 5)]) == "xxxxx"


def test_rle_roundtrip():
    for s in ["", "a", "aa", "abc", "aaabbbccc", "mississippi"]:
        assert rle_decode(rle_encode(s)) == s


def test_rle_string_access():
    rle = RLEString("aaabbcaaa")
    assert rle.access(0) == 'a'
    assert rle.access(2) == 'a'
    assert rle.access(3) == 'b'
    assert rle.access(5) == 'c'
    assert rle.access(6) == 'a'
    assert rle.access(8) == 'a'


def test_rle_string_rank():
    rle = RLEString("aaabbcaaa")
    assert rle.rank('a', 0) == 0
    assert rle.rank('a', 3) == 3
    assert rle.rank('a', 5) == 3  # positions 0,1,2 are 'a'
    assert rle.rank('a', 9) == 6  # all 6 a's
    assert rle.rank('b', 5) == 2
    assert rle.rank('b', 3) == 0
    assert rle.rank('c', 6) == 1
    assert rle.rank('z', 9) == 0  # not in alphabet


def test_rle_string_len():
    rle = RLEString("aaabbcaaa")
    assert len(rle) == 9
    assert rle.n == 9
    assert rle.num_runs == 4
    assert rle.compression_ratio() == 9 / 4


def test_rle_string_from_runs():
    runs = [('a', 5), ('b', 3)]
    rle = RLEString(runs, from_runs=True)
    assert rle.decode() == "aaaaabbb"
    assert rle.n == 8


def test_rle_string_access_out_of_range():
    rle = RLEString("abc")
    with pytest.raises(IndexError):
        rle.access(3)
    with pytest.raises(IndexError):
        rle.access(-1)


def test_rle_empty():
    rle = RLEString("")
    assert rle.n == 0
    assert rle.num_runs == 0
    assert rle.decode() == ""