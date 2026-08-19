"""Tests for the FM-index and backward search pattern matching."""

import pytest
import random

from wavelet_tree.fm_index import (
    FMIndex,
    backward_search,
    compute_bwt,
    compute_c_array,
    _compute_suffix_array,
)


class TestSuffixArray:
    """Tests for suffix array computation."""

    def test_empty(self):
        assert _compute_suffix_array([]) == []

    def test_single(self):
        assert _compute_suffix_array(["a"]) == [0]

    def test_simple(self):
        sa = _compute_suffix_array(list("banana"))
        # Suffixes: banana, anana, nana, ana, na, a
        # Sorted: a(5), ana(3), anana(1), banana(0), na(4), nana(2)
        assert sa == [5, 3, 1, 0, 4, 2]

    def test_abracadabra(self):
        sa = _compute_suffix_array(list("abracadabra"))
        n = len("abracadabra")
        # Verify: suffixes at SA positions should be sorted
        text = list("abracadabra")
        suffixes = [text[sa[i]:] for i in range(n)]
        assert suffixes == sorted(suffixes)

    @pytest.mark.parametrize("seed", range(20))
    def test_random(self, seed):
        """Suffix array should produce sorted suffixes."""
        random.seed(seed)
        n = random.randint(1, 100)
        sigma = random.randint(1, 10)
        text = [chr(ord("a") + random.randint(0, sigma - 1)) for _ in range(n)]
        sa = _compute_suffix_array(text)
        suffixes = [text[sa[i]:] for i in range(n)]
        assert suffixes == sorted(suffixes), f"SA not sorted for seed={seed}"


class TestBWT:
    """Tests for Burrows-Wheeler Transform computation."""

    def test_empty(self):
        assert compute_bwt([]) == []

    def test_single(self):
        assert compute_bwt(["a"]) == ["a"]

    def test_banana(self):
        """BWT of 'banana' should be 'annb$aa' with a sentinel, but without
        sentinel it's the last column of sorted rotations."""
        bwt = compute_bwt(list("banana"))
        assert len(bwt) == 6
        # BWT[i] = text[(SA[i]-1) % n]
        sa = _compute_suffix_array(list("banana"))
        text = list("banana")
        expected = [text[(sa[i] - 1) % len(text)] for i in range(len(text))]
        assert bwt == expected

    @pytest.mark.parametrize("seed", range(20))
    def test_random(self, seed):
        """BWT should be invertible (same multiset as original)."""
        random.seed(seed)
        n = random.randint(1, 100)
        sigma = random.randint(1, 10)
        text = [chr(ord("a") + random.randint(0, sigma - 1)) for _ in range(n)]
        bwt = compute_bwt(text)
        # BWT is a permutation of the original text
        assert sorted(bwt) == sorted(text)


class TestCArray:
    """Tests for C array computation."""

    def test_empty(self):
        assert compute_c_array([]) == {}

    def test_simple(self):
        c = compute_c_array(list("abracadabra"))
        # Counts: a=5, b=2, c=1, d=1, r=2
        # C[a]=0, C[b]=5, C[c]=7, C[d]=8, C[r]=9
        assert c["a"] == 0
        assert c["b"] == 5
        assert c["c"] == 7
        assert c["d"] == 8
        assert c["r"] == 9

    def test_single_symbol(self):
        c = compute_c_array(list("aaaa"))
        assert c["a"] == 0


class TestBackwardSearch:
    """Tests for backward search on FM-index."""

    def test_empty_text(self):
        fm = FMIndex("")
        assert fm.count("a") == 0
        assert fm.locate("a") == []

    def test_empty_pattern(self):
        fm = FMIndex("abc")
        assert fm.count("") == 0
        assert fm.locate("") == []

    def test_single_char_text(self):
        fm = FMIndex("a")
        assert fm.count("a") == 1
        assert fm.locate("a") == [0]
        assert fm.count("b") == 0

    def test_abracadabra(self):
        fm = FMIndex("abracadabra")
        assert fm.count("abra") == 2
        assert fm.locate("abra") == [0, 7]
        assert fm.count("bra") == 2
        assert fm.locate("bra") == [1, 8]
        assert fm.count("a") == 5
        assert fm.count("cad") == 1
        assert fm.locate("cad") == [4]
        assert fm.count("xyz") == 0
        assert fm.locate("xyz") == []

    def test_mississippi(self):
        fm = FMIndex("mississippi")
        assert fm.count("issi") == 2
        assert fm.locate("issi") == [1, 4]
        assert fm.count("ss") == 2
        assert fm.locate("ss") == [2, 5]
        assert fm.count("i") == 4
        assert fm.count("p") == 2
        assert fm.count("mississippi") == 1
        assert fm.locate("mississippi") == [0]

    def test_repeated_pattern(self):
        text = "aaaaaaa"
        fm = FMIndex(text)
        assert fm.count("a") == 7
        assert fm.count("aa") == 6
        assert fm.count("aaa") == 5
        assert fm.locate("aaa") == [0, 1, 2, 3, 4]
        assert fm.count("aaaaaaa") == 1

    @pytest.mark.parametrize("seed", range(30))
    @pytest.mark.parametrize("structure", ["tree", "matrix", "huffman-tree", "huffman-matrix"])
    def test_random_patterns(self, seed, structure):
        """Random pattern matching should match brute force."""
        random.seed(seed)
        n = random.randint(1, 100)
        sigma = random.randint(1, 8)
        text = "".join(chr(ord("a") + random.randint(0, sigma - 1)) for _ in range(n))
        fm = FMIndex(text, structure=structure)

        # Test several patterns
        for _ in range(10):
            plen = random.randint(1, min(n, 10))
            start = random.randint(0, n - plen)
            pattern = text[start:start + plen]

            # Brute force count
            brute_count = sum(1 for i in range(n - plen + 1) if text[i:i + plen] == pattern)
            assert fm.count(pattern) == brute_count, (
                f"count mismatch: pattern='{pattern}', fm={fm.count(pattern)}, "
                f"brute={brute_count}, seed={seed}, structure={structure}"
            )

            # Brute force locate
            brute_locate = [i for i in range(n - plen + 1) if text[i:i + plen] == pattern]
            assert fm.locate(pattern) == brute_locate, (
                f"locate mismatch: pattern='{pattern}', "
                f"fm={fm.locate(pattern)}, brute={brute_locate}, "
                f"seed={seed}, structure={structure}"
            )

    def test_pattern_not_in_text(self):
        fm = FMIndex("abcde")
        assert fm.count("xyz") == 0
        assert fm.locate("xyz") == []

    def test_full_text_match(self):
        text = "abracadabra"
        fm = FMIndex(text)
        assert fm.count(text) == 1
        assert fm.locate(text) == [0]

    @pytest.mark.parametrize("structure", ["tree", "matrix", "huffman-tree", "huffman-matrix"])
    def test_all_structures_agree(self, structure):
        """All structures should give the same results."""
        text = "mississippi"
        fm = FMIndex(text, structure=structure)
        assert fm.count("iss") == 2
        assert fm.locate("iss") == [1, 4]

    def test_repr(self):
        fm = FMIndex("abracadabra")
        r = repr(fm)
        assert "FMIndex" in r
        assert "len=11" in r

    def test_len(self):
        fm = FMIndex("hello")
        assert len(fm) == 5

    def test_invalid_structure(self):
        with pytest.raises(ValueError):
            FMIndex("abc", structure="invalid")