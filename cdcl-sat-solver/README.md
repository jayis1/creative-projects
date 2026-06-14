# CDCL SAT Solver

A fully-featured **Conflict-Driven Clause Learning (CDCL)** SAT solver implemented in pure Python, supporting the standard DIMACS CNF input format.

## Features

- **CDCL Algorithm**: Complete implementation with 1-UIP conflict analysis and non-chronological backtracking
- **Two-Watched Literals**: Efficient Boolean Constraint Propagation using the watched-literal scheme
- **VSIDS Heuristic**: Variable State Independent Decaying Sum for smart decision ordering
- **Phase Saving**: Remembers variable polarities across backtracks for better decisions
- **Luby Restarts**: Luby-sequence based restart strategy for robust search
- **Clause Deletion**: Garbage collection of low-activity learnt clauses to bound memory
- **DIMACS I/O**: Standard input/output format compatible with SAT competition benchmarks
- **Model Verification**: Built-in verification that computed models satisfy the formula
- **Proof Logging**: Optional DRAT-format proof output for UNSAT results
- **Time Limits**: Configurable timeout for large instances

## How It Works

### CDCL Algorithm

The solver implements the classic CDCL algorithm:

1. **Decide**: Pick an unassigned variable using VSIDS heuristic and phase saving
2. **Propagate**: Apply Boolean Constraint Propagation (BCP) using two-watched-literal scheme
3. **Analyze**: On conflict, perform 1-UIP conflict analysis to learn a new clause
4. **Backtrack**: Non-chronologically backtrack to the assertion level of the learnt clause

### Two-Watched-Literal Scheme

Instead of scanning all clauses during propagation, each clause maintains two "watched" literals. A clause is only visited when one of its watched literals becomes false, making it a candidate for unit propagation or conflict detection.

### VSIDS (Variable State Independent Decaying Sum)

Variables involved in recent conflicts receive activity bumps. Variable activities decay over time, ensuring that the solver focuses on recently relevant variables.

### 1-UIP Learning

When a conflict occurs, the solver resolves clauses backwards along the implication graph until exactly one literal from the current decision level remains. This produces a compact learnt clause.

### Luby Restarts

The solver periodically restarts from scratch (keeping learnt clauses) using the Luby sequence, which has theoretical guarantees for randomized search.

## Usage

### As a Command-Line Tool

```bash
python3 solver.py input.cnf [-t TIMEOUT] [-v] [-p proof.drat] [-o model.out]
```

Options:
- `-t, --timeout`: Time limit in seconds (0 = unlimited)
- `-v, --verbose`: Print detailed statistics
- `-p, --proof`: Write DRAT proof to file
- `-o, --output`: Write SAT model to file

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
else:
    print("UNSAT")
```

### DIMACS Format

Input files use the standard DIMACS CNF format:

```
c This is a comment
p cnf <num_vars> <num_clauses>
1 2 3 0        % clause: x1 OR x2 OR x3
-1 2 0         % clause: NOT x1 OR x2
```

Each clause is a line of space-separated literals ending with 0. Negative literals represent negated variables.

## Example Formulas

The project includes a generator for classic SAT instances:
- **Pigeonhole**: `php(n,m)` — classic unsatisfiable benchmarks
- **Random CNF**: Random k-SAT instances at various ratios
- **Chain**: Simple chain formulas for testing

```bash
python3 generator.py --type php --n 3 --m 2 -o php_3_2.cnf
python3 generator.py --type random --vars 50 --clauses 200 -o random_50.cnf
python3 generator.py --type chain --vars 10 -o chain_10.cnf
```

## Performance Notes

This is a reference implementation in pure Python. For production use on large instances (100K+ variables), compiled solvers like MiniSAT, Glucose, or CaDiCaL will be significantly faster. However, this solver correctly handles:
- Standard SAT competition instances up to ~10K variables
- All classic unsatisfiable benchmarks (pigeonhole, mutilated chessboard)
- Random k-SAT instances at the phase transition