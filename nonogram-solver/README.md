# Nonogram Solver

A from-scratch nonogram (Picross / Hanjie / Griddlers) solver, generator, and
player — pure Python, no external dependencies.

Nonograms are logic puzzles where you fill cells in a grid based on numbered
clues given for each row and column. The numbers indicate the lengths of
consecutive runs of filled cells in that line, separated by at least one blank
cell. The goal is to determine which cells are filled and which are left blank.

## Features

### Core
- **Line solver** with the overlap method and constraint propagation
- **Full-board solver** combining iterative propagation with backtracking
- **MRV heuristic** for smarter cell selection during backtracking
- **Solution counter** — count all solutions up to a limit
- **Unique-solution checker** — robust multi-solution detection
- **Puzzle generator** with unique-solution verification
- **Interactive player** with hints and progress checking

### I/O & Rendering
- **JSON serialization** for puzzles and solutions
- **NON format** support (compact text format)
- **PNG export** (pure stdlib — no Pillow needed)
- **SVG export** for scalable vector graphics
- **ANSI colored terminal rendering** with clue display
- **HTML rendering** with styled tables

### Extras
- **10 curated preset puzzles** (heart, smiley, cross, letter-A, tree, house,
  ship, cat, space invader, key) — all verified solvable and unique
- **Difficulty analyzer** — grades puzzles as trivial/easy/medium/hard/expert
  based on grid size, clue complexity, propagation efficiency, and
  backtracking effort
- **CLI** with 8 subcommands: `solve`, `generate`, `validate`, `hint`,
    `presets`, `analyze`, `render`, `count`

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
yet complete, it falls back to **depth-first backtracking** with the **MRV
(Minimum Remaining Values)** heuristic: it picks the cell in the row or column
with the fewest unknown cells, which tends to produce immediate deductions or
contradictions, reducing the search tree.

### Generator (`Generator`)

The generator creates random grids at a given density, derives the clues, and
verifies (via the solver) that the clues produce a unique solution. It retries
up to `max_attempts` times if uniqueness is required but not achieved.

### Difficulty Analyzer (`DifficultyAnalyzer`)

Estimates puzzle difficulty based on:
- Grid size and total cells
- Clue complexity (number of blocks, average block size)
- Filled-cell ratio
- Whether constraint propagation alone solves the puzzle
- Backtracking effort (number of backtracks, backtrack ratio)

Produces a score and classifies as: trivial / easy / medium / hard / expert.

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

With ANSI color:
```bash
python -m nonogram.cli solve puzzles/heart.json --color
```

### Generate a puzzle

```bash
python -m nonogram.cli generate --width 10 --height 10 --seed 42 --difficulty
```

### Validate uniqueness

```bash
python -m nonogram.cli validate puzzles/heart.json
# VALID: puzzle has a unique solution.
```

### List and solve presets

```bash
python -m nonogram.cli presets
python -m nonogram.cli presets --name ship --solve
```

### Analyze difficulty

```bash
python -m nonogram.cli analyze puzzles/heart.json
```

### Count solutions

```bash
python -m nonogram.cli count puzzles/heart.json --limit 10
```

### Render in various formats

```bash
python -m nonogram.cli render puzzles/heart.json --format ansi
python -m nonogram.cli render puzzles/heart.json --format html --output heart.html
python -m nonogram.cli render puzzles/heart.json --format svg --output heart.svg
python -m nonogram.cli render puzzles/heart.json --format png --output heart.png
```

### Python API

```python
from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.generator import Generator
from nonogram.presets import get_preset, list_presets
from nonogram.analyzer import DifficultyAnalyzer
from nonogram.io import PuzzleIO
from nonogram.renderer import Renderer

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

# Check uniqueness
solver = Solver()
print(solver.is_unique(puzzle))  # True

# Count solutions
print(solver.count_solutions(puzzle, limit=5))  # 1

# Analyze difficulty
info = DifficultyAnalyzer().analyze(puzzle)
print(info["difficulty"])  # "medium"

# Use a preset
ship = get_preset("ship")
print(ship.render())

# Export to PNG/SVG/HTML
PuzzleIO.save_png(board, "output.png")
PuzzleIO.save_svg(board, "output.svg")
html = Renderer.html(board, title="My Puzzle")

# Interactive player
from nonogram.player import Player
player = Player(puzzle)
player.fill(0, 2)
player.blank(0, 0)
hint = player.hint()
print(hint)  # (row, col, Cell)
```

## Puzzle File Formats

### JSON

