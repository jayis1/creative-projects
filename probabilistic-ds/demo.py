#!/usr/bin/env python3
"""Command-line demo for the probabilistic-ds toolkit."""
import argparse
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pds import (
    BloomFilter, CountingBloomFilter, CuckooFilter,
    CountMinSketch, HyperLogLog, TopK, TDigest, SkipList,
)


def demo_bloom(args):
    bf = BloomFilter(capacity=args.capacity, error_rate=args.fpr)
    for i in range(args.capacity):
        bf.add(f"item-{i}")
    # Test false positives
    fp = sum(1 for i in range(args.capacity, args.capacity * 2) if f"item-{i}" in bf)
    print(f"Bloom Filter: {args.capacity} items, {bf.num_bits} bits, {bf.num_hashes} hashes")
    print(f"  False positive rate: {fp / args.capacity:.4f} (target {args.fpr})")
    print(f"  Current estimated FPR: {bf.estimated_false_positive_rate:.4f}")


def demo_cuckoo(args):
    cf = CuckooFilter(capacity=args.capacity)
    for i in range(args.capacity):
        cf.add(f"item-{i}")
    fp = sum(1 for i in range(args.capacity, args.capacity * 2) if f"item-{i}" in cf)
    print(f"Cuckoo Filter: {args.capacity} items, load factor {cf.load_factor:.3f}")
    print(f"  False positive rate: {fp / args.capacity:.4f}")
    # Test deletion
    cf.remove("item-0")
    print(f"  After delete item-0: {'item-0' in cf} (should be False)")


def demo_cms(args):
    cms = CountMinSketch(error=0.01, confidence=0.99)
    freqs = {}
    for _ in range(args.n):
        item = f"word-{random.randint(0, 99)}"
        cms.add(item)
        freqs[item] = freqs.get(item, 0) + 1
    # Check accuracy
    errors = [abs(cms.query(k) - v) for k, v in freqs.items()]
    avg_err = sum(errors) / len(errors)
    max_err = max(errors)
    print(f"Count-Min Sketch: {args.n} updates, {len(freqs)} distinct")
    print(f"  Avg error: {avg_err:.2f}, Max error: {max_err}")


def demo_hll(args):
    hll = HyperLogLog(precision=14)
    true = set()
    for _ in range(args.n):
        x = random.randint(0, 10**9)
        hll.add(str(x))
        true.add(x)
    est = hll.estimate()
    print(f"HyperLogLog: {args.n} inserts, {len(true)} distinct")
    print(f"  Estimated: {est:.0f}, Actual: {len(true)}")
    print(f"  Error: {abs(est - len(true)) / len(true) * 100:.2f}%")
    print(f"  Memory: {hll.m} registers (~{hll.m} bytes)")


def demo_topk(args):
    tk = TopK(k=10)
    for _ in range(args.n):
        # Zipfian-ish: item-0 frequent, item-9 rare
        item = f"item-{int(random.random()**3 * 10)}"
        tk.add(item)
    print(f"TopK (k=10): {args.n} updates")
    for item, count in tk.topk(10):
        print(f"  {item}: {count}")


def demo_tdigest(args):
    td = TDigest(compression=200)
    data = [random.gauss(100, 15) for _ in range(args.n)]
    for x in data:
        td.add(x)
    data_sorted = sorted(data)
    print(f"T-Digest: {args.n} values, {td.num_centroids} centroids")
    for q in [0.01, 0.25, 0.5, 0.75, 0.99]:
        actual = data_sorted[int(q * len(data_sorted))]
        est = td.quantile(q)
        print(f"  p{int(q*100):02d}: estimated={est:.2f}, actual={actual:.2f}, "
              f"err={abs(est-actual)/actual*100:.2f}%")


def demo_skiplist(args):
    sl = SkipList()
    keys = list(range(args.n))
    random.shuffle(keys)
    for k in keys:
        sl.insert(k, f"val-{k}")
    print(f"Skip List: {args.n} insertions")
    print(f"  Min: {sl.min()}, Max: {sl.max()}")
    print(f"  Search 0: {sl.search(0)}")
    sl.delete(0)
    print(f"  After delete 0: {0 in sl} (should be False)")
    print(f"  Range [0,5]: {[k for k,v in sl.range(0,5)]}")


def main():
    parser = argparse.ArgumentParser(description="Probabilistic DS toolkit demo")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("bloom", help="Bloom filter demo")
    p.add_argument("--capacity", type=int, default=10000)
    p.add_argument("--fpr", type=float, default=0.01)
    p.set_defaults(func=demo_bloom)

    p = sub.add_parser("cuckoo", help="Cuckoo filter demo")
    p.add_argument("--capacity", type=int, default=10000)
    p.set_defaults(func=demo_cuckoo)

    p = sub.add_parser("cms", help="Count-Min Sketch demo")
    p.add_argument("--n", type=int, default=100000)
    p.set_defaults(func=demo_cms)

    p = sub.add_parser("hll", help="HyperLogLog demo")
    p.add_argument("--n", type=int, default=1000000)
    p.set_defaults(func=demo_hll)

    p = sub.add_parser("topk", help="Top-K demo")
    p.add_argument("--n", type=int, default=100000)
    p.set_defaults(func=demo_topk)

    p = sub.add_parser("tdigest", help="T-Digest demo")
    p.add_argument("--n", type=int, default=100000)
    p.set_defaults(func=demo_tdigest)

    p = sub.add_parser("skiplist", help="Skip list demo")
    p.add_argument("--n", type=int, default=1000)
    p.set_defaults(func=demo_skiplist)

    args = parser.parse_args()
    random.seed(42)
    args.func(args)


if __name__ == "__main__":
    main()