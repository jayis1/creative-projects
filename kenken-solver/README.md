# KenKen Solver & Generator

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/kenken-ci.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions/workflows/kenken-ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-66%20passing-brightgreen.svg)](#testing)
[![Code style: typed](https://img.shields.io/badge/code%20style-typed-blue.svg)](https://peps.python.org/pep-0481/)

> A from-scratch KenKen (Calcudoku / Mathdoku) puzzle engine: generator, solver,
> verifier, analyzer, interactive mode, and hint system — in pure Python with
> **zero external dependencies**.

## Table of Contents

- [What is KenKen?](#what-is-kenken)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Generate Puzzles](#generate-puzzles)
  - [Solve Puzzles](#solve-puzzles)
  - [Verify Uniqueness](#verify-uniqueness)
  - [Analyze Difficulty](#analyze-difficulty)
  - [Batch Generation](#batch-generation)
  - [Hints](#hints)
  - [Interactive Mode](#interactive-mode)
  - [Config Files](#config-files)
  - [Python API](#python-api)
- [Text Format](#text-format)
- [Architecture](#architecture)
- [ASCII Demo](#ascii-demo)
- [Testing](#testing)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

## What is KenKen?

KenKen is an arithmetical-logic puzzle invented by Japanese mathematics
teacher Tetsuya Miyamoto in 2004. An *n×n* grid must be filled so that:

1. Each **row** contains the numbers 1–*n* exactly once (Latin square constraint).
2. Each **column** contains the numbers 1–*n* exactly once.
3. The grid is divided into **cages** — contiguous groups of cells, each with a
   target number and an operator (`+`, `-`, `*`, `/`, or `=` for single-cell
   cages). The numbers in each cage must combine via the operator to produce
   the target.

For subtraction and division cages with more than two cells, any left-to-right
ordering of the values that yields the target is accepted (all permutations
are checked).

## Features

### Core Engine
- **Solver** — Backtracking search with constraint propagation, the
  Minimum-Remaining-Values (MRV) heuristic, forward-checking via cage
  feasibility bounds, and naked-single propagation.
- **Solution counter** — `count_solutions()` counts all solutions without
  storing them, with an optional limit.
- **Generator** — Produces solvable puzzles with **guaranteed unique
  solutions** by generating a random Latin square, partitioning into
  contiguous cages via random-region growth, and verifying uniqueness.
- **Difficulty levels** — `easy` (favors `+` and `=`, avoids `*`/`/`),
  `medium` (balanced), `hard` (favors `*` and `/`).
- **Operator support** — `+`, `-`, `*`, `/`, `=` (single-cell freebies).

### Analysis & Hints
- **Puzzle analyzer** — Analyzes cage statistics, operator distribution,
  difficulty scoring, solver complexity metrics (nodes/backtracks), and
  difficulty categorization (easy/medium/hard).
- **Hint system** — Provides cell-value hints for partially solved puzzles,
  with conflict detection for invalid partial assignments.
- **Interactive mode** — REPL-like session for filling cells, getting hints,
  checking validity, and revealing the solution.

### Infrastructure
- **CLI** — Full argparse-based interface with 7 subcommands and `--verbose` /
  `--quiet` logging flags.
- **Config files** — Load generation parameters from JSON or YAML files.
- **Batch generation** — Generate multiple puzzles with timing statistics and
  progress reporting.
- **Serialization** — JSON and compact text format (with comment support).
- **Logging** — Structured logging throughout the library.
- **Type hints** — Complete type annotations with PEP 561 `py.typed` marker.
- **Installable** — `pip install .` with a `kenken` console script entry point.
- **CI** — GitHub Actions workflow testing Python 3.9–3.12.
- **Zero dependencies** — Pure standard-library Python. YAML is optional.

## Installation

### From source (recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/kenken-solver

# Create a virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Or without dev dependencies
pip install -e .
```

After installation, the `kenken` command is available:

```bash
kenken --help
kenken generate --size 5
```

### Without installation (standalone)

The legacy `kenken.py` shim works as a standalone script:

```bash
cd kenken-solver
python3 kenken.py --help
python3 kenken.py generate --size 5
```

### Optional dependencies

For YAML config file support:

```bash
pip install pyyaml
```

## Quick Start

```bash
# Generate and solve a 5×5 puzzle
python3 kenken.py generate --size 5 --solve

# Generate a hard 6×6 puzzle from a config file
python3 kenken.py generate --config examples/config.json

# Solve a puzzle from a file
python3 kenken.py solve --input puzzle.json --stats

# Interactive solving
python3 kenken.py interactive --input puzzle.json
```

## Usage

### Generate Puzzles

```bash
# 5×5 medium puzzle
python3 kenken.py generate --size 5

# 6×6 hard puzzle with a seed, also show the solution
python3 kenken.py generate --size 6 --difficulty hard --seed 42 --solve

# 4×4 puzzle without single-cell cages
python3 kenken.py generate --size 4 --no-singletons --solve

# Save puzzle to JSON file
python3 kenken.py generate --size 4 --output puzzle.json --format json

# Export in compact text format
python3 kenken.py generate --size 5 --format text

# Generate from a config file (CLI args override config values)
python3 kenken.py generate --config examples/config.json
```

### Solve Puzzles

```bash
python3 kenken.py solve --input puzzle.json
python3 kenken.py solve --input puzzle.json --all       # find all solutions
python3 kenken.py solve --input puzzle.json --stats     # show solver statistics
python3 kenken.py solve --input puzzle.txt              # text format also supported
```

### Verify Uniqueness

```bash
python3 kenken.py verify --input puzzle.json
```

Output:
```
UNIQUE — puzzle has exactly one solution.
```

### Analyze Difficulty

```bash
python3 kenken.py analyze --input puzzle.json
```

Output (JSON):
```json
{
  "size": 5,
  "num_cages": 10,
  "avg_cage_size": 2.5,
  "max_cage_size": 4,
  "num_singletons": 2,
  "operator_distribution": {"+": 3, "-": 2, "*": 3, "/": 1, "=": 1},
  "difficulty_score": 24,
  "difficulty_category": "medium",
  "solver_nodes": 45,
  "solver_backtracks": 12
}
```

### Batch Generation

```bash
# Generate 10 puzzles with progress reporting
python3 kenken.py batch --size 5 --count 10 --difficulty medium --output-dir puzzles/

# Generate without single-cell cages
python3 kenken.py batch --size 5 --count 20 --no-singletons --output-dir puzzles/
```

### Hints

```bash
# Get 3 hints given some pre-filled cells
python3 kenken.py hint --input puzzle.json --cells "0,0=3" "1,2=5" --num 3
```

### Interactive Mode

```bash
python3 kenken.py interactive --input puzzle.json
```

Commands available in the interactive session:

| Command | Description |
|---------|-------------|
| `fill R C V` | Fill cell (R,C) with value V |
| `clear R C` | Clear cell (R,C) |
| `hint [N]` | Get N hints (default 1) |
| `check` | Check if current grid is valid |
| `show` | Show the puzzle |
| `state` | Show current grid state |
| `solution` | Reveal the full solution |
| `quit` / `exit` | Exit the session |

### Config Files

Generate puzzles from JSON or YAML configuration files:

**JSON** (`examples/config.json`):
```json
{
    "size": 6,
    "difficulty": "hard",
    "seed": 42,
    "max_cage_size": 4,
    "allow_singletons": false,
    "format": "json",
    "output": "puzzle_hard_6x6.json"
}
```

**YAML** (`examples/config.yaml`):
```yaml
size: 5
difficulty: medium
seed: 123
max_cage_size: 4
allow_singletons: true
format: text
```

```bash
python3 kenken.py generate --config examples/config.json
```

CLI arguments override config file values.

### Python API

```python
from kenken_solver import (
    KenKenGenerator, KenKenSolver, KenKenPuzzle, PuzzleAnalyzer,
    render_puzzle, render_solved_puzzle,
)

# Generate
gen = KenKenGenerator(size=5, seed=42, difficulty="medium")
puzzle = gen.generate()
solution = gen.solution  # the intended solution grid
print(render_puzzle(puzzle))

# Solve
solver = KenKenSolver(puzzle)
grid = solver.solve_grid()
print(grid)

# Count solutions
count = solver.count_solutions()
print(f"Number of solutions: {count}")

# Analyze
analyzer = PuzzleAnalyzer(puzzle)
analysis = analyzer.analyze()
print(analysis)

# Get hints
hints = solver.get_hint({(0, 0): 3, (1, 2): 5}, num=3)

# Serialize
json_str = puzzle.to_json()
puzzle2 = KenKenPuzzle.from_json(json_str)
text = puzzle.to_text()
puzzle3 = KenKenPuzzle.from_text(text)
```

## Text Format

The compact text format is human-readable and editable:

```
size: 5
# Comments start with #
0,0 0,1 + 7
0,2 = 3
1,0 1,1 * 12
...
```

Each cage line: space-separated `row,col` cell coordinates, then the operator,
then the target.

## Architecture

The project is organized as a modular Python package (`kenken_solver/`):

```
kenken-solver/
├── kenken.py                — Backward-compatible shim (re-exports package)
├── pyproject.toml            — PEP 621 project metadata
├── setup.py                  — Legacy setup.py shim
├── LICENSE                   — MIT license
├── CONTRIBUTING.md           — Development guide
├── CHANGELOG.md              — Version history
├── .github/workflows/        — GitHub Actions CI
├── kenken_solver/            — Main package
│   ├── __init__.py           — Public API re-exports
│   ├── types.py             — Shared type aliases (Cell, Assignment) & helpers
│   ├── cage.py              — Cage class (cells, operator, target, evaluation)
│   ├── puzzle.py            — KenKenPuzzle (validation, serialization, equality)
│   ├── solver.py            — KenKenSolver (backtracking, MRV, hints)
│   ├── generator.py         — KenKenGenerator (Latin squares, cage partitioning)
│   ├── analyzer.py          — PuzzleAnalyzer (difficulty scoring, metrics)
│   ├── render.py            — ASCII rendering functions
│   ├── config.py            — GenerationConfig (JSON/YAML config support)
│   ├── cli.py               — Argparse CLI with 7 subcommands
│   └── py.typed             — PEP 561 type marker
├── tests/
│   ├── conftest.py          — Pytest path configuration
│   ├── test_kenken.py       — 53 core tests
│   └── test_bug_hunt.py     — 13 bug hunt tests
├── examples/
│   ├── generate_and_solve.py — Basic generation, solving, and analysis demo
│   ├── serialization.py      — JSON/text round-trip demo
│   ├── hint_demo.py          — Progressive hint-based solving demo
│   ├── batch_analyze.py      — Batch generation with difficulty analysis
│   ├── config.json           — JSON config example
│   └── config.yaml           — YAML config example
└── docs/
    └── solver-internals.md   — Deep dive into the solver algorithm
```

### Solver Algorithm

The solver (`KenKenSolver`) uses backtracking with:

1. **Domain tracking**: Each cell maintains a set of candidate values `{1..n}`,
   reduced by row and column constraints.
2. **MRV heuristic**: At each step, the unassigned cell with the fewest
   candidates is selected first, dramatically reducing the search space.
3. **Naked-single propagation**: After each assignment, cells reduced to a
   single candidate are automatically assigned. Row/column reductions are
   processed in a separate phase before naked-single assignment to ensure
   correct constraint ordering.
4. **Cage feasibility pruning**: After assigning a value, the cage containing
   that cell is checked for feasibility:
   - For `+` cages: the partial sum plus the minimum/maximum possible
     contribution from unassigned cells must bracket the target.
   - For `*` cages: similarly using product bounds.
   - For `-` and `/` cages: defers to the full permutation check once all
     cells are assigned.
5. **Full domain snapshot/restore**: Before each branch, a complete snapshot
   of all domains is saved. This ensures correct restoration after
   propagation modifies domains across the entire grid.

### Generator Algorithm

The generator (`KenKenGenerator`) works as follows:

1. **Random Latin square**: A base cyclic Latin square is constructed, then
   randomized via independent row, column, and symbol permutations.
2. **Cage partitioning**: Starting from random seed cells, cages grow by
   absorbing unassigned orthogonal neighbors until reaching a random size
   (1 to `max_cage_size`). If `allow_singletons=False`, orphan singletons are
   merged into adjacent cages.
3. **Operator selection**: For each cage, all valid `(operator, target)` pairs
   are computed from the solution values. A weighted random choice is made
   based on the difficulty level.
4. **Uniqueness verification**: The solver is invoked with
   `max_solutions=2`. If exactly one solution exists, the puzzle is accepted;
   otherwise, the process repeats (up to `max_attempts` times).

## ASCII Demo

```
$ python3 kenken.py generate --size 4 --seed 42 --solve
+----+----+----+----+
| 4= | 6* |    |12* |
|    |    |    |    |
+----+----+----+----+
| 3+ |    |    |    |
|    |    |    |    |
+----+----+----+----+
| 9+ |    |    | 2/ |
|    |    |    |    |
+----+----+----+----+
|    | 3= | 2= |    |
|    |    |    |    |
+----+----+----+----+

Solution:
+-----+-----+-----+-----+
| 4=  | 6*  |     |12*  |
|  4  |  1  |  2  |  3  |
+-----+-----+-----+-----+
| 3+  |     |     |     |
|  3  |  2  |  4  |  1  |
+-----+-----+-----+-----+
| 9+  |     |     | 2/  |
|  2  |  4  |  3  |  1  |
+-----+-----+-----+-----+
|     | 3=  | 2=  |     |
|  1  |  3  |  2  |  4  |
+-----+-----+-----+-----+
```

## Testing

The project includes **66 tests** (53 core + 13 bug hunt), all passing.

```bash
# Run all tests
python3 tests/test_kenken.py
python3 tests/test_bug_hunt.py

# Or with pytest (if installed)
pytest

# With coverage
pytest --cov=kenken_solver --cov-report=term-missing
```

Test coverage:

| Category | Count | Description |
|----------|-------|-------------|
| Cage | 9 | Operator evaluation, validation, hashing |
| Puzzle validation | 4 | Missing cells, overlaps, non-contiguity, bounds |
| Solver | 7 | Uniqueness, Latin square property, unsolvable |
| Serialization | 3 | JSON and text round-trips |
| Hints | 3 | Basic, partial, conflict detection |
| Analyzer | 1 | Difficulty metrics |
| Generator options | 3 | No-singletons, difficulty, max cage size |
| Rendering | 3 | Puzzle, cage map, solved puzzle |
| Edge cases | 3 | 2×2, unsolvable, repr |
| Package/shim | 4 | Backward compat, version, equality, hash |
| Config | 3 | Defaults, from dict, from file |
| CLI | 6 | Generate, solve, verify, analyze, hint, text |
| Types | 2 | Neighbors, contiguity |
| Bug hunt | 13 | All previously fixed bugs verified |

## Examples

The `examples/` directory contains four demo scripts:

```bash
# Generate and solve puzzles of various sizes
python3 examples/generate_and_solve.py

# Serialize and deserialize puzzles
python3 examples/serialization.py

# Progressively solve a puzzle using hints
python3 examples/hint_demo.py

# Batch generate and analyze difficulty distribution
python3 examples/batch_analyze.py
```

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and fixed:

1. **Hint system ignored partial assignments** — `get_hint()` called `solve()`
   without constraining the search to the partial assignment, so hints could
   be inconsistent with the user's pre-filled cells. **Fix**: Added cage
   constraint validation for partial assignments, solution consistency
   checking, and early return of empty hints when the partial assignment
   conflicts with the unique solution.

2. **Domain restoration bug in backtracking solver** — The solver only
   saved/restored domains for cells directly modified by the row/column
   update, but propagation modifies domains across the entire grid. This
   caused stale domain state after backtracking, leading to missing solutions.
   **Fix**: Save and restore a complete snapshot of ALL domains before each
   branching step.

3. **Naked-single propagation ordering bug** — Multiple naked singles were
   assigned in the same propagation phase before their row/column constraints
   were propagated, causing incorrect domain reductions. **Fix**: Assign only
   ONE naked single per propagation iteration, then re-loop to propagate its
   constraints before assigning the next.

4. **`render_solved_puzzle` crashed on None grid** — Passing `None`
   (unsolvable puzzle) to `render_solved_puzzle` caused a `TypeError`. **Fix**:
   Added a None check that falls back to `render_puzzle()`.

5. **Unused variables in `possible_targets`** — The `ok` and `ok2` variables in
   the subtraction/division branch were set but never checked. **Fix**:
   Removed unused variables and renamed `ok2` to `div_ok` for clarity.

6. **Unused `math` import** — The `math` module was imported but never used.
   **Fix**: Removed the import.

7. **Subtraction operator produced negative targets** — The generator's
   `_choose_operator` could produce negative subtraction targets for 3+ cell
   cages. **Fix**: Only keep permutation results that are positive (`r > 0`).

8. **`_cage_feasible` had dead code for `*` operator** — The `p == 0` check was
   unreachable (values are always 1..n) and the `min_v` computation was a
   no-op (`min_v *= 1`). **Fix**: Simplified the product bounds computation
   using exponentiation.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

### v3.0.0 (2026-07-27) — Comprehensive Improvement

- Split monolithic 1,310-line `kenken.py` into a modular `kenken_solver/`
  package with 10 focused modules
- Added interactive solving mode (`interactive` subcommand)
- Added config file support (JSON/YAML)
- Added structured logging throughout the library
- Added complete type hints with PEP 561 `py.typed` marker
- Added `pyproject.toml` with `kenken` console script entry point
- Added GitHub Actions CI (Python 3.9–3.12)
- Added 4 example scripts and example config files
- Added CONTRIBUTING.md, LICENSE, CHANGELOG.md
- Added 17 new tests (53 total core + 13 bug hunt = 66)
- Maintained full backward compatibility via `kenken.py` shim

### v2.0.0 (2026-07-27) — Enhancement

- Puzzle analyzer with difficulty scoring
- Hint system with conflict detection
- Batch generation with timing statistics
- Cage contiguity validation
- No-singletons generation mode
- Compact text format with comment support
- Enhanced rendering

### v1.0.0 (2026-07-27) — Initial Release

- Core solver, generator, and CLI

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding
conventions, and contribution guidelines.

## Roadmap

- [ ] Web interface (Flask/Streamlit)
- [ ] SVG/PNG puzzle export
- [ ] More solver strategies (constraint learning, arc consistency)
- [ ] Import puzzles from common KenKen puzzle formats
- [ ] Timed challenge mode with leaderboards
- [ ] Puzzle rating system (Elo-based)
- [ ] Killer KenKen variant (combining KenKen and Sudoku)
- [ ] Parallel generation for large batch jobs
- [ ] Benchmark suite comparing solver configurations

## License

[MIT](LICENSE) — Copyright (c) 2026 Creative Coder Pipeline