# Probabilistic Data Structures Toolkit

A from-scratch collection of memory-efficient probabilistic data structures in pure Python. Each structure trades exactness for dramatic savings in memory and/or time, enabling analysis of datasets far larger than available RAM.

## Structures

| Structure | Purpose | Error Guarantee | Memory |
|-----------|---------|-----------------|--------|
| **BloomFilter** | Set membership (no false negatives) | FPR ≤ configurable (e.g. 1%) | ~9.6 bits/element @ 1% FPR |
| **CountingBloomFilter** | Deletable set membership | FPR ≤ configurable | ~4× Bloom (4-bit counters) |
| **CuckooFilter** | Deletable set membership, better space | FPR ≤ configurable | ~5 bits/element @ 1% FPR |
| **CountMinSketch** | Frequency estimation | Additive: `ε·N` w/ prob `1-δ` | `O(1/ε · log 1/δ)` |
| **HyperLogLog** | Cardinality (distinct count) | Relative: ~1.04/√m | `2^p` registers (~5 bits each) |
| **TopK** | Heavy-hitters tracking | Exact for top-k, approximate rest | `O(k)` |
| **TDigest** | Streaming quantiles | High accuracy at tails | `O(compression)` centroids |
| **SkipList** | Ordered map (support structure) | Exact, O(log n) expected | `O(n)` |

## How It Works

### Bloom Filter
Uses `k` independent hash functions mapping elements into a bit array of `m` bits. To add an element, set all `k` bits. To query, check all `k` bits — if any is unset, the element is definitely not present. Optimal `m` and `k` are derived analytically from the target FPR and capacity.

### Counting Bloom Filter
Same as Bloom but each "bit" is a 4-bit counter (0–15). Adding increments counters; deletion decrements them. An element is present iff all its counters are ≥ 1. Supports deletion at ~4× the memory cost.

### Cuckoo Filter
Stores small fingerprints (e.g. 12-bit) in a table of buckets. Uses partial-key cuckoo hashing: each item has two candidate buckets (`i1` and `i2 = i1 ⊕ hash(fp)`). On collision, evicts an existing fingerprint to its alternate bucket (cuckoo hashing). Supports deletion naturally.

### Count-Min Sketch
A 2D array of `d × w` counters, each row hashed independently. The estimated frequency is the **minimum** across all rows — this guarantees overestimation but never underestimation. Error is bounded: `Pr[error > ε·N] < δ` with `w = e/ε`, `d = ln(1/δ)`.

### HyperLogLog
Hashes each element to 128 bits. Uses the top `p` bits as a register index and counts leading zeros in the rest. The harmonic mean of register values gives a cardinality estimate with small-range and large-range corrections. Standard error ≈ `1.04/√(2^p)`.

### Top-K (Space-Saving)
Maintains exactly `k` counters. When a new item arrives and the table is full, it replaces the item with the smallest count, inheriting that count (overestimate). Frequent items always have accurate counts; rare items may be dropped.

### T-Digest
Maintains a set of centroids `(mean, weight)`. New data either merges into the nearest centroid or creates a new one. Centroid capacity is governed by a scale function `k(q) = δ·4·N·q·(1-q)` that places more centroids near the tails (q→0 or q→1), giving high accuracy at extreme quantiles.

### Skip List
A probabilistic alternative to balanced trees. Each node has a random height (geometric distribution). Search proceeds by "fast-forwarding" at high levels then descending. Expected O(log n) for all operations, with no rebalancing overhead.

## Installation

```bash
cd probabilistic-ds
pip install -e .
# or just add the pds/ directory to your path
```

## Usage

### Bloom Filter

```python
from pds import BloomFilter

bf = BloomFilter(capacity=10000, error_rate=0.01)
for i in range(10000):
    bf.add(f"user-{i}@example.com")

print("user-5@example.com" in "user-5@example.com" )  # True
# Wait, need the filter:
bf.add("user-5@example.com")
print(bf.__contains__("user-5@example.com"))  # True
print("unknown@example.com" in bf)             # False (probably)
print(f"Current FPR estimate: {bf.estimated_false_positive_rate:.4f}")
```

