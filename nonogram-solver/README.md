# Nonogram Solver

A from-scratch nonogram (Picross / Hanjie / Griddlers) solver, generator, and player.

Nonograms are logic puzzles where you fill cells in a grid based on numbered
clues given for each row and column. The numbers indicate the lengths of
consecutive runs of filled cells in that line, separated by at least one blank
cell. The goal is to determine which cells are filled and which are left blank.

## Features

- **Line solver** with the overlap method and constraint propagation
- **Full-board solver** combining iterative propagation with backtracking
- **Puzzle generator** with unique-solution verification
- **Interactive player** with hints and progress checking
- **JSON serialization** for puzzles and solutions
- **CLI** with `solve`, `generate`, `validate`, and `hint` subcommands
- **Sample puzzles** included (heart, smiley, arrow)
- Pure Python, no external dependencies

## How It Works

### Line Solver (`LineSolver`)

The core of the solver operates on a single row or column ("line"). Given a
line with some cells known and some unknown, plus the clue for that line, it
determines which additional cells can be definitively decided.

**Overlap method:** For each block in the clue, compute the leftmost and
rightmost valid positions. If these placements overlap, the overlapping cells
are guaranteed to be filled. For example, clue `[3]` on a 5-cell line:

```
Leftmost:  ###..    (positions 0-2)
Rightmost: ..###    (positions 2-4)
Overlap:   ..#..    (position 2 → definitely filled)
```

**Constraint propagation:** The solver iterates to a fixpoint, repeatedly
applying the overlap method. Each pass may reveal new filled or empty cells,
which constrain the next pass further.

**Feasibility check:** A backtracking verifier confirms that at least one
valid arrangement exists consistent with the known cells.

### Board Solver (`Solver`)

The board solver applies the line solver to every row and column iteratively
until no more progress is made (constraint propagation). If the board is not
yet complete, it falls back to **depth-first backtracking**: pick an unknown
cell, try filling it, propagate, and recurse. If a contradiction is found,
backtrack and try the other value.

### Generator (`Generator`)

The generator creates random grids at a given density, derives the clues, and
verifies (via the solver) that the clues produce a unique solution. It retries
up to `max_attempts` times if uniqueness is required but not achieved.

## Installation

```bash
cd nonogram-solver
pip install -e .
```

Or run directly with `python -m nonogram.cli`.

## Usage

### Solve a puzzle

```bash
python -m nonogram.cli solve puzzles/heart.json
```

Output:
```
. . # . .
. # # # .
# # # # #
. # # # .
. . # . .

Solved in 17 iterations, 9 backtracks.
```

### Generate a puzzle

```bash
python -m nonogram.cli generate --width 10 --height 10 --seed 42
```

### Validate uniqueness

```bash
python -m nonogram.cli validate puzzles/heart.json
```

### Get a hint

```bash
python -m nonogram.cli hint puzzles/heart.json
```

### Python API

```python
from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.generator import Generator

# Solve a puzzle
board = Board(
    row_clues=[[1], [3], [5], [3], [1]],
    col_clues=[[1], [3], [5], [3], [1]],
)
result = Solver().solve(board)
print(board.render())

# Generate a puzzle
gen = Generator(seed=42)
puzzle = gen.generate(10, 10, density=0.5, unique=True)

# Interactive player
from nonogram.player import Player
player = Player(puzzle)
player.fill(0, 2)
player.blank(0, 0)
hint = player.hint()
print(hint)  # (row, col, Cell)
```

## Puzzle JSON Format

```json
{
  "row_clues": [[1], [3], [5], [3], [1]],
  "col_clues": [[1], [3], [5], [3], [1]],
  "grid": [[0,0,1,0,0], [0,1,1,1,0], [1,1,1,1,1], [0,1,1,1,0], [0,0,1,0,0]]
}
```

- `row_clues` / `col_clues`: list of clue lists (integers)
- `grid` (optional): 2D array of cell values (`-1`=unknown, `0`=empty, `1`=filled)

## Project Structure

```
nonogram-solver/
├── nonogram/
│   ├── __init__.py      # Package exports
│   ├── board.py         # Board and Cell data structures
│   ├── line_solver.py   # Per-line constraint propagation solver
│   ├── solver.py        # Full-board solver (propagation + backtracking)
│   ├── generator.py     # Random puzzle generator
│   ├── player.py        # Interactive player
│   └── cli.py           # Command-line interface
├── puzzles/
│   ├── heart.json       # 5×5 heart shape
│   ├── smiley.json      # 5×5 smiley face
│   └── arrow.json       # 10×10 arrow
├── pyproject.toml
└── README.md
```

## License

MIT