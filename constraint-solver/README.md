# Constraint Satisfaction Problem Solver

A comprehensive, from-scratch implementation of CSP solving algorithms including AC-3, backtracking with MRV/LCV heuristics, forward checking, and MAC (Maintaining Arc Consistency).

## Features

- **AC-3 Algorithm**: Enforces arc consistency to prune domains before and during search
- **Backtracking Search** with configurable heuristics:
  - **MRV** (Minimum Remaining Values): Selects the most constrained variable first
  - **Degree Heuristic**: Tiebreaker for MRV — picks variable involved in most constraints
  - **LCV** (Least Constraining Value): Orders values to minimize pruning of neighbors
- **Forward Checking**: Prunes neighbor domains after each assignment
- **MAC** (Maintaining Arc Consistency): Full arc consistency propagation during search
- **Built-in problem generators**:
  - Sudoku (9×9)
  - N-Queens
  - Graph Coloring (e.g., Australia map)
  - Cryptarithm (e.g., SEND + MORE = MONEY)
- **CLI interface** for solving problems from the command line
- **Statistics tracking**: assignments tried, backtracks, time elapsed

## How It Works

### Core Architecture

The solver is built around three key data structures:

1. **`Variable`**: A named variable with a domain (set of possible values)
2. **`Constraint`**: A predicate over a set of variables, defining allowed combinations
3. **`CSP`**: A collection of variables and constraints, with indexing for efficient lookup

### Solving Pipeline

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

### Cryptarithm Solving

For puzzles like SEND + MORE = MONEY:
- Each letter maps to a unique digit (0-9)
- Leading digits cannot be zero
- The arithmetic equation must hold
- All-different constraints are enforced between all pairs of letters
- A final n-ary constraint checks the arithmetic

## Usage

### As a Python Library

```python
from csp_solver import CSPSolver, sudoku_csp, n_queens_csp, cryptarithm_csp

# Solve a Sudoku
puzzle = [
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
csp = sudoku_csp(puzzle)
solver = CSPSolver(use_mac=True)
result = solver.solve(csp)
print(result.assignment)  # Dict mapping "R0C0".."R8C8" to values

# Solve 8-Queens
csp = n_queens_csp(8)
result = solver.solve(csp)

# Solve SEND + MORE = MONEY
csp = cryptarithm_csp(["SEND", "MORE"], "MONEY")
result = solver.solve(csp)
# S=9, E=5, N=6, D=7, M=1, O=0, R=8, Y=2
```

### Command Line

```bash
# Solve a hard Sudoku
python -m csp_solver sudoku --grid "100007090030020008009600500005300900010080002600004000300000010040000007007000300"

# Solve N-Queens
python -m csp_solver queens --n 12

# Solve cryptarithm
python -m csp_solver cryptarithm --words SEND MORE --result MONEY

# Graph coloring (Australia)
python -m csp_solver coloring --colors 3

# JSON output
python -m csp_solver queens --n 8 --json

# Disable heuristics for comparison
python -m csp_solver sudoku --no-mac --no-mrv --no-lcv
```

## Project Structure

```
constraint-solver/
├── csp_solver/
│   ├── __init__.py       # Package exports
│   ├── csp.py            # Core CSP data structures
│   ├── ac3.py            # AC-3 arc consistency algorithm
│   ├── backtrack.py      # Backtracking solver with heuristics
│   ├── solver.py         # High-level solver interface
│   ├── problems.py       # Built-in problem generators
│   └── cli.py            # Command-line interface
├── tests/
│   └── test_solver.py    # Comprehensive test suite
├── README.md
└── pyproject.toml
```

## Algorithm Details

### AC-3
The algorithm maintains a queue of arcs (directed edges between variables). For each arc (Xi, Xj), it removes values from Xi's domain that have no supporting value in Xj. If Xi's domain changes, all arcs (Xk, Xi) are re-queued.

### MRV Heuristic
Selects the unassigned variable with the fewest legal values. This fails first, pruning the search tree early.

### Degree Heuristic
When MRV ties, picks the variable involved in the most constraints with unassigned variables, maximizing future pruning.

### LCV Heuristic
Orders values by how many options they leave for neighboring variables. The least constraining value is tried first.

### MAC
After each assignment, runs AC-3 on arcs from the assigned variable's neighbors. This is more powerful than forward checking because it propagates constraints transitively.