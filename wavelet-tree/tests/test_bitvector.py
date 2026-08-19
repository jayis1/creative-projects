"""Tests for the BitVector and BlockedBitVector implementations."""

import pytest
import random

from wavelet_tree.bitvector import BitVector, BlockedBitVector


class TestBitVector:
    """Tests for the naive BitVector."""

    def test_empty(self):
        bv = BitVector()
        assert len(bv) == 0
        assert bv.rank1(0) == 0
        assert bv.rank0(0) == 0
        assert bv.count1() == 0
        assert bv.count0() == 0
        assert bv.select1(0) == -1
        assert bv.select0(0) == -1

    def test_all_zeros(self):
        bv = BitVector([0, 0, 0, 0, 0])
        assert bv.rank1(5) == 0
        assert bv.rank0(5) == 5
        assert bv.count1() == 0
        assert bv.count0() == 5
        assert bv.select1(0) == -1
        assert bv.select0(0) == 0
        assert bv.select0(4) == 4

    def test_all_ones(self):
        bv = BitVector([1, 1, 1, 1, 1])
        assert bv.rank1(5) == 5
        assert bv.rank0(5) == 0
        assert bv.count1() == 5
        assert bv.select1(0) == 0
        assert bv.select1(4) == 4
        assert bv.select0(0) == -1

    def test_mixed(self):
        bv = BitVector([1, 0, 1, 1, 0, 0, 1, 0, 1, 1])
        assert bv.rank1(0) == 0
        assert bv.rank1(1) == 1
        assert bv.rank1(3) == 2
        assert bv.rank1(5) == 3
        assert bv.rank1(10) == 6
        assert bv.rank0(10) == 4
        assert bv.select1(0) == 0
        assert bv.select1(1) == 2
        assert bv.select1(5) == 9
        assert bv.select0(0) == 1
        assert bv.select0(3) == 7

    def test_indexing(self):
        bv = BitVector([1, 0, 1])
        assert bv[0] == 1
        assert bv[1] == 0
        assert bv[2] == 1
        assert bv[-1] == 1
        with pytest.raises(IndexError):
            _ = bv[3]
        with pytest.raises(IndexError):
            _ = bv[-4]

    def test_invalid_bit(self):
        with pytest.raises(ValueError):
            BitVector([0, 1, 2])
        bv = BitVector([0, 1])
        with pytest.raises(ValueError):
            bv.append(2)

    def test_negative_rank(self):
        bv = BitVector([1, 0, 1])
        with pytest.raises(ValueError):
            bv.rank1(-1)
        with pytest.raises(ValueError):
            bv.rank0(-1)

    def test_negative_select(self):
        bv = BitVector([1, 0, 1])
        with pytest.raises(ValueError):
            bv.select1(-1)
        with pytest.raises(ValueError):
            bv.select0(-1)

    def test_rank_overflow(self):
        """rank(i) with i > n should clamp to n."""
        bv = BitVector([1, 0, 1])
        assert bv.rank1(100) == 2
        assert bv.rank0(100) == 1

    def test_append(self):
        bv = BitVector()
        bv.append(1)
        bv.append(0)
        bv.append(1)
        assert len(bv) == 3
        assert bv.rank1(3) == 2

    def test_to_list(self):
        bits = [1, 0, 1, 1, 0]
        bv = BitVector(bits)
        assert bv.to_list() == bits


class TestBlockedBitVector:
    """Tests for the BlockedBitVector — must match BitVector exactly."""

    @pytest.mark.parametrize("n", [0, 1, 2, 5, 10, 25, 50, 100, 200, 500])
    def test_random_rank1(self, n):
        """BlockedBitVector.rank1 must match BitVector.rank1 for all i."""
        random.seed(n)
        bits = [random.randint(0, 1) for _ in range(n)]
        bv = BitVector(bits)
        bbv = BlockedBitVector(bits)
        for i in range(n + 1):
            assert bbv.rank1(i) == bv.rank1(i), f"rank1 mismatch at i={i}, n={n}"

    @pytest.mark.parametrize("n", [0, 1, 2, 5, 10, 25, 50, 100, 200, 500])
    def test_random_rank0(self, n):
        """BlockedBitVector.rank0 must match BitVector.rank0 for all i."""
        random.seed(n + 1000)
        bits = [random.randint(0, 1) for _ in range(n)]
        bv = BitVector(bits)
        bbv = BlockedBitVector(bits)
        for i in range(n + 1):
            assert bbv.rank0(i) == bv.rank0(i), f"rank0 mismatch at i={i}, n={n}"

    @pytest.mark.parametrize("n", [1, 5, 10, 25, 50, 100, 200, 500])
    def test_random_select1(self, n):
        """BlockedBitVector.select1 must match BitVector.select1 for all k."""
        random.seed(n + 2000)
        bits = [random.randint(0, 1) for _ in range(n)]
        bv = BitVector(bits)
        bbv = BlockedBitVector(bits)
        total_ones = bv.count1()
        for k in range(total_ones):
            assert bbv.select1(k) == bv.select1(k), f"select1 mismatch at k={k}, n={n}"
        # Test out-of-range select
        assert bbv.select1(total_ones) == -1

    @pytest.mark.parametrize("n", [1, 5, 10, 25, 50, 100, 200, 500])
    def test_random_select0(self, n):
        """BlockedBitVector.select0 must match BitVector.select0 for all k."""
        random.seed(n + 3000)
        bits = [random.randint(0, 1) for _ in range(n)]
        bv = BitVector(bits)
        bbv = BlockedBitVector(bits)
        total_zeros = bv.count0()
        for k in range(total_zeros):
            assert bbv.select0(k) == bv.select0(k), f"select0 mismatch at k={k}, n={n}"

    def test_empty(self):
        bbv = BlockedBitVector()
        assert len(bbv) == 0
        assert bbv.rank1(0) == 0
        assert bbv.select1(0) == -1

    def test_single_bit(self):
        bbv = BlockedBitVector([1])
        assert bbv.rank1(1) == 1
        assert bbv.rank0(1) == 0
        assert bbv.select1(0) == 0

    def test_count_methods(self):
        bits = [1, 0, 1, 1, 0, 0, 1]
        bv = BitVector(bits)
        bbv = BlockedBitVector(bits)
        assert bbv.count1() == bv.count1()
        assert bbv.count0() == bv.count0()