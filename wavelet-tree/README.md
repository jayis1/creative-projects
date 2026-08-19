# 🌳 Wavelet Tree

<p align="center">
<strong>A from-scratch succinct data structure library for sequence analysis</strong>
</p>

<p align="center">
<img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10+-blue.svg">
<img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green.svg">
<img alt="Tests: 2349" src="https://img.shields.io/badge/tests-2349-brightgreen.svg">
<img alt="Pure stdlib" src="https://img.shields.io/badge/dependencies-none-success.svg">
<img alt="CI" src="https://img.shields.io/badge/CI-GitHub%20Actions-blue.svg">
</p>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [Huffman-Shaped Variants](#huffman-shaped-variants)
  - [Range Queries](#range-queries)
  - [FM-Index Pattern Matching](#fm-index-pattern-matching)
  - [Statistics & Benchmarking](#statistics--benchmarking)
  - [CLI](#cli)
  - [Configuration](#configuration)
  - [Serialization](#serialization)
- [Architecture](#architecture)
  - [BitVector](#bitvector)
  - [Wavelet Tree](#wavelet-tree-1)
  - [Wavelet Matrix](#wavelet-matrix)
  - [Huffman Shape](#huffman-shape)
  - [RRR Compression](#rrr-compression)
  - [FM-Index](#fm-index)
- [Examples](#examples)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)

---

## Overview

A **Wavelet Tree** is a succinct data structure that represents a sequence over an alphabet Σ while supporting three fundamental operations efficiently:

- **`access(i)`** — return the symbol at position `i` in O(log |Σ|) time
- **`rank(c, i)`** — count occurrences of symbol `c` in the prefix `S[0..i)` in O(log |Σ|) time
- **`select(c, k)`** — return the position of the `k`-th occurrence of symbol `c` in O(log |Σ|) time

The wavelet tree achieves this in **n·H₀(S) + o(n·log σ)** bits of space, where H₀ is the zeroth-order empirical entropy of the sequence — far less than a naive array representation.

This library implements four wavelet structure variants, three BitVector backends, 16+ range query types, an FM-index for pattern matching, a benchmarking suite, and a full CLI — all in pure Python with zero external dependencies.

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                    Wavelet Tree Library                          │
 ├──────────────┬──────────────┬──────────────┬───────────────────┤
 │  WaveletTree │ WaveletMatrix│ HuffmanTree  │ HuffmanMatrix     │
 │  (balanced)  │ (level-ord)  │ (Huffman)    │ (Huffman+matrix)  │
 ├──────────────┴──────────────┴──────────────┴───────────────────┤
 │  BitVector Backends:                                           │
 │    BitVector (naive) · BlockedBitVector (O(1) rank)           │
 │    RRRBitVector (two-level index)                              │
 ├────────────────────────────────────────────────────────────────┤
 │  Queries: access · rank · select · range_count · range_quantile│
 │    range_min · range_max · range_next · range_prev · interval  │
 │    intersection · prefix_search · count_distinct · report      │
 │    report_all · top_k · bottom_k                               │
 ├────────────────────────────────────────────────────────────────┤
 │  FM-Index: backward_search · count · locate                    │
 ├────────────────────────────────────────────────────────────────┤
 │  Infrastructure: CLI · Config · Logging · Serialization · Stats│
 └────────────────────────────────────────────────────────────────┘
```

## Features

### Structures (4 variants)
- **Wavelet Tree (Balanced)** — classic recursive binary decomposition over the alphabet
- **Wavelet Matrix** — level-ordered variant with better cache locality
- **Wavelet Tree (Huffman-shaped)** — Huffman-optimal shape, O(H₀(S)) average query time
- **Huffman-shaped Wavelet Matrix** — Huffman optimality + level-ordered layout

### BitVector Backends (3 variants)
- **BitVector** — naive O(n) rank/select, O(1) build
- **BlockedBitVector** — precomputed prefix sums, O(1) rank, O(log n) select
- **RRRBitVector** — two-level superblock/block index, O(1) rank, O(log n) select

### Query Operations (16+ types)
| Operation | Description |
|---|---|
| `access(i)` | Symbol at position i |
| `rank(c, i)` | Count of c in S[0..i) |
| `select(c, k)` | Position of k-th occurrence of c |
| `range_count(c, l, r)` | Count of c in S[l..r) |
| `range_quantile(l, r, k)` | k-th smallest symbol in S[l..r) |
| `range_min(l, r)` | Minimum symbol in S[l..r) |
| `range_max(l, r)` | Maximum symbol in S[l..r) |
| `range_next_value(l, r, t)` | Smallest symbol ≥ t in range |
| `range_prev_value(l, r, t)` | Largest symbol ≤ t in range |
| `interval_symbols(l, r)` | All distinct symbols with counts |
| `range_intersection(l1, r1, l2, r2)` | Symbols common to two ranges |
| `prefix_search(prefix)` | All positions matching prefix |
| `count_distinct(l, r)` | Number of distinct symbols in range |
| `range_report(l, r)` | Sorted (symbol, count) pairs in range |
| `range_report_all(l, r)` | All symbols in range, sorted |
| `range_top_k(l, r, k)` | k most frequent symbols in range |
| `range_bottom_k(l, r, k)` | k least frequent symbols in range |

### FM-Index (Pattern Matching)
- **`FMIndex(text)`** — Build a full FM-index from any text
- **`count(pattern)`** — Count occurrences in O(|P|·log|Σ|) time
- **`locate(pattern)`** — Find all positions in O(|P|·log|Σ| + occ) time
- Supports all four wavelet structure backends
- Uses sentinel-terminated BWT for correct handling of all edge cases

### Python Protocol Support
All structures inherit from `WaveletBase` and support:
- **Indexing**: `wt[i]` (including negative indices)
- **Iteration**: `for sym in wt`
- **Reversed**: `reversed(wt)`
- **Membership**: `c in wt`
- **Equality**: `wt1 == wt2`
- **Convenience**: `wt.count(c)`, `wt.index(c)`, `wt.positions(c)`, `wt.to_list()`

### Infrastructure
- **JSON serialization** — save/load any structure
- **Config system** — JSON/TOML/YAML configuration files
- **Structured logging** — text and JSON formats
- **CLI** — 8 subcommands (build, load, compare, info, config, benchmark, stats, search)
- **Statistics** — space usage (bits, bytes, entropy), structural metrics (depth, nodes)
- **Benchmarking** — timed build/access/rank/select across all structures
- **GitHub Actions CI** — Python 3.10–3.13
- **Pure stdlib** — no external dependencies

## Installation

```bash
# From the wavelet-tree directory
pip install -e .

# Or for development
pip install -e ".[dev]"
```

Requires Python 3.10 or later.

## Quick Start

```python
from wavelet_tree import WaveletTree

wt = WaveletTree("abracadabra")

# Basic operations
print(wt[0])              # 'a' — indexing
print(wt.rank('a', 11))   # 5   — count of 'a' in first 11 chars
print(wt.select('r', 1))  # 9   — second 'r' at index 9
print(wt.count('b'))      # 2   — total count
print(list(wt))           # iterate over all symbols
print('a' in wt)          # True — membership check
```

## Usage

### Python API

```python
from wavelet_tree import WaveletTree, WaveletMatrix
from wavelet_tree.queries import (
    range_quantile, range_count, interval_symbols,
    range_min, range_max, count_distinct,
    range_report, range_report_all, range_top_k, range_bottom_k,
)

seq = "abracadabra"
wt = WaveletTree(seq)

# Basic operations
print(wt.access(0))                  # 'a'
print(wt.rank('a', 11))             # 5 (all 'a's)
print(wt.rank('b', 11))             # 2
print(wt.select('r', 1))            # 9 (second 'r')

# Range queries
print(range_count(wt, 'a', 0, 5))   # 3 (a's in "abrac")
print(range_quantile(wt, 0, 11, 0)) # 'a' (smallest symbol)
print(range_min(wt, 0, 11))         # 'a'
print(range_max(wt, 0, 11))         # 'r'
print(interval_symbols(wt, 0, 11))  # {'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1}
print(count_distinct(wt, 0, 11))    # 5

# New: range reporting
print(range_report(wt, 0, 11))      # [('a',5), ('b',2), ('c',1), ('d',1), ('r',2)]
print(range_report_all(wt, 0, 5))   # ['a', 'a', 'b', 'c', 'r'] (sorted)
print(range_top_k(wt, 0, 11, 2))    # [('a',5), ('b',2)] — top 2 by frequency
print(range_bottom_k(wt, 0, 11, 3)) # [('c',1), ('d',1), ('b',2)] — bottom 3

# Protocol methods
print(wt[0])           # 'a' — indexing
print(wt[-1])          # 'a' — negative indexing
print(wt.count('a'))   # 5 — total count
print(wt.index('r'))   # 2 — first occurrence
print(wt.positions('b'))  # [1, 8] — all positions
print(wt.to_list())    # reconstruct original sequence
print('a' in wt)       # True — membership
for sym in wt: ...     # iteration
```

### Huffman-Shaped Variants

```python
from wavelet_tree import HuffmanWaveletTree, HuffmanWaveletMatrix

hwt = HuffmanWaveletTree("abracadabra")
print(hwt.codes)  # {'a': '0', 'c': '100', 'd': '101', 'b': '110', 'r': '111'}
print(hwt.access(0))      # 'a'
print(hwt.rank('a', 11))  # 5

# Huffman shapes give O(H₀) average query time
# Frequent symbols are near the root → faster queries
```

### FM-Index Pattern Matching

```python
from wavelet_tree import FMIndex

fm = FMIndex("abracadabra")

# Count occurrences
print(fm.count("abra"))  # 2
print(fm.count("bra"))   # 2
print(fm.count("xyz"))   # 0

# Locate occurrences
print(fm.locate("abra"))  # [0, 7]
print(fm.locate("bra"))   # [1, 8]

# Use different wavelet structure backends
fm = FMIndex("mississippi", structure="huffman-matrix")
print(fm.count("issi"))   # 2
print(fm.locate("issi"))  # [1, 4]
```

### Statistics & Benchmarking

```python
from wavelet_tree import WaveletTree, space_stats, tree_stats, benchmark, benchmark_report

wt = WaveletTree("abracadabra")

# Space usage
ss = space_stats(wt)
print(f"Total: {ss.total_bits} bits ({ss.total_bytes} bytes)")
print(f"Bits/symbol: {ss.bits_per_symbol:.2f}")
print(f"H₀ entropy: {ss.h0:.4f}")

# Structural metrics
ts = tree_stats(wt)
print(f"Tree depth: {ts.max_tree_depth}")
print(f"Internal nodes: {ts.num_internal_nodes}")
print(f"Leaves: {ts.num_leaves}")
print(f"Total bitvector length: {ts.total_bitvector_length}")

# Benchmark all structures
results = benchmark("mississippi", num_rank_queries=1000)
print(benchmark_report(results))
```

### CLI

```bash
# Build and query
python -m wavelet_tree build "abracadabra" --rank a 11
python -m wavelet_tree build "abracadabra" --select r 1
python -m wavelet_tree build "abracadabra" --quantile 0 11 0
python -m wavelet_tree build "abracadabra" --range-min 0 11 --range-max 0 11
python -m wavelet_tree build "abracadabra" --count-distinct 0 11

# Using different structures
python -m wavelet_tree build "abracadabra" --structure matrix --rank a 11
python -m wavelet_tree build "abracadabra" --structure huffman-tree --select a 0

# Save / load
python -m wavelet_tree build "abracadabra" --save wt.json
python -m wavelet_tree load wt.json --rank a 5

# Compare all structures
python -m wavelet_tree compare "mississippi"

# NEW: Benchmark all structures
python -m wavelet_tree benchmark "the quick brown fox" --num-queries 5000

# NEW: Space and structural statistics
python -m wavelet_tree stats "abracadabra"

# NEW: FM-index pattern search
python -m wavelet_tree search "abracadabra" "abra"
python -m wavelet_tree search "mississippi" "issi" --count
python -m wavelet_tree search "mississippi" "issi" --locate

# Config management
python -m wavelet_tree config show
python -m wavelet_tree config create --output config.json --structure matrix
python -m wavelet_tree build "hello" --config config.json --rank l 5
```

### Configuration

Config files support JSON, TOML, and YAML:

```json
{
  "structure": "matrix",
  "use_blocked": true,
  "log_level": "INFO",
  "log_format": "json"
}
```

### Serialization

```python
from wavelet_tree import WaveletTree, save, load

wt = WaveletTree("abracadabra")
save(wt, "wt.json")

wt2 = load("wt.json")
assert wt == wt2  # equality via WaveletBase
```

## Architecture

### BitVector

The foundational building block. A bitvector stores a sequence of bits and supports:
- `rank1(i)` — number of 1-bits in `B[0..i)`
- `rank0(i)` — number of 0-bits in `B[0..i)`
- `select1(k)` — position of the k-th 1-bit
- `select0(k)` — position of the k-th 0-bit

Three implementations:
1. **Naive** (`BitVector`) — scans the bits; O(n) per query, O(1) build
2. **Blocked** (`BlockedBitVector`) — one-level prefix-sum array at block boundaries (block_size = log n); O(1) rank, O(log n) select via binary search
3. **RRR** (`RRRBitVector`) — two-level superblock/block index (block_size = log n, superblock_interval = log²n); O(1) rank, O(log n) select

### Wavelet Tree

The sequence is recursively partitioned. At each node, a bitvector records which half of the alphabet each symbol belongs to. The left child holds symbols in the lower half, the right child holds the upper half. Queries descend the tree, using `rank` to map positions between levels.

### Wavelet Matrix

A flattened variant where all bitvectors at the same depth are concatenated. The sequence is stably partitioned level by level: elements with bit 0 go to the front, elements with bit 1 go to the back. After all levels, elements are sorted by their **bit-reversed** code. This gives better cache behavior and simpler code while supporting the same operations.

### Huffman Shape

Instead of splitting the alphabet in half at each node, we build a Huffman tree over symbol frequencies. Frequent symbols end up near the root, giving O(H₀) average query time. The HuffmanWaveletMatrix pads shorter codes to the maximum code length with trailing zeros so all symbols participate at every level.

### RRR Compression

The RRR (Raman-Raman-Rao) bitvector uses a two-level index structure:
- **Blocks** of size w = log(n): each block stores its popcount (class)
- **Superblocks** at intervals of w²: store cumulative popcounts

This gives O(1) rank queries with o(n) bits of overhead, approaching the information-theoretic optimum for bitvector compression.

### FM-Index

The FM-index enables pattern matching in O(|P|·log|Σ|) time using only rank queries on a wavelet tree built over the BWT (Burrows-Wheeler Transform):

1. Compute the suffix array of the text (with sentinel)
2. Compute the BWT from the suffix array
3. Build a wavelet tree over the BWT
4. Compute the C array (count of symbols < c in text)
5. **Backward search**: iteratively narrow [l, r) using `l = C[c] + rank(c, l)`, `r = C[c] + rank(c, r)`

The sentinel character (`\x00`) ensures correct handling of patterns longer than some suffixes.

## Examples

| File | Description |
|---|---|
| `examples/basic_operations.py` | Basic access/rank/select/range queries |
| `examples/compare_structures.py` | Verify all four variants agree |
| `examples/dna_analysis.py` | DNA sequence analysis with range queries |
| `examples/fm_index_search.py` | FM-index pattern matching demo |
| `examples/benchmark_stats.py` | Space statistics and performance benchmarking |

Run any example:
```bash
python examples/basic_operations.py
python examples/fm_index_search.py
python examples/benchmark_stats.py
```

## Testing

```bash
# Run all 2349 tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_wavelet_tree.py -v    # Core structure tests
python -m pytest tests/test_bitvector.py -v       # BitVector tests
python -m pytest tests/test_rrr_bitvector.py -v   # RRR BitVector tests
python -m pytest tests/test_huffman.py -v         # Huffman structure tests
python -m pytest tests/test_queries.py -v         # Range query tests
python -m pytest tests/test_new_queries.py -v     # New query tests
python -m pytest tests/test_base.py -v            # Base class tests
python -m pytest tests/test_fm_index.py -v        # FM-index tests
python -m pytest tests/test_stats.py -v           # Statistics tests
```

## Roadmap

- [ ] **RRR full compression** — Store only block classes and offsets (not raw bits)
- [ ] **Linear-time suffix array** — Replace O(n² log n) SA construction with SA-IS
- [ ] **LF-mapping** — Support `locate()` without storing the full SA
- [ ] **Memory-mapped persistence** — Binary format for large sequences
- [ ] **Parallel construction** — Multi-threaded tree building
- [ ] **NumPy integration** — Optional fast path using NumPy arrays
- [ ] **Visualization** — ASCII/Unicode tree visualization
- [ ] **Mutable sequences** — Dynamic wavelet trees with insert/delete

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
testing guidelines, and pull request process.

## License

MIT — See [LICENSE](LICENSE) for details.

## Known Issues (Resolved)

The following bugs were found during the Phase 3 bug hunt and have been fixed:

1. **BlockedBitVector rank/select incorrect for larger bitvectors** — The original two-level super-block/block structure had an off-by-one error in block index computation when the query position crossed super-block boundaries (affected sequences with >25 symbols). Fixed by replacing the two-level structure with a simpler one-level prefix-sum array. (Fixed)

2. **WaveletTree.select returns wrong result for out-of-range k with single-symbol alphabet** — When the alphabet has only one symbol, the tree root is a leaf (no bitvector), so select skipped the climb-back-up loop and returned `k` directly. Fixed by adding an explicit range check using `rank(c, n)`. (Fixed)

3. **HuffmanWaveletTree.select same out-of-range issue** — Same root cause as #2. Fixed by adding the same range check. (Fixed)

4. **Serialization roundtrip broken for non-character symbols** — The original `repr()`-based encoding couldn't reverse the conversion for integers. Fixed with typed JSON encoding. (Fixed)

5. **Config.from_dict doesn't coerce string booleans from fallback parsers** — Fixed by adding type coercion for string boolean values. (Fixed)

6. **dna_analysis.py example had incorrect range_count call** — Removed redundant broken line. (Fixed)

7. **FM-index backward search incorrect for single-symbol alphabets** — Without a sentinel character, the backward search couldn't distinguish suffixes of different lengths when the text had only one unique symbol. Fixed by appending a `\x00` sentinel to the text before computing the BWT and suffix array. (Fixed)

## Changelog

### v3.0.0 — Comprehensive Improvement
- **New: `WaveletBase` ABC** — Abstract base class with `__getitem__`, `__iter__`, `__reversed__`, `__contains__`, `count`, `index`, `positions`, `to_list`, `__eq__`, `__hash__`
- **New: `RRRBitVector`** — RRR-style compressed bitvector with two-level superblock/block index for O(1) rank
- **New: `FMIndex`** — Full FM-index with backward search pattern matching (count + locate), sentinel-terminated BWT, all four structure backends
- **New: 4 range query functions** — `range_report`, `range_report_all`, `range_top_k`, `range_bottom_k`
- **New: Statistics module** — `space_stats` (bits, bytes, entropy, bits/symbol), `tree_stats` (depth, nodes, bitvector lengths)
- **New: Benchmarking module** — `benchmark` (timed build/access/rank/select), `benchmark_report` (formatted report)
- **New: 3 CLI subcommands** — `benchmark`, `stats`, `search`
- **New: LICENSE** — MIT license file
- **New: CONTRIBUTING.md** — Development guidelines
- **New: 2 examples** — `fm_index_search.py`, `benchmark_stats.py`
- **New: 4 test files** — `test_base.py`, `test_rrr_bitvector.py`, `test_fm_index.py`, `test_stats.py`, `test_new_queries.py`
- **1366 new tests** — Total test count: 2349 (up from 983)

### v2.0.0 — Enhancement
- Config system (JSON/TOML/YAML), structured logging, 6 new query types, CLI config subcommand, GitHub Actions CI, 3 example scripts

### v1.0.0 — Initial Release
- WaveletTree, WaveletMatrix, HuffmanWaveletTree, HuffmanWaveletMatrix
- BitVector, BlockedBitVector
- 12 range query functions, JSON serialization, CLI