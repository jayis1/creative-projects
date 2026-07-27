# KenKen Solver & Generator

A from-scratch KenKen (Calcudoku / Mathdoku) puzzle engine: generator, solver, verifier, analyzer, and hint system in pure Python with no external dependencies.

## What is KenKen?

KenKen is an arithmetical-logic puzzle invented by Japanese mathematics teacher Tetsuya Miyamoto in 2004. An *n×n* grid must be filled so that:

1. Each **row** contains the numbers 1–*n* exactly once (Latin square constraint).
2. Each **column** contains the numbers 1–*n* exactly once.
3. The grid is divided into **cages** — contiguous groups of cells, each with a target number and an operator (`+`, `-`, `*`, `/`, or `=` for single-cell cages). The numbers in each cage must combine via the operator to produce the target.

For subtraction and division cages with more than two cells, any left-to-right ordering of the values that yields the target is accepted (all permutations are checked).

## Features

### Core
- **Solver**: Backtracking search with constraint propagation, the Minimum-Remaining-Values (MRV) heuristic, forward-checking via cage feasibility bounds, and naked-single propagation.
- **Solution counter**: `count_solutions()` counts all solutions without storing them, with an optional limit.
- **Generator**: Produces solvable puzzles with **guaranteed unique solutions** by generating a random Latin square, partitioning into contiguous cages via random-region growth, and verifying uniqueness with the solver.
- **Difficulty levels**: `easy` (favors `+` and `=`, avoids `*`/`/`), `medium` (balanced), `hard` (favors `*` and `/`).
- **Operator support**: `+`, `-`, `*`, `/`, `=` (single-cell freebies).

### Enhanced (v2.0)
- **Puzzle analyzer**: Analyzes puzzle properties including cage statistics, operator distribution, difficulty scoring, solver complexity metrics (nodes/backtracks), and difficulty categorization (easy/medium/hard).
- **Hint system**: Provides cell-value hints for partially solved puzzles, with conflict detection for invalid partial assignments.
- **Batch generation**: Generate multiple puzzles in one command with timing statistics and progress reporting.
- **Cage contiguity validation**: Validates that all cages form connected regions (4-connectivity).
- **No-singletons mode**: Generate puzzles without single-cell cages (orphan singletons are merged into adjacent cages).
- **Compact text format**: Human-readable puzzle format for easy editing and sharing (with comment support).
- **Enhanced rendering**: Cage map rendering, solved puzzle overlay (cage labels + solution values), and improved grid display.
- **Input validation**: Operator validation, target positivity checks, `=` operator requires single cell, cell bounds checking, overlapping cage detection.

### Serialization
- **JSON**: Full round-trip serialization for programmatic use.
- **Text format**: Compact human-readable format with comment support (`#` lines).

## How It Works

### Solver

The solver (`KenKenSolver`) uses backtracking with:

1. **Domain tracking**: Each cell maintains a set of candidate values `{1..n}`, reduced by row and column constraints.
2. **MRV heuristic**: At each step, the unassigned cell with the fewest candidates is selected first, dramatically reducing the search space.
3. **Naked-single propagation**: After each assignment, cells reduced to a single candidate are automatically assigned. Row/column reductions are processed in a separate phase before naked-single assignment to ensure correct constraint ordering.
4. **Cage feasibility pruning**: After assigning a value, the cage containing that cell is checked for feasibility:
   - For `+` cages: the partial sum plus the minimum/maximum possible contribution from unassigned cells must bracket the target.
   - For `*` cages: similarly using product bounds.
   - For `-` and `/` cages: defers to the full permutation check once all cells are assigned.
5. **Full domain snapshot/restore**: Before each branch, a complete snapshot of all domains is saved. This ensures correct restoration after propagation modifies domains across the entire grid (not just the row/column of the assigned cell).

### Generator

The generator (`KenKenGenerator`) works as follows:

