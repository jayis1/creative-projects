"""Benchmarking utilities for probabilistic data structures.

Provides functions to measure accuracy, memory usage, and throughput
of the various structures against exact baselines.
"""
import time
import random
import sys
from . import (
    BloomFilter, CountingBloomFilter, CuckooFilter,
    CountMinSketch, HyperLogLog, TopK, TDigest, SkipList,
)
from .conservative_cms import ConservativeCountMinSketch
from .scalable_bloom import ScalableBloomFilter


def _sizeof(obj) -> int:
    """Recursive size estimation using sys.getsizeof."""
    seen = set()
    def _size(o):
        oid = id(o)
        if oid in seen:
            return 0
        seen.add(oid)
        s = sys.getsizeof(o)
        if isinstance(o, dict):
            s += sum(_size(k) + _size(v) for k, v in o.items())
        elif isinstance(o, (list, tuple)):
            s += sum(_size(i) for i in o)
        elif isinstance(o, bytearray):
            s += len(o)
        return s
    return _size(obj)


def benchmark_bloom(n: int = 100000, error_rate: float = 0.01) -> dict:
    """Benchmark a Bloom filter: throughput, FPR, memory."""
    bf = BloomFilter(capacity=n, error_rate=error_rate)
    t0 = time.perf_counter()
    for i in range(n):
        bf.add(str(i))
    add_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    for i in range(n):
        _ = str(i) in bf
    lookup_time = time.perf_counter() - t0

    fp = sum(1 for i in range(n, 2 * n) if str(i) in bf)
    return {
        "structure": "BloomFilter",
        "items": n,
        "add_throughput": n / add_time,
        "lookup_throughput": n / lookup_time,
        "false_positive_rate": fp / n,
        "target_fpr": error_rate,
        "memory_bytes": len(bf._bits),
    }


def benchmark_cuckoo(n: int = 50000, fp_bits: int = 16) -> dict:
    """Benchmark a Cuckoo filter."""
    cf = CuckooFilter(capacity=n, fingerprint_bits=fp_bits)
    t0 = time.perf_counter()
    for i in range(n):
        cf.add(str(i))
    add_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    for i in range(n):
        _ = str(i) in cf
    lookup_time = time.perf_counter() - t0

    fp = sum(1 for i in range(n, 2 * n) if str(i) in cf)
    return {
        "structure": "CuckooFilter",
        "items": n,
        "add_throughput": n / add_time,
        "lookup_throughput": n / lookup_time,
        "false_positive_rate": fp / n,
        "load_factor": cf.load_factor,
        "memory_bytes": _sizeof(cf._table),
    }


def benchmark_cms(n: int = 100000, distinct: int = 1000) -> dict:
    """Benchmark Count-Min Sketch vs conservative variant."""
    results = []
    for name, cls in [("CMS", CountMinSketch),
                      ("ConservativeCMS", ConservativeCountMinSketch)]:
        cms = cls(error=0.001, confidence=0.99)
        freqs = {}
        t0 = time.perf_counter()
        for _ in range(n):
            item = f"item-{random.randint(0, distinct - 1)}"
            cms.add(item)
            freqs[item] = freqs.get(item, 0) + 1
        add_time = time.perf_counter() - t0

        errors = [abs(cms.query(k) - v) for k, v in freqs.items()]
        avg_err = sum(errors) / len(errors)
        max_err = max(errors)
        results.append({
            "structure": name,
            "items": n,
            "add_throughput": n / add_time,
            "avg_error": avg_err,
            "max_error": max_err,
            "memory_bytes": _sizeof(cms._counts),
        })
    return results


def benchmark_hll(n: int = 1000000, precision: int = 14) -> dict:
    """Benchmark HyperLogLog."""
    hll = HyperLogLog(precision=precision)
    seen = set()
    t0 = time.perf_counter()
    for _ in range(n):
        x = random.randint(0, 10**12)
        s = str(x)
        hll.add(s)
        seen.add(x)
    add_time = time.perf_counter() - t0
    est = hll.estimate()
    return {
        "structure": "HyperLogLog",
        "items": n,
        "distinct": len(seen),
        "estimated": est,
        "relative_error": abs(est - len(seen)) / len(seen),
        "add_throughput": n / add_time,
        "memory_bytes": len(hll._registers),
        "exact_memory_estimate": len(seen) * 28,  # ~28 bytes per str in a set
    }


def benchmark_tdigest(n: int = 100000) -> dict:
    """Benchmark T-Digest quantile estimation."""
    td = TDigest(compression=200)
    data = [random.gauss(100, 15) for _ in range(n)]
    t0 = time.perf_counter()
    for x in data:
        td.add(x)
    add_time = time.perf_counter() - t0

    data_sorted = sorted(data)
    quantiles = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
    errors = []
    for q in quantiles:
        actual = data_sorted[int(q * len(data_sorted))]
        est = td.quantile(q)
        errors.append(abs(est - actual) / actual * 100)

    return {
        "structure": "TDigest",
        "items": n,
        "add_throughput": n / add_time,
        "num_centroids": td.num_centroids,
        "quantile_errors_pct": dict(zip(quantiles, errors)),
        "max_error_pct": max(errors),
        "memory_bytes": _sizeof(td._centroids),
    }


def benchmark_skiplist(n: int = 100000) -> dict:
    """Benchmark SkipList vs Python dict + sorted."""
    sl = SkipList(max_level=20)
    keys = list(range(n))
    random.shuffle(keys)
    t0 = time.perf_counter()
    for k in keys:
        sl.insert(k, k)
    insert_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    for k in range(n):
        sl.search(k)
    search_time = time.perf_counter() - t0

    return {
        "structure": "SkipList",
        "items": n,
        "insert_throughput": n / insert_time,
        "search_throughput": n / search_time,
        "memory_bytes": _sizeof(sl),
    }


def run_all_benchmarks(seed: int = 42) -> list[dict]:
    """Run all benchmarks and return a list of result dicts."""
    random.seed(seed)
    results = []
    results.append(benchmark_bloom(n=50000))
    results.append(benchmark_cuckoo(n=20000))
    results.extend(benchmark_cms(n=50000, distinct=500))
    results.append(benchmark_hll(n=500000))
    results.append(benchmark_tdigest(n=50000))
    results.append(benchmark_skiplist(n=50000))
    return results