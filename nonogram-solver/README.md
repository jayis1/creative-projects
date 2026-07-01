<div align="center">

# 🧩 Nonogram Solver

**A from-scratch nonogram (Picross / Hanjie / Griddlers) solver, generator, and player — pure Python, no external dependencies.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 100](https://img.shields.io/badge/tests-100%20passing-brightgreen.svg)]()
[![Version: 3.0.0](https://img.shields.io/badge/version-3.0.0-orange.svg)]()
[![No Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-lightgrey.svg)]()

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Puzzle File Formats](#puzzle-file-formats)
- [Architecture](#architecture)
- [Preset Puzzles](#preset-puzzles)
- [Configuration](#configuration)
- [Web Server](#web-server)
- [Batch Solving & Benchmarking](#batch-solving--benchmarking)
- [Testing](#testing)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

Nonograms are logic puzzles where you fill cells in a grid based on numbered
clues given for each row and column. The numbers indicate the lengths of
consecutive runs of filled cells in that line, separated by at least one blank
cell. The goal is to determine which cells are filled and which are left blank.

This project implements a complete nonogram toolkit from scratch — no external
libraries required (PyYAML is optional for YAML config support). It includes a
solver using constraint propagation + backtracking, a puzzle generator, an
interactive player, a web-based solver, batch processing, benchmarking, and
difficulty analysis.

## Features

### Core Solver
- **Line solver** with the overlap method and constraint propagation
- **Full-board solver** combining iterative propagation with backtracking
- **MRV heuristic** for smarter cell selection during backtracking
- **Solution counter** — count all solutions up to a limit
- **Unique-solution checker** — robust multi-solution detection
- **Result caching** in the line solver for performance

### Generation & Analysis
- **Puzzle generator** with unique-solution verification
- **Difficulty analyzer** — grades puzzles as trivial/easy/medium/hard/expert
- **10 curated preset puzzles** — all verified solvable and unique

### I/O & Rendering
- **JSON serialization** for puzzles and solutions
- **NON format** support (compact text format)
- **PNG export** (pure stdlib — no Pillow needed)
- **SVG export** for scalable vector graphics
- **ANSI colored terminal rendering** with clue display
- **HTML rendering** with styled tables

### Tools & Extensions
- **Interactive web solver** — browser-based solving via stdlib `http.server`
- **Batch solver** — process multiple puzzle files, generate JSON/CSV reports
- **Benchmark suite** — measure solver performance on presets and generated puzzles
- **Solver statistics** — propagation rounds, cache hit ratio, backtrack nodes
- **Configuration management** — JSON/YAML/TOML config files with validation

### CLI
- **12 subcommands**: `solve`, `generate`, `validate`, `hint`, `presets`,
  `analyze`, `render`, `count`, `batch`, `benchmark`, `web`, `config`
- Global options: `--config`, `--verbose`, `--quiet`

## Installation

```bash
cd nonogram-solver
pip install -e .
```

With development dependencies (pytest, PyYAML):
```bash
pip install -e ".[dev]"
```

For YAML config support only:
```bash
pip -e ".[yaml]"
```

**Requirements:** Python 3.10+ (uses `match` statements, `tomllib` on 3.11+)

## Quick Start

```bash
# Solve a puzzle
nonogram solve puzzles/heart.json

# Solve with ANSI colors
nonogram solve puzzles/heart.json --color

# Generate a new puzzle
nonogram generate --width 10 --height 10 --seed 42 --difficulty

# List preset puzzles
nonogram presets

# Solve a preset
nonogram presets --name ship --solve

# Start the web solver
nonogram web puzzles/heart.json --port 8080

# Run benchmarks
nonogram benchmark

# Batch solve a directory
nonogram batch puzzles/ --check-unique --report-json report.json
```

## CLI Reference

### `solve` — Solve a puzzle

```bash
nonogram solve puzzles/heart.json [options]
```

| Flag | Description |
|------|-------------|
| `--output, -o FILE` | Save solved board to JSON file |
| `--max-backtracks N` | Max backtracking nodes (default: 100000) |
| `--no-mrv` | Disable MRV cell selection heuristic |
| `--color` | ANSI colored output |

### `generate` — Generate a new puzzle

```bash
nonogram generate --width 10 --height 10 --seed 42 [options]
```

| Flag | Description |
|------|-------------|
| `--width, -w N` | Grid width (default: 10) |
| `--height, -H N` | Grid height (default: 10) |
| `--density, -d F` | Fraction of filled cells (default: 0.55) |
| `--seed, -s N` | Random seed |
| `--no-unique` | Skip uniqueness check |
| `--difficulty` | Print difficulty analysis |

### `batch` — Batch solve

```bash
nonogram batch puzzles/ [options]
```

| Flag | Description |
|------|-------------|
| `--output-dir, -o DIR` | Directory for solved JSON files |
| `--recursive, -r` | Search subdirectories |
| `--check-unique, -u` | Also check uniqueness |
| `--report-json FILE` | Save JSON report |
| `--report-csv FILE` | Save CSV report |

### `benchmark` — Run benchmarks

```bash
nonogram benchmark [options]
```

| Flag | Description |
|------|-------------|
| `--preset, -p NAME` | Benchmark a specific preset |
| `--output, -o FILE` | Save results as JSON |

### `web` — Interactive web solver

```bash
nonogram web puzzles/heart.json [options]
```

| Flag | Description |
|------|-------------|
| `--port, -p N` | Port number (default: 8080) |
| `--no-browser` | Don't open browser automatically |

### `config` — Config file management

```bash
nonogram config --generate config.json
nonogram config --validate config.json
```

### Other commands

```bash
nonogram validate puzzles/heart.json   # Check uniqueness
nonogram hint puzzles/heart.json        # Get a hint
nonogram analyze puzzles/heart.json    # Difficulty analysis
nonogram count puzzles/heart.json -l 5 # Count solutions
nonogram render puzzles/heart.json -f ansi  # Render
nonogram render puzzles/heart.json -f png -o heart.png
```

## Python API

```python
from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.generator import Generator
from nonogram.player import Player
from nonogram.analyzer import DifficultyAnalyzer
from nonogram.io import PuzzleIO
from nonogram.renderer import Renderer
from nonogram.presets import get_preset, list_presets
from nonogram.batch import BatchSolver
from nonogram.benchmark import BenchmarkSuite
from nonogram.stats import SolverStats
from nonogram.config import AppConfig, load_config

# ── Solve a puzzle ──
board = Board(
    row_clues=[[1], [3], [5], [3], [1]],
    col_clues=[[1], [3], [5], [3], [1]],
)
result = Solver().solve(board)
print(board.render())
# . . # . .
# . # # # .
# # # # #
# . # # # .
# . . # . .

# ── Generate a puzzle ──
gen = Generator(seed=42)
puzzle = gen.generate(10, 10, density=0.5, unique=True)

# ── Check uniqueness ──
solver = Solver()
print(solver.is_unique(puzzle))  # True

# ── Count solutions ──
print(solver.count_solutions(puzzle, limit=5))  # 1

# ── Analyze difficulty ──
info = DifficultyAnalyzer().analyze(puzzle)
print(info["difficulty"])  # "medium"

# ── Interactive player ──
player = Player(puzzle)
player.fill(0, 2)
player.blank(0, 0)
hint = player.hint()  # (row, col, Cell)
print(player.check())  # True if correct so far

# ── Export to formats ──
PuzzleIO.save_png(board, "output.png")
PuzzleIO.save_svg(board, "output.svg")
PuzzleIO.save_json(board, "output.json")
PuzzleIO.save_non(board, "output.non")
html = Renderer.html(board, title="My Puzzle")

# ── Batch solve ──
bs = BatchSolver(output_dir="solutions/", check_unique=True)
report = bs.solve_files("puzzles/*.json")
print(report.summary())
print(report.to_csv())

# ── Benchmark ──
suite = BenchmarkSuite()
suite.run_all()
print(suite.summary())

# ── Configuration ──
config = AppConfig()
config.solver.max_iterations = 5000
config.validate()  # Validate all settings

# ── Load config from file ──
# config = load_config("config.json")  # or .yaml, .toml
```

## Puzzle File Formats

### JSON

```json
{
  "row_clues": [[1], [3], [5], [3], [1]],
  "col_clues": [[1], [3], [5], [3], [1]],
  "grid": [[0,0,1,0,0], [0,1,1,1,0], [1,1,1,1,1], [0,1,1,1,0], [0,0,1,0,0]]
}
```

- `row_clues` / `col_clues`: list of clue lists (integers)
- `grid` (optional): 2D array of cell values (`-1`=unknown, `0`=empty, `1`=filled)

### NON (compact text)

```
5 5
1
3
5
3
1
1
3
5
3
1
```

First line: `width height`. Next `height` lines: row clues. Next `width` lines:
column clues. Use `0` for an empty clue (no filled cells).

## Architecture

The project is organized into focused modules with clear separation of concerns:

```
nonogram-solver/
├── nonogram/
│   ├── __init__.py      # Package exports (all public symbols)
│   ├── board.py         # Board and Cell data structures
│   ├── line_solver.py   # Per-line constraint propagation (overlap method)
│   ├── solver.py        # Full-board solver (propagation + MRV backtracking)
│   ├── generator.py     # Random puzzle generator with unique-solution check
│   ├── player.py        # Interactive player with hints and progress checking
│   ├── presets.py       # 10 curated preset puzzles
│   ├── analyzer.py      # Difficulty analyzer (trivial→expert grading)
│   ├── io.py            # File I/O (JSON, NON, PNG, SVG)
│   ├── renderer.py      # ANSI and HTML renderers
│   ├── cli.py           # CLI (12 subcommands + global options)
│   ├── config.py        # Configuration management (JSON/YAML/TOML)
│   ├── batch.py         # Batch solver with report generation
│   ├── benchmark.py     # Performance benchmarking suite
│   ├── stats.py         # Solver statistics and profiling
│   └── web.py           # Interactive web solver (stdlib http.server)
├── tests/
│   ├── test_bug_hunt.py # Bug hunt regression tests (11 tests)
│   └── test_nonogram.py # Comprehensive test suite (89 tests)
├── puzzles/             # Example puzzle files
├── examples/            # Usage example scripts (5 examples)
├── docs/                # Architecture documentation
├── .github/workflows/   # CI (GitHub Actions)
├── pyproject.toml       # Build config, dependencies, pytest config
├── config.example.json  # Example configuration file
├── CONTRIBUTING.md      # Contribution guidelines
├── CHANGELOG.md         # Version history
├── LICENSE              # MIT License
└── README.md
```

### Core Algorithm

**LineSolver** (the fundamental building block):
1. **Overlap method** — For each clue block, compute leftmost and rightmost
   valid positions. Overlapping cells are guaranteed filled.
2. **Constraint propagation** — Iterate to a fixpoint, each pass further
   constraining the next.
3. **Feasibility check** — Backtracking verifier confirms at least one valid
   arrangement exists.
4. **Result caching** — Cache by (line_state, clue, length) to avoid
   redundant computation.

**Solver** (full-board):
1. **Constraint propagation** — Apply LineSolver to every row and column
   iteratively until fixpoint.
2. **MRV backtracking** — When propagation stalls, pick the most constrained
   line (fewest unknowns), try both values, and recurse.
3. **Solution counting** — Count all solutions up to a limit for uniqueness
   checking.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a detailed description.

## Preset Puzzles

| Name | Size | Difficulty | Description |
|------|------|------------|-------------|
| heart | 5×5 | easy | A heart shape |
| smiley | 5×5 | easy | A smiley face |
| cross | 7×7 | easy | A plus sign |
| letter-a | 5×5 | easy | The letter A |
| tree | 7×7 | medium | A tree |
| house | 5×5 | medium | A house |
| ship | 10×10 | medium | A ship with mast and hull |
| cat | 8×8 | hard | A cat face |
| space-invader | 8×8 | hard | A classic space invader |
| key | 10×10 | hard | A key |

All presets are verified to have unique solutions.

```
$ nonogram presets --name ship --solve
Preset 'ship' solution:
. . . . # . . . . .
. . . # # # . . . .
. . . . # . . . . .
. . . . # . . . . .
# # # # # # # # # #
# # # # # # # # # #
. # # # # # # # # .
. . # # # # # # . .
. . . # # # # . . .
. . . . # # # . . .
```

## Configuration

The solver supports configuration via JSON, YAML, or TOML files:

```bash
# Generate a default config
nonogram config --generate config.json

# Validate a config
nonogram config --validate config.json

# Use config with any command
nonogram --config config.json solve puzzles/heart.json
```

Example config (`config.example.json`):
```json
{
  "solver": {
    "max_iterations": 5000,
    "max_backtracks": 50000,
    "use_mrv": true
  },
  "generator": {
    "default_density": 0.55,
    "default_max_attempts": 200
  },
  "rendering": {
    "cell_size": 20,
    "filled_color": [40, 40, 40],
    "empty_color": [255, 255, 255],
    "unknown_color": [200, 200, 200]
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
  }
}
```

## Web Server

The interactive web solver runs entirely on stdlib `http.server` — no Flask,
Django, or other framework needed:

```bash
nonogram web puzzles/heart.json --port 8080
```

Then open `http://localhost:8080` in your browser. Features:
- Click cells to fill/blank/erase
- Hint button for solver-generated hints
- Check button to verify progress
- Solve button to auto-solve
- Reset button to start over
- Clue display (rows and columns)
- Dark-themed responsive UI

## Batch Solving & Benchmarking

### Batch Solver

Process multiple puzzle files at once:

```bash
# Solve all puzzles in a directory
nonogram batch puzzles/ --check-unique --report-json report.json

# Solve with glob pattern
nonogram batch "puzzles/*.json" --output-dir solutions/
```

Output:
```
Batch Report: 4 puzzles
  Solved:    4
  Failed:    0
  Unique:    4
  Total time: 0.01s
  Avg time:   0.0003s
```

### Benchmark Suite

Measure solver performance:

```bash
nonogram benchmark
```

Output:
```
Nonogram Solver Benchmarks
======================================================================
✓ preset:heart              5×5      iters=3      bt=0      0.0001s [trivial]
✓ preset:smiley              5×5      iters=5      bt=0      0.0001s [easy]
✓ preset:ship               10×10    iters=12     bt=3      0.0021s [medium]
...
----------------------------------------------------------------------
Solved: 16/16  Total time: 0.234s
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ --cov=nonogram --cov-report=term-missing
```

**Test suite:** 100 tests across 2 files:
- `tests/test_bug_hunt.py` — 11 regression tests from Phase 3 bug hunt
- `tests/test_nonogram.py` — 89 comprehensive tests covering all modules

All tests pass. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Known Issues (Resolved)

All bugs found during the Phase 3 bug hunt have been fixed and verified with
tests in `tests/test_bug_hunt.py` (11 tests, all passing).

1. **Dead code in `save_png`** — Redundant loop removed.
2. **Misleading `_propagate` docstring** — Updated to match implementation.
3. **`Board.from_dict` grid validation** — Now validates dimensions.
4. **`PuzzleIO.load_non` line count validation** — Now raises `ValueError`.
5. **`Player.check()` with no grid** — Solves clues to get solution first.
6. **`LineSolver` empty clue handling** — Empty clues now mark all cells EMPTY.
7. **`LineSolver` FILLED cell coverage** — Leftmost/rightmost now accounts for
   FILLED cells.
8. **`arrow.json` unsolvable puzzle** — Replaced with valid design.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

1. Clone the repo and install: `pip install -e ".[dev]"`
2. Run tests: `python -m pytest tests/ -v`
3. Make changes with tests and docstrings
4. Ensure all tests pass before committing

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

### v3.0.0 (2026-07-01)
- Added web server, batch solver, benchmark suite, solver stats, config management
- Added 4 new CLI subcommands (total: 12)
- Added GitHub Actions CI, examples, architecture docs
- Added 89 new tests (total: 100, all passing)
- Fixed pyproject.toml build-backend

### v2.0.0 (2026-07-01)
- Added MRV heuristic, solution counter, 10 presets, difficulty analyzer
- Added NON format, PNG/SVG/ANSI/HTML rendering
- Fixed 8 bugs with 11 regression tests

### v1.0.0 (2026-07-01)
- Initial release: solver, generator, player, JSON I/O

## Roadmap

- [ ] Line solver with DP-based full feasibility (faster than backtracking)
- [ ] More puzzle formats (XML, GNF, WebPBN)
- [ ] Multi-color nonogram support (colored clues)
- [ ] Puzzle editor GUI (tkinter or web-based)
- [ ] Solver visualization (step-by-step propagation animation)
- [ ] Puzzle database with import/export
- [ ] Difficulty-based puzzle recommendation
- [ ] Parallel batch solving with multiprocessing
- [ ] Timed challenge mode for the player
- [ ] Puzzle symmetry detection and generation

## License

MIT — see [LICENSE](LICENSE)