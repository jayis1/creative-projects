# 🧩 CSP Solver

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-141%20passing-brightgreen.svg)]()

A comprehensive, from-scratch implementation of Constraint Satisfaction Problem (CSP) solving algorithms. Features AC-3 arc consistency, backtracking with MRV/LCV heuristics, forward checking, MAC, and built-in problem generators for Sudoku, N-Queens, graph coloring, cryptarithms, Latin squares, magic squares, and job shop scheduling.

## 📑 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python Library](#python-library)
  - [Command Line](#command-line)
  - [Configuration Files](#configuration-files)
  - [Serialization](#serialization)
- [Architecture](#architecture)
  - [Core Pipeline](#core-pipeline)
  - [Module Overview](#module-overview)
  - [Algorithm Details](#algorithm-details)
- [Built-in Problems](#built-in-problems)
- [Visualization](#visualization)
- [Examples](#examples)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Changelog](#changelog)

## ✨ Features

- **AC-3 Algorithm** — Enforces arc consistency to prune domains before and during search, with optimized singleton-domain handling and chain propagation
- **Backtracking Search** with configurable heuristics:
  - **MRV** (Minimum Remaining Values) — selects the most constrained variable first
  - **Degree Heuristic** — tiebreaker for MRV; picks variable involved in most constraints
  - **LCV** (Least Constraining Value) — orders values to minimize pruning of neighbors
- **Forward Checking** — prunes neighbor domains after each assignment
- **MAC** (Maintaining Arc Consistency) — full arc consistency propagation during search
- **Strategy Comparison** — built-in utility to compare different solving strategies
- **Progress Callbacks** — hook into the search process for monitoring and visualization
- **Solver Statistics** — assignments tried, backtracks, domain prunes, timing
- **Built-in problem generators**: Sudoku, N-Queens, Graph Coloring, Cryptarithm, Latin Square, Magic Square, Job Shop Scheduling
- **Configuration system** — JSON/YAML/TOML config files for solver settings
- **Serialization** — JSON export/import for CSP problems and solutions
- **Visualization** — pretty ASCII rendering for all problem types
- **CLI interface** with subcommands, strategy comparison, and JSON output
- **Comprehensive test suite** with 141 tests covering all modules

## 🔧 Installation

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/constraint-solver

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode (with test dependencies)
pip install -e ".[dev]"
```

### Optional Dependencies

For YAML configuration file support:
```bash
pip install pyyaml
```

For pretty console output:
```bash
pip install rich
```

## 🚀 Quick Start

```python
from csp_solver import CSPSolver, sudoku_csp, n_queens_csp

# Solve a Sudoku puzzle
grid = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]
csp = sudoku_csp(grid)
solver = CSPSolver(use_mac=True)
result = solver.solve(csp)
print(f"Satisfiable: {result.is_satisfiable}")
print(f"Time: {result.stats.elapsed:.4f}s")
print(f"Assignments: {result.stats.assignments_tried}")

# Solve 8-Queens
csp = n_queens_csp(8)
result = solver.solve(csp)
print(f"Solution found: {result.is_satisfiable}")
```

## 📖 Usage

### Python Library

```python
from csp_solver import (
    CSPSolver, CSP, Variable, Constraint,
    sudoku_csp, generate_sudoku, n_queens_csp, count_n_queens_solutions,
    graph_coloring_csp, cryptarithm_csp, latin_square_csp, magic_square_csp,
    job_shop_csp, graph_csp_from_edges,
    format_sudoku_solution, format_queens_solution,
    SolverConfig, SolverProgress,
    render_sudoku, render_queens, render_graph_coloring,
    export_csp, save_solution,
    compare_strategies,
    AUSTRALIA_EDGES, US_REGIONS_EDGES,
)

# ─── Configuration ───────────────────────────────────────────────

# Create solver from config
config = SolverConfig(use_mac=True, timeout=30.0, log_level="INFO")
solver = config.create_solver()

# Save/load config
config.to_file("my_config.json")
loaded = SolverConfig.from_file("my_config.json")

# ─── Progress Tracking ───────────────────────────────────────────

from csp_solver import BacktrackingSolver

progress = SolverProgress(log_interval=100)
progress.start(csp)
bt = BacktrackingSolver(use_mac=True, progress_callback=progress.callback)
result = bt.solve(csp)
summary = progress.summary()
print(f"Steps: {summary['total_steps']}, Time: {summary['total_time']}s")

# ─── Pretty Visualization ────────────────────────────────────────

result = solver.solve(sudoku_csp(grid))
print(render_sudoku(result.assignment))         # Box-style grid
print(render_queens(result.assignment, 8))      # Chess board
print(render_graph_coloring(result.assignment, edges))  # With emoji

# ─── Serialization ───────────────────────────────────────────────

# Export CSP definition
data = export_csp(csp)
print(f"Variables: {data['num_variables']}")

# Save solution to JSON
save_solution(result.assignment, "solution.json", method=result.method)

# ─── Strategy Comparison ─────────────────────────────────────────

csp = n_queens_csp(8)
results = compare_strategies(csp)
for r in results:
    print(f"{r['strategy']}: {r['time']}s, {r['assignments']} assignments")

# ─── All Solutions ──────────────────────────────────────────────

solutions = solver.solve_all(csp, max_solutions=10)
print(f"Found {len(solutions)} solutions")

# ─── Job Shop Scheduling ─────────────────────────────────────────

jobs = {"J1": (3, "R1"), "J2": (2, "R1"), "J3": (4, "R2")}
csp = job_shop_csp(jobs)
result = solver.solve(csp)

# ─── Custom CSP ──────────────────────────────────────────────────

csp = CSP()
csp.add_variable(Variable("X", domain={1, 2, 3}))
csp.add_variable(Variable("Y", domain={1, 2, 3}))
csp.add_constraint(Constraint(
    ("X", "Y"),
    lambda a: a["X"] != a["Y"],
    pair_check=lambda x, y: x != y,
    name="X≠Y",
))
result = solver.solve(csp)
```

### Command Line

```bash
# Solve Sudoku
csp-solver sudoku --grid "530070000600019000098000006800060003400803001700020000060000028000400500000070009"

# Generate and solve a random Sudoku
csp-solver sudoku --generate --difficulty hard --seed 42

# Solve N-Queens with verbose output
csp-solver queens --n 8 -vv

# Count all N-Queens solutions
csp-solver queens --n 8 --count

# Solve cryptarithm
csp-solver cryptarithm --words SEND MORE --result MONEY

# Graph coloring (Australia map)
csp-solver coloring --colors 3

# US regions coloring
csp-solver coloring --map us --colors 4

# Latin Square
csp-solver latin --n 5

# Magic Square
csp-solver magic --n 3

# Job shop scheduling
csp-solver schedule --jobs "J1:3:R1,J2:2:R1,J3:4:R2"

# JSON output
csp-solver queens --n 8 --json

# Pretty rendering
csp-solver queens --n 8 --pretty

# Compare strategies
csp-solver queens --n 8 --compare

# Save solution to file
csp-solver queens --n 8 --output solution.json

# Use a config file
csp-solver queens --n 8 --config my_config.json

# Disable heuristics for comparison
csp-solver sudoku --no-mac --no-mrv --no-lcv

# Export CSP definition
csp-solver queens --n 8 --export-csp queens_csp.json
```

### Configuration Files

Create a JSON config file to customize solver behavior:

```json
{
  "use_mrv": true,
  "use_degree": true,
  "use_lcv": true,
  "use_forward_check": false,
  "use_mac": true,
  "preprocess_ac3": true,
  "timeout": 30.0,
  "max_solutions": 10,
  "log_level": "WARNING"
}
```

Then use it:
```bash
csp-solver queens --n 12 --config solver_config.json
```

Programmatic usage:
```python
from csp_solver import SolverConfig

config = SolverConfig.from_file("solver_config.json")
solver = config.create_solver()
```

### Serialization

```python
from csp_solver import export_csp, save_csp, save_solution, load_csp

# Export CSP to dictionary
data = export_csp(csp)
print(f"Variables: {data['num_variables']}")

# Save CSP to file
save_csp(csp, "problem.json")

# Load CSP from file (variables and domains only)
loaded = load_csp("problem.json")

# Save solution
save_solution(result.assignment, "solution.json", 
              stats=result.stats, method=result.method)
```

## 🏗️ Architecture

### Core Pipeline

```
Input CSP → AC-3 Preprocessing → Backtracking Search → Solution
                                    ↓
                              Variable Selection (MRV + Degree)
                                    ↓
                              Value Ordering (LCV)
                                    ↓
                              Constraint Propagation (MAC/FC)
```

1. **AC-3** reduces domains by removing values that cannot participate in any consistent assignment
2. **Backtracking** assigns values to variables one at a time
3. **MRV** picks the variable with the fewest remaining values (most constrained)
4. **LCV** picks the value that eliminates the fewest options for neighbors
5. **MAC** re-runs arc consistency after each assignment for aggressive pruning

### Module Overview

```
constraint-solver/
├── csp_solver/
│   ├── __init__.py         # Package exports & version
│   ├── csp.py              # Core data structures (Variable, Constraint, CSP)
│   ├── ac3.py              # AC-3 arc consistency, node consistency, domain reduction
│   ├── backtrack.py        # Backtracking solver with heuristics and stats
│   ├── solver.py           # High-level solver, solve_all, compare_strategies
│   ├── problems.py         # Problem generators (Sudoku, Queens, Coloring, etc.)
│   ├── problems_extra.py   # Additional generators (Job Shop, Knight's Tour, generic graph)
│   ├── cli.py              # Command-line interface with subcommands
│   ├── config.py           # Configuration management (JSON/YAML/TOML)
│   ├── logging_utils.py    # Logging and progress tracking
│   ├── visualization.py    # Pretty ASCII rendering for all problem types
│   └── serialization.py    # JSON export/import for CSPs and solutions
├── tests/
│   ├── test_solver.py      # Core test suite (84 tests)
│   ├── test_bug_hunt.py    # Bug regression tests (11 tests)
│   └── test_new_features.py # New feature tests (46 tests)
├── examples/               # Usage examples
│   ├── sudoku_example.py
│   ├── queens_example.py
│   └── coloring_crypto_example.py
│   └── config_example.py
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI
├── pyproject.toml           # Package configuration
├── CONTRIBUTING.md          # Contribution guidelines
├── LICENSE                  # MIT License
└── README.md                # This file
```

### Algorithm Details

#### AC-3
The algorithm maintains a queue of arcs (directed edges between variables). For each arc (Xi, Xj), it removes values from Xi's domain that have no supporting value in Xj. If Xi's domain changes, all arcs (Xk, Xi) are re-queued. An optimized path handles singleton domains for faster pruning.

**Time complexity**: O(c · d³) where c = number of constraints, d = max domain size.

#### MRV Heuristic
Selects the unassigned variable with the fewest legal values. This "fail-first" strategy prunes the search tree early by detecting dead ends sooner.

#### Degree Heuristic
When MRV ties, picks the variable involved in the most constraints with unassigned variables, maximizing future pruning opportunities.

#### LCV Heuristic
Orders values by how many options they leave for neighboring variables. The least constraining value is tried first, reducing the chance of dead ends.

#### MAC (Maintaining Arc Consistency)
After each assignment, runs AC-3 on arcs from the assigned variable's neighbors. More powerful than forward checking because it propagates constraints transitively through the constraint graph.

#### Strategy Comparison
The `compare_strategies` function tests five configurations:
| Strategy | Description |
|----------|-------------|
| BT | Plain backtracking, no heuristics |
| BT+MRV | Variable ordering only |
| BT+MRV+LCV | Variable and value ordering |
| FC+MRV+LCV | Forward checking with heuristics |
| MAC+MRV+LCV | Full constraint propagation — **fastest in practice** |

## 🧮 Built-in Problems

| Problem | Generator | CLI Command | Description |
|---------|-----------|-------------|-------------|
| Sudoku | `sudoku_csp(grid)` | `csp-solver sudoku` | 9×9 Sudoku puzzles |
| N-Queens | `n_queens_csp(n)` | `csp-solver queens --n 8` | Place N non-attacking queens |
| Graph Coloring | `graph_coloring_csp(edges, k)` | `csp-solver coloring --colors 3` | Color graph with k colors |
| Cryptarithm | `cryptarithm_csp(words, result)` | `csp-solver cryptarithm` | SEND+MORE=MONEY etc. |
| Latin Square | `latin_square_csp(n)` | `csp-solver latin --n 5` | n×n Latin Square |
| Magic Square | `magic_square_csp(n)` | `csp-solver magic --n 3` | n×n Magic Square |
| Job Shop | `job_shop_csp(jobs)` | `csp-solver schedule` | Job scheduling |
| Generic Graph | `graph_csp_from_edges(edges, k)` | — | Custom graph CSP |

## 🎨 Visualization

All problem types have pretty rendering with Unicode box-drawing characters:

```python
from csp_solver import render_sudoku, render_queens, render_graph_coloring

# Sudoku with box separators
print(render_sudoku(assignment))

# N-Queens chess board
print(render_queens(assignment, 8))

# Graph coloring with emoji and verification
print(render_graph_coloring(assignment, edges, "Australia"))
```

Example output (N-Queens):
```
  ────────────────
0│· ♛ · · · · · ·
1│· · · · ♛ · · ·
2│· · · · · · · ♛
3│♛ · · · · · · ·
4│· · ♛ · · · · ·
5│· · · · · ♛ · ·
6│· · · ♛ · · · ·
7│· · · · · · ♛ ·
  ────────────────
```

## 📁 Examples

See the `examples/` directory for complete scripts:

- `sudoku_example.py` — Solving, generating, and comparing strategies
- `queens_example.py` — N-Queens with progress tracking
- `coloring_crypto_example.py` — Graph coloring and cryptarithms
- `config_example.py` — Configuration files and progress tracking

Run them:
```bash
python examples/sudoku_example.py
python examples/queens_example.py
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=csp_solver --cov-report=term-missing

# Run specific test file
pytest tests/test_solver.py -v
pytest tests/test_new_features.py -v
```

**Test coverage**: 141 tests covering:
- Core data structures (Variable, Constraint, CSP)
- AC-3 algorithm (arc consistency, node consistency, domain reduction)
- Backtracking solver (MRV, LCV, degree heuristic, MAC, FC)
- High-level solver (CSPSolver, solve_all, compare_strategies)
- All problem generators (Sudoku, Queens, Coloring, Cryptarithm, Latin, Magic)
- Configuration system
- Serialization (export/import)
- Visualization rendering
- Progress tracking
- CLI argument parsing
- Bug regression tests

## 🗺️ Roadmap

- [ ] **AC-4 algorithm** — alternative arc consistency with better worst-case complexity
- [ ] **Constraint learning** — no-good recording during search
- [ ] **Parallel solving** — multi-threaded strategy comparison
- [ ] **Interactive mode** — step-by-step solving visualization
- [ ] **Web dashboard** — real-time search tree visualization
- [ ] **Weighted CSP** — soft constraints with penalty-based optimization
- [ ] **CSP analyzer** — detect problem structure (trees, bipartite graphs)
- [ ] **Benchmarking suite** — standardized problem instances with known solutions
- [ ] **Symmetry breaking** — automatic detection and breaking of problem symmetries
- [ ] **More problem types** — KenKen, Kakuro, Hamiltonian path, crosswords

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Development setup
- Code style requirements
- Adding new problem generators
- Writing tests
- Commit message conventions

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 📋 Changelog

### v2.0.0 (2026-06-14) — Comprehensive Improvement

**New Features:**
- 🆕 **Configuration system** (`SolverConfig`) — load/save solver settings from JSON/YAML/TOML files
- 🆕 **Progress tracking** (`SolverProgress`) — monitor search with callbacks, depth histograms
- 🆕 **Visualization module** — pretty ASCII rendering with Unicode box-drawing for all problem types
- 🆕 **Serialization** — JSON export/import for CSP definitions and solutions
- 🆕 **Job Shop Scheduling** problem generator (`job_shop_csp`)
- 🆕 **Knight's Tour** problem generator (`knights_tour_csp`)
- 🆕 **Generic Graph CSP** from edge list (`graph_csp_from_edges`)
- 🆕 **Enhanced CLI** — subcommands, `--pretty` flag, `--config` flag, `--output`/`--export-csp` flags, verbosity (`-v`/`-vv`)
- 🆕 **GitHub Actions CI** — automated testing on Python 3.9–3.12
- 🆕 **`pyproject.toml`** — installable package with `[dev]` extras
- 🆕 **`CONTRIBUTING.md`** and **`LICENSE`** files
- 🆕 **Examples directory** with complete usage scripts

**Architecture:**
- 🏗️ Modular package with 11 modules (was 6)
- 🏗️ Clean separation: core (`csp.py`, `ac3.py`, `backtrack.py`, `solver.py`), problems, utilities, CLI
- 🏗️ Type hints throughout all modules
- 🏗️ Logging infrastructure with configurable levels

**Tests:**
- ✅ 141 tests total (up from 95)
- ✅ 46 new tests for config, serialization, visualization, new problem types, CLI, integration
- ✅ All tests pass

### v1.1.0 — Bug Fixes
- Fixed `solve_all()` mutating original CSP (deep copy fix)
- Fixed `compare_strategies()` destroying strategy dicts (dict comprehension fix)
- Fixed AC-3 empty domain detection (pre-check before processing)
- Added 11 bug regression tests

### v1.0.0 — Initial Release
- AC-3, backtracking with MRV/LCV/degree heuristics
- Forward checking and MAC constraint propagation
- Sudoku, N-Queens, graph coloring, cryptarithm, Latin square, magic square
- CLI interface
- 84 tests