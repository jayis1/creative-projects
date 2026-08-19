# Wavelet Tree

A from-scratch **succinct data structure** library implementing Wavelet Trees (and variants) for sequence analysis with `rank`, `select`, and `access` operations in sublinear time.

## Overview

A **Wavelet Tree** is a succinct data structure that represents a sequence over an alphabet Σ while supporting three fundamental operations efficiently:

- **`access(i)`** — return the symbol at position `i` in O(log |Σ|) time
- **`rank(c, i)`** — count occurrences of symbol `c` in the prefix `S[0..i)` in O(log |Σ|) time
- **`select(c, k)`** — return the position of the `k`-th occurrence of symbol `c` in O(log |Σ|) time

The wavelet tree achieves this in **n·H₀(S) + o(n·log σ)** bits of space, where H₀ is the zeroth-order empirical entropy of the sequence — far less than a naive array representation.

## Features

### Structures
- **Wavelet Tree (Balanced)** — classic recursive binary decomposition over the alphabet
- **Wavelet Matrix** — level-ordered variant with better cache locality, identical query interface
- **Wavelet Tree (Huffman-shaped)** — Huffman-optimal shape reducing query time to O(H₀(S))
- **Huffman-shaped Wavelet Matrix** — combining Huffman optimality with level-ordered layout

### Core Primitives
- **BitVector** — naive O(n) rank/select, O(1) build
- **BlockedBitVector** — precomputed prefix-sum blocks for O(log n) rank, O(log n) select via binary search

### Query Operations
- `access(i)` — symbol at position i
- `rank(c, i)` — count of symbol c in S[0..i)
- `select(c, k)` — position of k-th occurrence of c
- `range_count(c, l, r)` — count of c in S[l..r)
- `range_quantile(l, r, k)` — k-th smallest symbol in S[l..r)
- `range_min(l, r)` — minimum symbol in S[l..r)
- `range_max(l, r)` — maximum symbol in S[l..r)
- `range_next_value(l, r, threshold)` — smallest symbol ≥ threshold in range
- `range_prev_value(l, r, threshold)` — largest symbol ≤ threshold in range
- `interval_symbols(l, r)` — all distinct symbols in range with counts
- `range_intersection(l1, r1, l2, r2)` — symbols common to two ranges
- `prefix_search(prefix)` — find all positions matching a prefix
- `count_distinct(l, r)` — number of distinct symbols in range

### Infrastructure
- **JSON serialization** — save/load structures
- **Config system** — JSON/TOML/YAML configuration files
- **Structured logging** — text and JSON formats
- **CLI** — argparse-based with 5 subcommands (build, load, compare, info, config)
- **GitHub Actions CI** — Python 3.10–3.13
- **Pure stdlib** — no external dependencies

## How It Works

### BitVector

The foundational building block. A bitvector stores a sequence of bits and supports:
- `rank1(i)` — number of 1-bits in `B[0..i)`
- `rank0(i)` — number of 0-bits in `B[0..i)`
- `select1(k)` — position of the k-th 1-bit
- `select0(k)` — position of the k-th 0-bit

We implement two strategies:
1. **Naive** — scans the bits; O(n) per query, O(1) build
2. **Blocked** — precomputes cumulative prefix sums at block boundaries (block size = log n) for O(log n) rank; select uses binary search over prefix sums + short linear scan

### Wavelet Tree

The sequence is recursively partitioned. At each node, a bitvector records which half of the alphabet each symbol belongs to. The left child holds symbols in the lower half, the right child holds the upper half. Queries descend the tree, using `rank` to map positions between levels.

### Wavelet Matrix

A flattened variant where all bitvectors at the same depth are concatenated. The sequence is stably partitioned level by level: elements with bit 0 go to the front, elements with bit 1 go to the back. After all levels, elements are sorted by their **bit-reversed** code. This gives better cache behavior and simpler code while supporting the same operations.

### Huffman Shape

Instead of splitting the alphabet in half at each node, we build a Huffman tree over symbol frequencies. Frequent symbols end up near the root, giving O(H₀) average query time. The HuffmanWaveletMatrix pads shorter codes to the maximum code length with trailing zeros so all symbols participate at every level.

## Usage

### Python API

```python
from wavelet_tree import WaveletTree, WaveletMatrix
from wavelet_tree.queries import range_quantile, range_count, interval_symbols, range_min, range_max, count_distinct

seq = "abracadabra"
wt = WaveletTree(seq)
print(wt.access(0))              # 'a'
print(wt.rank('a', 11))          # 5  (all 'a's)
print(wt.rank('b', 11))          # 2
print(wt.select('r', 1))         # 9  (second 'r' at index 9)
print(range_count(wt, 'a', 0, 5))  # 3  (a's in "abrac")
print(range_quantile(wt, 0, 11, 0))  # 'a' (smallest symbol)
print(range_min(wt, 0, 11))      # 'a'
print(range_max(wt, 0, 11))      # 'r'
print(interval_symbols(wt, 0, 11))   # {'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1}
print(count_distinct(wt, 0, 11))     # 5
```

### Huffman-shaped variants

```python
from wavelet_tree import HuffmanWaveletTree, HuffmanWaveletMatrix

hwt = HuffmanWaveletTree("abracadabra")
print(hwt.codes)  # {'a': '0', 'c': '100', 'd': '101', 'b': '110', 'r': '111'}
print(hwt.access(0))   # 'a'
print(hwt.rank('a', 11))  # 5
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

## Installation

```bash
pip install -e .
```

## Examples

- `examples/basic_operations.py` — basic access/rank/select/range queries
- `examples/compare_structures.py` — verify all four variants agree
- `examples/dna_analysis.py` — DNA sequence analysis with range queries

## License

MIT