### Counting Bloom Filter (with deletion)

```python
from pds import CountingBloomFilter

cbf = CountingBloomFilter(capacity=1000, error_rate=0.01)
cbf.add("alice")
print("alice" in cbf)      # True
cbf.remove("alice")
print("alice" in cbf)      # False
```

### Cuckoo Filter

```python
from pds import CuckooFilter

cf = CuckooFilter(capacity=10000)
cf.add("hello")
print("hello" in cf)       # True
cf.remove("hello")
print("hello" in cf)       # False
```

### Count-Min Sketch

```python
from pds import CountMinSketch

cms = CountMinSketch(error=0.001, confidence=0.999)
for _ in range(1000):
    cms.add("click")
for _ in range(500):
    cms.add("view")
print(f"click count ≈ {cms.query('click')}")  # ~1000
print(f"view count ≈ {cms.query('view')}")    # ~500
```

### HyperLogLog

```python
from pds import HyperLogLog

hll = HyperLogLog(precision=14)  # 16384 registers, ~0.81% error
for i in range(1_000_000):
    hll.add(str(i))
print(f"Distinct count ≈ {hll.estimate():.0f}")  # ~1,000,000
print(f"Memory: {hll.m} bytes vs 8MB for exact set")
```

### Top-K

```python
from pds import TopK

tk = TopK(k=10)
words = ["the", "the", "the", "cat", "cat", "dog"]
for w in words:
    tk.add(w)
print(tk.topk())  # [('the', 3), ('cat', 2), ('dog', 1)]
```

### T-Digest

```python
import random
from pds import TDigest

td = TDigest(compression=100)
for _ in range(100000):
    td.add(random.gauss(100, 15))
print(f"Median ≈ {td.quantile(0.5):.1f}")       # ~100
print(f"99th pct ≈ {td.quantile(0.99):.1f}")    # ~135
print(f"CDF at 100 ≈ {td.cdf(100):.2f}")        # ~0.50
```

### Skip List

```python
from pds import SkipList

sl = SkipList()
sl.insert(5, "five")
sl.insert(1, "one")
sl.insert(3, "three")
print(list(sl))                    # [(1,'one'), (3,'three'), (5,'five')]
print(sl.search(3))                # 'three'
sl.delete(1)
print(list(sl.range(0, 10)))       # [(3,'three'), (5,'five')]
```

## CLI Demo

```bash
python demo.py bloom --capacity 10000 --fpr 0.01
python demo.py cuckoo --capacity 10000
python demo.py cms --n 100000
python demo.py hll --n 1000000
python demo.py topk --n 100000
python demo.py tdigest --n 100000
python demo.py skiplist --n 1000
```

## Architecture

```
probabilistic-ds/
├── pds/
│   ├── __init__.py      # Package exports
│   ├── hashing.py       # FNV-1a, double hashing, MD5 utilities
│   ├── bloom.py         # BloomFilter, CountingBloomFilter
│   ├── cuckoo.py        # CuckooFilter
│   ├── countmin.py      # CountMinSketch
│   ├── hll.py           # HyperLogLog
│   ├── topk.py          # TopK (Space-Saving)
│   ├── tdigest.py       # TDigest
│   └── skiplist.py      # SkipList
├── tests/
│   └── test_all.py
├── demo.py
└── README.md
```

## Design Notes

- **Double hashing**: All structures needing multiple hash probes use the Kirsch-Mitzenmacher technique (`g_i(x) = h1(x) + i·h2(x)`) to derive `k` hashes from just 2, cutting hash cost dramatically.
- **FNV-1a**: Used for non-cryptographic hashing where speed matters (Bloom, Cuckoo, CMS, TopK). MD5 is used for HLL where uniform distribution is critical.
- **Serialization**: BloomFilter supports `to_bytes()`/`from_bytes()` for checkpointing.
- **Mergeability**: HyperLogLog, CountMinSketch, and TDigest support `merge()` for distributed/streaming aggregation.

## License

MIT