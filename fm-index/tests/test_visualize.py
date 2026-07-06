"""Tests for the visualize module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fmindex import FMIndex
from fmindex.visualize import (
    visualize_bwt_matrix,
    visualize_suffix_array,
    visualize_lcp_skyline,
    visualize_matches,
    visualize_coverage,
    visualize_alphabet_distribution,
)


def test_visualize_bwt_matrix():
    idx = FMIndex("banana")
    result = visualize_bwt_matrix(idx, max_rows=5)
    assert "SA" in result
    assert "BWT" in result
    assert "banana" in result or "banana$" in result


def test_visualize_suffix_array():
    idx = FMIndex("banana")
    result = visualize_suffix_array(idx, max_entries=5)
    assert "SA[i]" in result
    assert "suffix" in result


def test_visualize_lcp_skyline():
    idx = FMIndex("mississippi")
    result = visualize_lcp_skyline(idx, width=30)
    assert "max LCP" in result


def test_visualize_lcp_skyline_no_repeats():
    idx = FMIndex("abc")
    result = visualize_lcp_skyline(idx)
    assert "0" in result  # no repeats


def test_visualize_matches():
    idx = FMIndex("mississippi")
    result = visualize_matches(idx, "iss", context=3)
    assert "iss" in result
    assert "Matches" in result
    assert "^" in result


def test_visualize_matches_no_matches():
    idx = FMIndex("banana")
    result = visualize_matches(idx, "xyz")
    assert "No matches" in result


def test_visualize_coverage():
    idx = FMIndex("mississippi")
    result = visualize_coverage(idx, "ss", width=30)
    assert "Coverage" in result
    assert "Covered:" in result


def test_visualize_alphabet_distribution():
    idx = FMIndex("mississippi")
    result = visualize_alphabet_distribution(idx, width=20)
    assert "│" in result
    assert "i" in result
    assert "s" in result