# Wavelet Tree

A from-scratch **succinct data structure** library implementing Wavelet Trees (and variants) for sequence analysis with `rank`, `select`, and `access` operations in sublinear time.

## Overview

A **Wavelet Tree** is a succinct data structure that represents a sequence over an alphabet Σ while supporting three fundamental operations efficiently:

- **`access(i)`** — return the symbol at position `i` in O(log |Σ|) time
- **`rank(c, i)`** — count occurrences of symbol `c` in the prefix `S[0..i)` in O(log |Σ|) time
- **`select(c, k)`** — return the position of the `k`-th occurrence of symbol `c` in O(log |Σ|) time

The wavelet tree achieves this in **n·H₀(S) + o(n·log σ)** bits of space, where H₀ is the zeroth-order empirical entropy of the sequence — far less than a naive array representation.

## Features

- **Wavelet Tree (Balanced)** — classic recursive binary decomposition over the alphabet
- **Wavelet Matrix** — level-ordered variant with better cache locality, identical query interface
- **Wavelet Tree (Huffman-shaped)** — Huffman-optimal shape reducing query time to O(H₀(S))
- **Huffman-shaped Wavelet Matrix** — combining Huffman optimality with level-ordered layout
- **BitVector with rank/select** — the core primitive, supporting both naive (O(n)) and precomputed-block (O(1) amortized) rank/select
- **Prefix-sum / range quantile queries** — find the k-th smallest element in a range
- **Range frequency queries** — count occurrences of a symbol in a range [l, r)
- **Range next value** — find the smallest value ≥ threshold in a range
- **Interval symbols** — enumerate all distinct symbols in a range with their counts
- **JSON serialization** — save/load structures
- **Config files** — JSON/TOML/YAML configuration
- **Structured logging**
- **CLI** — argparse-based with multiple subcommands
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
2. **Blocked** — precomputes cumulative rank at block boundaries for O(1) rank with a small lookup table; select uses binary search over blocks + linear scan within

### Wavelet Tree

The sequence is recursively partitioned. At each node, a bitvector records which half of the alphabet each symbol belongs to. The left child holds symbols in the lower half, the right child holds the upper half. Queries descend the tree, using `rank` to map positions between levels.

### Wavelet Matrix

A flattened variant where all bitvectors at the same depth are concatenated. The sequence is stably partitioned level by level. This gives better cache behavior and simpler code while supporting the same operations.

### Huffman Shape

Instead of splitting the alphabet in half at each node, we build a Huffman tree over symbol frequencies. Frequent symbols end up near the root, giving O(H₀) average query time.

## Usage

### Python API

```python
from wavelet_tree import WaveletTree, WaveletMatrix

seq = "abracadabra"
wt = WaveletTree(seq)
print(wt.access(0))          # 'a'
print(wt.rank('a', 11))      # 5  (all 'a's)
print(wt.rank('b', 11))      # 2
print(wt.select('r', 1))     # 2  (first 'r' at index 2)
print(wt.range_count('a', 0, 5))  # 3  (a's in "abrac")
print(wt.range_quantile(0, 11, 0))  # 'a' (smallest symbol)
print(wt.interval_symbols(0, 11))   # {'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1}
```

### CLI

```bash
# Build and query
python -m wavelet_tree build "abracadabra" --rank a 11
python -m wavelet_tree build "abracadabra" --select r 1
python -m wavelet_tree build "abracadabra" --quantile 0 11 0

# Save / load
python -m wavelet_tree build "abracadabra" --save wt.json
python -m wavelet_tree load wt.json --rank a 5

# Interactive range queries
python -m wavelet_tree build "mississippi" --range-count s 0 11
python -m wavelet_tree build "mississippi" --interval-symbols 0 11
```

## Installation

```bash
pip install -e .
```

## License

MIT