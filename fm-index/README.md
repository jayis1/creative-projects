# FM-Index

A from-scratch **compressed full-text index** in pure Python — the FM-Index
(Ferragina–Manzini) built on the Burrows–Wheeler Transform, a wavelet tree,
the LF-mapping, and a sampled suffix array.  No external dependencies.

The FM-Index lets you answer pattern queries on a text in time
**O(|pattern| · log |Σ|)** while storing only the BWT (compressed in a
wavelet tree) plus a sparse suffix-array sample — no need to keep the full
text in memory.

## Features

| Capability | Method | Complexity |
|---|---|---|
| Count occurrences of a pattern | `count(pattern)` | O(m log σ) |
| Locate all occurrences (start positions) | `locate(pattern)` | O(m log σ + occ · log n / s) |
| Extract any substring by position | `extract(pos, len)` | O(len · log n / s) |
| Approximate search (Hamming distance) | `search_approx(pattern, k)` | exponential in k |
| Iterate distinct k-mers with counts | `iter_kmers(k)` | O(n) |
| BWT encode / decode | `bwt_encode`, `bwt_decode` | O(n) |

Where `m` = pattern length, `σ` = alphabet size, `n` = text length,
`occ` = number of matches, `s` = sample rate.

## How it works

### 1. Suffix array
The suffix array `SA` lists the starting positions of all suffixes of the
text in lexicographic order.  We build it with prefix-doubling
(Manber–Myers) in O(n log² n) time, or a naive O(n² log n) sort for
validation.

### 2. Burrows–Wheeler Transform
The BWT is the last column of the sorted-rotations matrix of the text.  We
construct it directly from the suffix array in O(n):

    BWT[i] = text[SA[i] - 1]   if SA[i] > 0
           = '$' (the sentinel) if SA[i] == 0

The text must end with a unique sentinel `$` (lexicographically smallest)
so the BWT is invertible.  `bwt_decode` reconstructs the text via the
LF-mapping in O(n).

### 3. Wavelet tree
The BWT string is stored in a balanced wavelet tree, giving rank/select
queries over the alphabet in O(log σ) time.  Each internal node holds a
`BitArray` with precomputed popcount superblocks for O(1) bit-level rank.

### 4. Backward search
`count(pattern)` uses the classic backward-search algorithm.  Starting
from the full SA range `[0, n)`, for each character `c` of the pattern
(processed right-to-left) it narrows the range:

    [l, r) ← [C[c] + rank(c, l), C[c] + rank(c, r))

where `C[c]` is the number of alphabet symbols lexicographically smaller
than `c` (precomputed once).  If the range becomes empty, the pattern
doesn't occur.

### 5. Locate via sampled suffix array
`locate(pattern)` recovers actual text positions.  The full suffix array is
sampled every `s` rows.  For each row in the match range we walk LF-mapping
backwards until we hit a sampled row, counting steps; the position is
`sampled_value + steps`.

### 6. Approximate search
`search_approx(pattern, k)` does recursive backward search with
backtracking, trying every alphabet symbol at each depth and accumulating
mismatches, pruning branches that exceed `k`.  Returns matches with their
mismatch counts.

## Installation

```bash
pip install -e .
```

## Usage

### Python API

```python
from fmindex import FMIndex

idx = FMIndex("banana", sample_rate=4)

idx.count("ana")          # 2
idx.locate("ana")         # [1, 3]
idx.locate("a")           # [1, 3, 5]
idx.extract(0, 4)         # "bana"
"ana" in idx              # True

# approximate search (≤ 1 mismatch)
for m in idx.search_approx("ana", max_mismatches=1):
    print(m.position, m.mismatches)

# iterate distinct k-mers
for kmer, count in idx.iter_kmers(2):
    print(kmer, count)    # an 2, ba 1, na 2
```

### Command line

```bash
# Build an index from a text file
fmindex build corpus.txt index.pkl -s 16

# Count / locate / search
fmindex count   index.pkl "the quick"
fmindex locate  index.pkl "the quick" --json
fmindex search  index.pkl "the quick" -c 20

# Approximate search
fmindex approx  index.pkl "the quikc" -m 2

# Extract a substring
fmindex extract index.pkl 1000 50

# List top 20 5-mers
fmindex kmers   index.pkl 5 --limit 20

# Benchmark
fmindex bench   index.pkl -q 5000 --min-k 6 --max-k 20
```

## Module layout

```
fmindex/
├── __init__.py        # package exports
├── suffix_array.py    # SA construction (prefix-doubling + naive)
├── bwt.py             # BWT encode/decode via LF-mapping
├── wavelet.py         # BitArray + balanced wavelet tree (rank/select/access)
├── index.py           # FMIndex: backward search, locate, extract, approx
└── cli.py             # argparse CLI with 8 subcommands
```

## License

MIT.