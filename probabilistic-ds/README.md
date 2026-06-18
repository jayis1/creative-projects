# Probabilistic Data Structures Toolkit

A from-scratch collection of memory-efficient probabilistic data structures in pure Python. Each structure trades exactness for dramatic savings in memory and/or time, enabling analysis of datasets far larger than available RAM.

## Structures

| Structure | Purpose | Error Guarantee | Memory |
|-----------|---------|-----------------|--------|
| **BloomFilter** | Set membership (no false negatives) | FPR ≤ configurable (e.g. 1%) | ~9.6 bits/element @ 1% FPR |
| **CountingBloomFilter** | Deletable set membership | FPR ≤ configurable | ~4× Bloom (4-bit counters) |
| **ScalableBloomFilter** | Auto-growing Bloom filter | Compounded FPR ≤ target | grows as needed |
| **CuckooFilter** | Deletable set membership, better space | FPR ≤ configurable | ~5 bits/element @ 1% FPR |
| **CountMinSketch** | Frequency estimation | Additive: `ε·N` w/ prob `1-δ` | `O(1/ε · log 1/δ)` |
| **ConservativeCountMinSketch** | Frequency estimation (reduced error) | Better additive bound | same as CMS |
| **HyperLogLog** | Cardinality (distinct count) | Relative: ~1.04/√m | `2^p` registers (~5 bits each) |
| **TopK** | Heavy-hitters tracking (Space-Saving) | Exact for top-k, approximate rest | `O(k)` with min-heap |
| **TDigest** | Streaming quantiles | High accuracy at tails | `O(compression)` centroids |
| **SkipList** | Ordered map (support structure) | Exact, O(log n) expected | `O(n)` |

## How It Works

### Bloom Filter
Uses `k` independent hash functions (derived via Kirsch-Mitzenmacher double hashing from 2 base hashes) mapping elements into a bit array of `m` bits. To add an element, set all `k` bits. To query, check all `k` bits — if any is unset, the element is definitely not present. Optimal `m` and `k` are derived analytically from the target FPR and capacity.

### Counting Bloom Filter
Same as Bloom but each "bit" is a 4-bit counter (0–15). Adding increments counters; deletion decrements them. An element is present iff all its counters are ≥ 1. Supports deletion at ~4× the memory cost.

### Scalable Bloom Filter
A Bloom filter that grows dynamically. When the current slice reaches capacity, a new slice is allocated with exponentially growing capacity and a tightened error rate. The compounded FPR across all slices stays below the target. Ideal when the total number of elements is unknown in advance.

### Cuckoo Filter
Stores small fingerprints (e.g. 16-bit) in a table of buckets. Uses partial-key cuckoo hashing: each item has two candidate buckets (`i1` and `i2 = i1 ⊕ hash(fp)`). On collision, evicts an existing fingerprint to its alternate bucket (cuckoo hashing). Supports deletion naturally. The fingerprint is derived from the upper bits of the hash while the index uses the lower bits, ensuring independence.

### Count-Min Sketch
A 2D array of `d × w` counters, each row hashed independently. The estimated frequency is the **minimum** across all rows — this guarantees overestimation but never underestimation. Error is bounded: `Pr[error > ε·N] < δ` with `w = e/ε`, `d = ln(1/δ)`.

### Conservative Count-Min Sketch
A variant of CMS that uses the "conservative update" strategy: when incrementing, only update the counters that currently have the minimum value, rather than all rows. This reduces overestimation error by up to 50% at the cost of slightly more computation per add().

### HyperLogLog
Hashes each element to 128 bits (MD5 for uniform distribution). Uses the top `p` bits as a register index and counts leading zeros in the rest. The harmonic mean of register values gives a cardinality estimate with small-range and large-range corrections. Standard error ≈ `1.04/√(2^p)`.

### Top-K (Space-Saving)
Maintains exactly `k` counters using a min-heap for O(log k) replacement. When a new item arrives and the table is full, it replaces the item with the smallest count, inheriting that count (overestimate). Frequent items always have accurate counts; rare items may be dropped. Supports merge for distributed aggregation.

