# KenKen Solver & Generator

A from-scratch KenKen (Calcudoku / Mathdoku) puzzle engine: generator, solver, and verifier in pure Python with no external dependencies.

## What is KenKen?

KenKen is an arithmetical-logic puzzle invented by Japanese mathematics teacher Tetsuya Miyamoto in 2004. An *n×n* grid must be filled so that:

1. Each **row** contains the numbers 1–*n* exactly once (Latin square constraint).
2. Each **column** contains the numbers 1–*n* exactly once.
3. The grid is divided into **cages** — contiguous groups of cells, each with a target number and an operator (`+`, `-`, `*`, `/`, or `=` for single-cell cages). The numbers in each cage must combine via the operator to produce the target.

For subtraction and division cages with more than two cells, any left-to-right ordering of the values that yields the target is accepted (all permutations are checked).

## Features

- **Solver**: Backtracking search with constraint propagation, the Minimum-Remaining-Values (MRV) heuristic, and forward-checking via cage feasibility bounds.
- **Generator**: Produces solvable puzzles with **guaranteed unique solutions** by generating a random Latin square, partitioning into contiguous cages via random-region growth, and verifying uniqueness with the solver.
- **Difficulty levels**: `easy` (favors `+` and `=`, avoids `*`/`/`), `medium` (balanced), `hard` (favors `*` and `/`).
- **Operator support**: `+`, `-`, `*`, `/`, `=` (single-cell freebies).
- **JSON serialization**: Save and load puzzles in JSON format.
- **ASCII rendering**: Human-readable grid display showing cage targets and operators.
- **CLI**: Three subcommands — `generate`, `solve`, `verify`.
- **Pure standard library**: No NumPy, no external packages required.

## How It Works

### Solver

The solver (`KenKenSolver`) uses backtracking with:

1. **Candidate computation**: For each unassigned cell, candidates are `{1..n} − {values already in the same row or column}`.
2. **MRV heuristic**: At each step, the unassigned cell with the fewest candidates is selected first. This dramatically reduces the search space.
3. **Cage feasibility pruning**: After assigning a value, the cage containing that cell is checked for feasibility:
   - For `+` cages: the partial sum plus the minimum/maximum possible contribution from unassigned cells must bracket the target.
   - For `*` cages: similarly using product bounds.
   - For `-` and `/` cages: defers to the full check once all cells are assigned (permutation search).
4. **Solution count control**: The solver stops early once the requested number of solutions is found (1 by default; 2 for uniqueness verification).

### Generator

The generator (`KenKenGenerator`) works as follows:

1. **Random Latin square**: A base cyclic Latin square is constructed, then randomized via independent row, column, and symbol permutations.
2. **Cage partitioning**: Starting from random seed cells, cages grow by absorbing unassigned orthogonal neighbors until reaching a random size (1 to `max_cage_size`).
3. **Operator selection**: For each cage, all valid `(operator, target)` pairs are computed from the solution values. A weighted random choice is made based on the difficulty level.
4. **Uniqueness verification**: The solver is invoked with `max_solutions=2`. If exactly one solution exists, the puzzle is accepted; otherwise, the process repeats (up to `max_attempts` times).

## Usage

### Generate a puzzle

```bash
# 5×5 medium puzzle
python3 kenken.py generate --size 5

# 6×6 hard puzzle with a seed, also show the solution
python3 kenken.py generate --size 6 --difficulty hard --seed 42 --solve

# Save puzzle to JSON file
python3 kenken.py generate --size 4 --output puzzle.json --format json
```

### Solve a puzzle

```bash
python3 kenken.py solve --input puzzle.json
python3 kenken.py solve --input puzzle.json --all    # find all solutions
python3 kenken.py solve --input puzzle.json --stats  # show solver statistics
```

### Verify uniqueness

```bash
python3 kenken.py verify --input puzzle.json
```

### Python API

```python
from kenken import KenKenGenerator, KenKenSolver, KenKenPuzzle

# Generate
gen = KenKenGenerator(size=5, seed=42, difficulty="medium")
puzzle = gen.generate()
solution = gen.solution  # the intended solution grid

# Solve
solver = KenKenSolver(puzzle)
grid = solver.solve_grid()
print(grid)

# Serialize
json_str = puzzle.to_json()
puzzle2 = KenKenPuzzle.from_json(json_str)
```

## Project Structure

```
kenken-solver/
├── kenken.py       # Main implementation: Cage, KenKenPuzzle, KenKenSolver, KenKenGenerator, CLI
├── tests/
│   └── test_kenken.py
└── README.md
```

## License

MIT