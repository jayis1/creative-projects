"""Tests for the RRRBitVector implementation."""

import pytest
import random

from wavelet_tree.bitvector import BitVector
from wavelet_tree.rrr_bitvector import RRRBitVector


class TestRRRBitVector:
    """Comprehensive tests for the RRR-style compressed bitvector."""

    def test_empty(self):
        bv = RRRBitVector()
        assert len(bv) == 0
        assert bv.rank1(0) == 0
        assert bv.rank0(0) == 0
        assert bv.count1() == 0
        assert bv.count0() == 0
        assert bv.select1(0) == -1
        assert bv.select0(0) == -1

    def test_single_zero(self):
        bv = RRRBitVector([0])
        assert bv.rank1(1) == 0
        assert bv.rank0(1) == 1
        assert bv.select0(0) == 0
        assert bv.select1(0) == -1

    def test_single_one(self):
        bv = RRRBitVector([1])
        assert bv.rank1(1) == 1
        assert bv.rank0(1) == 0
        assert bv.select1(0) == 0
        assert bv.select0(0) == -1

    def test_all_zeros(self):
        bits = [0] * 100
        bv = RRRBitVector(bits)
        nbv = BitVector(bits)
        for i in range(101):
            assert bv.rank1(i) == nbv.rank1(i)
            assert bv.rank0(i) == nbv.rank0(i)
        assert bv.count1() == 0
        assert bv.count0() == 100

    def test_all_ones(self):
        bits = [1] * 100
        bv = RRRBitVector(bits)
        nbv = BitVector(bits)
        for i in range(101):
            assert bv.rank1(i) == nbv.rank1(i)
            assert bv.rank0(i) == nbv.rank0(i)
        assert bv.count1() == 100
        assert bv.count0() == 0

    @pytest.mark.parametrize("seed", range(50))
    def test_random_rank(self, seed):
        """rank1 and rank0 should match naive BitVector for random sequences."""
        random.seed(seed)
        n = random.randint(1, 500)
        bits = [random.randint(0, 1) for _ in range(n)]
        bv = RRRBitVector(bits)
        nbv = BitVector(bits)
        for i in range(n + 1):
            assert bv.rank1(i) == nbv.rank1(i), f"rank1({i}) mismatch seed={seed}"
            assert bv.rank0(i) == nbv.rank0(i), f"rank0({i}) mismatch seed={seed}"

    @pytest.mark.parametrize("seed", range(50))
    def test_random_select(self, seed):
        """select1 and select0 should match naive BitVector for random sequences."""
        random.seed(seed)
        n = random.randint(1, 500)
        bits = [random.randint(0, 1) for _ in range(n)]
        bv = RRRBitVector(bits)
        nbv = BitVector(bits)
        total_ones = sum(bits)
        total_zeros = n - total_ones
        for k in range(max(total_ones, total_zeros) + 2):
            assert bv.select1(k) == nbv.select1(k), f"select1({k}) mismatch seed={seed}"
            assert bv.select0(k) == nbv.select0(k), f"select0({k}) mismatch seed={seed}"

    @pytest.mark.parametrize("seed", range(20))
    def test_large_sequence(self, seed):
        """Test with larger sequences to exercise superblock structure."""
        random.seed(seed)
        n = random.randint(1000, 5000)
        bits = [random.randint(0, 1) for _ in range(n)]
        bv = RRRBitVector(bits)
        nbv = BitVector(bits)
        # Sample some positions
        for _ in range(100):
            i = random.randint(0, n)
            assert bv.rank1(i) == nbv.rank1(i)
            assert bv.rank0(i) == nbv.rank0(i)

    def test_invalid_bit(self):
        with pytest.raises(ValueError):
            RRRBitVector([0, 1, 2])

    def test_negative_rank(self):
        bv = RRRBitVector([1, 0, 1])
        with pytest.raises(ValueError):
            bv.rank1(-1)

    def test_negative_select(self):
        bv = RRRBitVector([1, 0, 1])
        with pytest.raises(ValueError):
            bv.select1(-1)

    def test_repr(self):
        bv = RRRBitVector([1, 0, 1, 1])
        r = repr(bv)
        assert "RRRBitVector" in r
        assert "len=4" in r

    def test_getitem(self):
        bv = RRRBitVector([1, 0, 1, 1, 0])
        assert bv[0] == 1
        assert bv[1] == 0
        assert bv[-1] == 0

    def test_iter(self):
        bv = RRRBitVector([1, 0, 1])
        assert list(bv) == [1, 0, 1]

    def test_to_list(self):
        bv = RRRBitVector([1, 0, 1, 1])
        assert bv.to_list() == [1, 0, 1, 1]