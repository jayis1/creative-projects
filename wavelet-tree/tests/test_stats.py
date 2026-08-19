"""Tests for the statistics and benchmarking module."""

import pytest
import random

from wavelet_tree import WaveletTree, WaveletMatrix, HuffmanWaveletTree, HuffmanWaveletMatrix
from wavelet_tree.stats import (
    space_stats,
    tree_stats,
    benchmark,
    benchmark_report,
    SpaceStats,
    TreeStats,
    BenchmarkResult,
)


SEQUENCES = [
    "abracadabra",
    "mississippi",
    "hello world",
    "abcdefg",
    "a",
    "aaaaaaaaaa",
]

ALL_STRUCTURES = [WaveletTree, WaveletMatrix, HuffmanWaveletTree, HuffmanWaveletMatrix]


class TestSpaceStats:
    """Tests for space statistics."""

    @pytest.mark.parametrize("cls", ALL_STRUCTURES)
    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_space_stats_basic(self, cls, seq):
        """space_stats should return valid metrics."""
        wt = cls(seq)
        ss = space_stats(wt)
        assert isinstance(ss, SpaceStats)
        assert ss.sequence_length == len(seq)
        assert ss.alphabet_size == len(set(seq))
        assert ss.total_bits >= 0
        assert ss.total_bytes >= 0
        assert ss.bits_per_symbol >= 0
        assert ss.h0 >= 0

    def test_empty_sequence(self):
        wt = WaveletTree("")
        ss = space_stats(wt)
        assert ss.sequence_length == 0
        assert ss.alphabet_size == 0
        assert ss.h0 == 0.0

    def test_single_symbol(self):
        wt = WaveletTree("aaaa")
        ss = space_stats(wt)
        assert ss.h0 == 0.0  # zero entropy for single symbol
        assert ss.sequence_length == 4
        assert ss.alphabet_size == 1

    def test_uniform_distribution(self):
        """Uniform distribution should have max entropy."""
        wt = WaveletTree("abcdef")
        ss = space_stats(wt)
        # log2(6) ≈ 2.585
        assert abs(ss.h0 - 2.585) < 0.01


class TestTreeStats:
    """Tests for structural statistics."""

    @pytest.mark.parametrize("cls", ALL_STRUCTURES)
    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_tree_stats_basic(self, cls, seq):
        """tree_stats should return valid metrics."""
        wt = cls(seq)
        ts = tree_stats(wt)
        assert isinstance(ts, TreeStats)
        assert ts.structure_type == type(wt).__name__
        assert ts.sequence_length == len(seq)
        assert ts.alphabet_size == len(set(seq))
        assert ts.num_levels >= 0
        assert ts.num_bitvectors >= 0
        assert ts.total_bitvector_length >= 0

    def test_empty(self):
        wt = WaveletTree("")
        ts = tree_stats(wt)
        assert ts.sequence_length == 0
        assert ts.num_levels == 0

    def test_single_symbol(self):
        wt = WaveletTree("aaa")
        ts = tree_stats(wt)
        assert ts.alphabet_size == 1
        # Single symbol = no bitvectors needed
        assert ts.num_bitvectors == 0 or ts.total_bitvector_length == 0

    def test_tree_has_depth(self):
        """Tree-based structures should report max_tree_depth."""
        wt = WaveletTree("abracadabra")
        ts = tree_stats(wt)
        assert ts.max_tree_depth > 0
        assert ts.num_internal_nodes > 0
        assert ts.num_leaves > 0

    def test_matrix_has_levels(self):
        """Matrix-based structures should report num_levels."""
        wt = WaveletMatrix("abracadabra")
        ts = tree_stats(wt)
        assert ts.num_levels > 0
        assert ts.num_bitvectors == ts.num_levels


class TestBenchmark:
    """Tests for the benchmarking functionality."""

    def test_benchmark_returns_results(self):
        results = benchmark("abracadabra", num_rank_queries=10, num_access_queries=10, num_select_queries=10)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, BenchmarkResult)
            assert r.structure
            assert r.operation in ("access", "rank", "select")
            assert r.build_time >= 0
            assert r.num_queries == 10
            assert r.avg_query_time_us >= 0

    def test_benchmark_all_structures(self):
        results = benchmark("mississippi", num_rank_queries=5, num_access_queries=5, num_select_queries=5)
        structures = {r.structure for r in results}
        assert "WaveletTree" in structures
        assert "WaveletMatrix" in structures
        assert "HuffmanWaveletTree" in structures
        assert "HuffmanWaveletMatrix" in structures

    def test_benchmark_specific_structures(self):
        results = benchmark("hello", structures=["tree", "matrix"],
                           num_rank_queries=5, num_access_queries=5, num_select_queries=5)
        structures = {r.structure for r in results}
        assert structures == {"WaveletTree", "WaveletMatrix"}

    def test_benchmark_report(self):
        results = benchmark("abc", num_rank_queries=5, num_access_queries=5, num_select_queries=5)
        report = benchmark_report(results)
        assert isinstance(report, str)
        assert "Benchmark" in report
        assert "Structure" in report

    def test_benchmark_empty_sequence(self):
        """Benchmarking an empty sequence should not crash."""
        results = benchmark("", num_rank_queries=5, num_access_queries=5, num_select_queries=5)
        # No queries to run on empty sequence
        assert isinstance(results, list)