"""Tests for Phase 2 enhancements: ScalableBloomFilter, ConservativeCMS,
serialization, TopK merge, and TDigest accuracy improvements."""
import os
import sys
import random
import math
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pds import (
    BloomFilter, CountingBloomFilter, CuckooFilter, CountMinSketch,
    HyperLogLog, TopK, TDigest, SkipList, ScalableBloomFilter,
    ConservativeCountMinSketch, serialize, deserialize,
)


class TestScalableBloomFilter:
    def test_grows_beyond_initial(self):
        sbf = ScalableBloomFilter(initial_capacity=100, error_rate=0.01, growth=2.0)
        for i in range(500):
            sbf.add(str(i))
        assert sbf.num_slices > 1
        assert len(sbf) == 500

    def test_no_false_negatives(self):
        sbf = ScalableBloomFilter(initial_capacity=50, error_rate=0.01)
        for i in range(200):
            sbf.add(str(i))
        for i in range(200):
            assert str(i) in sbf

    def test_compounded_fpr(self):
        sbf = ScalableBloomFilter(initial_capacity=1000, error_rate=0.01)
        for i in range(1000):
            sbf.add(str(i))
        fp = sum(1 for i in range(1000, 2000) if str(i) in sbf)
        assert fp / 1000 < 0.05


class TestConservativeCMS:
    def test_reduces_overestimation(self):
        random.seed(123)
        std = CountMinSketch(error=0.001, confidence=0.99)
        cons = ConservativeCountMinSketch(error=0.001, confidence=0.99)
        freqs = {}
        for _ in range(10000):
            item = f"item-{random.randint(0, 99)}"
            std.add(item)
            cons.add(item)
            freqs[item] = freqs.get(item, 0) + 1
        std_errors = [abs(std.query(k) - v) for k, v in freqs.items()]
        cons_errors = [abs(cons.query(k) - v) for k, v in freqs.items()]
        assert sum(cons_errors) <= sum(std_errors) + 1  # conservative should be <=

    def test_inherits_properties(self):
        cms = ConservativeCountMinSketch(width=100, depth=5)
        cms.add("x", 5)
        assert cms.query("x") == 5
        assert cms.total == 5


class TestSerialization:
    def test_bloom_roundtrip(self):
        bf = BloomFilter(capacity=1000, error_rate=0.01)
        for i in range(100):
            bf.add(str(i))
        data = serialize(bf)
        bf2 = deserialize(data)
        for i in range(100):
            assert str(i) in bf2

    def test_cms_roundtrip(self):
        cms = CountMinSketch(width=100, depth=5)
        cms.add("hello", 10)
        cms.add("world", 5)
        data = serialize(cms)
        cms2 = deserialize(data)
        assert cms2.query("hello") == 10
        assert cms2.query("world") == 5

    def test_hll_roundtrip(self):
        hll = HyperLogLog(precision=12)
        for i in range(10000):
            hll.add(str(i))
        data = serialize(hll)
        hll2 = deserialize(data)
        assert abs(hll.estimate() - hll2.estimate()) < 1

    def test_topk_roundtrip(self):
        tk = TopK(k=10)
        for _ in range(100):
            tk.add("a")
        for _ in range(50):
            tk.add("b")
        data = serialize(tk)
        tk2 = deserialize(data)
        assert tk2.query("a") == 100
        assert tk2.query("b") == 50

    def test_tdigest_roundtrip(self):
        td = TDigest(compression=100)
        for x in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]:
            td.add(x)
        data = serialize(td)
        td2 = deserialize(data)
        assert abs(td.quantile(0.5) - td2.quantile(0.5)) < 0.1

    def test_unknown_type_raises(self):
        with pytest.raises(TypeError):
            serialize(42)


class TestTopKMerge:
    def test_merge(self):
        t1 = TopK(k=10)
        t2 = TopK(k=10)
        for _ in range(10):
            t1.add("a")
        for _ in range(5):
            t2.add("a")
        for _ in range(3):
            t2.add("b")
        t1.merge(t2)
        assert t1.query("a") == 15
        assert t1.query("b") == 3


class TestTDigestAccuracy:
    def test_tail_accuracy(self):
        random.seed(42)
        td = TDigest(compression=200)
        data = [random.gauss(0, 1) for _ in range(50000)]
        for x in data:
            td.add(x)
        ds = sorted(data)
        for q, tol in [(0.01, 0.15), (0.99, 0.15), (0.001, 0.3), (0.999, 0.3)]:
            actual = ds[int(q * len(ds))]
            est = td.quantile(q)
            # Relative to std (1.0) — absolute tolerance
            assert abs(est - actual) < tol, f"q={q}: est={est:.3f}, actual={actual:.3f}"

    def test_cdf(self):
        td = TDigest(compression=100)
        for x in range(100):
            td.add(float(x))
        assert td.cdf(-1) == 0.0
        assert td.cdf(200) == 1.0
        assert 0.4 < td.cdf(50) < 0.6

    def test_merge(self):
        td1 = TDigest(compression=100)
        td2 = TDigest(compression=100)
        for x in range(500):
            td1.add(float(x))
        for x in range(500, 1000):
            td2.add(float(x))
        td1.merge(td2)
        # median should be ~499.5
        assert abs(td1.quantile(0.5) - 499.5) < 50


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))