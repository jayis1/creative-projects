"""Initial smoke tests for the probabilistic-ds toolkit."""
import os
import sys
import random
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pds import (
    BloomFilter, CountingBloomFilter, CuckooFilter,
    CountMinSketch, HyperLogLog, TopK, TDigest, SkipList,
)


class TestBloomFilter:
    def test_no_false_negatives(self):
        bf = BloomFilter(capacity=1000, error_rate=0.01)
        for i in range(1000):
            bf.add(f"item-{i}")
        for i in range(1000):
            assert f"item-{i}" in bf, f"False negative on item-{i}"

    def test_false_positive_rate(self):
        bf = BloomFilter(capacity=10000, error_rate=0.01)
        for i in range(10000):
            bf.add(f"item-{i}")
        fp = sum(1 for i in range(10000, 20000) if f"item-{i}" in bf)
        rate = fp / 10000
        assert rate < 0.05, f"FPR {rate} too high"

    def test_serialization(self):
        bf = BloomFilter(capacity=100, error_rate=0.01)
        bf.add("hello")
        data = bf.to_bytes()
        bf2 = BloomFilter.from_bytes(data)
        assert "hello" in bf2
        assert bf2.count == 1

    def test_count_and_len(self):
        bf = BloomFilter(capacity=100)
        bf.add("a")
        bf.add("b")
        assert len(bf) == 2

    def test_invalid_params(self):
        with pytest.raises(ValueError):
            BloomFilter(capacity=0)
        with pytest.raises(ValueError):
            BloomFilter(capacity=10, error_rate=0)


class TestCountingBloomFilter:
    def test_add_remove(self):
        cbf = CountingBloomFilter(capacity=1000, error_rate=0.01)
        cbf.add("x")
        assert "x" in cbf
        assert cbf.remove("x")
        assert "x" not in cbf

    def test_no_false_negatives(self):
        cbf = CountingBloomFilter(capacity=500, error_rate=0.01)
        for i in range(500):
            cbf.add(str(i))
        for i in range(500):
            assert str(i) in cbf


class TestCuckooFilter:
    def test_add_lookup_delete(self):
        cf = CuckooFilter(capacity=1000)
        cf.add("apple")
        assert "apple" in cf
        assert cf.remove("apple")
        assert "apple" not in cf

    def test_no_false_negatives(self):
        cf = CuckooFilter(capacity=2000)
        for i in range(1000):
            cf.add(f"k{i}")
        for i in range(1000):
            assert f"k{i}" in cf

    def test_fp_rate(self):
        cf = CuckooFilter(capacity=10000, fingerprint_bits=12)
        for i in range(5000):
            cf.add(f"k{i}")
        fp = sum(1 for i in range(5000, 10000) if f"k{i}" in cf)
        assert fp / 5000 < 0.1


class TestCountMinSketch:
    def test_frequency_estimation(self):
        cms = CountMinSketch(error=0.001, confidence=0.99)
        for _ in range(1000):
            cms.add("a")
        for _ in range(500):
            cms.add("b")
        assert cms.query("a") >= 1000  # overestimate
        assert cms.query("b") >= 500
        assert cms.query("a") <= 1100  # not too much
        assert cms.query("b") <= 600

    def test_total(self):
        cms = CountMinSketch()
        for i in range(100):
            cms.add(str(i))
        assert cms.total == 100

    def test_merge(self):
        c1 = CountMinSketch(width=100, depth=5)
        c2 = CountMinSketch(width=100, depth=5)
        c1.add("x", 3)
        c2.add("x", 2)
        c1.merge(c2)
        assert c1.query("x") == 5


class TestHyperLogLog:
    def test_cardinality(self):
        random.seed(42)
        hll = HyperLogLog(precision=14)
        n = 100000
        seen = set()
        for _ in range(n):
            x = random.randint(0, 10**12)
            hll.add(str(x))
            seen.add(x)
        est = hll.estimate()
        err = abs(est - len(seen)) / len(seen)
        assert err < 0.05, f"Error {err:.4f} too high"

    def test_merge(self):
        h1 = HyperLogLog(precision=12)
        h2 = HyperLogLog(precision=12)
        for i in range(5000):
            h1.add(str(i))
        for i in range(5000, 10000):
            h2.add(str(i))
        h1.merge(h2)
        est = h1.estimate()
        assert abs(est - 10000) / 10000 < 0.1


class TestTopK:
    def test_basic(self):
        tk = TopK(k=3)
        for _ in range(10):
            tk.add("a")
        for _ in range(5):
            tk.add("b")
        for _ in range(3):
            tk.add("c")
        top = tk.topk()
        assert top[0][0] == "a"
        assert top[0][1] == 10

    def test_capacity(self):
        tk = TopK(k=2)
        tk.add("x")
        tk.add("y")
        tk.add("z")  # should evict one
        assert len(tk) == 2


class TestTDigest:
    def test_quantiles(self):
        random.seed(42)
        td = TDigest(compression=200)
        data = [random.gauss(100, 15) for _ in range(10000)]
        for x in data:
            td.add(x)
        data_sorted = sorted(data)
        for q in [0.5, 0.25, 0.75]:
            actual = data_sorted[int(q * len(data_sorted))]
            est = td.quantile(q)
            assert abs(est - actual) / actual < 0.1, f"q={q}: est={est}, actual={actual}"

    def test_empty(self):
        td = TDigest()
        import math
        assert math.isnan(td.quantile(0.5))


class TestSkipList:
    def test_insert_search(self):
        sl = SkipList()
        sl.insert(3, "c")
        sl.insert(1, "a")
        sl.insert(2, "b")
        assert sl.search(1) == "a"
        assert sl.search(2) == "b"
        assert sl.search(3) == "c"

    def test_ordering(self):
        sl = SkipList()
        keys = list(range(100))
        random.shuffle(keys)
        for k in keys:
            sl.insert(k, k)
        result = [k for k, v in sl]
        assert result == list(range(100))

    def test_delete(self):
        sl = SkipList()
        sl.insert(1, "a")
        sl.insert(2, "b")
        assert sl.delete(1)
        assert 1 not in sl
        assert 2 in sl

    def test_range(self):
        sl = SkipList()
        for i in range(20):
            sl.insert(i, i)
        result = [k for k, v in sl.range(5, 10)]
        assert result == [5, 6, 7, 8, 9, 10]

    def test_update(self):
        sl = SkipList()
        sl.insert(1, "old")
        sl.insert(1, "new")
        assert sl.search(1) == "new"
        assert len(sl) == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))