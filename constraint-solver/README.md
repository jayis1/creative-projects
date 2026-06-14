# Constraint Satisfaction Problem Solver

A comprehensive, from-scratch implementation of CSP solving algorithms including AC-3, backtracking with MRV/LCV heuristics, forward checking, and MAC (Maintaining Arc Consistency). Includes built-in generators for Sudoku, N-Queens, graph coloring, cryptarithms, Latin squares, and magic squares.

## Features

- **AC-3 Algorithm**: Enforces arc consistency to prune domains before and during search, with optimized singleton-domain handling and chain propagation
- **Backtracking Search** with configurable heuristics:
  - **MRV** (Minimum Remaining Values): Selects the most constrained variable first
  - **Degree Heuristic**: Tiebreaker for MRV — picks variable involved in most constraints
  - **LCV** (Least Constraining Value): Orders values to minimize pruning of neighbors
- **Forward Checking**: Prunes neighbor domains after each assignment
- **MAC** (Maintaining Arc Consistency): Full arc consistency propagation during search
- **Strategy Comparison**: Built-in utility to compare different solving strategies
- **Progress Callbacks**: Hook into the search process for monitoring or visualization
- **Solver Statistics**: Assignments tried, backtracks, domain prunes, timing
- **Built-in problem generators**:
  - **Sudoku** (9×9) with puzzle generation
  - **N-Queens** with solution counting
  - **Graph Coloring** (Australia map, US regions)
  - **Cryptarithm** (SEND + MORE = MONEY, etc.)
  - **Latin Square**
  - **Magic Square**
- **CLI interface** for solving problems from the command line
- **Comprehensive test suite** with 84 tests covering all modules

## How It Works

### Core Architecture

The solver is built around three key data structures:

1. **`Variable`**: A named variable with a domain (set of possible values) and tracking of the initial domain
2. **`Constraint`**: A predicate over a set of variables, with an optional fast `pair_check` for binary constraints
3. **`CSP`**: A collection of variables and constraints, with indexing for efficient neighbor and constraint lookup

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

### Sudoku Generation

The generator:
1. Solves an empty Sudoku to get a complete valid grid
2. Removes cells randomly based on difficulty (easy: 30-35 blanks, medium: 36-45, hard: 46-52)
3. Returns both the puzzle and the known solution

## Usage

### As a Python Library

```python
from csp_solver import CSPSolver, sudoku_csp, n_queens_csp, cryptarithm_csp
from csp_solver import latin_square_csp, magic_square_csp, compare_strategies
from csp_solver import generate_sudoku, format_sudoku_solution

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
print(format_sudoku_solution(result.assignment))

# Generate a random Sudoku
puzzle, solution = generate_sudoku(difficulty="hard", seed=42)

# Solve 8-Queens
csp = n_queens_csp(8)
result = solver.solve(csp)

# Solve SEND + MORE = MONEY
csp = cryptarithm_csp(["SEND", "MORE"], "MONEY")
result = solver.solve(csp)

# Solve a 5×5 Latin Square
csp = latin_square_csp(5)
result = solver.solve(csp)

# Solve a 3×3 Magic Square
csp = magic_square_csp(3)
result = solver.solve(csp)

# Compare strategies on N-Queens
from csp_solver import compare_strategies
csp = n_queens_csp(8)
results = compare_strategies(csp)
for r in results:
    print(f"{r['strategy']}: {r['time']}s, {r['assignments']} assignments")
```

### Command Line

```bash
# Solve a hard Sudoku
python -m csp_solver sudoku --grid "100007090030020008009600500005300900010080002600004000300000010040000007007000300"

# Generate and solve a random Sudoku
python -m csp_solver sudoku --generate --difficulty hard --seed 42

# Solve N-Queens
python -m csp_solver queens --n 12

# Count all N-Queens solutions
python -m csp_solver queens --n 8 --count

# Solve cryptarithm
python -m csp_solver cryptarithm --words SEND MORE --result MONEY

# Graph coloring (Australia map)
python -m csp_solver coloring --colors 3

# US regions coloring
python -m csp_solver coloring --map us --colors 4

# Latin Square
python -m csp_solver latin --n 5

# Magic Square
python -m csp_solver magic --n 3

# JSON output
python -m csp_solver queens --n 8 --json

# Compare strategies
python -m csp_solver queens --n 8 --compare

# Disable heuristics for comparison
python -m csp_solver sudoku --no-mac --no-mrv --no-lcv
```

## Project Structure

```
constraint-solver/
├── csp_solver/
│   ├── __init__.py       # Package exports
│   ├── csp.py            # Core CSP data structures (Variable, Constraint, CSP)
│   ├── ac3.py            # AC-3 arc consistency, node consistency, domain reduction
│   ├── backtrack.py      # Backtracking solver with heuristics and stats
│   ├── solver.py         # High-level solver, solve_all, compare_strategies
│   ├── problems.py       # Problem generators (Sudoku, Queens, Coloring, etc.)
│   └── cli.py            # Command-line interface
├── tests/
│   └── test_solver.py    # 84 comprehensive tests
├── README.md
└── pyproject.toml
```

## Algorithm Details

### AC-3
The algorithm maintains a queue of arcs (directed edges between variables). For each arc (Xi, Xj), it removes values from Xi's domain that have no supporting value in Xj. If Xi's domain changes, all arcs (Xk, Xi) are re-queued. An optimized path handles singleton domains for faster pruning.

### MRV Heuristic
Selects the unassigned variable with the fewest legal values. This fails first, pruning the search tree early.

### Degree Heuristic
When MRV ties, picks the variable involved in the most constraints with unassigned variables, maximizing future pruning.

### LCV Heuristic
Orders values by how many options they leave for neighboring variables. The least constraining value is tried first.

### MAC
After each assignment, runs AC-3 on arcs from the assigned variable's neighbors. This is more powerful than forward checking because it propagates constraints transitively.

### Strategy Comparison
The `compare_strategies` function tests five configurations:
1. **BT** (plain backtracking, no heuristics)
2. **BT+MRV** (variable ordering only)
3. **BT+MRV+LCV** (variable and value ordering)
4. **FC+MRV+LCV** (forward checking with heuristics)
5. **MAC+MRV+LCV** (full constraint propagation — fastest in practice)