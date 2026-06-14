# CDCL SAT Solver

A fully-featured **Conflict-Driven Clause Learning (CDCL)** SAT solver implemented in pure Python, supporting the standard DIMACS CNF input format and a rich set of solving strategies.

## Features

### Core Solver
- **CDCL Algorithm**: Complete implementation with 1-UIP conflict analysis and non-chronological backtracking
- **Two-Watched Literals**: Efficient Boolean Constraint Propagation using the watched-literal scheme
- **VSIDS Heuristic**: Variable State Independent Decaying Sum for smart decision ordering
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

### Diagnostics
- **Model Verification**: Built-in verification that computed models satisfy the formula
- **Proof Logging**: Optional DRAT-format proof output for UNSAT results
- **Detailed Statistics**: Track decisions, propagations, conflicts, restarts, and timing
- **Verbose Mode**: Detailed solving trace for debugging

## How It Works

### CDCL Algorithm

The solver implements the classic CDCL algorithm:

1. **Decide**: Pick an unassigned variable using VSIDS heuristic and phase saving
2. **Propagate**: Apply Boolean Constraint Propagation (BCP) using two-watched-literal scheme
3. **Analyze**: On conflict, perform 1-UIP conflict analysis to learn a new clause
4. **Backtrack**: Non-chronologically backtrack to the assertion level of the learnt clause
5. **Propagate learnt clause**: After adding the learnt clause, immediately propagate its implications

### Two-Watched-Literal Scheme

Instead of scanning all clauses during propagation, each clause maintains two "watched" literals. A clause is only visited when one of its watched literals becomes false, making it a candidate for unit propagation or conflict detection.

### VSIDS (Variable State Independent Decaying Sum)

Variables involved in recent conflicts receive activity bumps. Variable activities decay over time, ensuring that the solver focuses on recently relevant variables.

### 1-UIP Learning

When a conflict occurs, the solver resolves clauses backwards along the implication graph until exactly one literal from the current decision level remains. This produces a compact learnt clause that prevents the same conflict pattern.

### Glue-Based Clause Management

Learnt clauses are assigned a "glue" score (Literal Block Distance) measuring how many decision levels their literals span. Low-glue clauses are considered high quality and are preserved during clause deletion.

### Luby Restarts

The solver periodically restarts from scratch (keeping learnt clauses) using the Luby sequence, which has theoretical guarantees for randomized search.

## Usage

### As a Command-Line Tool

```bash
python3 solver.py input.cnf [-t TIMEOUT] [-v LEVEL] [-p proof.drat] [-o model.out] [-r STRATEGY] [--preprocess]
```

Options:
- `-t, --timeout`: Time limit in seconds (0 = unlimited)
- `-v, --verbose`: Verbosity level (0=silent, 1=stats, 2=trace)
- `-p, --proof`: Write DRAT proof to file
- `-o, --output`: Write SAT model to file
- `-r, --restart`: Restart strategy (`luby` or `geometric`)
- `--preprocess`: Run preprocessing before solving

### As a Python Library

```python
from solver import Solver

# From a DIMACS string
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

### From a File

```python
from solver import Solver

solver = Solver.from_file("problem.cnf")
result = solver.solve(time_limit=60)
print(f"Result: {result}")
print(f"Stats: {solver.get_stats()}")
```

### With Assumptions (Incremental Solving)

```python
from solver import Solver

dimacs = "p cnf 2 1\n1 2 0\n"
solver = Solver.from_dimacs(dimacs)

# Solve assuming x1=False and x2=False → UNSAT
result = solver.solve(assumptions=[-1, -2])
# UNSAT because the clause (x1 OR x2) can't be satisfied
```

### With Preprocessing

```python
from solver import Solver

solver = Solver.from_file("problem.cnf")
solver.preprocess()  # Simplify before solving
result = solver.solve()
```

### DIMACS Format

Input files use the standard DIMACS CNF format:

```
c This is a comment
p cnf <num_vars> <num_clauses>
1 2 3 0        % clause: x1 OR x2 OR x3
-1 2 0         % clause: NOT x1 OR x2
```

Each clause is a line of space-separated literals ending with 0. Negative literals represent negated variables. Multi-line clauses are supported (0 terminates each clause).

## Instance Generator

The project includes a generator for classic SAT benchmark instances:

```bash
# Pigeonhole principle (UNSAT for n > m)
python3 generator.py --type php --n 4 --m 3 -o php_4_3.cnf

# Random 3-SAT
python3 generator.py --type random --vars 50 --clauses 200 --seed 42 -o random_50.cnf

# Chain formula (SAT)
python3 generator.py --type chain --vars 10 -o chain_10.cnf

# Tseitin parity formula
python3 generator.py --type tseitin --vars 5 -o tseitin_5.cnf

# Mutilated chessboard (UNSAT)
python3 generator.py --type chessboard --n 4 -o chess_4.cnf
```

## Performance Notes

This is a reference implementation in pure Python. For production use on large instances (100K+ variables), compiled solvers like MiniSAT, Glucose, or CaDiCaL will be significantly faster. However, this solver correctly handles:

- Standard SAT competition instances up to ~10K variables
- All classic unsatisfiable benchmarks (pigeonhole, mutilated chessboard)
- Random k-SAT instances at the phase transition
- Incremental solving with assumptions

## Architecture

The solver uses these key data structures:

- **Clause**: Slotted object with literal list, learnt flag, activity, glue score, frozen flag
- **VarInfo**: Per-variable activity, polarity, decision level, reason clause, seen flag
- **LitInfo**: Per-literal watcher list for two-watched-literal BCP
- **SolverStats**: Collects decisions, propagations, conflicts, restarts, timing

Key algorithms:
- BCP uses O(1)-amortized two-watched-literal scheme with deque-based propagation queue
- VSIDS with periodic activity decay (0.95 factor)
- 1-UIP conflict analysis with seen-flag cleanup
- Glucose-style clause deletion based on LBD/glue scores
- Luby or geometric restart strategies

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