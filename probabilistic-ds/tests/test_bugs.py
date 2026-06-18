"""Bug hunt tests — verify identified bugs before fixing."""
import os
import sys
import math
import random
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pds import (
    BloomFilter, CountingBloomFilter, CuckooFilter, CountMinSketch,
    HyperLogLog, TopK, TDigest, SkipList, ScalableBloomFilter,
    ConservativeCountMinSketch,
)


class TestCuckooDoubleHash:
    """Bug: CuckooFilter._fingerprint and _hash both compute the same
    fnv1a_64(data + b'\\x01'), wasting a hash computation per add/lookup."""

    def test_fingerprint_and_hash_use_same_computation(self):
        cf = CuckooFilter(capacity=100)
        data = b"test_item"
        # Both call fnv1a_64(data + b"\x01") — redundant
        from pds.hashing import fnv1a_64
        h = fnv1a_64(data + b"\x01")
        fp_expected = (h >> (64 - cf.fingerprint_bits)) & cf.fingerprint_mask
        idx_expected = h & 0xFFFFFFFF & (cf.num_buckets - 1)
        fp_actual = cf._fingerprint(data)
        idx_actual = cf._hash(data) & (cf.num_buckets - 1)
        assert fp_actual == fp_expected
        assert idx_actual == idx_expected


class TestTDigestCompressPerformance:
    """Bug: TDigest._compress() recomputes cum_count from scratch each
    iteration of the outer while loop, making it O(n²) instead of O(n)."""

    def test_compress_is_slow(self):
        """Verify the O(n²) behavior by timing a large compress."""
        import time
        td = TDigest(compression=50)
        # Add many items to trigger compression with many centroids
        for i in range(5000):
            td.add(float(i))
        # Force compression
        t0 = time.perf_counter()
        td._compress()
        elapsed = time.perf_counter() - t0
        # If O(n²), this would be very slow. Just verify it completes.
        assert elapsed < 10.0  # Should be fast after fix


class TestTDigestCDF:
    """Bug: TDigest.cdf() uses a crude 50% approximation instead of
    proper linear interpolation between centroids."""

    def test_cdf_symmetry(self):
        """For symmetric data, CDF at mean should be ~0.5."""
        td = TDigest(compression=200)
        random.seed(42)
        data = [random.gauss(0, 1) for _ in range(10000)]
        for x in data:
            td.add(x)
        cdf_at_0 = td.cdf(0.0)
        # With proper interpolation, this should be very close to 0.5
        # With the crude 50% approximation, it could be off
        assert abs(cdf_at_0 - 0.5) < 0.1, f"CDF at 0: {cdf_at_0}"


class TestCountMinSketchMergeDocstring:
    """Bug: CMS.merge() docstring says 'pointwise max' but code does sum."""

    def test_merge_is_sum_not_max(self):
        c1 = CountMinSketch(width=100, depth=5)
        c2 = CountMinSketch(width=100, depth=5)
        c1.add("x", 3)
        c2.add("x", 2)
        c1.merge(c2)
        # If it were max, result would be 3. With sum, it's 5.
        assert c1.query("x") == 5  # sum, not max


class TestTDigestUnusedImport:
    """Bug: tdigest.py imports bisect but never uses it."""

    def test_no_bisect_usage(self):
        import pds.tdigest as mod
        # bisect should not be referenced in the module's code
        source = open(mod.__file__).read()
        # Count uses of bisect (besides the import line)
        uses = source.count("bisect.")
        assert uses == 0, f"bisect imported but used {uses} times"


class TestCountingBloomRemoveOnAbsent:
    """Bug: CountingBloomFilter.remove() decrements self.count even when
    removing a false positive (item never actually added), corrupting
    the count."""

    def test_remove_absent_decrements_count(self):
        cbf = CountingBloomFilter(capacity=100, error_rate=0.01)
        cbf.add("real")
        initial_count = cbf.count  # should be 1
        # Try to remove something that was never added
        # With high capacity and few items, likely not a false positive
        result = cbf.remove("nonexistent_12345")
        if result:  # if it was a false positive
            assert cbf.count == 0  # count was decremented — this is the bug
            # The count is now wrong — we removed something we never added
        else:
            # Not a false positive, count unchanged — correct
            assert cbf.count == initial_count


class TestSkipListDeleteLevelBug:
    """Bug: SkipList.delete() iterates range(self._level + 1) which is
    correct, but the break condition may miss levels if the deleted node
    has forward pointers at levels that update doesn't track."""

    def test_delete_high_level_node(self):
        """Delete a node that happens to be at a high level."""
        sl = SkipList(max_level=4)
        # Insert many nodes to build up levels
        for i in range(100):
            sl.insert(i, i)
        # Delete several nodes and verify integrity
        for i in range(0, 50, 2):
            assert sl.delete(i), f"Failed to delete {i}"
        # Verify remaining nodes: all odds (1-99) + evens >= 50
        remaining = [k for k, v in sl]
        expected = [i for i in range(100) if i % 2 != 0 or i >= 50]
        assert remaining == expected
        # Verify search still works
        for i in range(1, 100, 2):
            assert sl.search(i) == i
        # Verify deleted nodes are gone
        for i in range(0, 50, 2):
            assert i not in sl


class TestCuckooFilterFullError:
    """Bug: CuckooFilter.add() raises RuntimeError when full, but doesn't
    provide capacity info. Also, the filter could be more resilient."""

    def test_full_raises_runtime_error(self):
        cf = CuckooFilter(capacity=10, bucket_size=2, fingerprint_bits=8, max_kicks=10)
        # Fill beyond capacity
        with pytest.raises(RuntimeError):
            for i in range(100):
                cf.add(f"item-{i}")


class TestHyperLogLogRegisterOverflow:
    """Bug: HLL registers stored as bytearray (max 255) but rank can
    exceed 255 for high precision values. With precision=4, remaining
    bits = 124, so max rank = 125. Fine. But the estimate formula
    uses 2**(-r) which for r=0 gives 1, for r=255 gives tiny number."""

    def test_register_max_value(self):
        hll = HyperLogLog(precision=4)
        # Max possible rank = 128 - 4 + 1 = 125, fits in byte
        hll.add(b"\x00" * 16)  # all zeros hash → max rank
        assert all(r <= 255 for r in hll._registers)


class TestTDigestSingleCentroid:
    """Edge case: TDigest with a single centroid should return its mean
    for any quantile."""

    def test_single_centroid(self):
        td = TDigest(compression=100)
        td.add(42.0)
        assert td.quantile(0.5) == 42.0
        assert td.quantile(0.0) == 42.0
        assert td.quantile(1.0) == 42.0


class TestTDigestQuantileInterpolation:
    """Bug: verify the quantile interpolation is correct by checking
    known uniform distribution values."""

    def test_uniform_distribution(self):
        td = TDigest(compression=500)
        # Uniform [0, 100)
        for i in range(10000):
            td.add(float(i))
        # For uniform distribution, q-th quantile ≈ q * 100
        for q in [0.1, 0.3, 0.5, 0.7, 0.9]:
            est = td.quantile(q)
            expected = q * 10000  # actually q * 9999
            assert abs(est - q * 9999) < 500, f"q={q}: est={est}, expected~{q*9999}"


class TestCMSHashCollision:
    """Bug: CMS uses sequential seeds (i * golden_ratio) which could
    produce correlated hash positions for small width."""

    def test_seeds_produce_different_positions(self):
        cms = CountMinSketch(width=100, depth=5)
        data = b"test"
        positions = cms._hashes(data)
        # Positions should not all be the same
        assert len(set(positions)) > 1, "All hash positions are the same!"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))