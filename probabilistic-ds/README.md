# Probabilistic Data Structures Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-130%20passing-brightgreen.svg)](#testing)
[![Version](https://img.shields.io/badge/version-3.0.0-orange.svg)](#changelog)

> **16 probabilistic data structures** for membership testing, cardinality,
> frequency estimation, quantile tracking, set similarity, and stream
> sampling — all from scratch in pure Python.

A from-scratch collection of memory-efficient probabilistic data structures.
Each structure trades exactness for dramatic savings in memory and/or time,
enabling analysis of datasets far larger than available RAM.

---

## Table of Contents

- [Structures](#structures)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [CLI](#cli)
- [Benchmark Results](#benchmark-results)
- [Architecture](#architecture)
- [Design Notes](#design-notes)
- [Examples Directory](#examples-directory)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Structures

| Structure | Purpose | Error Guarantee | Memory |
|-----------|---------|-----------------|--------|
| **BloomFilter** | Set membership (no false negatives) | FPR ≤ configurable (e.g. 1%) | ~9.6 bits/element @ 1% FPR |
| **CountingBloomFilter** | Deletable set membership | FPR ≤ configurable | ~4× Bloom (4-bit counters) |
| **ScalableBloomFilter** | Auto-growing Bloom filter | Compounded FPR ≤ target | grows as needed |
| **BlockedBloomFilter** | Cache-friendly membership | FPR ≤ configurable | ~same as Bloom, 1 cache line/access |
| **CuckooFilter** | Deletable set membership, better space | FPR ≤ configurable | ~5 bits/element @ 1% FPR |
| **CountMinSketch** | Frequency estimation | Additive: `ε·N` w/ prob `1-δ` | `O(1/ε · log 1/δ)` |
| **ConservativeCountMinSketch** | Frequency estimation (reduced error) | Better additive bound | same as CMS |
| **HyperLogLog** | Cardinality (distinct count) | Relative: ~1.04/√m | `2^p` registers (~5 bits each) |
| **KMV** | Cardinality (alternative to HLL) | Relative: ~1/√(k-2) | `O(k)` integers |
| **MinHash** | Set similarity (Jaccard) | SE ≈ 1/√num_perm | `O(num_perm)` integers |
| **LSHIndex** | Near-duplicate detection | Threshold-based | `O(n)` per band |
| **TopK** | Heavy-hitters tracking (Space-Saving) | Exact for top-k, approximate rest | `O(k)` with min-heap |
| **TDigest** | Streaming quantiles | High accuracy at tails | `O(compression)` centroids |
| **SkipList** | Ordered map (support structure) | Exact, O(log n) expected | `O(n)` |
| **ReservoirSampler** | Uniform random stream sampling | Exact uniform | `O(k)` |
| **WeightedReservoirSampler** | Weighted stream sampling | Weighted-proportional | `O(k)` |

## How It Works

### Bloom Filter
Uses `k` independent hash functions (derived via Kirsch-Mitzenmacher double hashing from 2 base hashes) mapping elements into a bit array of `m` bits. To add an element, set all `k` bits. To query, check all `k` bits — if any is unset, the element is definitely not present. Optimal `m` and `k` are derived analytically from the target FPR and capacity.

### Counting Bloom Filter
Same as Bloom but each "bit" is a 4-bit counter (0–15). Adding increments counters; deletion decrements them. An element is present iff all its counters are ≥ 1. Supports deletion at ~4× the memory cost.

### Scalable Bloom Filter
A Bloom filter that grows dynamically. When the current slice reaches capacity, a new slice is allocated with exponentially growing capacity and a tightened error rate. The compounded FPR across all slices stays below the target. Ideal when the total number of elements is unknown in advance.

### Blocked Bloom Filter
A cache-friendly variant that divides the bit array into blocks (typically 512 bits = one cache line). Each element maps to a single block, and all `k` hash functions operate within that block. This means every access touches at most one cache line instead of `k` scattered lines, dramatically improving cache performance. Uses MD5 for within-block hashing to ensure high-quality independent probes (FNV-1a's poor avalanche properties for short inputs cause inflated FPRs within small blocks).

### Cuckoo Filter
Stores small fingerprints (e.g. 16-bit) in a table of buckets. Uses partial-key cuckoo hashing: each item has two candidate buckets (`i1` and `i2 = i1 ⊕ hash(fp)`). On collision, evicts an existing fingerprint to its alternate bucket (cuckoo hashing). Supports deletion naturally. The fingerprint is derived from the upper bits of the hash while the index uses the lower bits, ensuring independence.

### Count-Min Sketch
A 2D array of `d × w` counters, each row hashed independently. The estimated frequency is the **minimum** across all rows — this guarantees overestimation but never underestimation. Error is bounded: `Pr[error > ε·N] < δ` with `w = e/ε`, `d = ln(1/δ)`.

### Conservative Count-Min Sketch
A variant of CMS that uses the "conservative update" strategy: when incrementing, only update the counters that currently have the minimum value, rather than all rows. This reduces overestimation error by up to 50% at the cost of slightly more computation per add().

### HyperLogLog
Hashes each element to 128 bits (MD5 for uniform distribution). Uses the top `p` bits as a register index and counts leading zeros in the rest. The harmonic mean of register values gives a cardinality estimate with small-range and large-range corrections. Standard error ≈ `1.04/√(2^p)`.

### KMV (K-Minimum Values)
Keeps the `k` smallest distinct hash values seen. The cardinality estimate is `(k-1) / (max_stored_hash / hash_space)`. Simpler than HLL and mergeable (union via merging the k smallest from both sketches). Standard error ≈ `1/√(k-2)`.

### MinHash
Estimates Jaccard similarity `|A ∩ B| / |A ∪ B|` using `num_perm` independent hash functions. Each "signature" is an array of minimum hash values; similarity ≈ fraction of matching signature positions. Standard error ≈ `1/√num_perm`.

### LSH Index
Locality-Sensitive Hashing for fast near-duplicate detection. Bands MinHash signatures into groups; documents that share at least one band are candidates for near-duplicate. Reduces O(n²) pairwise comparison to O(n) per band. Threshold ≈ `(1/num_bands)^(1/rows_per_band)`.

### Top-K (Space-Saving)
Maintains exactly `k` counters using a min-heap for O(log k) replacement. When a new item arrives and the table is full, it replaces the item with the smallest count, inheriting that count (overestimate). Frequent items always have accurate counts; rare items may be dropped. Supports merge for distributed aggregation.

### T-Digest
Maintains a set of centroids `(mean, weight)`. New data either merges into the nearest centroid or creates a new one. Centroid capacity is governed by a scale function `k(q) = δ·4·N·q·(1-q)` that places more centroids near the tails (q→0 or q→1), giving high accuracy at extreme quantiles. Supports merge for parallel/streaming aggregation.

### Skip List
A probabilistic alternative to balanced trees. Each node has a random height (geometric distribution). Search proceeds by "fast-forwarding" at high levels then descending. Expected O(log n) for all operations, with no rebalancing overhead.

### Reservoir Sampler (Algorithm R)
Maintains a reservoir of `k` items; for the i-th item (i > k), include it with probability `k/i`, replacing a random existing item. At any point, the reservoir contains a uniform random sample of the stream seen so far. Supports merge for combining samples from parallel streams.

### Weighted Reservoir Sampler (A-Res)
Each item has a weight; the sample is a weighted random sample without replacement. Uses the key = `u^(1/w)` technique where `u` is uniform(0,1) and `w` is the item weight. Keep the `k` items with largest keys.

---

## Installation

```bash
# From the repo
cd probabilistic-ds
pip install -e ".[dev]"

# Or without extras
pip install -e .

# YAML config support (optional)
pip install -e ".[yaml]"
```

**Requirements:** Python 3.10+

The toolkit uses only the Python standard library (plus optional PyYAML for
YAML config files).

---

## Quick Start

```python
from pds import BloomFilter, HyperLogLog, TDigest, TopK

# Bloom filter: URL dedup
bf = BloomFilter(capacity=1_000_000, error_rate=0.001)
bf.add("https://example.com/page/1")
print("page/1 visited:", "https://example.com/page/1" in bf)  # True

# HyperLogLog: unique visitor counting
hll = HyperLogLog(precision=14)
for i in range(1_000_000):
    hll.add(f"user-{i}")
print(f"Unique visitors: ~{hll.estimate():,.0f}")  # ~1,000,000

# T-Digest: latency percentiles
td = TDigest(compression=200)
import random
for _ in range(100_000):
    td.add(random.lognormvariate(4.5, 0.5))
print(f"p50: {td.quantile(0.5):.1f}ms, p99: {td.quantile(0.99):.1f}ms")

# Top-K: trending pages
tk = TopK(k=10)
for _ in range(100_000):
    tk.add(f"/page-{random.randint(0, 99)}")
print("Top 3:", tk.topk(3))
```

---

## Usage Examples

### Bloom Filter

```python
from pds import BloomFilter

bf = BloomFilter(capacity=10000, error_rate=0.01)
for i in range(10000):
    bf.add(f"user-{i}@example.com")
print("user-5@example.com" in bf)         # True
print("unknown@example.com" in bf)       # False (probably)
print(f"Current FPR estimate: {bf.estimated_false_positive_rate:.4f}")

# Binary serialization
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

### Blocked Bloom Filter (cache-friendly)

```python
from pds import BlockedBloomFilter

bf = BlockedBloomFilter(capacity=100000, error_rate=0.01)
for i in range(100000):
    bf.add(str(i))
print(f"Blocks: {bf.num_blocks}, FPR: {bf.estimated_false_positive_rate:.4f}")
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

### Count-Min Sketch

```python
from pds import CountMinSketch, ConservativeCountMinSketch

cms = CountMinSketch(error=0.001, confidence=0.999)
for _ in range(1000):
    cms.add("click")
print(f"click count ≈ {cms.query('click')}")  # ~1000

# Conservative variant — lower overestimation
ccms = ConservativeCountMinSketch(error=0.001, confidence=0.999)

# Merge two sketches
cms2 = CountMinSketch(error=0.001, confidence=0.999)
for _ in range(500):
    cms2.add("click")
cms.merge(cms2)
print(f"Merged count ≈ {cms.query('click')}")  # ~1500
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

### KMV (K-Minimum Values)

```python
from pds import KMV

kmv = KMV(k=4096)  # ~1.6% error
for i in range(100_000):
    kmv.add(str(i))
print(f"Distinct count ≈ {kmv.estimate():.0f}")  # ~100,000
print(f"Theoretical error: {kmv.relative_error:.4f}")

# Merge (union)
kmv2 = KMV(k=4096)
for i in range(100_000, 200_000):
    kmv2.add(str(i))
kmv.merge(kmv2)
print(f"Merged ≈ {kmv.estimate():.0f}")  # ~200,000
```

### MinHash + LSH (Near-Duplicate Detection)

```python
from pds import MinHash, LSHIndex

m1 = MinHash(num_perm=128)
m2 = MinHash(num_perm=128)
for w in "the quick brown fox".split():
    m1.add(w)
for w in "the quick red fox".split():
    m2.add(w)
print(f"Jaccard similarity: {m1.jaccard(m2):.3f}")  # ~0.5

# LSH for fast near-duplicate search
idx = LSHIndex(num_perm=128, num_bands=32)
idx.add("doc1", m1)
candidates = idx.query(m2)  # {"doc1"} if similarity > threshold
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
print(f"99th pct ≈ {td.quantile(0.99):.1f}")     # ~135
print(f"CDF at 100 ≈ {td.cdf(100):.2f}")         # ~0.50
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
print(list(sl.range(0, 10)))      # [(3,'three'), (5,'five')]
print(sl.min(), sl.max())          # (3, 'three') (5, 'five')
```

### Reservoir Sampling

```python
from pds import ReservoirSampler

rs = ReservoirSampler(k=100)
for i in range(1_000_000):
    rs.add(i)
sample = rs.sample()  # 100 uniform random items from the stream
print(f"Sampled {len(sample)} from {rs.total_seen} items")
```

### JSON Serialization

```python
from pds import BloomFilter, BlockedBloomFilter, KMV, MinHash, serialize, deserialize

bf = BloomFilter(capacity=1000, error_rate=0.01)
bf.add("checkpoint")
data = serialize(bf)  # JSON string
bf2 = deserialize(data)
print("checkpoint" in bf2)  # True

# All structures support serialization:
kmv = KMV(k=256)
for i in range(1000):
    kmv.add(str(i))
kmv2 = deserialize(serialize(kmv))
print(f"KMV roundtrip: {kmv2.estimate():.0f}")
```

---

## Configuration

Structures can be built from configuration files (JSON, YAML, or TOML):

```yaml
# config.yaml
structure: bloom
capacity: 1000000
error_rate: 0.001
```

```python
from pds import build_from_file

# Build from config file (format auto-detected from extension)
bf = build_from_file("config.yaml")
print(type(bf))  # <class 'pds.bloom.BloomFilter'>
```

```bash
# Via CLI
python cli.py config config.yaml --populate < urls.txt --output filter.json
```

Supported config formats:
- `.json` — standard JSON
- `.yaml` / `.yml` — YAML (requires PyYAML)
- `.toml` — TOML (requires Python 3.11+ or `tomli`)

See [`examples/config.yaml`](examples/config.yaml) for all supported structures.

```python
from pds import list_structures, get_param_spec

# List all supported structures
print(list_structures())
# ['blocked-bloom', 'bloom', 'cms', 'conservative-cms', 'counting-bloom',
#  'cuckoo', 'hll', 'kmv', 'minhash', 'reservoir', 'scalable-bloom',
#  'tdigest', 'topk']

# Get accepted parameters for a structure
print(get_param_spec("bloom"))
# ['capacity', 'error_rate']
```

---

## CLI

The toolkit includes a comprehensive CLI:

```bash
# List all supported structures
python cli.py structures

# Build a structure from a config file
python cli.py config examples/config.yaml --populate < data.txt --output out.json

# Run benchmarks
python cli.py bench

# Build a structure from stdin and save
cat urls.txt | python cli.py save output.json --type bloom --capacity 10000

# Load and query
python cli.py load output.json --query "hello" "world"
python cli.py load output.json --topk 10
python cli.py load output.json --estimate          # HLL/KMV cardinality
python cli.py load output.json --quantile 0.5 0.95 # TDigest quantiles
python cli.py load output.json --cdf 100 200       # TDigest CDF
python cli.py load output.json --jaccard other.json  # MinHash similarity
python cli.py load output.json --sample 10         # Reservoir sample

# Demo CLI (from demo.py)
python demo.py bloom --capacity 10000 --fpr 0.01
python demo.py cuckoo --capacity 10000
python demo.py cms --n 100000
python demo.py hll --n 1000000
python demo.py topk --n 100000
python demo.py tdigest --n 100000
python demo.py skiplist --n 1000
```

---

## Benchmark Results

Typical performance on a standard machine:

| Structure | Throughput | Accuracy | Memory |
|-----------|-----------|----------|--------|
| BloomFilter | ~150K ops/s | 1% FPR | 60KB / 50K items |
| BlockedBloomFilter | ~80K ops/s | 1.1% FPR | 60KB / 50K items |
| CuckooFilter | ~270K ops/s | <1% FPR | 1.3MB / 20K items |
| CountMinSketch | ~73K ops/s | avg error 0 | 112KB |
| ConservativeCMS | ~70K ops/s | avg error 0 | 111KB |
| HyperLogLog | ~462K ops/s | 0.03% error | 16KB / 500K items |
| KMV | ~350K ops/s | ~1.6% error | 32KB / 500K items |
| MinHash | ~200K ops/s | SE ~8.8% | 1KB / 128 perms |
| TDigest | — | <1% at p99 | ~4KB / 50K items |

> **Note:** BlockedBloomFilter uses MD5 for within-block hashing (to ensure
> FPR quality), making it slower than the standard BloomFilter but with
> better cache locality. Use it when cache performance matters more than
> raw throughput.

---

## Architecture

```
probabilistic-ds/
├── pds/
│   ├── __init__.py            # Package exports (16 structures + utils)
│   ├── hashing.py             # FNV-1a 64-bit, double hashing, MD5-128
│   ├── bloom.py               # BloomFilter, CountingBloomFilter
│   ├── blocked_bloom.py       # BlockedBloomFilter (cache-friendly)
│   ├── scalable_bloom.py      # ScalableBloomFilter (auto-growing)
│   ├── cuckoo.py              # CuckooFilter
│   ├── countmin.py            # CountMinSketch
│   ├── conservative_cms.py    # ConservativeCountMinSketch
│   ├── hll.py                 # HyperLogLog
│   ├── kmv.py                 # KMV (K-Minimum Values)
│   ├── minhash.py             # MinHash + LSHIndex
│   ├── sampling.py            # ReservoirSampler, WeightedReservoirSampler
│   ├── topk.py                # TopK (Space-Saving + min-heap + merge)
│   ├── tdigest.py             # TDigest (streaming quantiles + merge)
│   ├── skiplist.py            # SkipList (ordered map)
│   ├── serialization.py       # JSON serialize/deserialize for all structures
│   ├── config.py              # Config system (JSON/YAML/TOML → structure)
│   ├── logging_utils.py       # Structured logging utilities
│   ├── benchmark.py           # Benchmarking utilities
│   └── quotient.py            # Placeholder (see docstring)
├── tests/
│   ├── test_all.py            # Core structure tests
│   ├── test_enhancements.py   # Enhancement tests
│   ├── test_bugs.py           # Bug hunt tests
│   ├── test_fixes.py          # Bug fix verification tests
│   └── test_new_structures.py # New structure tests (v3.0)
├── examples/
│   ├── bloom_dedup.py         # URL dedup with Bloom filter
│   ├── stream_analytics.py    # HLL + CMS + TopK stream analytics
│   ├── near_duplicate_detection.py  # MinHash + LSH
│   ├── latency_monitoring.py  # TDigest for latency percentiles
│   └── config.yaml            # Example config file
├── .github/workflows/ci.yml   # GitHub Actions CI
├── pyproject.toml             # pip-installable package
├── CONTRIBUTING.md            # Contribution guide
├── LICENSE                    # MIT
├── demo.py                    # Interactive demo CLI
├── cli.py                     # Main CLI (bench, save, load, config)
└── README.md                  # This file
```

---

## Design Notes

- **Double hashing**: All structures needing multiple hash probes use the Kirsch-Mitzenmacher technique (`g_i(x) = h1(x) + i·h2(x)`) to derive `k` hashes from just 2, cutting hash cost dramatically. Exception: BlockedBloomFilter uses independently-seeded MD5 hashes within blocks (see below).
- **FNV-1a vs MD5**: FNV-1a is used for non-cryptographic hashing where speed matters (Bloom, Cuckoo, CMS, TopK). MD5 is used for HLL, KMV, MinHash, and BlockedBloomFilter where uniform distribution is critical — FNV-1a has poor avalanche properties for short inputs, which inflates false-positive rates in BlockedBloomFilter and biases cardinality/similarity estimates.
- **Cuckoo fingerprint/index independence**: The fingerprint uses the upper bits of a 64-bit hash while the index uses the lower 32 bits, ensuring they are independent and FPR stays low.
- **Serialization**: All structures support JSON serialization via `serialize()`/`deserialize()`. BloomFilter and BlockedBloomFilter additionally support binary `to_bytes()`/`from_bytes()`.
- **Mergeability**: HyperLogLog, KMV, CountMinSketch, TDigest, TopK, MinHash, and ReservoirSampler support `merge()` for distributed/streaming aggregation.
- **Min-heap TopK**: Uses a lazy-rebuilt min-heap for O(log k) eviction instead of O(k) linear scan.
- **Config system**: All structures can be instantiated from JSON/YAML/TOML config files, with parameter validation and helpful error messages.

---

## Examples Directory

The `examples/` directory contains runnable demos:

| Example | Structures Used | Description |
|---------|-----------------|-------------|
| `bloom_dedup.py` | BloomFilter | URL deduplication for web crawling |
| `stream_analytics.py` | HLL + CMS + TopK | Real-time web event stream analytics |
| `near_duplicate_detection.py` | MinHash + LSHIndex | Near-duplicate document detection |
| `latency_monitoring.py` | TDigest | API latency percentile monitoring |
| `config.yaml` | — | Example config file for all structures |

Run with: `python examples/bloom_dedup.py`

---

## Testing

The toolkit has **130 tests** (1 skipped if PyYAML not installed):

```bash
python -m pytest tests/ -v
```

Test files:
- `test_all.py` — Core structure tests (24 tests)
- `test_enhancements.py` — Enhancement tests (15 tests)
- `test_bugs.py` — Bug identification tests (12 tests)
- `test_fixes.py` — Bug fix verification tests (9 tests)
- `test_new_structures.py` — New v3.0 structure tests (68 tests)

Coverage includes:
- No-false-negative guarantees for all membership filters
- False-positive rate validation against targets
- Serialization roundtrips for all structures
- Merge correctness for mergeable structures
- Edge cases (empty structures, single element, full capacity)
- Config system validation (JSON/YAML/TOML)
- Logging utilities

---

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and fixed:

1. **CuckooFilter redundant hash computation** — `_fingerprint()` and `_hash()` both called `fnv1a_64(data + b"\x01")` separately, computing the same 64-bit hash twice per add/lookup/remove. Fixed by introducing `_compute_fp_and_index()` which computes the hash once and derives both fingerprint (upper bits) and index (lower bits) from it. *(Performance fix — ~33% fewer hash calls.)*

2. **TDigest._compress() was O(n²)** — The compress method recomputed `sum(c.count for c in new_centroids)` from scratch on every iteration of the outer while loop, making it quadratic in the number of centroids. Fixed by tracking `cum_count` incrementally. *(Performance fix — compress is now O(n).)*

3. **TDigest.cdf() used crude 50% approximation** — The CDF estimation added `c.count * 0.5` for the boundary centroid instead of properly interpolating between centroid means. Fixed with linear interpolation between the previous and current centroid means, giving much more accurate CDF values. *(Accuracy fix — CDF at quartiles now within 5% of true value vs ~25% before.)*

4. **CountMinSketch.merge() docstring was wrong** — Docstring said "pointwise max" but the code does pointwise sum (which is correct for merging two independent CMS streams). Fixed the docstring. *(Documentation fix.)*

5. **TDigest unused `bisect` import** — The `bisect` module was imported but never used. Removed the dead import. *(Code quality fix.)*

6. **CountingBloomFilter.remove() count behavior undocumented** — The `remove()` method decrements `self.count` on any successful removal, including false-positive removals. Added clear documentation explaining the behavior. *(Documentation fix.)*

7. **TDigest.quantile() dead code** — The quantile interpolation had dead variables (`prev` and `prev_center` assigned but never used). Cleaned up. *(Code quality fix.)*

8. **BloomFilter.estimated_false_positive_rate used bits_set instead of count** — The FPR estimator counted set bits via `bin(int.from_bytes(...)).count('1')` which is slow on large filters. Fixed to use `self.count` with the standard `(1 - e^(-k*n/m))^k` formula. *(Correctness + performance fix.)*

---

## Roadmap

Future plans for the toolkit:

- **Streaming Bloom filter** — variant that handles cold-start with adaptive sizing
- **HLL++ / HLL TailCut** — improved HLL variants with better small-range accuracy
- **Streaming partition** — parallel multi-threaded ingestion with merge
- **C++ extension** — optional C extension for FNV-1a to boost throughput 5-10×
- **Parquet/Arrow export** — export sketches to columnar formats for data pipelines
- **Merkle tree integration** — content-addressed serialization for P2P sync
- **More structures**: Ribbon Filter, Spectral Bloom Filter, Misra-Gries
- **Visualization**: ASCII art diagrams of internal structure state
- **Benchmark suite**: automated comparison vs `pybloom`, `mmh3`-based filters

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
and how to add new data structures.

---

## Changelog

### v3.0.0 — Comprehensive Improvement (2026-06-18)

**New structures (8 added):**
- `BlockedBloomFilter` — cache-friendly Bloom filter variant (MD5-based within-block hashing for FPR quality)
- `KMV` — K-Minimum Values cardinality estimator (alternative to HLL)
- `MinHash` — approximate Jaccard set similarity with merge support
- `LSHIndex` — locality-sensitive hashing for near-duplicate detection
- `ReservoirSampler` — uniform random stream sampling (Algorithm R) with merge
- `WeightedReservoirSampler` — weighted stream sampling (A-Res algorithm)

**New infrastructure:**
- Config system (`config.py`) — build any structure from JSON/YAML/TOML files
- Structured logging (`logging_utils.py`) — `get_logger()`, `set_log_level()`, `disable()`
- `pyproject.toml` — pip-installable package with entry point `pds`
- GitHub Actions CI — runs tests on Python 3.10/3.11/3.12
- `CONTRIBUTING.md` and `LICENSE`
- 4 runnable example scripts in `examples/`

**Enhanced serialization:**
- Added JSON serialization for all new structures (BlockedBloomFilter, CountingBloomFilter, CuckooFilter, ConservativeCountMinSketch, KMV, MinHash, ReservoirSampler)

**CLI improvements:**
- New `config` subcommand — build from config files
- New `structures` subcommand — list all supported structures
- Support for new structures in `save`/`load` subcommands
- New query options: `--cdf`, `--jaccard`, `--sample`, `--estimate` (for KMV)

**Testing:**
- 68 new tests (130 total, up from 62)
- Tests for all new structures, config system, logging, enhanced serialization

### v2.0.0 — Enhancement (2026-06-18)
- Added ScalableBloomFilter, ConservativeCountMinSketch
- JSON serialization for all structures
- Benchmarking utilities
- TopK min-heap + merge
- TDigest improvements + CDF + merge
- Comprehensive CLI (bench/save/load)
- 15 new tests (39 total)

### v1.0.0 — Initial Release (2026-06-18)
- 8 core structures: BloomFilter, CountingBloomFilter, CuckooFilter, CountMinSketch, HyperLogLog, TopK, TDigest, SkipList
- FNV-1a/double hashing
- CLI demo
- 24 tests

---

## License

[MIT](LICENSE)