1. **Random Latin square**: A base cyclic Latin square is constructed, then randomized via independent row, column, and symbol permutations.
2. **Cage partitioning**: Starting from random seed cells, cages grow by absorbing unassigned orthogonal neighbors until reaching a random size (1 to `max_cage_size`). If `allow_singletons=False`, orphan singletons are merged into adjacent cages.
3. **Operator selection**: For each cage, all valid `(operator, target)` pairs are computed from the solution values. A weighted random choice is made based on the difficulty level.
4. **Uniqueness verification**: The solver is invoked with `max_solutions=2`. If exactly one solution exists, the puzzle is accepted; otherwise, the process repeats (up to `max_attempts` times).

### Analyzer

The `PuzzleAnalyzer` computes:
- **Cage statistics**: number of cages, average/max cage size, singleton count.
- **Operator distribution**: count of each operator type.
- **Difficulty score**: weighted combination of grid size, average cage size, operator mix, and singleton count.
- **Difficulty category**: easy (≤15), medium (≤30), hard (>30).
- **Solver complexity**: node count and backtrack count for finding the first solution.

## Usage

### Generate a puzzle

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
```

### Solve a puzzle

```bash
python3 kenken.py solve --input puzzle.json
python3 kenken.py solve --input puzzle.json --all       # find all solutions
python3 kenken.py solve --input puzzle.json --stats     # show solver statistics
python3 kenken.py solve --input puzzle.txt              # text format also supported
```

### Verify uniqueness

```bash
python3 kenken.py verify --input puzzle.json
```

### Analyze difficulty

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

### Batch generate

```bash
python3 kenken.py batch --size 5 --count 10 --difficulty medium --output-dir puzzles/
```

### Get hints

```bash
# Get 3 hints given some pre-filled cells
python3 kenken.py hint --input puzzle.json --cells "0,0=3" "1,2=5" --num 3
```

### Python API

```python
from kenken import KenKenGenerator, KenKenSolver, KenKenPuzzle, PuzzleAnalyzer

# Generate
gen = KenKenGenerator(size=5, seed=42, difficulty="medium")
puzzle = gen.generate()
solution = gen.solution  # the intended solution grid

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

Each cage line: space-separated `row,col` cell coordinates, then the operator, then the target.

## Project Structure

```
kenken-solver/
├── kenken.py       # Main implementation
├── tests/
│   └── test_kenken.py   # 36 tests
└── README.md
```

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and fixed:

1. **Hint system ignored partial assignments** — `get_hint()` called `solve()` without constraining the search to the partial assignment, so hints could be inconsistent with the user's pre-filled cells. **Fix**: Added cage constraint validation for partial assignments, solution consistency checking, and early return of empty hints when the partial assignment conflicts with the unique solution.

2. **Domain restoration bug in backtracking solver** — The solver only saved/restored domains for cells directly modified by the row/column update, but propagation modifies domains across the entire grid. This caused stale domain state after backtracking, leading to missing solutions. **Fix**: Save and restore a complete snapshot of ALL domains before each branching step.

3. **Naked-single propagation ordering bug** — Multiple naked singles were assigned in the same propagation phase before their row/column constraints were propagated, causing incorrect domain reductions (e.g., a cell could be assigned a value that was already used in its row/column by another naked single in the same phase). **Fix**: Assign only ONE naked single per propagation iteration, then re-loop to propagate its constraints before assigning the next.

4. **`render_solved_puzzle` crashed on None grid** — Passing `None` (unsolvable puzzle) to `render_solved_puzzle` caused a `TypeError`. **Fix**: Added a None check that falls back to `render_puzzle()`.

5. **Unused variables in `possible_targets`** — The `ok` and `ok2` variables in the subtraction/division branch were set but never checked. **Fix**: Removed unused variables and renamed `ok2` to `div_ok` for clarity.

6. **Unused `math` import** — The `math` module was imported but never used. **Fix**: Removed the import.

7. **Subtraction operator produced negative targets** — The generator's `_choose_operator` could produce negative subtraction targets for 3+ cell cages. **Fix**: Only keep permutation results that are positive (`r > 0`).

8. **`_cage_feasible` had dead code for `*` operator** — The `p == 0` check was unreachable (values are always 1..n) and the `min_v` computation was a no-op (`min_v *= 1`). **Fix**: Simplified the product bounds computation using exponentiation.

## License

MIT