"""Tests for compression analysis utilities."""

import pytest
from compression_engine.analysis import (
    shannon_entropy,
    frequency_distribution,
    optimal_compression_ratio,
    compressibility_score,
    byte_histogram,
    unique_byte_count,
    redundancy,
    analyze,
)


class TestEntropy:
    def test_empty_data(self):
        assert shannon_entropy(b"") == 0.0

    def test_single_byte(self):
        # All same byte = 0 entropy
        assert shannon_entropy(b"a") == 0.0

    def test_constant_data(self):
        assert shannon_entropy(b"aaaaaa") == 0.0

    def test_two_equal_symbols(self):
        # 50/50 distribution = 1 bit of entropy
        assert abs(shannon_entropy(b"ab") - 1.0) < 1e-10

    def test_uniform_distribution(self):
        # All 256 byte values equally likely ≈ 8 bits
        data = bytes(range(256))
        entropy = shannon_entropy(data)
        assert abs(entropy - 8.0) < 1e-10


class TestAnalysis:
    def test_frequency_distribution(self):
        data = b"aabb"
        dist = frequency_distribution(data)
        assert abs(dist[ord('a')] - 0.5) < 1e-10
        assert abs(dist[ord('b')] - 0.5) < 1e-10

    def test_optimal_ratio(self):
        # Constant data: optimal ratio is 0
        assert optimal_compression_ratio(b"aaaa") == 0.0

    def test_compressibility_score(self):
        # Constant data: score is 1.0
        assert compressibility_score(b"aaaa") == 1.0

    def test_byte_histogram(self):
        data = b"aab"
        hist = byte_histogram(data)
        assert hist[ord('a')] == 2
        assert hist[ord('b')] == 1

    def test_unique_byte_count(self):
        assert unique_byte_count(b"") == 0
        assert unique_byte_count(b"a") == 1
        assert unique_byte_count(b"abc") == 3
        assert unique_byte_count(b"aaa") == 1

    def test_redundancy(self):
        # Constant data: redundancy = 1.0
        assert redundancy(b"aaaa") == 1.0

    def test_analyze(self):
        result = analyze(b"hello world")
        assert "entropy_bits" in result
        assert "optimal_ratio" in result
        assert "compressibility" in result
        assert "redundancy" in result
        assert "size_bytes" in result
        assert "unique_bytes" in result