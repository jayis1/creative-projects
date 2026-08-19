"""Tests for Huffman-shaped wavelet trees and matrices."""

import pytest
import random

from wavelet_tree import HuffmanWaveletTree, HuffmanWaveletMatrix, build_huffman_code


SEQUENCES = [
    "abracadabra",
    "mississippi",
    "hello world",
    "the quick brown fox jumps over the lazy dog",
    "aaaaaaaaaa",
    "ab",
    "a",
    "abcdefg",
    "",
]

for seed in range(20):
    random.seed(seed)
    length = random.randint(1, 200)
    sigma = random.randint(1, 26)
    seq = "".join(chr(ord("a") + random.randint(0, sigma - 1)) for _ in range(length))
    SEQUENCES.append(seq)


class TestBuildHuffmanCode:
    def test_empty(self):
        assert build_huffman_code({}) == {}

    def test_single_symbol(self):
        codes = build_huffman_code({"a": 10})
        assert codes == {"a": "0"}

    def test_two_symbols(self):
        codes = build_huffman_code({"a": 1, "b": 1})
        assert len(codes) == 2
        assert all(len(c) == 1 for c in codes.values())

    def test_optimal_lengths(self):
        """More frequent symbols should have shorter codes."""
        codes = build_huffman_code({"a": 100, "b": 1, "c": 1, "d": 1})
        assert len(codes["a"]) <= len(codes["b"])
        assert len(codes["a"]) <= len(codes["c"])
        assert len(codes["a"]) <= len(codes["d"])

    def test_prefix_free(self):
        """No code should be a prefix of another."""
        codes = build_huffman_code({"a": 5, "b": 3, "c": 2, "d": 1, "e": 1})
        code_list = list(codes.values())
        for i, c1 in enumerate(code_list):
            for c2 in code_list[i + 1:]:
                assert not c1.startswith(c2), f"'{c1}' starts with '{c2}'"
                assert not c2.startswith(c1), f"'{c2}' starts with '{c1}'"


class TestHuffmanWaveletTree:

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_access(self, seq, use_blocked):
        if not seq:
            return
        hwt = HuffmanWaveletTree(seq, use_blocked=use_blocked)
        for i in range(len(seq)):
            assert hwt.access(i) == seq[i], f"access({i}) mismatch in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_rank(self, seq, use_blocked):
        if not seq:
            return
        hwt = HuffmanWaveletTree(seq, use_blocked=use_blocked)
        for c in set(seq):
            expected = seq.count(c)
            assert hwt.rank(c, len(seq)) == expected, f"rank('{c}', {len(seq)}) in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_select(self, seq, use_blocked):
        if not seq:
            return
        hwt = HuffmanWaveletTree(seq, use_blocked=use_blocked)
        for c in set(seq):
            positions = [i for i, ch in enumerate(seq) if ch == c]
            for k, expected_pos in enumerate(positions):
                assert hwt.select(c, k) == expected_pos, f"select('{c}', {k}) in '{seq}'"
            assert hwt.select(c, len(positions)) == -1

    def test_single_symbol(self):
        hwt = HuffmanWaveletTree("aaaaa")
        assert hwt.access(0) == "a"
        assert hwt.rank("a", 5) == 5
        assert hwt.select("a", 0) == 0
        assert hwt.select("a", 4) == 4


class TestHuffmanWaveletMatrix:

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_access(self, seq, use_blocked):
        if not seq:
            return
        hwm = HuffmanWaveletMatrix(seq, use_blocked=use_blocked)
        for i in range(len(seq)):
            assert hwm.access(i) == seq[i], f"access({i}) mismatch in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_rank(self, seq, use_blocked):
        if not seq:
            return
        hwm = HuffmanWaveletMatrix(seq, use_blocked=use_blocked)
        for c in set(seq):
            expected = seq.count(c)
            assert hwm.rank(c, len(seq)) == expected, f"rank('{c}', {len(seq)}) in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_select(self, seq, use_blocked):
        if not seq:
            return
        hwm = HuffmanWaveletMatrix(seq, use_blocked=use_blocked)
        for c in set(seq):
            positions = [i for i, ch in enumerate(seq) if ch == c]
            for k, expected_pos in enumerate(positions):
                assert hwm.select(c, k) == expected_pos, f"select('{c}', {k}) in '{seq}'"
            assert hwm.select(c, len(positions)) == -1

    def test_single_symbol(self):
        hwm = HuffmanWaveletMatrix("aaaaa")
        assert hwm.access(0) == "a"
        assert hwm.rank("a", 5) == 5
        assert hwm.select("a", 0) == 0
        assert hwm.select("a", 4) == 4

    def test_select_out_of_range(self):
        """select should return -1 when k >= count."""
        hwm = HuffmanWaveletMatrix("abracadabra")
        assert hwm.select("a", 5) == -1  # only 5 a's (0-indexed 0-4)
        assert hwm.select("r", 2) == -1  # only 2 r's (0-indexed 0-1)
        assert hwm.select("z", 0) == -1  # z not in alphabet