### T-Digest
Maintains a set of centroids `(mean, weight)`. New data either merges into the nearest centroid or creates a new one. Centroid capacity is governed by a scale function `k(q) = δ·4·N·q·(1-q)` that places more centroids near the tails (q→0 or q→1), giving high accuracy at extreme quantiles. Supports merge for parallel/streaming aggregation.

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
print("user-5@example.com" in bf)         # True
print("unknown@example.com" in bf)         # False (probably)
print(f"Current FPR estimate: {bf.estimated_false_positive_rate:.4f}")

# Serialize / deserialize
data = bf.to_bytes()
bf2 = BloomFilter.from_bytes(data)
```

### Scalable Bloom Filter

```python
from pds import ScalableBloomFilter

sbf = ScalableBloomFilter(initial_capacity=1000, error_rate=0.01)
for i in range(50000):  # far exceeds initial capacity
    sbf.add(str(i))
print(f"Slices: {sbf.num_slices}, Total bits: {sbf.total_bits}")
print(f"Compounded FPR: {sbf.compounded_fpr:.4f}")
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

cf = CuckooFilter(capacity=10000, fingerprint_bits=16)
cf.add("hello")
print("hello" in cf)       # True
cf.remove("hello")
print("hello" in cf)       # False
print(f"Load factor: {cf.load_factor:.3f}")
```

### Count-Min Sketch (and Conservative variant)

```python
from pds import CountMinSketch, ConservativeCountMinSketch

cms = CountMinSketch(error=0.001, confidence=0.999)
for _ in range(1000):
    cms.add("click")
print(f"click count ≈ {cms.query('click')}")  # ~1000

# Conservative variant — lower overestimation
ccms = ConservativeCountMinSketch(error=0.001, confidence=0.999)
```

### HyperLogLog

```python
from pds import HyperLogLog

hll = HyperLogLog(precision=14)  # 16384 registers, ~0.81% error
for i in range(1_000_000):
    hll.add(str(i))
print(f"Distinct count ≈ {hll.estimate():.0f}")  # ~1,000,000
print(f"Memory: {hll.m} bytes vs 8MB for exact set")
print(f"Theoretical error: {hll.relative_error:.4f}")
```

### Top-K

```python
from pds import TopK

tk = TopK(k=10)
words = ["the", "the", "the", "cat", "cat", "dog"]
for w in words:
    tk.add(w)
print(tk.topk())  # [('the', 3), ('cat', 2), ('dog', 1)]

# Merge two TopK trackers
tk2 = TopK(k=10)
tk2.add("the", 5)
tk.merge(tk2)
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
print(sl.min(), sl.max())          # (3, 'three') (5, 'five')
```

### JSON Serialization

```python
from pds import BloomFilter, serialize, deserialize

bf = BloomFilter(capacity=1000, error_rate=0.01)
bf.add("checkpoint")
data = serialize(bf)  # JSON string
bf2 = deserialize(data)
print("checkpoint" in bf2)  # True
```

## CLI

The toolkit includes two CLI entry points:

### Demo CLI (`demo.py`)

```bash
python demo.py bloom --capacity 10000 --fpr 0.01
python demo.py cuckoo --capacity 10000
python demo.py cms --n 100000
python demo.py hll --n 1000000
python demo.py topk --n 100000
python demo.py tdigest --n 100000
python demo.py skiplist --n 1000
```

### Main CLI (`cli.py`)

```bash
# Run benchmarks
python cli.py bench

# Build a structure from stdin and save
cat words.txt | python cli.py save output.json --type cms --error 0.001

