<div align="center">

# diff-merge

A from-scratch text diff, patch, and three-way merge toolkit

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-116%20passing-brightgreen)
![Version](https://img.shields.io/badge/version-3.0.0-orange)
![Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-success)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Architecture](#architecture)
- [Algorithms](#algorithms)
- [Recent Improvements (v3.0)](#recent-improvements-v30)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [License](#license)

## Overview

**diff-merge** is a pure-Python text diff/patch/merge toolkit with **zero
external runtime dependencies** (stdlib only). It implements four diff
algorithms from scratch, three output formats, patch parsing and
application, three-way merge with conflict markers, side-by-side visual
diff, HTML diff output, directory-level diff, and more.

## Features

### Diff Algorithms (4)
| Algorithm | Complexity | Description |
|----------|-----------|-------------|
| **Myers** | O(ND) | Classic edit-graph shortest-edit-script with backtracking (Eugene W. Myers, 1986) |
| **LCS** | O(NM) | Dynamic programming with backtracking — reference implementation |
| **Patience** | O(N log N) | Bram Cohen's algorithm using unique common lines as anchors |
| **Histogram** | O(N log N) | Eclipse JGit enhancement using least-frequency line matching |

### Output Formats (5)
- **Unified diff** — `@@ -start,count +start,count @@` with `+`/`-`/` ` prefixes
- **Context diff** — RCS-style with `***`/`---` headers
- **Normal diff** — classic `Nd`/`Na`/`Nc` commands with `<`/`>` content
- **Side-by-side** — two-column visual comparison with line numbers
- **HTML** — self-contained colourised HTML document for web/email

### Core Capabilities
- **Patch parsing & application** — unified-diff patches with fuzz tolerance, offset search, reject files, and reverse (undo) support
- **Three-way merge (diff3)** — merge two versions against a common ancestor with conflict markers
- **Intra-line (word-level) diff** — ANSI colour or bracket highlighting
- **Diff statistics (diffstat)** — additions, deletions, net change, ASCII histogram
- **Directory diff** — recursively compare two directory trees
- **Diff optimizer** — shrink REPLACE blocks by pulling common lines into context
- **Binary file detection** — null-byte + non-text-ratio heuristic
- **Whitespace & blank-line filtering**
- **Configuration system** — JSON / TOML / YAML
- **Logging** — configurable via `--verbose`/`--log-level` or env var
- **CLI tool** — 11 subcommands

## Installation

```bash
# From the repo
cd creative-projects/diff-merge
pip install -e .

# Or use directly without installation
python3 -m diff_merge.cli --help
```

### Requirements
- Python 3.10+ (uses `tomllib`, `match` statements, `type | type` unions)
- No external runtime dependencies
- `pytest` for running tests (optional, dev-only)

## Quick Start

```bash
# Unified diff (default)
diff-merge diff old.txt new.txt

# Side-by-side with colour
diff-merge sidebyside old.txt new.txt --color --width 100

# Generate HTML diff
diff-merge html old.txt new.txt --output review.html

# Apply a patch
cat patch.diff | diff-merge patch source.txt

# Three-way merge
diff-merge merge base.txt ours.txt theirs.txt

# Compare directories
diff-merge dirdiff v1/ v2/

# Word-level inline diff
diff-merge inline file1.txt file2.txt --color
```

## CLI Reference

```
diff-merge [--verbose] [--log-level LEVEL] COMMAND ...

Commands:
  diff         Compute diff between two files
  patch        Apply a patch to a file
  merge        Three-way merge
  lcs          Print longest common subsequence
  stat         Show diff statistics
  reverse      Generate reverse (undo) diff
  inline       Word-level inline diff
  sidebyside   Side-by-side visual diff
  html         Generate HTML diff output
  dirdiff      Compare two directories
  config       Show/save/load configuration
```

### diff

```bash
diff-merge diff OLD NEW [options]

  --format {unified,context,normal}   Output format (default: unified)
  --algorithm {myers,patience,histogram,lcs}  Diff algorithm (default: myers)
  --context N          Lines of context (default: 3)
  --color              Colorized output
  --ignore-whitespace  Ignore whitespace changes
  --ignore-blank-lines  Ignore blank line changes
  --config FILE        Load config from file
```

### sidebyside

```bash
diff-merge sidebyside FILE1 FILE2 [options]

  --algorithm ALGO   Diff algorithm (default: myers)
  --width N          Total output width (default: 80)
  --color            ANSI colour output
```

### html

```bash
diff-merge html FILE1 FILE2 [options]

  --algorithm ALGO   Diff algorithm
  --output FILE      Output HTML file (default: stdout)
  --no-inline        Disable word-level inline diff
```

### dirdiff

```bash
diff-merge dirdiff DIR_A DIR_B
```

### merge

```bash
diff-merge merge BASE OURS THEIRS [--marker-size N]
```

Exit code 0 = clean merge, 1 = conflicts present.

## Python API

```python
from diff_merge import (
    # Algorithms
    myers_diff, patience_diff, histogram_diff, lcs_diff,
    # Formats
    unified_diff, context_diff, normal_diff,
    # Patch
    parse_unified_diff, apply_patch,
    # Merge
    three_way_merge,
    # Inline
    word_diff, highlight_inline,
    # Stats
    compute_diffstat,
    # Side-by-side
    side_by_side,
    # HTML
    html_diff_document,
    # Directory diff
    diff_directories,
    # Optimizer
    optimize_diff,
    # Config
    Config, load_config, save_config,
    # Logging
    get_logger, setup_logging,
)

a = ["line1\n", "line2\n", "line3\n"]
b = ["line1\n", "line2 modified\n", "line3\n"]

# --- Diff ---
ops = myers_diff(a, b)          # or patience_diff, histogram_diff, lcs_diff

# --- Unified diff output ---
patch = unified_diff(a, b, fromfile="old", tofile="new")

# --- Patch roundtrip ---
hunks = parse_unified_diff(patch)
result = apply_patch(a, hunks)
assert result.patched == b

# --- Side-by-side ---
lines = side_by_side(a, b, width=80, color=True)

# --- HTML diff ---
doc = html_diff_document(a, b, fromfile="v1", tofile="v2")
# Write to file: open("diff.html", "w").write(doc)

# --- Directory diff ---
result = diff_directories("v1/", "v2/")
print(result.summary())  # "2 added, 1 removed, 3 modified, ..."

# --- Three-way merge ---
base = ["line1\n", "line2\n", "line3\n"]
ours = ["line1\n", "line2 ours\n", "line3\n"]
theirs = ["line1\n", "line2 theirs\n", "line3\n"]
merge = three_way_merge(base, ours, theirs)
# merge.clean == False (conflict on line 2)

# --- Diff optimizer ---
ops = myers_diff(["a", "b", "c"], ["a", "B", "c"])
optimized = optimize_diff(ops, ["a", "b", "c"], ["a", "B", "c"])

# --- Word-level inline diff ---
ha, hb = highlight_inline("hello world", "hello earth", use_color=False)
# ha = "hello [-world-]", hb = "hello [+earth+]"

# --- Statistics ---
stat = compute_diffstat(ops, a, b)
print(stat.summary())    # "1 insertion(s), 1 deletion(s), 2 unchanged"
print(stat.histogram())  # "+- (1+/1-)"

# --- Configuration ---
config = Config(algorithm="patience", context=5, color=True)
save_config(config, "myconfig.json")
loaded = load_config("myconfig.json")
```

## Architecture

```
diff_merge/
├── __init__.py         — Package exports (50+ symbols)
├── myers.py            — Myers O(ND) diff with backtracking
├── lcs.py              — LCS dynamic programming diff
├── patience.py         — Patience diff (Bram Cohen)
├── histogram.py        — Histogram diff (Eclipse JGit)
├── format.py           — Unified / context / normal diff formatters
├── sidebyside.py       — Side-by-side visual diff renderer  ★ new
├── htmlout.py          — HTML diff output with inline CSS    ★ new
├── dirdiff.py          — Recursive directory comparison      ★ new
├── optimizer.py        — Diff optimisation passes            ★ new
├── patch.py            — Patch parser and applier
├── merge.py            — Three-way merge (diff3)
├── inline.py           — Word-level intra-line diff
├── stat.py             — Diff statistics (diffstat)
├── config.py           — Configuration system (JSON/TOML/YAML)
├── logging_config.py   — Logging configuration               ★ new
├── utils.py            — Preprocessing, binary detection
├── cli.py              — CLI (11 subcommands)
├── examples/           — Usage examples
│   ├── basic_diff.py
│   ├── patch_demo.py
│   ├── three_way_merge.py
│   ├── side_by_side_demo.py    ★ new
│   ├── html_diff_demo.py       ★ new
│   └── dirdiff_demo.py         ★ new
└── tests/              — 116 tests across 5 files
    ├── test_diff_merge.py
    ├── test_enhanced.py
    ├── test_bug_hunt.py
    ├── test_bug_hunt2.py
    └── test_improvements.py     ★ new (32 tests)
```

## Algorithms

### Myers Diff

The Myers algorithm finds the shortest edit script between two sequences
by exploring an edit graph. It works on diagonals where `k = x - y`, and
for each edit distance `d`, computes the furthest-reaching point on each
diagonal. The algorithm is O(ND) where N is total sequence length and D is
the edit distance.

This implementation stores the V array at each edit distance level, then
backtracks through the trace to reconstruct the path from `(N, M)` to
`(0, 0)`, following snakes (diagonal moves through equal elements) and
edit moves (right = delete, down = insert).

### Patience Diff

Patience diff finds unique lines that appear exactly once in each
sequence, uses them as anchor points, then recursively diffs the
segments between anchors. This produces more human-readable diffs for
code with clear function/class boundaries. When no unique common lines
exist in a segment, it falls back to LCS diff.

### Histogram Diff

Histogram diff enhances patience by using the *least frequent* common
lines as anchors rather than only unique lines. When all lines are
non-unique, it picks the rarest lines (minimum combined frequency in
both sequences) and recurses. This improves diff quality for code with
repeated boilerplate.

### Three-Way Merge (diff3)

1. Compute diff(base → ours) and diff(base → theirs)
2. Find changed regions in each diff
3. Merge overlapping change regions from both sides
4. For each region:
   - Both sides identical → take either (clean)
   - Only one side changed → take that side (clean)
   - Both sides changed differently → conflict

### Diff Optimizer

Post-processes diff ops to improve readability:
- **Common edge extraction** — shrinks REPLACE blocks by pulling
  identical prefix/suffix lines into EQUAL context
- **Whitespace optimisation** — optionally converts whitespace-only
  changes to EQUAL

## Recent Improvements (v3.0)

> ★ = added in this improvement pass

| Feature | Description |
|---------|-------------|
| ★ Side-by-side diff | Two-column visual comparison with line numbers and colour |
| ★ HTML diff output | Self-contained HTML document with CSS, inline word-level diff |
| ★ Directory diff | Recursive directory tree comparison with per-file diffstats |
| ★ Diff optimizer | Post-processing passes to improve diff readability |
| ★ Logging | Configurable logging via `--verbose`, `--log-level`, or env var |
| ★ CLI expansion | 3 new subcommands (sidebyside, html, dirdiff) — 11 total |
| ★ CI configuration | GitHub Actions workflow for Python 3.10–3.12 |
| ★ CONTRIBUTING.md | Developer guide for contributing |
| ★ LICENSE | MIT license file |
| ★ .gitignore | Ignore build artifacts |
| ★ 32 new tests | Comprehensive tests for all new features (116 total) |
| ★ Improved pyproject.toml | Updated metadata, classifiers, dev extras |
| ★ 3 new examples | side_by_side, html_diff, dirdiff demo scripts |

## Known Issues (Resolved)

The following bugs were identified and fixed during the bug hunt:

1. **Myers backtracking negative indices** — Rewrote with classic O(ND) trace backtracking
2. **Patience/Histogram `_shift_ops` double-shifting** — Fixed count parameter
3. **Three-way merge infinite loop** — Complete rewrite using diff3 algorithm
4. **Merge conflict markers missing newlines** — Added line-ending detection
5. **Normal diff INSERT line numbers** — Fixed 0-based to 1-based conversion
6. **`is_binary` performance** — Set-based lookup + 8000-byte sampling
7. **Unified diff empty old file header** — Verified correct `-0,0` behavior
8. **Patch parser "No newline" markers** — Verified correct skip behavior
9. **Patch multi-hunk cumulative offset** — Verified correct behavior
10. **Merge overlapping vs adjacent regions** — Fixed to only merge truly overlapping regions

## Testing

```bash
# Run all 116 tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_improvements.py -v

# Run with coverage
python3 -m pytest tests/ --cov=diff_merge --cov-report=term-missing
```

Test coverage:
- Basic diffing (Myers, LCS, Patience, Histogram)
- Edge cases (empty inputs, identical inputs, completely different inputs)
- Large-scale random stress testing
- Unified/context/normal/side-by-side/HTML format output
- Patch roundtrip (generate → parse → apply → verify)
- Patch with offset and fuzz tolerance, reverse patch
- Three-way merge (clean, conflict, same change, insertions, empty base)
- Word-level inline diff highlighting
- Diff statistics, configuration system, binary detection
- Directory diff (added, removed, modified, nested, empty)
- Diff optimizer (common edges, whitespace, idempotency)
- Logging configuration

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
and pull request guidelines.

## Roadmap

- [ ] Git blame integration
- [ ] Semantic diff (AST-aware for Python/JS)
- [ ] Diff3 with minimal-conflict region selection
- [ ] Patch format detection (auto-detect unified vs context vs git)
- [ ] Configurable line-ending normalisation (CRLF/LF)
- [ ] Streaming diff for very large files
- [ ] JSON diff (structured data comparison)
- [ ] Performance: Myers middle-snake for O(N) space
- [ ] Colour theme configuration for HTML output
- [ ] Diff3 merge with conflict resolution strategies

## Changelog

### v3.0.0 — Comprehensive Improvement
- Added side-by-side visual diff renderer (`sidebyside.py`)
- Added HTML diff output with inline CSS and word-level highlighting (`htmlout.py`)
- Added recursive directory diff with per-file statistics (`dirdiff.py`)
- Added diff optimizer with common-edge extraction (`optimizer.py`)
- Added logging configuration module (`logging_config.py`)
- Expanded CLI to 11 subcommands (added `sidebyside`, `html`, `dirdiff`)
- Added `--verbose` and `--log-level` global CLI options
- Added GitHub Actions CI workflow (Python 3.10–3.12)
- Added CONTRIBUTING.md, LICENSE, .gitignore
- Added 3 new example scripts
- Added 32 new tests (116 total, all passing)
- Updated pyproject.toml with dev extras and expanded classifiers

### v2.0.0 — Enhancement + Bug Hunt
- Added word-level inline diff highlighting
- Added diff statistics module
- Added configuration system (JSON/TOML/YAML)
- Added binary file detection, whitespace/blank-line filtering
- Added reverse patch support
- Expanded CLI to 8 subcommands
- Found and fixed 10 bugs with 31 regression tests

### v1.0.0 — Initial Release
- 4 diff algorithms (Myers, LCS, Patience, Histogram)
- 3 output formats (unified, context, normal)
- Patch parser/applier with fuzz and reject support
- Three-way merge with conflict markers
- 20 tests

## License

MIT — see [LICENSE](LICENSE).