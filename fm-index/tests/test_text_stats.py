"""Tests for the text_stats module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fmindex import FMIndex
from fmindex.text_stats import compute_statistics, TextStatistics


def test_compute_statistics_basic():
    idx = FMIndex("mississippi")
    stats = compute_statistics(idx)
    assert stats.text_length == 11
    assert stats.alphabet_size == 5
    assert stats.shannon_entropy > 0
    assert stats.max_entropy > 0
    assert 0 <= stats.redundancy <= 1


def test_compute_statistics_entropy_uniform():
    # "abcd" — uniform distribution, entropy = log2(4) = 2.0
    idx = FMIndex("abcd")
    stats = compute_statistics(idx)
    assert abs(stats.shannon_entropy - 2.0) < 0.01
    assert abs(stats.redundancy - 0.0) < 0.01


def test_compute_statistics_entropy_single_char():
    idx = FMIndex("aaaa")
    stats = compute_statistics(idx)
    assert stats.shannon_entropy == 0.0  # zero entropy for single symbol


def test_compute_statistics_gini():
    idx = FMIndex("aaaaaa")
    stats = compute_statistics(idx)
    # single symbol → Gini = 0
    assert stats.gini_coefficient == 0.0


def test_compute_statistics_bwt_runs():
    idx = FMIndex("mississippi")
    stats = compute_statistics(idx)
    assert stats.bwt_num_runs > 0
    assert stats.bwt_average_run_length > 0


def test_compute_statistics_most_frequent():
    idx = FMIndex("aaabbc")
    stats = compute_statistics(idx)
    assert stats.most_frequent[0] == ('a', 3)


def test_summary_string():
    idx = FMIndex("banana")
    stats = compute_statistics(idx)
    s = stats.summary()
    assert "Text length" in s
    assert "Shannon entropy" in s