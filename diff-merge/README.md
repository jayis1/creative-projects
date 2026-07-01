# diff-merge

A from-scratch text diff, patch, and three-way merge toolkit implemented in pure Python (stdlib only, no external dependencies).

## Features

- **4 diff algorithms:**
  - **Myers** — Classic O(ND) edit-graph shortest-edit-script with backtracking (Eugene W. Myers, 1986)
  - **LCS** — Dynamic programming O(NM) with backtracking (reference implementation)
  - **Patience** — Bram Cohen's algorithm using unique common lines as anchors, falling back to LCS on segments with no unique lines
  - **Histogram** — Eclipse JGit enhancement of patience diff using least-frequency line matching for better anchor selection
- **3 output formats:**
  - **Unified diff** (`@@ -start,count +start,count @@` with ` `/`-`/`+` prefixes)
  - **Context diff** (RCS-style with `***`/`---` headers and `- `/`+ `/`  ` prefixes)
  - **Normal diff** (classic `Nd`, `Na`, `Nc` change commands with `<`/`>` content)
- **Patch parsing and application:**
  - Parse unified-diff patches into structured `Hunk` objects
  - Apply patches with configurable fuzz tolerance and max line offset
  - Automatic offset search when hunk position doesn't match exactly
  - Reject file (`.rej`) generation for unapplied hunks
- **Three-way merge (diff3):**
  - Merge two derived versions against a common ancestor
  - Automatic conflict detection with standard `<<<<<<<`/`=======`/`>>>>>>>` markers
  - Clean merge when only one side changes, or both sides make identical changes
  - Configurable conflict marker size
- **CLI tool** with 4 subcommands: `diff`, `patch`, `merge`, `lcs`
- **Comprehensive test suite** (20 tests)

## Installation

```bash
pip install -e .
```

Or use directly without installation:

```bash
python3 -m diff_merge.cli diff old.txt new.txt
```

## Usage

### Diff two files

```bash
# Unified diff (default)
python3 -m diff_merge.cli diff old.txt new.txt

# Context diff with 5 lines of context
python3 -m diff_merge.cli diff old.txt new.txt --format context --context 5

# Normal (RCS-style) diff
python3 -m diff_merge.cli diff old.txt new.txt --format normal

# Use patience diff algorithm
python3 -m diff_merge.cli diff old.txt new.txt --algorithm patience
```

### Apply a patch

```bash
# Apply from stdin
cat patch.diff | python3 -m diff_merge.cli patch source.txt

# Apply from file with fuzz tolerance
python3 -m diff_merge.cli patch source.txt --patchfile patch.diff --fuzz 2

# Write rejected hunks to .rej file
python3 -m diff_merge.cli patch source.txt --patchfile patch.diff --reject
```

### Three-way merge

```bash
python3 -m diff_merge.cli merge base.txt ours.txt theirs.txt
```

Exit code 0 = clean merge, exit code 1 = conflicts present.

### Longest common subsequence

```bash
python3 -m diff_merge.cli lcs file1.txt file2.txt
```

## Python API

```python
from diff_merge import (
    myers_diff, patience_diff, histogram_diff, lcs_diff,
    unified_diff, context_diff, normal_diff,
    parse_unified_diff, apply_patch,
    three_way_merge,
)

a = ["line1\n", "line2\n", "line3\n"]
b = ["line1\n", "line2 modified\n", "line3\n"]

# Compute diff using any algorithm
ops = myers_diff(a, b)
ops = patience_diff(a, b)
ops = histogram_diff(a, b)
ops = lcs_diff(a, b)

# Generate unified diff output
patch_lines = unified_diff(a, b, fromfile="old", tofile="new")

# Apply a patch
hunks = parse_unified_diff(patch_lines)
result = apply_patch(a, hunks)
print(result.patched)  # == b

# Three-way merge
base = ["line1\n", "line2\n", "line3\n"]
ours = ["line1\n", "line2 ours\n", "line3\n"]
theirs = ["line1\n", "line2 theirs\n", "line3\n"]
merge_result = three_way_merge(base, ours, theirs)
# merge_result.clean == False (conflict on line 2)
# merge_result.lines contains the merged output with conflict markers
```

## How It Works

### Myers Diff

The Myers algorithm finds the shortest edit script between two sequences by exploring an edit graph. It works on diagonals (where `k = x - y`), and for each edit distance `d`, it computes the furthest-reaching point on each diagonal. The algorithm is O(ND) where N is the total sequence length and D is the edit distance (number of differences).

This implementation stores the V array at each edit distance level, then backtracks through the trace to reconstruct the path. The backtrack walks from `(N, M)` backward to `(0, 0)`, following snakes (diagonal moves through equal elements) and edit moves (right = delete, down = insert).

### Patience Diff

Patience diff finds unique lines that appear exactly once in each sequence, uses them as anchor points, then recursively diffs the segments between anchors. This produces more human-readable diffs for code with clear function/class boundaries. When no unique common lines exist in a segment, it falls back to LCS diff.

### Histogram Diff

Histogram diff enhances patience diff by using the *least frequent* common lines as anchors rather than only unique lines. When all lines are non-unique, it picks the rarest lines (minimum combined frequency in both sequences) and recurses. This further improves diff quality for code with repeated boilerplate patterns.

### Three-Way Merge

The diff3 algorithm:
1. Compute diff(base → ours) and diff(base → theirs)
2. Find changed regions in each diff
3. Merge overlapping change regions from both sides
4. For each region, compare content:
   - Both sides identical → take either (clean)
   - Only one side changed → take that side (clean)
   - Both sides changed differently → conflict

## Architecture

```
diff_merge/
├── __init__.py    — Package exports
├── myers.py       — Myers O(ND) diff algorithm
├── lcs.py         — LCS dynamic programming diff
├── patience.py    — Patience diff (Bram Cohen)
├── histogram.py   — Histogram diff (Eclipse JGit)
├── format.py      — Unified/context/normal diff formatters
├── patch.py       — Patch parser and applier
├── merge.py       — Three-way merge (diff3)
└── cli.py         — Command-line interface
```

## License

MIT