```json
{
  "row_clues": [[1], [3], [5], [3], [1]],
  "col_clues": [[1], [3], [5], [3], [1]],
  "grid": [[0,0,1,0,0], [0,1,1,1,0], [1,1,1,1,1], [0,1,1,1,0], [0,0,1,0,0]]
}
```

- `row_clues` / `col_clues`: list of clue lists (integers)
- `grid` (optional): 2D array of cell values (`-1`=unknown, `0`=empty, `1`=filled)

### NON (compact text)

```
5 5
1
3
5
3
1
1
3
5
3
1
```

First line: `width height`. Next `height` lines: row clues. Next `width` lines:
column clues. Use `0` for an empty clue (no filled cells).

## Preset Puzzles

| Name | Size | Difficulty | Description |
|------|------|------------|-------------|
| heart | 5×5 | easy | A heart shape |
| smiley | 5×5 | easy | A smiley face |
| cross | 7×7 | easy | A plus sign |
| letter-a | 5×5 | easy | The letter A |
| tree | 7×7 | medium | A tree |
| house | 5×5 | medium | A house |
| ship | 10×10 | medium | A ship with mast and hull |
| cat | 8×8 | hard | A cat face |
| space-invader | 8×8 | hard | A classic space invader |
| key | 10×10 | hard | A key |

All presets are verified to have unique solutions.

## Known Issues (Resolved)

All bugs found during the Phase 3 bug hunt have been fixed and verified with
tests in `tests/test_bug_hunt.py` (11 tests, all passing).

1. **Dead code in `save_png`** — The PNG export had a redundant first loop
   that built pixel data only to be immediately overwritten by a second loop.
   Removed the dead code. *(No user-visible effect, but wasted computation.)*

2. **Misleading `_propagate` docstring** — The docstring claimed a "dirty-set
   optimisation" that was never implemented. Updated to accurately describe
   the simple fixpoint iteration. *(Documentation fix.)*

3. **`Board.from_dict` accepted mismatched grid dimensions** — Loading a JSON
   puzzle where the `grid` array dimensions didn't match the clue dimensions
   would silently produce a broken board or cause a confusing `IndexError`.
   Now raises a descriptive `ValueError`.

4. **`PuzzleIO.load_non` didn't validate line count** — A truncated NON file
   would cause an `IndexError` with no context. Now raises `ValueError` with
   the expected vs. actual line count.

5. **`Player.check()` failed for boards without a grid** — When a board was
   loaded from NON format (no grid/solution), `check()` would always return
   `False` because the solution was all-UNKNOWN. Now the `Player` constructor
   solves the clues to obtain the solution before play begins.

6. **`LineSolver` didn't handle empty clues** — A clue of `[]` (no filled
   cells in that line) left all cells as UNKNOWN instead of marking them
   EMPTY. Fixed: empty clues now correctly set all cells to EMPTY (or raise
   `ValueError` if any cell is already FILLED).

7. **`LineSolver` didn't account for FILLED cells in leftmost/rightmost
   placement** — The overlap method's leftmost/rightmost position calculation
   only avoided EMPTY cells but didn't ensure FILLED cells were covered by
   blocks. This caused the solver to miss deductions when a line had known
   FILLED cells (e.g., `[FILLED, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN]` with
   clue `[3]` should deduce positions 1,2 as FILLED and 3,4 as EMPTY, but
   previously left them UNKNOWN). Fixed with a post-verification step that
   checks all FILLED cells are covered and repositions blocks as needed.

8. **`arrow.json` puzzle was unsolvable** — The arrow puzzle's clues were
   inconsistent (no valid grid matched them). Replaced with a valid,
   uniquely-solvable arrow design.

## License

MIT

## Project Structure

```
├── nonogram/
│   ├── __init__.py      # Package exports
│   ├── board.py         # Board and Cell data structures
│   ├── line_solver.py   # Per-line constraint propagation solver
│   ├── solver.py        # Full-board solver (propagation + MRV backtracking)
│   ├── generator.py     # Random puzzle generator
│   ├── player.py        # Interactive player with hints
│   ├── presets.py       # 10 curated preset puzzles
│   ├── analyzer.py      # Difficulty analyzer
│   ├── io.py            # File I/O (JSON, NON, PNG, SVG)
│   ├── renderer.py      # ANSI and HTML renderers
│   └── cli.py           # Command-line interface (8 subcommands)
├── puzzles/
│   ├── heart.json       # 5×5 heart
│   ├── heart.non        # Same in NON format
│   ├── smiley.json      # 5×5 smiley
│   └── arrow.json       # 10×10 arrow
├── pyproject.toml
└── README.md
```

## License

MIT