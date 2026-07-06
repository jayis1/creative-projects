# FM-Index

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 77](https://img.shields.io/badge/tests-77%20passing-brightgreen.svg)](#testing)
[![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-orange.svg)](#changelog)

> A from-scratch **compressed full-text index** in pure Python — the
> FM-Index (Ferragina–Manzini) built on the Burrows–Wheeler Transform,
> wavelet tree/matrix, LF-mapping, and a sampled suffix array. No
> external dependencies.

The FM-Index answers pattern queries on a text in time
**O(|pattern| · log |Σ|)** while storing only the BWT (compressed in a
wavelet tree) plus a sparse suffix-array sample — no need to keep the
full text in memory for queries.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [Command Line](#command-line)
  - [Examples](#examples)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Visualization](#visualization)
- [Testing](#testing)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Capability | Method | Complexity |
|---|---|---|
| Count occurrences of a pattern | `count(pattern)` | O(m log σ) |
| Locate all occurrences (start positions) | `locate(pattern)` | O(m log σ + occ · log n / s) |
| Batch locate multiple patterns | `batch_locate(patterns)` | O(Σ mᵢ log σ) |
| First / last occurrence | `first_occurrence` / `last_occurrence` | O(m log σ + occ) |
| Count multiple patterns at once | `count_multi(patterns)` | O(Σ mᵢ log σ) |
| Count occurrences in a position range | `count_in_range(p, lo, hi)` | O(m log σ + occ) |
| Extract any substring by position | `extract(pos, len)` | O(len · log n / s) |
| Approximate search (Hamming distance) | `search_approx(pattern, k)` | exponential in k |
| Wildcard search (single-char `?`) | `search_wildcard(pattern)` | exponential in wildcards |
| Regex search (supports `.`) | `searchers.regex_search()` | exponential in `.` |
| LCP array (Kasai's algorithm) | `lcp_array()` | O(n) |
| Longest repeated substring | `longest_repeated_substring()` | O(n) |
| Find all repeated substrings | `searchers.find_all_repeats()` | O(n) |
| Top-k most frequent k-mers | `searchers.top_k_frequent_kmers()` | O(n) |
| Maximal unique matches (MUMs) | `searchers.find_maximal_unique_matches()` | O(q · log n) |
| Minimal unique substrings | `searchers.find_minimal_unique_substrings()` | O(n) |
| Iterate distinct k-mers with counts | `iter_kmers(k)` | O(n) |
| BWT encode / decode | `bwt_encode`, `bwt_decode` | O(n) |
| Run-length encoded BWT | `rle.RLEString` | O(log r) rank |
| Text statistics (entropy, Gini) | `text_stats.compute_statistics()` | O(n) |
| ASCII visualizations | `visualize.*` | O(n) |
| Serialization (JSON + binary) | `serialize.save_binary` / `load_binary` | — |
| Match analysis (clusters, coverage) | `analysis.cluster_matches` etc. | O(occ) |
| Memory estimation | `estimate_memory_bytes()` | O(1) |
| Configuration (YAML/JSON/TOML) | `config.load_config()` | — |
| Logging & timing | `logging_utils.log_time()` | — |

Where `m` = pattern length, `σ` = alphabet size, `n` = text length,
`occ` = number of matches, `s` = sample rate, `r` = number of BWT runs.

### Two Wavelet Backends

The FM-Index supports two interchangeable backends for the rank/select
structure over the BWT:

| Backend | Module | Strengths |
|---|---|---|
| `wavelet_tree` | `wavelet.py` | Tree-structured, classic implementation |
| `wavelet_matrix` | `wavelet_matrix.py` | Level-ordered, better memory locality |

Both produce identical results (verified by property-based tests). Choose
via the `backend` parameter:

```python
idx = FMIndex(text, backend="wavelet_matrix")
```

---

## Installation

### From source (development)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/fm-index
pip install -e .
```

### Dependencies

- **Python 3.10+** (uses `match` statements, `tomllib`, modern type hints)
- **No runtime dependencies** — pure Python standard library only
- Optional: `pyyaml` for YAML config files (`pip install pyyaml`)
- Development: `pytest`, `pytest-cov` (`pip install pytest pytest-cov`)

### Verify installation

```bash
fmindex config --generate /tmp/test_config.json
python3 -c "from fmindex import FMIndex; print(FMIndex('hello').count('l'))"
# Output: 2
```

---

## Quick Start

```python
from fmindex import FMIndex

idx = FMIndex("mississippi")

idx.count("iss")              # 2
idx.locate("iss")             # [1, 4]
idx.extract(0, 4)             # "miss"
"iss" in idx                  # True
idx.first_occurrence("iss")   # 1
idx.last_occurrence("iss")    # 4
```

---

## Usage

### Python API

#### Basic search

```python
from fmindex import FMIndex

idx = FMIndex("mississippi", sample_rate=2)

# Count and locate
idx.count("iss")             # 2
idx.locate("iss")            # [1, 4]
idx.extract(0, 4)            # "miss"
"iss" in idx                 # True

# First / last occurrence
idx.first_occurrence("iss")  # 1
idx.last_occurrence("iss")   # 4

# Batch locate
idx.batch_locate(["iss", "ss", "xyz"])
# {'iss': [1, 4], 'ss': [2, 5], 'xyz': []}
```

#### Approximate and wildcard search

```python
# Approximate search (≤ 1 mismatch)
for m in idx.search_approx("iss", max_mismatches=1):
    print(m.position, m.mismatches)

# Wildcard search (? matches any char)
for m in idx.search_wildcard("??ss"):
    print(m.position)       # 0, 3
```

#### Advanced search (searchers module)

```python
from fmindex import searchers

# Regex search (supports '.' for any char)
matches = searchers.regex_search(idx, ".ss")
# positions: [1, 4]

# Find all repeated substrings
for sub, count in searchers.find_all_repeats(idx, min_len=2):
    print(f"{count}x {sub!r}")

# Top-k most frequent k-mers
searchers.top_k_frequent_kmers(idx, k=2, top=5)

# Maximal unique matches vs a query
mums = searchers.find_maximal_unique_matches(idx, "miss", min_len=2)

# Minimal unique substrings at each position
mus = searchers.find_minimal_unique_substrings(idx, min_len=1, max_len=10)
```

#### Text statistics

```python
from fmindex import text_stats

stats = text_stats.compute_statistics(idx)
print(stats.summary())
# Text length        : 11
# Alphabet size      : 5
# Shannon entropy    : 1.8231 bits/char
# Max entropy        : 2.0000 bits/char
# Redundancy         : 8.85%
# Gini coefficient   : 0.2500
# BWT runs           : 9
# BWT avg run length : 1.33
```

#### LCP array and longest repeat

```python
idx.lcp_array()                    # Kasai's algorithm
idx.longest_repeated_substring()   # ('issi', 4)
```

#### Serialization

```python
from fmindex import serialize

# Binary format (compact, zlib-compressed)
serialize.save_binary(idx, "index.bin")
idx2 = serialize.load_binary("index.bin")

# JSON format (human-readable, zlib-compressed)
serialize.save_json(idx, "index.json")
idx3 = serialize.load_json("index.json")
```

#### Match analysis

```python
from fmindex import analysis

pos = idx.locate("iss")
analysis.coverage_stats(pos, 3, len(idx.text))
clusters = analysis.cluster_matches(pos, gap=0)
```

#### Run-length encoding

```python
from fmindex import rle

# RLE of the BWT (BWT tends to have long runs)
rle_str = rle.RLEString(idx.bwt)
print(f"Compression ratio: {rle_str.compression_ratio():.2f}x")
print(f"Runs: {rle_str.num_runs} / {rle_str.n} chars")

# RLE string supports access and rank
rle_str.access(0)            # first char
rle_str.rank('i', 5)         # count of 'i' in first 5 positions
```

### Command Line

The CLI has **20 subcommands**:

```bash
# Build an index from a text file
fmindex build corpus.txt index.bin -s 16
fmindex build corpus.txt index.bin --backend wavelet_matrix
fmindex build corpus.txt index.bin --config fm.yaml

# Count / locate / search
fmindex count   index.bin "the quick"
fmindex locate  index.bin "the quick" --json
fmindex search  index.bin "the quick" -c 20

# Approximate search
fmindex approx  index.bin "the quikc" -m 2

# Wildcard search
fmindex wildcard index.bin "the ?uick"

# Regex search (supports '.')
fmindex regex index.bin "the .uick"

# Multi-pattern count
fmindex multi   index.bin "the quick" "fox" "dog" --json
fmindex multi   index.bin -f patterns.txt

# Extract a substring
fmindex extract index.bin 1000 50

# List top 20 5-mers
fmindex kmers   index.bin 5 --limit 20

# LCP array
fmindex lcp     index.bin --limit 10

# Longest repeated substring
fmindex longest-repeat index.bin

# Find all repeated substrings
fmindex repeats index.bin --min-len 3 --limit 20

# Find maximal unique matches
fmindex mum index.bin "query string" --min-len 5

# Detailed text statistics
fmindex stats   index.bin

# ASCII visualizations
fmindex visualize index.bin bwt --rows 10
fmindex visualize index.bin sa --rows 10
fmindex visualize index.bin lcp --width 60
fmindex visualize index.bin matches --pattern "the" --context 5
fmindex visualize index.bin coverage --pattern "the" --width 70
fmindex visualize index.bin alphabet --width 50

# Configuration
fmindex config --generate fm.json
fmindex config --show fm.json

# Index statistics
fmindex info    index.bin

# Benchmark
fmindex bench   index.bin -q 5000 --min-k 6 --max-k 20

# Logging
fmindex --log-level INFO count index.bin "pattern"
fmindex --log-file fm.log build corpus.txt index.bin
```

### Examples

Five runnable example scripts are in `examples/`:

| Script | Demonstrates |
|---|---|
| `basic_usage.py` | Build, count, locate, extract, serialize |
| `approx_wildcard.py` | Approximate (Hamming) and wildcard search |
| `advanced_search.py` | Regex, repeats, MUMs, minimal unique substrings |
| `stats_and_viz.py` | Text statistics, ASCII visualizations, match analysis |
| `backend_and_config.py` | Wavelet matrix backend, RLE compression, config system |

```bash
python3 examples/basic_usage.py
python3 examples/advanced_search.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     FMIndex                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Suffix Array │  │     BWT      │  │  C Array   │ │
│  │  (sampled)   │  │  (in wavelet)│  │ (cum. count)│ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
│         │                │                │          │
│         │     ┌──────────┴──────────┐     │          │
│         │     │  Wavelet Tree/Matrix │     │          │
│         │     │  (rank/select/access)│     │          │
│         │     └─────────────────────┘     │          │
│         │              │                  │          │
│         └──────────────┼──────────────────┘          │
│                        │                             │
│              ┌─────────┴──────────┐                  │
│              │   LF-Mapping       │                  │
│              │   Backward Search  │                  │
│              └────────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

### How it works

#### 1. Suffix array
The suffix array `SA` lists the starting positions of all suffixes of the
text in lexicographic order. Built with prefix-doubling (Manber–Myers) in
O(n log² n) time, or a naive O(n² log n) sort for validation.

#### 2. Burrows–Wheeler Transform
The BWT is the last column of the sorted-rotations matrix, constructed
from the suffix array in O(n):

```
BWT[i] = text[SA[i] - 1]   if SA[i] > 0
       = '$' (sentinel)     if SA[i] == 0
```

The text must end with a unique sentinel `$` (lexicographically smallest)
so the BWT is invertible. `bwt_decode` reconstructs the text via the
LF-mapping in O(n).

#### 3. Wavelet tree / wavelet matrix
The BWT string is stored in a wavelet tree (or matrix), giving
rank/select queries over the alphabet in O(log σ) time. Each internal
node holds a `BitArray` with precomputed popcount superblocks for O(1)
bit-level rank.

The **wavelet matrix** is a level-ordered alternative with better memory
locality — each level is a contiguous bit array, and queries descend
log(σ) levels with a single array lookup per level.

#### 4. Backward search
`count(pattern)` uses the classic backward-search algorithm. Starting
from the full SA range `[0, n)`, for each character `c` of the pattern
(processed right-to-left) it narrows the range:

```
[l, r) ← [C[c] + rank(c, l), C[c] + rank(c, r))
```

where `C[c]` is the number of alphabet symbols lexicographically smaller
than `c`.

#### 5. Locate via sampled suffix array
`locate(pattern)` recovers actual text positions. The full suffix array
is sampled every `s` rows. For each row in the match range, walk
LF-mapping backwards until hitting a sampled row, counting steps; the
position is `sampled_value + steps`.

#### 6. Approximate search
`search_approx(pattern, k)` does recursive backward search with
backtracking, trying every alphabet symbol at each depth and accumulating
mismatches, pruning branches that exceed `k`.

#### 7. Run-length encoding
The `rle` module provides RLE encoding of the BWT. Since the BWT tends
to produce long runs of identical characters, RLE can significantly
reduce storage while still supporting O(log r) rank queries.

### Module layout

```
fmindex/
├── __init__.py          # package exports
├── suffix_array.py      # SA construction (prefix-doubling + naive)
├── bwt.py               # BWT encode/decode via LF-mapping
├── wavelet.py           # BitArray + balanced wavelet tree (rank/select/access)
├── wavelet_matrix.py    # level-ordered wavelet matrix (alternative backend)
├── index.py             # FMIndex: search, locate, extract, approx, wildcard, LCP
├── searchers.py         # high-level search (regex, MUMs, repeats, top-k)
├── rle.py               # run-length encoding with rank/access
├── serialize.py         # JSON + binary serialization
├── analysis.py          # match clustering & coverage analysis
├── text_stats.py        # Shannon entropy, Gini coefficient, BWT run stats
├── visualize.py         # ASCII visualizations (BWT matrix, LCP skyline, etc.)
├── config.py            # YAML/JSON/TOML configuration
├── logging_utils.py     # logging setup and timing context manager
├── errors.py            # exception hierarchy
└── cli.py               # argparse CLI with 20 subcommands

tests/
├── test_bugs.py             # original bug-hunt regression tests (9)
├── test_comprehensive.py    # property-based tests (10)
├── test_rle.py              # RLE module tests (10)
├── test_config.py           # config module tests (8)
├── test_searchers.py        # searchers module tests (13)
├── test_text_stats.py       # text statistics tests (7)
├── test_visualize.py        # visualization tests (8)
└── test_new_features.py     # backend/batch/memory tests (12)

examples/
├── basic_usage.py
├── approx_wildcard.py
├── advanced_search.py
├── stats_and_viz.py
└── backend_and_config.py
```

---

## Configuration

The FM-Index supports configuration via YAML, JSON, or TOML files.

```yaml
# fm.yaml
sample_rate: 32
backend: wavelet_matrix
use_naive_sa: false
query_defaults:
  max_mismatches: 2
  context: 20
  wildcard_char: "?"
  kmer_k: 5
serialization:
  format: binary
  compress_level: 9
logging:
  level: INFO
  file: fmindex.log
```

```bash
# Generate a default config
fmindex config --generate fm.json

# Build using a config
fmindex build corpus.txt index.bin --config fm.json
```

```python
from fmindex import config

cfg = config.load_config("fm.yaml")
idx = FMIndex(text, sample_rate=cfg.sample_rate, backend=cfg.backend)
```

---

## Visualization

The `visualize` module produces ASCII art for understanding index internals:

```
 SA  rotation      BWT
───  ────────────  ──
 11  $mississippi  i
 10  i$mississipp  p
  7  ippi$mississ  s
  4  issippi$miss  s
  1  ississippi$m  m
```

```
Matches for 'iss' (2 found):

     1 │ mississ
       │  ^^^
     4 │ ississipp
       │    ^^^
```

```
     i │██████████████████████████████████████████████████ 4
     s │██████████████████████████████████████████████████ 4
     p │█████████████████████████ 2
     m │████████████ 1
```

Access via the API or CLI:

```python
from fmindex import visualize as viz

print(viz.visualize_bwt_matrix(idx))
print(viz.visualize_lcp_skyline(idx))
print(viz.visualize_matches(idx, "iss"))
print(viz.visualize_coverage(idx, "ss"))
print(viz.visualize_alphabet_distribution(idx))
```

---

## Testing

77 tests covering all modules:

```bash
# Run all tests
python3 -m pytest tests/ -v

# With coverage
python3 -m pytest tests/ --cov=fmindex --cov-report=term-missing

# Run specific module
python3 -m pytest tests/test_rle.py -v
```

| Test file | Tests | Coverage |
|---|---|---|
| `test_bugs.py` | 9 | Original bug-hunt regressions |
| `test_comprehensive.py` | 10 | Property-based randomized tests |
| `test_rle.py` | 10 | RLE encode/decode/rank/access |
| `test_config.py` | 8 | Config loading/validation/round-trip |
| `test_searchers.py` | 13 | Regex, repeats, MUMs, top-k |
| `test_text_stats.py` | 7 | Entropy, Gini, frequency stats |
| `test_visualize.py` | 8 | All visualization functions |
| `test_new_features.py` | 12 | Backend parity, batch, memory |

CI runs on Python 3.10, 3.11, 3.12, and 3.13 via GitHub Actions.

---

## Changelog

### v2.0.0 (2026-07-06) — Comprehensive Improvement

**New modules:**
- `searchers.py` — high-level search: regex (`.` wildcard), find all
  repeats, top-k frequent k-mers, maximal unique matches (MUMs), minimal
  unique substrings
- `rle.py` — run-length encoding with O(log r) rank/access for BWT
  compression analysis
- `text_stats.py` — Shannon entropy, max entropy, redundancy, Gini
  coefficient, BWT run statistics, most/least frequent characters
- `visualize.py` — ASCII visualizations: BWT matrix, suffix array, LCP
  skyline, match positions with context, coverage bars, alphabet
  distribution
- `config.py` — YAML/JSON/TOML configuration with validation
- `logging_utils.py` — structured logging with timing context manager
- `errors.py` — exception hierarchy (ConstructionError,
  SerializationError, QueryError, ConfigError)

**New FMIndex features:**
- `backend` parameter — choose between `wavelet_tree` and
  `wavelet_matrix` (both produce identical results)
- `batch_locate()` — locate multiple patterns with deduplication
- `first_occurrence()` / `last_occurrence()` — convenience methods
- `estimate_memory_bytes()` — approximate memory footprint estimation
- Input validation on `count()` (type checking)
- Logging integration via `log_time()` context manager

**CLI improvements:**
- 7 new subcommands: `stats`, `regex`, `repeats`, `mum`, `visualize`,
  `config`, (plus enhanced `build` with `--backend`, `--format`,
  `--config` flags)
- Auto-detecting index format loader (pickle/binary/JSON)
- Global `--log-level` and `--log-file` options
- Error handling with user-friendly messages

**Testing & CI:**
- 58 new tests (77 total, all passing)
- GitHub Actions CI for Python 3.10–3.13
- 5 runnable example scripts in `examples/`

**Documentation:**
- Dramatically expanded README with TOC, badges, architecture diagram
- CONTRIBUTING.md with development setup and guidelines
- LICENSE (MIT)

### v1.1.0 — Bug Hunt
- Fixed `extract()` off-by-one (BWT gives char before suffix start)
- Removed dead code in `search_approx()` and `save_binary()`
- Fixed `BitArray.count_ones()` crash on empty array
- 19 regression tests added

### v1.0.0 — Initial Release
- FM-Index with BWT, wavelet tree, backward search, locate, extract
- Approximate search, wildcard search, multi-pattern, LCP, k-mers
- Wavelet matrix backend
- JSON + binary serialization
- Match analysis (clustering, coverage)
- CLI with 13 subcommands

---

## Known Issues (Resolved)

The following bugs were found during the bug-hunt phase and fixed:

1. **`extract()` off-by-one** — The BWT character at row `r` is
   `text[SA[r] - 1]` (the character *preceding* the suffix), not the
   suffix's first character. **Fix:** start at the row for
   `SA = pos + length` (one past the last desired character).
   *(regression test: `test_extract_randomized`,
   `test_extract_boundaries`)*

2. **Dead code in `search_approx()`** — A forward-search `recurse`
   function was defined but never called. Removed.

3. **Dead/misleading code in `serialize.save_binary()`** — A leftover
   `alpha_bytes` line used the wrong struct format. Removed.

4. **`BitArray.count_ones()` on empty array** — Would raise `IndexError`.
   Added a guard for empty `_ranks`. *(regression test:
   `test_bitarray_empty`)*

---

## Roadmap

- [ ] DC3/SA-IS linear-time suffix array construction for large texts
- [ ] Compressed suffix array (CSA) for reduced memory
- [ ] Bidirectional BWT for gapped pattern matching
- [ ] Edit-distance approximate search (not just Hamming)
- [ ] Multi-text FM-Index (collection of documents with document IDs)
- [ ] MUM finder for genome comparison (two-text version)
- [ ] Cython/C extension for performance-critical paths
- [ ] WebAssembly build for browser-based search
- [ ] Unicode-aware text handling (currently operates on ord() values)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
and guidelines.

---

## License

[MIT](LICENSE)