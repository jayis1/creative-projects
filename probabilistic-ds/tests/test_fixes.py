"""Tests verifying that bug-hunt fixes are correct."""
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


class TestCuckooSingleHashFix:
    """Verify CuckooFilter now computes hash only once per operation."""

    def test_compute_fp_and_index_exists(self):
        cf = CuckooFilter(capacity=100)
        fp, i1, i2 = cf._compute_fp_and_index(b"test")
        assert fp > 0
        assert 0 <= i1 < cf.num_buckets
        assert 0 <= i2 < cf.num_buckets
        # i1 and i2 should be different (usually)
        # alt_index(i1, fp) == i2 and alt_index(i2, fp) == i1
        assert cf._alt_index(i1, fp) == i2
        assert cf._alt_index(i2, fp) == i1

    def test_no_redundant_hash_calls(self):
        """Verify that add() calls fnv1a_64 only once for the main hash."""
        from pds.hashing import fnv1a_64
        call_count = [0]
        original = fnv1a_64

        def counting_fnv(data):
            call_count[0] += 1
            return original(data)

        # Monkey-patch
        import pds.cuckoo as cuckoo_mod
        old = cuckoo_mod.fnv1a_64
        cuckoo_mod.fnv1a_64 = counting_fnv
        try:
            cf = CuckooFilter(capacity=1000)
            cf.add("test_item")
            # Should call fnv1a_64 once for fp+index, plus once for alt_index's
            # hash(fp). So at least 2 calls but not 3 (was 3 before fix).
            assert call_count[0] <= 2, f"Expected <=2 hash calls, got {call_count[0]}"
        finally:
            cuckoo_mod.fnv1a_64 = old


class TestTDigestCompressFix:
    """Verify O(n) compress with incremental cum_count."""

    def test_compress_produces_fewer_centroids(self):
        td = TDigest(compression=50)
        for i in range(5000):
            td.add(float(i))
        before = len(td._centroids)
        td._compress()
        after = len(td._centroids)
        assert after <= before
        assert after <= td.compression * 5  # bounded

    def test_compress_preserves_total_count(self):
        td = TDigest(compression=50)
        for i in range(1000):
            td.add(float(i), 1.0)
        total_before = td._total_count
        td._compress()
        total_after = sum(c.count for c in td._centroids)
        assert abs(total_before - total_after) < 0.001

    def test_compress_is_fast(self):
        """O(n) compress should handle 10k centroids quickly."""
        import time
        td = TDigest(compression=50)
        for i in range(10000):
            td.add(float(i))
        t0 = time.perf_counter()
        td._compress()
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0, f"Compress took {elapsed:.3f}s — may still be O(n²)"


class TestTDigestCDFFix:
    """Verify CDF uses proper interpolation."""

    def test_cdf_monotonic(self):
        td = TDigest(compression=200)
        random.seed(42)
        for _ in range(10000):
            td.add(random.gauss(0, 1))
        # CDF should be monotonically non-decreasing
        values = sorted([random.gauss(0, 1) for _ in range(100)])
        cdfs = [td.cdf(v) for v in values]
        for i in range(1, len(cdfs)):
            assert cdfs[i] >= cdfs[i - 1] - 0.01, \
                f"CDF not monotonic at index {i}: {cdfs[i-1]} -> {cdfs[i]}"

    def test_cdf_at_quartiles(self):
        td = TDigest(compression=500)
        data = [float(i) for i in range(10000)]
        random.seed(42)
        random.shuffle(data)
        for x in data:
            td.add(x)
        # For uniform [0, 9999], CDF at 2500 ≈ 0.25, at 5000 ≈ 0.5
        assert abs(td.cdf(2500) - 0.25) < 0.05, f"CDF(2500)={td.cdf(2500)}"
        assert abs(td.cdf(5000) - 0.5) < 0.05, f"CDF(5000)={td.cdf(5000)}"
        assert abs(td.cdf(7500) - 0.75) < 0.05, f"CDF(7500)={td.cdf(7500)}"


class TestCMSMergeDocstringFix:
    """Verify merge docstring is accurate."""

    def test_merge_docstring_says_sum(self):
        assert "sum" in CountMinSketch.merge.__doc__.lower()


class TestTDigestNoBisectImport:
    """Verify bisect is no longer imported."""

    def test_no_bisect_in_source(self):
        import pds.tdigest as mod
        source = open(mod.__file__).read()
        assert "import bisect" not in source
        assert "bisect." not in source


class TestCountingBloomRemoveDocstring:
    """Verify remove() has proper documentation about false positive behavior."""

    def test_docstring_documents_false_positive(self):
        doc = CountingBloomFilter.remove.__doc__
        assert "false positive" in doc.lower() or "count" in doc.lower()


class TestTDigestDeadCodeRemoved:
    """Verify dead variables (prev, prev_center) are removed from quantile()."""

    def test_no_dead_code_in_quantile(self):
        import pds.tdigest as mod
        source = open(mod.__file__).read()
        # The old dead code assigned 'prev = self._centroids[i-1]' and
        # 'prev_center = cum' which were never used. After cleanup, only
        # prev_c and prev_center_pos should appear.
        # Check that 'prev_center = cum' (the dead assignment) is gone
        assert "prev_center = cum" not in source


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))