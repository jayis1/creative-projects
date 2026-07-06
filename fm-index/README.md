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
| Count multiple patterns at once | `count_multi(patterns)` | O(Σ mᵢ log σ) |
| Locate multiple patterns | `locate_multi(patterns)` | O(Σ mᵢ log σ + occᵢ · log n / s) |
| Count occurrences in a position range | `count_in_range(p, lo, hi)` | O(m log σ + occ) |
| Extract any substring by position | `extract(pos, len)` | O(len · log n / s) |
| Approximate search (Hamming distance) | `search_approx(pattern, k)` | exponential in k |
| Wildcard search (single-char `?`) | `search_wildcard(pattern)` | exponential in wildcards |
| LCP array (Kasai's algorithm) | `lcp_array()` | O(n) |
| Longest repeated substring | `longest_repeated_substring()` | O(n) |
| Iterate distinct k-mers with counts | `iter_kmers(k)` | O(n) |
| BWT encode / decode | `bwt_encode`, `bwt_decode` | O(n) |
| Serialization (JSON + binary) | `serialize.save_binary` / `load_binary` | — |
| Match analysis (clusters, coverage) | `analysis.cluster_matches` etc. | O(occ) |

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

### 3. Wavelet tree / wavelet matrix
The BWT string is stored in a balanced wavelet tree, giving rank/select
queries over the alphabet in O(log σ) time.  Each internal node holds a
`BitArray` with precomputed popcount superblocks for O(1) bit-level rank.

An alternative **wavelet matrix** backend (`WaveletMatrix`) is also
provided — a level-ordered structure with better memory locality.  Both
implement the same `access` / `rank` / `select` interface and produce
identical results (verified by property-based tests).

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

### 7. Wildcard search
`search_wildcard(pattern, wildcard='?')` works like approximate search but
at `?` positions it branches over all alphabet symbols without counting
mismatches — a true single-character wildcard.

### 8. LCP array and longest repeated substring
`lcp_array()` implements Kasai's O(n) algorithm.  The longest repeated
substring is found by taking the maximum LCP value (excluding the
sentinel) and reading the corresponding suffix.

## Installation

```bash
pip install -e .
```

## Usage

### Python API

```python
from fmindex import FMIndex

idx = FMIndex("mississippi", sample_rate=2)

idx.count("iss")             # 2
idx.locate("iss")            # [1, 4]
idx.extract(0, 4)            # "miss"
"iss" in idx                 # True

# wildcard search
for m in idx.search_wildcard("??ss"):
    print(m.position)       # 0, 3

# approximate search (≤ 1 mismatch)
for m in idx.search_approx("iss", max_mismatches=1):
    print(m.position, m.mismatches)

# multi-pattern
print(idx.count_multi(["iss", "ssi", "xyz"]))
# {'iss': 2, 'ssi': 2, 'xyz': 0}

# count in a range
idx.count_in_range("iss", 2, 6)  # 1

# LCP array and longest repeat
print(idx.lcp_array())              # Kasai's algorithm
print(idx.longest_repeated_substring())  # ('issi', 4)

# iterate distinct k-mers
for kmer, count in idx.iter_kmers(2):
    print(kmer, count)

# serialization
from fmindex import serialize
serialize.save_binary(idx, "index.bin")
idx2 = serialize.load_binary("index.bin")
serialize.save_json(idx, "index.json")
idx3 = serialize.load_json("index.json")

# match analysis
from fmindex import analysis
pos = idx.locate("iss")
print(analysis.coverage_stats(pos, 3, len(idx.text)))
clusters = analysis.cluster_matches(pos, gap=0)
```

### Wavelet matrix (alternative backend)

```python
from fmindex import WaveletMatrix, WaveletTree

data = [ord(c) for c in "mississippi"]
wt = WaveletTree(data)
wm = WaveletMatrix(data)

# identical results, different internal structure
assert wt.rank(ord('s'), 5) == wm.rank(ord('s'), 5)
assert wt.select(ord('s'), 2) == wm.select(ord('s'), 2)
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

# Wildcard search
fmindex wildcard index.pkl "the ?uick"

# Multi-pattern count
fmindex multi   index.pkl "the quick" "fox" "dog" --json
fmindex multi   index.pkl -f patterns.txt

# Extract a substring
fmindex extract index.pkl 1000 50

# List top 20 5-mers
fmindex kmers   index.pkl 5 --limit 20

# LCP array
fmindex lcp     index.pkl --limit 10

# Longest repeated substring
fmindex longest-repeat index.pkl

# Index statistics
fmindex info    index.pkl

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
├── wavelet_matrix.py  # level-ordered wavelet matrix (alternative backend)
├── index.py           # FMIndex: backward search, locate, extract, approx, wildcard, LCP
├── serialize.py        # JSON + binary serialization
├── analysis.py         # match clustering & coverage analysis
└── cli.py             # argparse CLI with 13 subcommands
```

## License

MIT.