# Load and query
python cli.py load output.json --query "hello" "world"
python cli.py load output.json --topk 10
python cli.py load output.json --estimate
python cli.py load output.json --quantile 0.5 0.95 0.99
```

## Benchmark Results

Typical performance on a standard machine:

| Structure | Throughput | Accuracy | Memory |
|-----------|-----------|----------|--------|
| BloomFilter | ~150K ops/s | 1% FPR | 60KB / 50K items |
| CuckooFilter | ~270K ops/s | <1% FPR | 1.3MB / 20K items |
| CountMinSketch | ~73K ops/s | avg error 0 | 112KB |
| ConservativeCMS | ~70K ops/s | avg error 0 | 111KB |
| HyperLogLog | ~462K ops/s | 0.03% error | 16KB / 500K items |
| TDigest | — | <1% at p99 | ~4KB / 50K items |

## Architecture

```
probabilistic-ds/
├── pds/
│   ├── __init__.py            # Package exports
│   ├── hashing.py             # FNV-1a, double hashing, MD5 utilities
│   ├── bloom.py               # BloomFilter, CountingBloomFilter
│   ├── scalable_bloom.py      # ScalableBloomFilter (auto-growing)
│   ├── cuckoo.py              # CuckooFilter
│   ├── countmin.py            # CountMinSketch
│   ├── conservative_cms.py    # ConservativeCountMinSketch
│   ├── hll.py                 # HyperLogLog
│   ├── topk.py                # TopK (Space-Saving + min-heap + merge)
│   ├── tdigest.py             # TDigest (streaming quantiles + merge)
│   ├── skiplist.py            # SkipList (ordered map)
│   ├── serialization.py       # JSON serialize/deserialize for all structures
│   └── benchmark.py           # Benchmarking utilities
├── tests/
│   ├── test_all.py            # Core structure tests (24 tests)
│   └── test_enhancements.py   # Enhancement tests (15 tests)
├── demo.py                    # Interactive demo CLI
├── cli.py                     # Main CLI (bench, save, load)
└── README.md
```

## Design Notes

- **Double hashing**: All structures needing multiple hash probes use the Kirsch-Mitzenmacher technique (`g_i(x) = h1(x) + i·h2(x)`) to derive `k` hashes from just 2, cutting hash cost dramatically.
- **FNV-1a**: Used for non-cryptographic hashing where speed matters (Bloom, Cuckoo, CMS, TopK). MD5 is used for HLL where uniform distribution is critical.
- **Cuckoo fingerprint/index independence**: The fingerprint uses the upper bits of a 64-bit hash while the index uses the lower 32 bits, ensuring they are independent and FPR stays low.
- **Serialization**: All structures support JSON serialization via `serialize()`/`deserialize()`. BloomFilter additionally supports binary `to_bytes()`/`from_bytes()`.
- **Mergeability**: HyperLogLog, CountMinSketch, TDigest, and TopK support `merge()` for distributed/streaming aggregation.
- **Min-heap TopK**: Uses a lazy-rebuilt min-heap for O(log k) eviction instead of O(k) linear scan.

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and fixed:

1. **CuckooFilter redundant hash computation** — `_fingerprint()` and `_hash()` both called `fnv1a_64(data + b"\x01")` separately, computing the same 64-bit hash twice per add/lookup/remove. Fixed by introducing `_compute_fp_and_index()` which computes the hash once and derives both fingerprint (upper bits) and index (lower bits) from it. *(Performance fix — ~33% fewer hash calls.)*

2. **TDigest._compress() was O(n²)** — The compress method recomputed `sum(c.count for c in new_centroids)` from scratch on every iteration of the outer while loop, making it quadratic in the number of centroids. Fixed by tracking `cum_count` incrementally. *(Performance fix — compress is now O(n).)*

3. **TDigest.cdf() used crude 50% approximation** — The CDF estimation added `c.count * 0.5` for the boundary centroid instead of properly interpolating between centroid means. Fixed with linear interpolation between the previous and current centroid means, giving much more accurate CDF values. *(Accuracy fix — CDF at quartiles now within 5% of true value vs ~25% before.)*

4. **CountMinSketch.merge() docstring was wrong** — Docstring said "pointwise max" but the code does pointwise sum (which is correct for merging two independent CMS streams). Fixed the docstring to accurately describe the sum behavior. *(Documentation fix.)*

5. **TDigest unused `bisect` import** — The `bisect` module was imported but never used. Removed the dead import. *(Code quality fix.)*

6. **CountingBloomFilter.remove() count behavior undocumented** — The `remove()` method decrements `self.count` on any successful removal, including false-positive removals (where the item was never actually added but counters happened to be set). This is inherent to counting Bloom filters but was undocumented. Added clear documentation explaining the behavior. *(Documentation fix.)*

7. **TDigest.quantile() dead code** — The quantile interpolation had dead variables (`prev` and `prev_center` assigned but never used, replaced by `prev_c` and `prev_center_pos`). Cleaned up the dead code and added clear comments. *(Code quality fix.)*

8. **BloomFilter.estimated_false_positive_rate used bits_set instead of count** — The FPR estimator counted set bits via `bin(int.from_bytes(...)).count('1')` which is slow on large filters and doesn't match the standard formula. Fixed to use `self.count` with the standard `(1 - e^(-k*n/m))^k` formula. *(Correctness + performance fix.)*

## License

MIT