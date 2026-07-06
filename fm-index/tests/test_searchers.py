"""Tests for the searchers module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fmindex import FMIndex
from fmindex.searchers import (
    regex_search,
    find_all_repeats,
    top_k_frequent_kmers,
    find_minimal_unique_substrings,
    find_maximal_unique_matches,
)


def test_regex_search_dot():
    idx = FMIndex("mississippi")
    # .ss should match "iss" at positions 1 and 4
    matches = regex_search(idx, ".ss")
    positions = sorted(m.position for m in matches)
    assert positions == [1, 4]


def test_regex_search_literal():
    idx = FMIndex("banana")
    matches = regex_search(idx, "ana")
    assert sorted(m.position for m in matches) == [1, 3]


def test_regex_search_no_match():
    idx = FMIndex("banana")
    matches = regex_search(idx, "xyz")
    assert len(matches) == 0


def test_regex_search_star_unsupported():
    idx = FMIndex("banana")
    with pytest.raises(ValueError):
        regex_search(idx, "a*")


def test_find_all_repeats():
    idx = FMIndex("mississippi")
    repeats = find_all_repeats(idx, min_len=2)
    repeat_strs = [r[0] for r in repeats]
    assert "issi" in repeat_strs
    assert "ssi" in repeat_strs
    assert "si" in repeat_strs
    # all repeats should appear >= 2 times
    for sub, cnt in repeats:
        assert cnt >= 2


def test_find_all_repeats_min_len():
    idx = FMIndex("banana")
    repeats = find_all_repeats(idx, min_len=3)
    for sub, cnt in repeats:
        assert len(sub) >= 3
        assert cnt >= 2


def test_find_all_repeats_invalid():
    idx = FMIndex("banana")
    with pytest.raises(ValueError):
        find_all_repeats(idx, min_len=0)


def test_top_k_frequent_kmers():
    idx = FMIndex("mississippi")
    top = top_k_frequent_kmers(idx, 2, 5)
    assert len(top) <= 5
    # 'ss', 'is', 'si' each appear twice
    counts = dict(top)
    assert counts.get('ss') == 2
    assert counts.get('is') == 2
    assert counts.get('si') == 2


def test_top_k_sorted_by_count():
    idx = FMIndex("aaabbc")
    top = top_k_frequent_kmers(idx, 1, 10)
    # 'a' appears 3 times, should be first
    assert top[0] == ('a', 3)


def test_find_minimal_unique_substrings():
    idx = FMIndex("mississippi")
    mus = find_minimal_unique_substrings(idx, min_len=1, max_len=10)
    # position 0 starts with 'm' which is unique
    assert 0 in mus
    sub, length = mus[0]
    assert sub == 'm'
    assert idx.count(sub) == 1


def test_find_maximal_unique_matches():
    idx = FMIndex("mississippi")
    mums = find_maximal_unique_matches(idx, "miss", min_len=2)
    assert len(mums) >= 1
    # "miss" appears once in text at position 0
    text_pos, query_pos, sub = mums[0]
    assert text_pos == 0
    assert query_pos == 0


def test_find_maximal_unique_matches_no_match():
    idx = FMIndex("banana")
    mums = find_maximal_unique_matches(idx, "zzz", min_len=2)
    assert len(mums) == 0


def test_regex_search_single_char_dot():
    idx = FMIndex("banana")
    # .a.a should match "bana" at 0 and "nana" at 2
    matches = regex_search(idx, ".a.a")
    positions = sorted(m.position for m in matches)
    assert 0 in positions  # "bana"
    assert 2 in positions  # "nana"