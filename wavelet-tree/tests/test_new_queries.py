"""Tests for new range query functions: range_report, range_report_all,
range_top_k, range_bottom_k."""

import pytest
import random
from collections import Counter

from wavelet_tree import WaveletTree, WaveletMatrix
from wavelet_tree.queries import (
    range_report,
    range_report_all,
    range_top_k,
    range_bottom_k,
    interval_symbols,
)

SEQUENCES = [
    "abracadabra",
    "mississippi",
    "hello world",
    "abcdefg",
    "a",
    "aaaaaaaaaa",
]

for seed in range(10):
    random.seed(seed)
    length = random.randint(1, 100)
    sigma = random.randint(1, 15)
    seq = "".join(chr(ord("a") + random.randint(0, sigma - 1)) for _ in range(length))
    SEQUENCES.append(seq)


class TestRangeReport:
    """Tests for range_report."""

    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_matches_interval_symbols(self, seq):
        """range_report should match interval_symbols but as sorted list."""
        wt = WaveletTree(seq)
        for l in range(0, len(seq) + 1):
            for r in range(l, len(seq) + 1):
                expected = sorted(interval_symbols(wt, l, r).items())
                assert range_report(wt, l, r) == expected

    def test_empty_range(self):
        wt = WaveletTree("abc")
        assert range_report(wt, 0, 0) == []

    def test_full_range(self):
        wt = WaveletTree("aab")
        result = range_report(wt, 0, 3)
        assert result == [("a", 2), ("b", 1)]

    def test_sorted_by_symbol(self):
        wt = WaveletTree("dcba")
        result = range_report(wt, 0, 4)
        symbols = [s for s, _ in result]
        assert symbols == sorted(symbols)


class TestRangeReportAll:
    """Tests for range_report_all."""

    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_matches_sorted_subsequence(self, seq):
        """range_report_all should return all symbols in sorted order."""
        wt = WaveletTree(seq)
        for l in range(0, len(seq) + 1):
            for r in range(l, len(seq) + 1):
                expected = sorted(seq[l:r])
                assert range_report_all(wt, l, r) == expected

    def test_empty_range(self):
        wt = WaveletTree("abc")
        assert range_report_all(wt, 1, 1) == []

    def test_single_element(self):
        wt = WaveletTree("cba")
        assert range_report_all(wt, 1, 2) == ["b"]

    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_matrix_matches_tree(self, seq):
        """WaveletMatrix should give same results as WaveletTree."""
        wt = WaveletTree(seq)
        wm = WaveletMatrix(seq)
        for l in range(0, len(seq) + 1, 3):
            for r in range(l, len(seq) + 1, 3):
                assert range_report_all(wt, l, r) == range_report_all(wm, l, r)


class TestRangeTopK:
    """Tests for range_top_k."""

    def test_basic(self):
        wt = WaveletTree("aabbbcc")
        result = range_top_k(wt, 0, 7, 2)
        assert result == [("b", 3), ("a", 2)]

    def test_k_greater_than_alphabet(self):
        wt = WaveletTree("aabb")
        result = range_top_k(wt, 0, 4, 10)
        # Should return all symbols
        assert len(result) == 2

    def test_k_zero(self):
        wt = WaveletTree("aabb")
        assert range_top_k(wt, 0, 4, 0) == []

    def test_tie_breaking(self):
        """Ties in count should be broken by symbol order."""
        wt = WaveletTree("abab")
        result = range_top_k(wt, 0, 4, 2)
        # a and b both have count 2, so a comes first
        assert result == [("a", 2), ("b", 2)]

    def test_sorted_by_count_desc(self):
        wt = WaveletTree("aaabbccccd")
        result = range_top_k(wt, 0, 10, 4)
        counts = [c for _, c in result]
        assert counts == sorted(counts, reverse=True)

    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_correctness(self, seq):
        """range_top_k should match brute force."""
        wt = WaveletTree(seq)
        for l in range(0, len(seq), max(1, len(seq) // 5)):
            for r in range(l + 1, len(seq) + 1, max(1, len(seq) // 5)):
                counts = Counter(seq[l:r])
                expected = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
                for k in [1, 2, 3]:
                    result = range_top_k(wt, l, r, k)
                    assert result == expected[:k], f"top_k mismatch seq={seq} l={l} r={r} k={k}"


class TestRangeBottomK:
    """Tests for range_bottom_k."""

    def test_basic(self):
        wt = WaveletTree("aabbbcc")
        result = range_bottom_k(wt, 0, 7, 2)
        # c has 2, a has 2 — tie broken by symbol, so c before a
        # Wait: counts are a=2, b=3, c=2. Bottom by count asc: a(2), c(2), b(3)
        # Tie break by symbol: a before c
        assert result == [("a", 2), ("c", 2)]

    def test_k_zero(self):
        wt = WaveletTree("aabb")
        assert range_bottom_k(wt, 0, 4, 0) == []

    def test_k_greater_than_alphabet(self):
        wt = WaveletTree("aabb")
        result = range_bottom_k(wt, 0, 4, 10)
        assert len(result) == 2

    def test_sorted_by_count_asc(self):
        wt = WaveletTree("aaabbccccd")
        result = range_bottom_k(wt, 0, 10, 4)
        counts = [c for _, c in result]
        assert counts == sorted(counts)

    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_correctness(self, seq):
        """range_bottom_k should match brute force."""
        wt = WaveletTree(seq)
        for l in range(0, len(seq), max(1, len(seq) // 5)):
            for r in range(l + 1, len(seq) + 1, max(1, len(seq) // 5)):
                counts = Counter(seq[l:r])
                expected = sorted(counts.items(), key=lambda x: (x[1], x[0]))
                for k in [1, 2, 3]:
                    result = range_bottom_k(wt, l, r, k)
                    assert result == expected[:k], f"bottom_k mismatch seq={seq} l={l} r={r} k={k}"