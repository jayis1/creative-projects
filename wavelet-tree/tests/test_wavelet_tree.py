"""Tests for WaveletTree and WaveletMatrix."""

import pytest
import random

from wavelet_tree import WaveletTree, WaveletMatrix


# ---- Test sequences ----

SEQUENCES = [
    "abracadabra",
    "mississippi",
    "hello world",
    "the quick brown fox jumps over the lazy dog",
    "aaaaaaaaaa",  # single symbol
    "ab",  # minimal
    "a",  # single char
    "abcdefg",  # all distinct
    "",  # empty
]

# Add random sequences
for seed in range(20):
    random.seed(seed)
    length = random.randint(1, 200)
    sigma = random.randint(1, 26)
    seq = "".join(chr(ord("a") + random.randint(0, sigma - 1)) for _ in range(length))
    SEQUENCES.append(seq)


# ---- WaveletTree tests ----

class TestWaveletTree:
    """Comprehensive tests for the balanced WaveletTree."""

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_access(self, seq, use_blocked):
        """access(i) must return the correct symbol for all i."""
        if not seq:
            return
        wt = WaveletTree(seq, use_blocked=use_blocked)
        for i in range(len(seq)):
            assert wt.access(i) == seq[i], f"access({i}) mismatch in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_rank(self, seq, use_blocked):
        """rank(c, n) must equal the count of c in the sequence."""
        if not seq:
            return
        wt = WaveletTree(seq, use_blocked=use_blocked)
        for c in set(seq):
            expected = seq.count(c)
            assert wt.rank(c, len(seq)) == expected, f"rank('{c}', {len(seq)}) in '{seq}'"
        # Test rank for non-existent symbol
        assert wt.rank("z" if "z" not in seq else "!", len(seq)) == 0

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_rank_prefix(self, seq, use_blocked):
        """rank(c, i) must equal count of c in S[0..i) for all i."""
        if not seq:
            return
        wt = WaveletTree(seq, use_blocked=use_blocked)
        for c in set(seq):
            for i in range(len(seq) + 1):
                expected = seq[:i].count(c)
                assert wt.rank(c, i) == expected, f"rank('{c}', {i}) in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_select(self, seq, use_blocked):
        """select(c, k) must return the position of the k-th occurrence."""
        if not seq:
            return
        wt = WaveletTree(seq, use_blocked=use_blocked)
        for c in set(seq):
            positions = [i for i, ch in enumerate(seq) if ch == c]
            for k, expected_pos in enumerate(positions):
                assert wt.select(c, k) == expected_pos, f"select('{c}', {k}) in '{seq}'"
            # select beyond range returns -1
            assert wt.select(c, len(positions)) == -1

    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_blocked_vs_naive(self, seq):
        """Blocked and naive BitVector must give identical results."""
        if not seq:
            return
        wt_blocked = WaveletTree(seq, use_blocked=True)
        wt_naive = WaveletTree(seq, use_blocked=False)
        for i in range(len(seq)):
            assert wt_blocked.access(i) == wt_naive.access(i)
        for c in set(seq):
            assert wt_blocked.rank(c, len(seq)) == wt_naive.rank(c, len(seq))
            positions = [i for i, ch in enumerate(seq) if ch == c]
            for k in range(len(positions)):
                assert wt_blocked.select(c, k) == wt_naive.select(c, k)

    def test_empty(self):
        wt = WaveletTree("")
        assert len(wt) == 0
        assert wt.alphabet == []
        assert wt.rank("a", 0) == 0
        assert wt.select("a", 0) == -1

    def test_single_symbol(self):
        wt = WaveletTree("aaaaa")
        assert wt.access(0) == "a"
        assert wt.rank("a", 5) == 5
        assert wt.select("a", 0) == 0
        assert wt.select("a", 4) == 4
        assert wt.select("a", 5) == -1

    def test_access_out_of_range(self):
        wt = WaveletTree("abc")
        with pytest.raises(IndexError):
            wt.access(3)
        with pytest.raises(IndexError):
            wt.access(-1)

    def test_rank_negative(self):
        wt = WaveletTree("abc")
        with pytest.raises(ValueError):
            wt.rank("a", -1)

    def test_select_negative(self):
        wt = WaveletTree("abc")
        with pytest.raises(ValueError):
            wt.select("a", -1)

    def test_alphabet(self):
        wt = WaveletTree("dcba")
        assert wt.alphabet == ["a", "b", "c", "d"]


# ---- WaveletMatrix tests ----

class TestWaveletMatrix:
    """Comprehensive tests for the WaveletMatrix."""

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_access(self, seq, use_blocked):
        if not seq:
            return
        wm = WaveletMatrix(seq, use_blocked=use_blocked)
        for i in range(len(seq)):
            assert wm.access(i) == seq[i], f"access({i}) mismatch in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_rank(self, seq, use_blocked):
        if not seq:
            return
        wm = WaveletMatrix(seq, use_blocked=use_blocked)
        for c in set(seq):
            expected = seq.count(c)
            assert wm.rank(c, len(seq)) == expected, f"rank('{c}', {len(seq)}) in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_rank_prefix(self, seq, use_blocked):
        if not seq:
            return
        wm = WaveletMatrix(seq, use_blocked=use_blocked)
        for c in set(seq):
            for i in range(len(seq) + 1):
                expected = seq[:i].count(c)
                assert wm.rank(c, i) == expected, f"rank('{c}', {i}) in '{seq}'"

    @pytest.mark.parametrize("seq", SEQUENCES)
    @pytest.mark.parametrize("use_blocked", [True, False])
    def test_select(self, seq, use_blocked):
        if not seq:
            return
        wm = WaveletMatrix(seq, use_blocked=use_blocked)
        for c in set(seq):
            positions = [i for i, ch in enumerate(seq) if ch == c]
            for k, expected_pos in enumerate(positions):
                assert wm.select(c, k) == expected_pos, f"select('{c}', {k}) in '{seq}'"
            assert wm.select(c, len(positions)) == -1

    def test_empty(self):
        wm = WaveletMatrix("")
        assert len(wm) == 0
        assert wm.rank("a", 0) == 0

    def test_single_symbol(self):
        wm = WaveletMatrix("aaaaa")
        assert wm.access(0) == "a"
        assert wm.rank("a", 5) == 5
        assert wm.select("a", 0) == 0
        assert wm.select("a", 4) == 4


# ---- Cross-structure consistency ----

class TestCrossStructure:
    """Verify all structures agree on all operations."""

    @pytest.mark.parametrize("seq", SEQUENCES)
    def test_tree_vs_matrix(self, seq):
        if not seq:
            return
        wt = WaveletTree(seq)
        wm = WaveletMatrix(seq)
        for i in range(len(seq)):
            assert wt.access(i) == wm.access(i)
        for c in set(seq):
            assert wt.rank(c, len(seq)) == wm.rank(c, len(seq))
            positions = [i for i, ch in enumerate(seq) if ch == c]
            for k in range(len(positions)):
                assert wt.select(c, k) == wm.select(c, k)