# CDCL SAT Solver

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Typed](https://img.shields.io/badge/code%20style-typed-444444.svg)](https://mypy.readthedocs.io/)

A fully-featured **Conflict-Driven Clause Learning (CDCL)** SAT solver implemented in pure Python, supporting the standard DIMACS CNF input format and a rich set of solving strategies.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Command Line Interface](#command-line-interface)
  - [Python Library](#python-library)
  - [Configuration](#configuration)
  - [Instance Generator](#instance-generator)
  - [DIMACS Validation](#dimacs-validation)
  - [Solution Counting](#solution-counting)
- [Architecture](#architecture)
  - [CDCL Algorithm](#cdcl-algorithm)
  - [Two-Watched-Literal Scheme](#two-watched-literal-scheme)
  - [VSIDS Heuristic](#vsids-heuristic)
  - [1-UIP Learning](#1-uip-learning)
  - [Clause Management](#clause-management)
- [Examples](#examples)
- [Performance](#performance)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Contributing](#contributing)
- [License](#license)

## Features

### Core Solver
- **CDCL Algorithm**: Complete implementation with 1-UIP conflict analysis and non-chronological backtracking
- **Two-Watched Literals**: Efficient Boolean Constraint Propagation using the watched-literal scheme
- **VSIDS Heuristic**: Variable State Independent Decaying Sum for smart decision ordering (with heap-based priority queue)
- **Phase Saving**: Remembers variable polarities across backtracks for better decisions
- **Luby Restarts**: Luby-sequence based restart strategy for robust search
- **Geometric Restarts**: Alternative geometric restart strategy
- **Clause Deletion**: Glucose-style garbage collection of low-activity learnt clauses based on glue (LBD) scores
- **DIMACS I/O**: Standard input/output format compatible with SAT competition benchmarks

### Preprocessing
- **Subsumption**: Removes clauses subsumed by shorter clauses
- **Failed Literal Detection**: Probes unassigned variables to detect forced assignments
- **Unit Propagation**: Simplifies using unit clauses before solving

### Incremental Solving
- **Assumption-based Solving**: Solve under a set of assumptions for incremental workflows
- **UNSAT Core Extraction**: Identify which assumptions led to unsatisfiability

### Diagnostics & Tooling
- **Model Verification**: Built-in verification that computed models satisfy the formula
- **Proof Logging**: Optional DRAT-format proof output for UNSAT results
- **Detailed Statistics**: Track decisions, propagations, conflicts, restarts, and timing
- **Verbose Mode**: Detailed solving trace for debugging
- **DIMACS Validation**: Validate DIMACS input files for common errors
- **Solution Counting**: Brute-force count satisfying assignments for small instances
- **JSON Statistics**: Export solver statistics as structured JSON

## Installation

### From Source

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/cdcl-sat-solver
pip install -e .
```

### For Development

```bash
pip install -e ".[dev]"
```

### Verify Installation

```bash
cdcl-sat --help
```

## Quick Start

### Python Library

```python
from cdcl_sat import Solver

# Create a solver from a DIMACS string
dimacs = """p cnf 3 3
1 2 0
-1 2 0
-2 3 0
"""
solver = Solver.from_dimacs(dimacs)
result = solver.solve()

if result:
    print("SAT!")
    model = solver.get_model()
    print(f"Model: {model}")
    assert solver.verify_model(model)
else:
    print("UNSAT")
```

### Command Line

```bash
# Solve a DIMACS file
cdcl-sat solve problem.cnf

# Solve with preprocessing and verbose output
cdcl-sat solve problem.cnf --preprocess -v 1

# Generate a pigeonhole instance
cdcl-sat generate --type php --n 4 --m 3 -o php_4_3.cnf

# Validate a DIMACS file
cdcl-sat validate problem.cnf
```

## Usage

### Command Line Interface

The `cdcl-sat` command provides four subcommands:

#### `solve` — Solve a DIMACS CNF file

```bash
cdcl-sat solve input.cnf [OPTIONS]

Options:
  -t, --timeout     Time limit in seconds (0 = unlimited)
  -v, --verbose     Verbosity level (0=silent, 1=stats, 2=trace)
  -p, --proof       Write DRAT proof to file
  -o, --output      Write model to file (if SAT)
  -r, --restart     Restart strategy (luby or geometric)
  --preprocess      Run preprocessing before solving
  --config          Load solver config from JSON file
  --stats-json      Write statistics to JSON file
```

#### `generate` — Generate CNF benchmark instances

```bash
cdcl-sat generate --type TYPE [OPTIONS]

Types: php, random, chain, tseitin, chessboard, coloring

Options:
  --n               Number of pigeons / board size
  --m               Number of holes (PHP)
  --vars            Number of variables (random/chain/tseitin)
  --clauses         Number of clauses (random)
  --k               Clause length (random, default: 3)
  --seed            Random seed
  --nodes           Number of nodes (coloring)
  --colors          Number of colors (coloring)
  --edge-prob       Edge probability (coloring)
  -o, --output      Output file (default: stdout)
```

#### `validate` — Validate a DIMACS CNF file

```bash
cdcl-sat validate input.cnf
```

#### `count` — Count satisfying assignments (brute force)

```bash
cdcl-sat count input.cnf [--max 65536] [--force]
```

### Python Library

#### Basic Solving

```python
from cdcl_sat import Solver

# From a DIMACS string
solver = Solver.from_dimacs("p cnf 3 1\n1 2 0\n")
result = solver.solve()

# From a file
solver = Solver.from_file("problem.cnf")

# With time limit
result = solver.solve(time_limit=60)

# Get model and verify
if result:
    model = solver.get_model()
    assert solver.verify_model(model)
    print(Solver.model_to_dimacs(model, solver.num_vars))

# Get statistics
stats = solver.get_stats()
print(f"Decisions: {stats.decisions}")
print(f"Conflicts: {stats.conflicts}")
print(f"Time: {stats.elapsed():.3f}s")
```

#### Incremental Solving with Assumptions

```python
from cdcl_sat import Solver

solver = Solver.from_dimacs("p cnf 2 1\n1 2 0\n")

# Solve assuming x1=False and x2=False → UNSAT
result = solver.solve(assumptions=[-1, -2])
# UNSAT because the clause (x1 OR x2) can't be satisfied

# Solve assuming x1=True → SAT
solver2 = Solver.from_dimacs("p cnf 2 1\n1 2 0\n")
result = solver2.solve(assumptions=[1])
```

#### Preprocessing

```python
from cdcl_sat import Solver

solver = Solver.from_file("problem.cnf")
solver.preprocess()  # Simplify before solving
result = solver.solve()
```

#### Configuration

```python
from cdcl_sat import SolverConfig, Solver

# Create configuration
config = SolverConfig(
    restart_strategy="geometric",
    var_decay=0.95,
    verbose=1,
    max_learnt_clauses=10000,
)

# Load from JSON file
config = SolverConfig.from_json("config.json")

# Load from environment variables
config = SolverConfig.from_env()

# Apply to solver
solver = Solver.from_file("problem.cnf")
config.apply_to_solver(solver)
result = solver.solve()

# Save configuration
config.to_json("my_config.json")
```

### Instance Generator

```python
from cdcl_sat.generator import generate_php, generate_random_cnf, generate_graph_coloring

# Pigeonhole (UNSAT for n > m)
num_vars, clauses = generate_php(4, 3)

# Random 3-SAT
num_vars, clauses = generate_random_cnf(50, 200, k=3, seed=42)

# Graph coloring
num_vars, clauses = generate_graph_coloring(10, 3, edge_prob=0.5, seed=7)
```

### DIMACS Validation

```python
from cdcl_sat.utils import validate_dimacs

dimacs = "p cnf 3 2\n1 2 0\n-1 3 0\n"
issues = validate_dimacs(dimacs)
if issues:
    for issue in issues:
        print(f"  - {issue}")
else:
    print("DIMACS is valid!")
```

### Solution Counting

```python
from cdcl_sat.utils import count_satisfying_assignments

# Count satisfying assignments (brute force, for small instances only)
clauses = [[1, 2], [-1, 2]]  # (x1 ∨ x2) ∧ (¬x1 ∨ x2)
count = count_satisfying_assignments(2, clauses)  # Returns 2
```

## Architecture

### CDCL Algorithm

The solver implements the classic CDCL algorithm:

```
1. Decide: Pick an unassigned variable using VSIDS heuristic and phase saving
2. Propagate: Apply Boolean Constraint Propagation (BCP) using two-watched-literal scheme
3. Analyze: On conflict, perform 1-UIP conflict analysis to learn a new clause
4. Backtrack: Non-chronologically backtrack to the assertion level of the learnt clause
5. Propagate learnt clause: After adding the learnt clause, immediately propagate its implications
```

### Two-Watched-Literal Scheme

Instead of scanning all clauses during propagation, each clause maintains two "watched" literals. A clause is only visited when one of its watched literals becomes false, making it a candidate for unit propagation or conflict detection.

```
Clause: [l₀, l₁, l₂, l₃]    ← l₀ and l₁ are watched
                ↑    ↑
              watched  watched

When l₁ becomes false:
  1. Try to find a non-false literal l₂ or l₃ to watch instead
  2. If found: swap watches, clause is satisfied or undetermined
  3. If not found: l₀ is the only unassigned/false literal
     - l₀ is unassigned → unit clause, propagate l₀
     - l₀ is false → conflict!
```

### VSIDS Heuristic

Variables involved in recent conflicts receive activity bumps. Variable activities decay over time, ensuring that the solver focuses on recently relevant variables. The implementation uses a heap-based priority queue for O(log n) variable selection:

```
1. On conflict: bump activity of all variables in the conflict clause
2. Periodically: decay all activities by factor (0.95)
3. On decision: select the unassigned variable with highest activity
4. Phase saving: use the last polarity of the variable
```

### 1-UIP Learning

When a conflict occurs, the solver resolves clauses backwards along the implication graph until exactly one literal from the current decision level remains. This produces a compact learnt clause that prevents the same conflict pattern.

### Clause Management

Learnt clauses are assigned a "glue" score (Literal Block Distance) measuring how many decision levels their literals span. Low-glue clauses are considered high quality and are preserved during clause deletion. The solver periodically removes low-activity, high-glue learnt clauses to bound memory usage.

## Examples

See the `examples/` directory for complete scripts:

| File | Description |
|------|-------------|
| `basic_solving.py` | Basic SAT solving with model extraction |
| `incremental_solving.py` | Assumption-based incremental solving |
| `generator_and_config.py` | Using generators and solver configuration |
| `validation_and_counting.py` | DIMACS validation and solution counting |

## Performance

This is a reference implementation in pure Python. For production use on large instances (100K+ variables), compiled solvers like MiniSAT, Glucose, or CaDiCaL will be significantly faster. However, this solver correctly handles:

- Standard SAT competition instances up to ~10K variables
- All classic unsatisfiable benchmarks (pigeonhole, mutilated chessboard)
- Random k-SAT instances at the phase transition
- Incremental solving with assumptions

Typical performance on modern hardware:

| Instance | Variables | Clauses | Result | Time |
|----------|-----------|---------|--------|------|
| PHP(4,3) | 12 | 22 | UNSAT | <0.01s |
| PHP(5,4) | 20 | 65 | UNSAT | ~0.1s |
| Random 3-SAT (50 vars) | 50 | 200 | Varies | <0.1s |
| Random 3-SAT (100 vars) | 100 | 400 | Varies | ~0.5s |

## Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=cdcl_sat

# Run specific test class
python -m pytest tests/ -v -k TestCoreSolving

# Run slow tests only
python -m pytest tests/ -v -m slow
```

The test suite includes **60+ tests** covering:
- Core SAT/UNSAT solving
- DIMACS parsing edge cases
- Preprocessing (subsumption, unit propagation, probing)
- Incremental solving with assumptions
- VSIDS heuristic and restart strategies
- Clause management and deletion
- Model extraction and verification
- Configuration loading
- DIMACS validation
- Solution counting
- Proof logging
- Edge cases and robustness

## Project Structure

```
cdcl-sat-solver/
├── src/cdcl_sat/
│   ├── __init__.py         # Package initialization, public API
│   ├── solver.py           # Core CDCL SAT solver engine
│   ├── generator.py        # CNF instance generators
│   ├── config.py           # Solver configuration (dataclass + JSON/env)
│   ├── utils.py            # DIMACS I/O, validation, counting
│   ├── cli.py              # Command-line interface
│   └── __main__.py         # Entry point for python -m cdcl_sat
├── tests/
│   └── test_solver.py      # Comprehensive pytest test suite
├── examples/
│   ├── basic_solving.py        # Basic solving example
│   ├── incremental_solving.py  # Assumption-based solving
│   ├── generator_and_config.py # Generator + configuration
│   └── validation_and_counting.py # Validation + counting
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI
├── pyproject.toml          # Package configuration
├── CONTRIBUTING.md          # Contributing guidelines
├── LICENSE                  # MIT License
└── README.md               # This file
```

## Roadmap

- [ ] **Parallel Solving**: Shared-memory parallel CDCL with clause exchange
- [ ] **Inprocessing**: Variable elimination (DP), bounded variable elimination
- [ ] **All-UIP Learning**: Alternative conflict analysis strategy
- [ ] **Phase Selection Heuristic**: More sophisticated phase selection (caching)
- [ ] **Incremental CNF**: Add/remove clauses between solve calls
- [ ] **DIMACS Proof Checking**: Verify DRAT proofs
- [ ] **Circuit-to-CNF Converter**: Tseitin encoding for Boolean circuits
- [ ] **WebAssembly Build**: Run in-browser via Pyodide
- [ ] **Benchmarking Suite**: Automated comparison against MiniSAT/Glucose
- [ ] **Visualization**: Implication graph and search tree visualization

## Known Issues (Resolved)

### 1. Propagation Not Run After Learning Unit Clauses (FIXED)
After conflict analysis and backtracking, unit learnt clauses were assigned via `_assign()` but their implications were not propagated before the next decision. This caused the solver to miss constraints and incorrectly report SAT for unsatisfiable instances (e.g., pigeonhole problems). **Fix**: Added explicit `_propagate()` call after `_add_learnt()` in the main solve loop, with proper conflict handling for cascading unit implications.

### 2. Probing State Restoration Missing var_info (FIXED)
The `_save_state()` and `_restore_state()` methods used by failed literal probing only saved trail, trail_lim, assignment, and prop_queue, but not the `var_info` fields (level, reason, polarity, seen). After restoring state, stale `var_info` from the failed probe could cause incorrect subsequent probes. **Fix**: Extended `_save_state()` and `_restore_state()` to include all `var_info` fields.

### 3. model_to_dimacs Incorrect for Negative Literals (FIXED)
The `model_to_dimacs()` method used incorrect logic (`v in model or -(v) not in model`) to determine variable values. When a variable appeared as a negative literal in the model (e.g., `-2`), the condition `-(v) not in model` would incorrectly evaluate, producing wrong output. **Fix**: Replaced with explicit set-based lookup that checks both positive and negative literal membership.

### 4. Unit Clause Conflict Detection During Parsing (FIXED)
When conflicting unit clauses (e.g., `[1]` and `[-1]`) were added during DIMACS parsing, the `_add_clause_watches` method only enqueued the second literal without checking for conflict with the first. The `_assign` method was called but its return value was not checked. **Fix**: `_add_clause_watches` now directly calls `_assign` for unit clauses and sets `self.ok = False` on conflict. The `from_dimacs` parser checks `self.ok` after all clauses are added.

### 5. _analyze Trail Indexing Bounds (FIXED)
The conflict analysis routine could attempt to access trail indices below 0 when analyzing conflicts involving unit clauses, causing an IndexError. **Fix**: Added `trail_idx >= 0` bounds check in the inner loop of `_analyze` and a `found_uip` flag to handle the case where no UIP is found (safety check).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.