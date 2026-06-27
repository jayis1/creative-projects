# simplex-solver

> **Exact-arithmetic linear & integer programming in pure Python — no NumPy, no SciPy, no external solvers.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 60](https://img.shields.io/badge/tests-60%20passed-brightgreen.svg)](#testing)
[![Build: CI](https://img.shields.io/badge/CI-github%20actions-lightgrey.svg)](../../.github/workflows/simplex-solver-ci.yml)
[![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-blue.svg)](#changelog)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [JSON Problem Format](#json-problem-format)
  - [LP Format (CPLEX)](#lp-format-cplex)
  - [MPS Format](#mps-format)
  - [Configuration Files](#configuration-files)
- [Examples](#examples)
- [Architecture](#architecture)
  - [Tableau Construction](#tableau-construction)
  - [Phase I](#phase-i)
  - [Phase II](#phase-ii)
  - [Dual Extraction](#dual-extraction)
  - [Branch-and-Bound](#branch-and-bound)
  - [Gomory Cuts](#gomory-cuts)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**simplex-solver** implements the two-phase primal Simplex method from
scratch using Python's `fractions.Fraction` for *bit-exact* rational
arithmetic.  Every pivot, ratio test, and reduced-cost computation is
performed with exact rationals — no floating-point roundoff can pollute
the solution.  This makes it suitable for educational use, verification of
results from floating-point solvers, and problems where numerical
robustness is critical.

The solver supports:

- **Linear Programming** (LP): `<=`, `>=`, `=` constraints; free, bounded,
  and shifted variables; unbounded/infeasible detection; dual values and
  reduced costs.
- **Mixed-Integer Programming** (MILP): branch-and-bound with best-first,
  depth-first, or breadth-first search; Gomory fractional cuts; node and
  time limits.
- **File I/O**: JSON, CPLEX LP format, and MPS format (read + write, with
  round-trip support).
- **Sensitivity Analysis**: objective coefficient ranges and RHS ranges via
  perturbation + bisection.
- **CLI**: `solve`, `convert`, `batch`, `validate`, `mps-info`, `config`,
  `version` subcommands with configurable output formats.
- **Configuration**: JSON/TOML/YAML config files for persistent solver
  settings.

---

## Features

### Linear Programming
- **Two-phase primal Simplex method** with exact rational arithmetic
  (`fractions.Fraction`) — no floating-point roundoff during pivoting.
- **Phase I** minimises the sum of artificial variables to find a feasible
  starting basis; **Phase II** optimises the original objective.
- **Bland's rule** (default) for anti-cycling, or **Dantzig's rule**
  (most-positive reduced cost) for speed.
- **Constraint types**: `<=`, `>=`, `=`.
- **Variable bounds**: non-negative (default), lower-bounded (shifted),
  upper-bounded (explicit constraint), free variables (split into
  `x⁺ − x⁻`), and flipped variables (`x = ub − y`).
- **Dual values** (shadow prices) and **reduced costs** extracted from the
  optimal tableau.
- **Unbounded** and **infeasible** detection.
- **Iteration counting**: the solver reports the total number of simplex
  pivots performed.
- **Problem validation**: `LPProblem.validate()` checks for unknown
  variables, inconsistent bounds, duplicate names, and missing fields.

### Mixed-Integer Programming
- **Branch-and-bound** with best-first, depth-first, or breadth-first
  search strategies and incumbent pruning.
- **Gomory fractional cuts** generated from the simplex tableau to tighten
  relaxations and accelerate convergence.
- Supports both pure-integer and mixed-integer problems.
- Tightens bounds at each branch node (floor/ceiling branching).
- **Node limit** (`max_nodes`) and **time limit** (`time_limit` in seconds).
- Correctly handles infeasible subproblems (negative-rhs normalisation
  ensures Phase I detects infeasibility).

### File I/O
- **JSON** problem specification for programmatic use.
- **CPLEX LP format** reader and writer (human-readable text format).
- **MPS format** reader and writer (fixed-column and free-format compatible).
- **Round-trip** support: write to any format and read back produces an
  equivalent problem.
- **Format conversion** via the `convert` CLI subcommand.

### Analysis Tools
- **Sensitivity analysis**: objective coefficient ranges and RHS ranges via
  basis-change detection with binary search.
- **Pretty-printing**: boxed table output (`--table`) and human-readable
  text output (`--pretty`).

### CLI
- `solve` — solve an LP/MILP from JSON, LP, or MPS, with optional
  sensitivity analysis and configurable output format (JSON/text/table).
- `convert` — convert between JSON, LP, and MPS formats.
- `batch` — solve multiple problem files and print a summary table.
- `validate` — validate a problem file and report issues.
- `mps-info` — inspect an MPS file with detailed constraint listing.
- `config` — display or initialise a solver configuration file.
- `version` — print version.
- Supports `python -m simplex` as an entry point.
- Global flags: `--config`, `--log-level`, `--verbose`, `--quiet`.

### Configuration
- **JSON / TOML / YAML** config files for persistent solver settings.
- Auto-discovery: looks for `simplex.json`, `simplex.toml`, `simplex.yaml`
  in the current directory, then `~/.simplex/config.json`.
- CLI flags override config file settings.
- Configurable: `max_iter`, `max_nodes`, `bland`, `use_cuts`, `eps`,
  `log_level`, `output_format`, `sensitivity`.

---

## Installation

### From source (development)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/simplex-solver
pip install -e .
```

### With optional dependencies

```bash
# For YAML config support:
pip install -e ".[yaml]"

# For development (includes pytest, ruff, etc.):
pip install -e ".[dev]"
```

### Requirements

- Python 3.10 or later (uses `match`-compatible syntax, `|` union types).
- No runtime dependencies — the solver uses only the Python standard library.
- Optional: `pyyaml` for YAML config files, `tomli` for TOML on Python < 3.11.
- Development: `pytest`, `ruff`.

---

## Quick Start

```bash
# Solve the diet problem (minimise cost subject to nutrient minimums)
python -m simplex solve examples/diet.json --pretty

# Solve with boxed table output
python -m simplex solve examples/diet.json --table

# Solve a MILP (0/1 knapsack) with depth-first search
python -m simplex solve examples/knapsack.json --pretty --strategy depth-first

# Convert JSON to CPLEX LP format
python -m simplex convert examples/production.json /tmp/production.lp

# Solve all example problems at once
python -m simplex batch "examples/*.json"

# Run sensitivity analysis
python -m simplex solve examples/diet.json --pretty --sensitivity

# Validate a problem file
python -m simplex validate examples/production.json
```

---

## Usage

### Python API

```python
from simplex import LPProblem, SimplexSolver, MILPSolver, SearchStrategy

# Define a linear program
lp = LPProblem(
    name="diet",
    objective="min",
    variables=("bread", "milk"),
    objective_coeffs={"bread": 2, "milk": 3},
    constraints=[
        {"coeffs": {"bread": 1, "milk": 3}, "relation": ">=", "rhs": 5, "name": "calories"},
        {"coeffs": {"bread": 2, "milk": 1}, "relation": ">=", "rhs": 4, "name": "vitamins"},
    ],
)

# Validate before solving
errors = lp.validate()
assert not errors

# Solve
result = SimplexSolver().solve(lp)
print(f"Status: {result.status.value}")
print(f"Objective: {result.objective_value}")
print(f"Solution: {result.solution}")
print(f"Duals: {result.duals}")
print(f"Pivots: {result.iterations}")

# Mixed-integer programming (0/1 knapsack)
milp = LPProblem(
    name="knapsack",
    objective="max",
    variables=("i1", "i2", "i3"),
    objective_coeffs={"i1": 60, "i2": 50, "i3": 70},
    constraints=[
        {"coeffs": {"i1": 5, "i2": 3, "i3": 4}, "relation": "<=", "rhs": 10, "name": "capacity"},
    ],
    bounds={"i1": (0, 1), "i2": (0, 1), "i3": (0, 1)},
    integer={"i1", "i2", "i3"},
)
result = MILPSolver(max_nodes=1000, strategy="depth-first").solve(milp)
print(f"MILP objective: {result.objective_value}")
print(f"Nodes explored: {result.iterations}")
```

#### Pretty-printing results

```python
from simplex import format_result, format_tableau

result = SimplexSolver().solve(lp)
print(format_result(result, lp))      # boxed table
print(format_tableau(lp, result))      # ASCII summary
```

#### Format conversion

```python
from simplex import write_lp, write_mps, read_lp, read_mps

# Write to CPLEX LP format
write_lp(lp, "diet.lp")

# Write to MPS format
write_mps(lp, "diet.mps")

# Read back
lp2 = read_lp("diet.lp")
lp3 = read_mps("diet.mps")
```

#### Configuration

```python
from simplex import SolverConfig, load_config, save_config

# Load config from file (or defaults if not found)
cfg = load_config("myconfig.json")

# Modify and save
cfg = cfg.merge({"max_iter": 50000, "bland": False})
save_config(cfg, "myconfig.json")
```

### CLI

```bash
# Solve from JSON with pretty output
python -m simplex solve examples/diet.json --pretty

# Solve with boxed table output
python -m simplex solve examples/diet.json --table

# Solve with JSON output (default)
python -m simplex solve examples/diet.json

# Solve with sensitivity analysis
python -m simplex solve examples/diet.json --pretty --sensitivity

# Solve MILP with depth-first search strategy
python -m simplex solve examples/knapsack.json --pretty --strategy depth-first

# Solve MILP with time limit (seconds)
python -m simplex solve examples/knapsack.json --pretty --time-limit 5.0

# Solve using Dantzig's rule
python -m simplex solve examples/production.json --pretty --dantzig

# Validate a problem file
python -m simplex validate examples/production.json

# Inspect MPS file
python -m simplex mps-info examples/problem.mps

# Convert between formats
python -m simplex convert examples/diet.json output.lp
python -m simplex convert examples/diet.json output.mps
python -m simplex convert output.lp output.json

# Batch solve multiple files
python -m simplex batch "examples/*.json"

# Display or initialise configuration
python -m simplex config
python -m simplex config --init --path ~/.simplex/config.json --set max_iter=50000

# Use a config file
python -m simplex --config myconfig.json solve examples/diet.json --pretty

# Version
python -m simplex version
```

### JSON Problem Format

```json
{
  "name": "diet",
  "objective": "min",
  "variables": ["bread", "milk"],
  "objective_coeffs": {"bread": 2, "milk": 3},
  "constraints": [
    {"coeffs": {"bread": 1, "milk": 3}, "relation": ">=", "rhs": 5, "name": "calories"},
    {"coeffs": {"bread": 2, "milk": 1}, "relation": ">=", "rhs": 4, "name": "vitamins"}
  ],
  "bounds": {"bread": [0, null], "milk": [0, null]},
  "integer": []
}
```

### LP Format (CPLEX)

```
\ Problem: diet

Minimize
  obj: + 2 bread + 3 milk

Subject To
  calories: + bread + 3 milk >= 5
  vitamins: + 2 bread + milk >= 4

End
```

### MPS Format

The solver reads and writes standard MPS files with support for ROWS,
COLUMNS, RHS, RANGES, BOUNDS, and integer markers (MARKER INTORG/INTEND).

### Configuration Files

Create a `simplex.json` in your project directory or `~/.simplex/config.json`:

```json
{
  "max_iter": 50000,
  "max_nodes": 10000,
  "bland": true,
  "use_cuts": true,
  "eps": 1e-7,
  "log_level": "WARNING",
  "output_format": "json",
  "sensitivity": false
}
```

Or use TOML:

```toml
max_iter = 50000
bland = false
log_level = "INFO"
```

---

## Examples

| File | Description | Type |
|------|-------------|------|
| `examples/diet.json` | Classic diet problem (minimise cost subject to nutrient minimums) | LP |
| `examples/knapsack.json` | 0/1 knapsack problem (5 items) | MILP |
| `examples/production.json` | Production planning (3 products, 3 resources) | LP |
| `examples/transport.json` | Transportation problem (2 suppliers, 3 customers) | LP |
| `examples/blending.json` | Blending problem (quality constraints) | LP |
| `examples/scheduling.json` | Staff scheduling (7 days, integer staffing levels) | MILP |
| `examples/portfolio.json` | Portfolio optimisation (risk budget, asset limits) | LP |

---

## Architecture

```
simplex-solver/
├── simplex/
│   ├── __init__.py       # Public API exports
│   ├── __main__.py        # python -m simplex entry point
│   ├── problem.py         # LPProblem, LPResult, LPStatus data classes
│   ├── simplex.py         # Two-phase primal Simplex (Tableau class)
│   ├── integer.py         # MILP branch-and-bound + Gomory cuts
│   ├── mps.py             # MPS format reader/writer
│   ├── formatting.py      # LP format reader/writer + pretty-printing
│   ├── sensitivity.py     # Post-optimality sensitivity analysis
│   ├── config.py          # Configuration file support
│   ├── cli.py             # Command-line interface
│   └── logging_utils.py  # Logging configuration
├── tests/
│   ├── test_basic.py      # Core LP tests (8)
│   ├── test_enhanced.py   # Iteration counting, validation, MPS (10)
│   ├── test_bughunt.py    # Bug-hunt regression tests (6)
│   ├── test_formatting.py # LP format round-trip tests (6)
│   ├── test_config.py     # Configuration tests (8)
│   ├── test_milp.py       # MILP strategy and cut tests (10)
│   └── test_cli.py        # CLI subcommand tests (12)
├── examples/              # Example problem files
├── pyproject.toml         # Package metadata + build config
├── CONTRIBUTING.md        # Contribution guidelines
├── LICENSE               # MIT license
└── README.md             # This file
```

### Tableau Construction

The `Tableau` class transforms an `LPProblem` into a standard simplex
tableau:

1. **Variable transformations**:
   - Free variables `(−∞, +∞)` → split `x = x⁺ − x⁻`, both `≥ 0`.
   - Lower bound only `(−∞, ub]` → substitute `x = ub − y`, `y ≥ 0`.
   - Lower bound shift `x ≥ lb` → substitute `x' = x − lb`, `x' ≥ 0`.
   - Upper bounds `x ≤ ub` → explicit `≤` constraint row added.

2. **Constraint rows**: each constraint gets a slack (for `≤`), surplus +
   artificial (for `≥`), or artificial (for `=`). **Negative-rhs rows** are
   normalised by negating the entire row *before* fixing the basic
   variable's identity coefficient to +1, ensuring the initial basis is
   always feasible and the identity column property holds.

3. **Initial basis**: slack variables (for `≤` with non-negative rhs) or
   artificial variables (for `≥`, `=`, and `≤` with negative rhs). All
   basic variables have coefficient +1 in their row (identity column), and
   all rhs values are non-negative.

### Phase I

Minimises `Σ artificials` (equivalently maximises `−Σ artificials`). The
reduced costs are computed by pricing out the artificial basic variables
against each non-basic column. If the optimal artificial sum is positive,
the problem is **infeasible**. Otherwise, artificials are driven out of the
basis (pivoting on non-artificial columns with nonzero row coefficients),
and the original objective is restored by recomputing reduced costs against
the feasible basis. Artificial variables are permanently barred from
re-entering the basis in Phase II.

### Phase II

Standard primal simplex: at each iteration, select an entering variable
(positive reduced cost), perform the ratio test to find the leaving variable
(minimum ratio, unbounded if none), and pivot. Bland's rule prevents
cycling by always selecting the smallest-index improving variable. The
pivot count is tracked and reported in the result.

### Dual Extraction

For a `≤` constraint, the dual (shadow price) is `−reduced_cost(slack)`.
For a `≥` constraint, it's `reduced_cost(surplus)`. For `=`, it's
`−reduced_cost(artificial)`. For `min` problems (where costs are negated
internally), duals are negated to match the original sense.

### Branch-and-Bound

The `MILPSolver` solves LP relaxations at each node. When a fractional
integer variable is found, two child nodes are created with tightened
bounds (`x ≤ floor` and `x ≥ ceil`). Three search strategies are supported:

- **Best-first** (default): explores the node with the best relaxation bound
  first (priority queue keyed by relaxation objective).
- **Depth-first**: dives deep quickly, which can find good incumbents fast.
  Uses a stack (LIFO) with reversed node IDs for tie-breaking.
- **Breadth-first**: explores nodes in FIFO order (shallowest first). Uses
  a deque.

Pruning occurs when a relaxation bound is worse than the incumbent. The
solver correctly detects infeasible subproblems via Phase I.

### Gomory Cuts

At each branch-and-bound node, Gomory fractional cuts are generated from
the simplex tableau rows of fractional basic integer variables. For each
such variable with fractional value `b_i`, the cut is:

```
Σ_j  f(a_{ij}) * x_j  ≥  f(b_i)
```

where `f()` is the fractional-part function (mapping to `[0, 1)`) and `j`
ranges over non-basic structural columns. These cuts tighten the LP
relaxation, reducing the number of branch-and-bound nodes needed.

---

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and fixed:

1. **Artificial variables re-entering basis in Phase II** — After Phase I
   drove artificials out of the basis, they could re-enter during Phase II
   (their reduced cost was positive under the restored objective), undoing
   Phase I's work and returning a trivially zero solution. **Fix**:
   Artificials are permanently barred from re-entering the basis in
   `_select_entering`.

2. **Dual sign error** — The shadow price for `<=` constraints was reported
   with the wrong sign. **Fix**: Corrected sign extraction.

3. **Negative-rhs constraint handling** — Constraints with negative rhs
   after variable shifts would have their slack/surplus coefficient
   negated, breaking the identity column. **Fix**: Full row negation before
   establishing the identity coefficient.

4. **MILP `_apply_bounds` convoluted logic** — Dead, unreachable branches
   and duplicate return. **Fix**: Simplified to clean max/min tightening.

5. **MILP `floor_v` computation** — Incorrect for negative values. **Fix**:
   Replaced with `math.floor()`.

6. **MILP node_id mismatch in priority key** — Heap priority tuple was
   off-by-one. **Fix**: Create nodes first, then push.

7. **Phase I obj_const not restored** — Shift constant lost during
   restoration. **Fix**: Save and re-add the shift constant.

8. **MPS INTEND marker malformed** — Missing column name field. **Fix**:
   Include the last variable's name.

9. **MPS RANGES L-row handling** — Overwrote constraint instead of adding
   both. **Fix**: Generate both `<=` and `>=` constraints.

10. **Dead code: `_frac_part`** — Unused and incorrect. **Fix**: Removed.

11. **Unused imports** — `Iterable`, `Sequence` imported but never used.
    **Fix**: Removed.

### Issues found and fixed during comprehensive improvement (v2.0.0)

12. **MILP breadth-first search returned suboptimal results** — The
    priority tuple used `(0, node_id)` instead of the relaxation objective,
    causing premature pruning. **Fix**: All strategies now store the
    negated relaxation objective in the priority for correct pruning.

13. **LP reader did not merge multi-line bounds** — Multiple bound lines
    for the same variable (e.g., `1 <= y` on one line and `y <= 8` on the
    next) would overwrite each other. **Fix**: Merge bounds by taking the
    max of lower bounds and min of upper bounds.

14. **LP reader did not default non-free variables to lower bound 0** —
    Variables with only an upper bound line were treated as unbounded
    below. **Fix**: Track explicitly declared free variables and default
    others to lower bound 0.

---

## Changelog

### v2.0.0 — Comprehensive Improvement

**New modules:**
- `formatting.py` — CPLEX LP format reader/writer + pretty-printing
  (`format_result`, `format_tableau`)
- `config.py` — JSON/TOML/YAML configuration file support (`SolverConfig`)
- `logging_utils.py` — Structured logging configuration

**New CLI subcommands:**
- `convert` — Convert between JSON, LP, and MPS formats
- `batch` — Solve multiple problem files with a summary table
- `config` — Display or initialise a solver configuration file

**Enhanced MILP:**
- Real Gomory fractional cut generation from the simplex tableau
- Three search strategies: best-first, depth-first, breadth-first
  (`SearchStrategy` enum)
- Time limit support (`time_limit` parameter)
- Verbose logging option
- Reports `nodes_explored` and `cuts_generated` statistics

**Enhanced CLI:**
- `--table` flag for boxed table output
- `--json` flag for explicit JSON output
- `--output-format` flag for format selection
- `--strategy` flag for MILP search strategy
- `--time-limit` flag for MILP time limit
- `--config` / `-c` global flag for config file
- `--log-level` global flag
- `--verbose` / `-q` global flags
- Config file settings merge with CLI flags

**New examples:**
- `blending.json` — Blending problem with quality constraints
- `scheduling.json` — Staff scheduling (7-day, integer)
- `portfolio.json` — Portfolio optimisation with risk budget

**Infrastructure:**
- GitHub Actions CI workflow (multi-OS, multi-Python)
- `CONTRIBUTING.md` with development guidelines
- `LICENSE` file (MIT)
- Enhanced `pyproject.toml` with optional dependencies and ruff config
- Version bumped to 2.0.0

**Tests:**
- 36 new tests (60 total, all passing):
  - `test_formatting.py` (6 tests) — LP format round-trip
  - `test_config.py` (8 tests) — Configuration
  - `test_milp.py` (10 tests) — Search strategies, cuts, limits
  - `test_cli.py` (12 tests) — CLI subcommands

### v1.0.0 — Initial Release

- Two-phase primal Simplex with exact `Fraction` arithmetic
- Branch-and-bound MILP
- MPS format I/O
- JSON problem specs
- Sensitivity analysis
- CLI with `solve`, `validate`, `mps-info`, `version` subcommands
- 24 tests (all passing)

---

## Roadmap

- [ ] Dual Simplex method for efficient re-optimisation after bound changes
- [ ] Interior-point (barrier) method for large-scale LPs
- [ ] Presolve/presolve-reductions (constraint propagation, bound tightening)
- [ ] Column generation for large-scale problems
- [ ] Quadratic programming (QP) support
- [ ] Python C-extension or Cython acceleration for the inner pivot loop
- [ ] Web-based interactive tableau visualiser
- [ ] Gomory mixed-integer cuts (GMI) for mixed-integer problems
- [ ] MIP start / warm-start support
- [ ] Solution export to CSV / Excel
- [ ] Problem import from PuLP / Pyomo models

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, code style,
testing instructions, and pull request guidelines.

---

## License

MIT — see [LICENSE](./LICENSE).