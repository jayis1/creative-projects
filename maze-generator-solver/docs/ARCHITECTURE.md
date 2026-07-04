# Architecture

## Overview

maze-generator-solver is structured as a Python package (`maze_solver/`)
with clear separation of concerns across modules. The design follows a
**data model + strategy** pattern: the `Maze` class is the central data
model, and generation/solving/rendering algorithms are strategies that
operate on it.

## Module Structure

```
maze_solver/
├── __init__.py      — Public API re-exports
├── core.py          — Cell, Direction, Maze (data model)
├── heuristics.py    — Manhattan, Euclidean, Chebyshev distance functions
├── generators.py    — 9 maze generation algorithms
├── solvers.py       — 7 pathfinding algorithms
├── renderers.py     — ASCII, PNG (stdlib), SVG rendering
├── analysis.py      — Statistics, difficulty scoring, maze comparison
├── io_utils.py      — Config loading (JSON/TOML/YAML), batch I/O
└── cli.py           — argparse command-line interface
```

## Data Model

### Cell

The `Cell` class uses `__slots__` for memory efficiency:
- `x`, `y` — grid coordinates
- `walls` — a `set[Direction]` of *present* walls (walls are removed
  during generation, so the set shrinks)
- `visited` — scratch boolean flag used by generation and solving
  algorithms; reset via `Maze.reset_visited()`

### Direction

A four-valued `Enum` (NORTH, EAST, SOUTH, WEST) with `dx`/`dy`
properties for movement vectors and an `opposite` property for
symmetric wall operations.

### Maze

The `Maze` class holds:
- `width`, `height` — grid dimensions
- `cells` — 2D list of `Cell` objects, indexed as `cells[y][x]`
- `rng` — a `random.Random` instance seeded for reproducibility
- `_start`, `_end` — optional custom start/end coordinates

The `Maze` class provides:
- **Generation dispatch** via `GENERATORS` registry (name → method)
- **Solving dispatch** via `SOLVERS` registry (name → method)
- **Convenience methods** (`render()`, `to_png()`, `to_svg()`, `analyze()`,
  `difficulty_score()`, `is_perfect()`, `benchmark()`) that delegate to
  the appropriate module

## Algorithm Architecture

### Generators

Each generator is a standalone function in `generators.py` that takes a
`Maze` and modifies its cells' wall sets in place. The `Maze` class
dispatches to these via thin wrapper methods. This separation allows:

1. **Testing generators in isolation** — they can be called directly
2. **Easy addition of new generators** — add a function, register it
3. **Clear algorithm code** — not mixed with class boilerplate

### Solvers

Similarly, each solver is a standalone function in `solvers.py`. All
solvers:
- Set `cell.visited = True` on explored cells (for benchmark counting)
- Return a list of `(x, y)` tuples, or `None` if unsolvable
- Use `maze._reconstruct_path()` to rebuild the path from a came-from map

### Renderers

Three rendering backends:
- **ASCII** — character grid with `+`, `|`, `-`, `·` markers
- **PNG** — pure stdlib implementation using `zlib` + `struct` (no PIL)
- **SVG** — vector graphics with polylines for solution paths

## Registry Pattern

The `GENERATORS` and `SOLVERS` dictionaries map algorithm names to
method names on the `Maze` class. This enables:
- Runtime discovery of available algorithms
- CLI auto-population of `choices` from the registries
- Easy extension without modifying dispatch logic

## Configuration

The `io_utils` module supports declarative maze generation via config
files (JSON/TOML/YAML). Configs are merged over `DEFAULT_CONFIG` and
passed to `maze_from_config()` which creates, generates, and optionally
braids the maze in one call.

## Testing

Two test suites:
- `test_maze.py` — original 71 tests (backward compatibility)
- `test_maze_v2.py` — 97 new tests covering all v2 features

Tests use `unittest.TestCase` and run with pytest. Generator and solver
tests iterate over `GENERATOR_NAMES` / `SOLVER_NAMES` so new algorithms
are automatically tested.