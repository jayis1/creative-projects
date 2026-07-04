# 🧩 Maze Generator & Solver

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](https://github.com/jayis1/creative-projects)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 168](https://img.shields.io/badge/tests-168%20passing-brightgreen)](#testing)
[![Version: 2.0](https://img.shields.io/badge/version-2.0.0-blue.svg)](#changelog)

> A comprehensive Python toolkit for generating, solving, analyzing, and
> visualizing mazes — featuring **9 generation algorithms**, **7 solving
> algorithms**, ASCII/PNG/SVG rendering, difficulty scoring, config files,
> and a full CLI.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Command-Line Interface](#command-line-interface)
  - [Python API](#python-api)
  - [Configuration Files](#configuration-files)
- [Algorithms](#algorithms)
  - [Generation Algorithms](#generation-algorithms-9)
  - [Solving Algorithms](#solving-algorithms-7)
- [Architecture](#architecture)
- [Examples](#examples)
- [Analysis & Difficulty Scoring](#analysis--difficulty-scoring)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Testing](#testing)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

### Generation Algorithms (9)

| Algorithm | Style | Characteristics |
|----------|-------|----------------|
| **Recursive Backtracking** | DFS-based | Long winding corridors, few junctions |
| **Prim's** | Frontier-growth | Branching, many dead ends |
| **Kruskal's** | Union-Find | Uniform, unbiased structure |
| **Eller's** | Row-by-row | Memory-efficient O(width) |
| **Wilson's** | Loop-erased random walk | Uniform spanning tree |
| **Binary Tree** | Bias-based | Diagonal bias, trivially solvable |
| **Sidewinder** | Run-based | Top row straight, slight bias |
| **Aldous-Broder** | Random walk | Uniform spanning tree, simple but slow |
| **Recursive Division** | Wall-additive | Starts open, adds walls recursively |

### Solving Algorithms (7)

| Solver | Strategy | Guarantees | Memory |
|--------|----------|------------|--------|
| **BFS** | Breadth-first search | Shortest path | O(n) |
| **DFS** | Depth-first search | Any path | O(path) |
| **A\*** | Heuristic-guided | Shortest path | O(n) |
| **Dijkstra** | Priority queue | Shortest path | O(n) |
| **Bidirectional BFS** | Two-frontier BFS | Shortest path | O(n) |
| **Greedy Best-First** | Heuristic-only | Fast, not optimal | O(n) |
| **IDA\*** | Iterative deepening A* | Shortest path | O(path) |

### Additional Capabilities

- **Braid Mazes** — Remove dead ends to create loops and multiple paths
- **JSON Serialization** — Save/load mazes with full round-trip fidelity
- **Batch I/O** — Save and load multiple mazes in a single file
- **PNG Export** — Pure-stdlib PNG writer (zlib + struct, no dependencies)
- **SVG Export** — Scalable vector graphics with solution path polylines
- **Distance Heatmap** — ANSI 256-color visualization of BFS distances
- **Multi-Solver Benchmark** — Compare all solvers (time, explored, length)
- **Maze Validation** — Check if a maze is perfect (connected, no cycles)
- **Waypoint Pathfinding** — Find paths visiting multiple points in sequence
- **Distance Map** — Compute BFS distance from any source to all cells
- **3 Heuristics** — Manhattan, Euclidean, Chebyshev for A*/greedy/IDA*
- **Difficulty Scoring** — 0–100 score based on twistiness, dead ends, junctions
- **Maze Comparison** — Structurally compare two mazes and report differences
- **Config Files** — JSON/TOML/YAML declarative maze generation
- **CLI** — Full argparse CLI with all features accessible via flags
- **Logging** — Configurable logging with `--verbose` flag
- **Custom Start/End** — Override default start/end points per solve

---

## Installation

### From source (no dependencies required)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/maze-generator-solver
```

The package requires **Python 3.10+** and has **zero external dependencies**
for core functionality. Optional dependencies:

```bash
# For YAML config support:
pip install pyyaml

# For TOML config support (Python < 3.11):
pip install tomli

# For development:
pip install pytest pyyaml
```

### Install as a package

```bash
cd creative-projects/maze-generator-solver
pip install -e .
```

This installs the `maze-solver` command-line tool and the `maze_solver`
Python package.

---

## Quick Start

```bash
# Generate and solve a maze
python3 -m maze_solver.cli -W 20 -H 10 -g recursive_backtracking --solve --seed 42

# Or using the installed command:
maze-solver -W 20 -H 10 -g prims -s astar --solve --seed 42
```

Output:
```
+-+-+-+-+-+-+-+-=-=-=-=-+
|S····|·······|·········|
+-+-+·+·+-+-+·+·+-+-+-+·+
|   |···|   |···|     |·|
+ +-+-+-+-+ +-+-+ +-+-+·+
|     |·····|   |     |·E|
+-+-+-+-+-+-+-+-+-+-+-+-+

Solution length: 26 steps
```

---

## Usage

### Command-Line Interface

```bash
# Generate a 20×10 maze with recursive backtracking
python3 maze.py -W 20 -H 10 -g recursive_backtracking

# Generate and solve, showing the solution path
python3 maze.py -W 15 -H 8 -g prims -s astar --solve --seed 42

# Generate with analysis statistics and validation
python3 maze.py -W 30 -H 15 -g wilsons --analyze --validate --seed 123

# Generate a braid maze (no dead ends)
python3 maze.py -W 15 -H 10 -g recursive_backtracking --braid 0.8 --solve

# Benchmark all solvers
python3 maze.py -W 20 -H 10 -g kruskals --benchmark --no-display

# Save and load mazes
python3 maze.py -W 10 -H 10 -g ellers --save my_maze.json --no-display
python3 maze.py --load my_maze.json --solve

# Export as PNG (with solution path in blue)
python3 maze.py -W 20 -H 15 -g sidewinder --png maze.png --no-display --solve

# Export as SVG (scalable, with solution path)
python3 maze.py -W 20 -H 15 -g sidewinder --svg maze.svg --no-display --solve

# Distance heatmap
python3 maze.py -W 10 -H 5 -g recursive_backtracking --heatmap

# Difficulty score
python3 maze.py -W 30 -H 20 -g recursive_backtracking --difficulty --no-display

# Use A* with Euclidean heuristic
python3 maze.py -W 15 -H 10 -g prims -s astar --heuristic euclidean --solve

# Generate from config file
python3 maze.py --config examples/config.json --validate

# Use the new Aldous-Broder generator
python3 maze.py -W 15 -H 10 -g aldous_broder --solve --seed 42

# Use the new Recursive Division generator
python3 maze.py -W 15 -H 10 -g recursive_division --solve --seed 42

# Use IDA* solver (memory-efficient optimal)
python3 maze.py -W 15 -H 10 -s ida_star --solve --seed 42

# Verbose logging
python3 maze.py -W 5 -H 5 --solve -v
```

**All CLI Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `-W, --width` | Maze width in cells | 20 |
| `-H, --height` | Maze height in cells | 10 |
| `-g, --generator` | Generation algorithm | recursive_backtracking |
| `-s, --solver` | Solving algorithm | bfs |
| `--heuristic` | Heuristic for A*/greedy/IDA* | manhattan |
| `--seed` | Random seed | None |
| `--solve` | Solve and display the path | off |
| `--analyze` | Print maze analysis statistics | off |
| `--braid [P]` | Braid maze (remove dead ends) | off |
| `--benchmark` | Benchmark all solvers | off |
| `--heatmap` | Print distance heatmap | off |
| `--save FILE` | Save maze to JSON | off |
| `--load FILE` | Load maze from JSON | off |
| `--png FILE` | Export as PNG | off |
| `--svg FILE` | Export as SVG | off |
| `--no-display` | Suppress maze rendering | off |
| `--validate` | Check if maze is perfect | off |
| `--config FILE` | Load config from JSON/TOML/YAML | off |
| `--difficulty` | Print difficulty score (0-100) | off |
| `-v, --verbose` | Enable verbose logging | off |

### Python API

```python
from maze_solver import Maze

# Create a 20×10 maze
maze = Maze(20, 10, seed=42)

# Generate using Prim's algorithm
maze.generate("prims")

# Solve using A* with Euclidean heuristic
solution = maze.solve("astar", heuristic="euclidean")
print(f"Solution has {len(solution)} steps")

# Render the maze with the solution path highlighted
print(maze.render(solution=solution))

# Analyze maze properties (now includes difficulty_score)
stats = maze.analyze()
print(f"Dead ends: {stats['dead_ends']}")
print(f"Is perfect: {stats['is_perfect']}")
print(f"Difficulty: {stats['difficulty_score']}/100")

# Braid the maze (remove dead ends)
braided_count = maze.braid(probability=1.0)
print(f"Removed {braided_count} dead ends")

# Benchmark all 7 solvers
results = maze.benchmark()
for r in results:
    print(f"{r['algorithm']}: {r['time_ms']}ms, {r['explored']} explored")

# Use IDA* (memory-efficient optimal solver)
solution_ida = maze.solve("ida_star")
print(f"IDA* solution: {len(solution_ida)} steps (optimal)")

# Distance map from start
dist = maze.distance_map()
print(f"Distance to (5,3): {dist[3][5]}")

# Waypoint pathfinding
path = maze.solve_waypoints([(0, 0), (10, 5), (19, 9)], algorithm="bfs")

# Save and load
maze.save("my_maze.json")
loaded = Maze.load("my_maze.json")

# Export as PNG (with solution path drawn in blue)
maze.to_png("maze.png", cell_size=15, wall_thickness=2, solution=solution)

# Export as SVG (scalable, with solution polyline)
maze.to_svg("maze.svg", cell_size=30, wall_width=3, solution=solution)

# Compare two mazes
from maze_solver.analysis import compare_mazes
maze2 = Maze(20, 10, seed=99)
maze2.generate("kruskals")
diff = compare_mazes(maze, maze2)
print(f"Wall differences: {diff['wall_diff_count']}")

# Custom start/end points
maze.set_start(0, 0)
maze.set_end(19, 9)
solution = maze.solve("astar")
```

### Configuration Files

Create mazes declaratively using JSON, TOML, or YAML config files:

**JSON config (`maze.json`):**
```json
{
  "width": 25,
  "height": 15,
  "seed": 42,
  "generator": "recursive_backtracking",
  "braid": 0.3,
  "start": [0, 0],
  "end": [24, 14]
}
```

```bash
python3 maze.py --config maze.json --solve --analyze
```

**Python config usage:**
```python
from maze_solver.io_utils import load_config, maze_from_config

config = load_config("maze.json")
maze = maze_from_config(config)
solution = maze.solve("astar")
```

---

## Algorithms

### Generation Algorithms (9)

#### Recursive Backtracking
Depth-first search with backtracking. Starts at a cell, picks a random
unvisited neighbor, removes the wall, and recurses. When stuck, backtracks.
Produces mazes with long winding corridors and few junctions.

#### Prim's
Modified Prim's algorithm. Starts from a random cell and maintains a
"frontier" of walls between visited and unvisited cells. Randomly picks
a frontier wall and opens it. Produces highly branching mazes.

#### Kruskal's
Uses a union-find (disjoint set) data structure. Creates a list of all
possible edges (walls between adjacent cells), shuffles them, and adds
each edge if it connects two different sets. Produces uniform, unbiased
mazes.

#### Eller's
Processes the maze row-by-row using union-find, only keeping one row in
memory at a time. Memory complexity is O(width) regardless of height.
Within each row, randomly merges adjacent cells; at row boundaries,
ensures each set has at least one vertical connection.

#### Wilson's
Produces a mathematically uniform random spanning tree. Picks a random
unvisited cell and performs a loop-erased random walk until hitting the
visited set. Slow on large mazes but guarantees uniform distribution.

#### Binary Tree
For each cell, randomly carves north or east. Produces a biased maze with
a diagonal texture and a straight corridor along the top and right edges.
Extremely fast but trivially solvable.

#### Sidewinder
Groups cells in each row into "runs" and randomly carves upward from a
random cell in the run. Top row is always a straight corridor. Slight
bias but fast and avoids the binary tree's diagonal issue.

#### Aldous-Broder (new in v2)
Performs a uniform random walk over the grid. When the walk enters an
unvisited cell, the wall between the previous and new cell is removed.
Produces a uniform spanning tree (like Wilson's) but with no memory of
the path — simpler but potentially slow since the walk revisits cells.

#### Recursive Division (new in v2)
Starts with an open grid and recursively adds walls with a single
passage hole. Unlike other generators that *remove* walls from a
fully-walled grid, this one *adds* walls to a fully-open grid.

### Solving Algorithms (7)

#### BFS (Breadth-First Search)
Explores all cells at the current depth before moving deeper.
**Guarantees the shortest path** on uniform-cost grids. Memory: O(n).

#### DFS (Depth-First Search)
Explores as deep as possible before backtracking. Finds *a* path but
not necessarily the shortest. Memory: O(path length).

#### A* (A-Star)
Best-first search using `f(n) = g(n) + h(n)` where g is the cost from
start and h is the heuristic estimate to the goal. With an admissible
heuristic, **guarantees the shortest path** while exploring fewer cells
than BFS. Memory: O(n).

#### Dijkstra
Priority-queue-based search expanding the lowest-cost node first.
Equivalent to BFS on uniform-cost grids. Memory: O(n).

#### Bidirectional BFS
Runs two BFS searches simultaneously — one from start, one from end —
meeting in the middle. **Guarantees shortest path** with potentially
faster convergence on large mazes.

#### Greedy Best-First
Expands the node that appears closest to the goal according to the
heuristic (ignoring cost-so-far). Fast but **does not guarantee the
shortest path**.

#### IDA* (Iterative Deepening A*) — new in v2
A* with iterative deepening on the cost threshold. Uses O(path length)
memory instead of O(n), making it suitable for very large mazes where
A*'s memory usage would be prohibitive. **Guarantees the shortest path**
with an admissible heuristic.

---

## Architecture

The project is structured as a proper Python package with clear module
separation:

```
maze-generator-solver/
├── maze_solver/           # Python package
│   ├── __init__.py        # Public API re-exports
│   ├── core.py            # Cell, Direction, Maze data model
│   ├── heuristics.py      # Manhattan, Euclidean, Chebyshev
│   ├── generators.py      # 9 generation algorithms
│   ├── solvers.py         # 7 solving algorithms
│   ├── renderers.py       # ASCII, PNG, SVG rendering
│   ├── analysis.py        # Stats, difficulty, comparison
│   ├── io_utils.py        # Config loading, batch I/O
│   └── cli.py             # Command-line interface
├── examples/              # Usage examples
│   ├── basic_usage.py
│   ├── benchmark_and_analysis.py
│   ├── export_formats.py
│   ├── config_usage.py
│   └── config.json
├── docs/
│   └── ARCHITECTURE.md
├── test_maze.py            # Original 71 tests
├── test_maze_v2.py         # 97 new tests
├── smoke_test.py           # Quick smoke test
├── pyproject.toml          # Package metadata
├── .github/workflows/ci.yml # GitHub Actions CI
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### Design Patterns

- **Registry Pattern** — `GENERATORS` and `SOLVERS` dicts map algorithm
  names to methods, enabling runtime discovery and CLI auto-population
- **Strategy Pattern** — Generation and solving algorithms are
  interchangeable strategies operating on the `Maze` data model
- **Delegation** — `Maze` convenience methods (`render()`, `to_png()`,
  `analyze()`) delegate to specialized modules

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full details.

---

## Examples

Run the example scripts:

```bash
# Basic generation and solving with all solver types
python3 examples/basic_usage.py

# Benchmarking and difficulty analysis
python3 examples/benchmark_and_analysis.py

# Export to PNG and SVG
python3 examples/export_formats.py

# Config file usage
python3 examples/config_usage.py
```

### Sample Output

```
+-+-+-+-+-+-+-+-+-+-+-+-+
|S····|·······|·········|
+-+-+·+·+-+-+·+·+-+-+-+·+
|   |···|   |···|     |·|
+ +-+-+-+-+ +-+-+ +-+-+·+
|     |·····|   |     |·E|
+-+-+-+-+-+-+-+-+-+-+-+-+

Solution length: 26 steps
```

### Benchmark Output

```
--- Solver Benchmark ---
Algorithm        Found  Length   Explored   Time (ms)
----------------------------------------------------
bfs              True   26       30         0.0916
dfs              True   38       25         0.0677
astar            True   26       18         0.1275
dijkstra         True   26       22         0.1204
bidirectional    True   26       16         0.1378
greedy           True   26       15         0.0868
ida_star         True   26       19         0.2150
```

---

## Analysis & Difficulty Scoring

The `analyze()` method reports comprehensive statistics:

| Metric | Description |
|--------|-------------|
| `total_walls_remaining` | Fewer = more open maze |
| `dead_ends` | Cells with only 1 opening |
| `corridors` | Cells with exactly 2 openings |
| `junctions` | Cells with 3+ openings (decision points) |
| `solution_length` | Shortest path length from start to end |
| `is_perfect` | Whether the maze is a perfect maze |
| `braid_ratio` | Fraction of non-dead-end cells |
| `difficulty_score` | 0–100 difficulty rating |

The **difficulty score** (0–100) combines three factors:
- **Twistiness** (40%) — solution length vs. theoretical minimum (Manhattan distance)
- **Dead-end density** (30%) — fraction of cells that are dead ends
- **Junction density** (30%) — fraction of cells with 3+ openings

| Score Range | Rating |
|-------------|--------|
| 0–20 | Easy |
| 20–40 | Medium |
| 40–60 | Hard |
| 60–80 | Very Hard |
| 80–100 | Extreme |

---

## Known Issues (Resolved)

The following bugs were identified during the bug hunt phase and have
been fixed:

1. **Benchmark explored count was 0 for A\*, Dijkstra, greedy, and
   bidirectional solvers** — These solvers used internal `closed`/`visited`
   sets instead of the `cell.visited` flag. **Fix**: All solvers now set
   `cell.visited = True` on exploration.

2. **Kruskal's algorithm removed walls even when cells were already
   connected** — Created cycles (non-perfect mazes). **Fix**: `remove_wall()`
   is only called when `union()` returns `True`.

3. **`distance_map()` returned all -1 after `solve()` or `is_perfect()`**
   — Previous operations left `cell.visited` flags set. **Fix**:
   `distance_map()` calls `reset_visited()` before starting.

4. **`from_dict()` didn't validate wall data dimensions or names** —
   Malformed JSON caused cryptic errors. **Fix**: Added dimension and
   wall name validation with descriptive error messages.

5. **Misleading comment in `to_png()`** — Said "RGBA" but was RGB.
   **Fix**: Corrected comment.

6. **Recursive Division didn't add border walls** (v2) — The generator
   started with all walls removed but didn't re-add the outer border.
   **Fix**: Border walls (NORTH on top row, SOUTH on bottom row, WEST on
   left column, EAST on right column) are now explicitly added.

---

## Testing

The project includes **168 tests** across two test suites:

- `test_maze.py` — 71 original tests (backward compatibility)
- `test_maze_v2.py` — 97 new tests covering all v2 features

### Test Coverage

- All 9 generation algorithms (perfect maze + solvability checks)
- All 7 solving algorithms (path validity, shortest path verification)
- IDA* optimality verification
- Heuristic functions (Manhattan, Euclidean, Chebyshev)
- Braid functionality
- JSON serialization (round-trip, file I/O, batch, invalid data)
- Maze validation (perfect maze check)
- Distance maps (including after solve)
- Waypoint pathfinding
- ASCII rendering, PNG export, SVG export
- Benchmarking (explored count correctness)
- Difficulty scoring
- Maze comparison
- Config file loading (JSON)
- CLI interface (all subcommands)
- Edge cases (1×1, 2×2, 1×N, N×1 mazes)
- Performance (50×50 maze BFS < 2s)
- Seed reproducibility

```bash
# Run all tests
python3 -m pytest test_maze.py test_maze_v2.py -v

# Run with coverage
pip install pytest-cov
python3 -m pytest test_maze.py test_maze_v2.py --cov=maze_solver -v

# Quick smoke test
python3 smoke_test.py
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on adding
new algorithms, renderers, and tests.

Key points:
- Follow PEP 8 and use type hints
- Add docstrings to all public functions
- Include tests for all new features
- Ensure all tests pass before submitting

---

## Changelog

### v2.0.0 — Comprehensive Improvement

**New Features:**
- 2 new generation algorithms: **Aldous-Broder**, **Recursive Division**
- 1 new solving algorithm: **IDA\*** (memory-efficient optimal search)
- **SVG export** with solution path polylines and start/end markers
- **Difficulty scoring** (0–100) based on twistiness, dead ends, junctions
- **Maze comparison** — structural diff between two mazes
- **Config file support** — JSON, TOML, YAML declarative generation
- **Batch I/O** — save/load multiple mazes in one file
- **CLI enhancements** — `--svg`, `--difficulty`, `--config`, `--verbose`
- **PNG export with solution path** — solution drawn in blue
- **Logging** — configurable with `--verbose` flag

**Architecture:**
- Split monolithic `maze.py` into modular `maze_solver/` package
- 8 focused modules: `core`, `heuristics`, `generators`, `solvers`,
  `renderers`, `analysis`, `io_utils`, `cli`
- Registry pattern for algorithm dispatch
- Delegation pattern for convenience methods
- Backward-compatible `maze.py` wrapper

**Quality:**
- 97 new tests (168 total, all passing)
- GitHub Actions CI (Python 3.10/3.11/3.12)
- `pyproject.toml` for pip installability
- Type hints throughout
- Comprehensive docstrings
- `CONTRIBUTING.md` with contribution guidelines
- `LICENSE` (MIT)
- `examples/` directory with 4 demo scripts
- `docs/ARCHITECTURE.md` design documentation

### v1.0.0 — Initial Release

- 7 generation algorithms
- 6 solving algorithms
- Braid maze support
- JSON serialization, PNG export
- Distance heatmap, benchmarking
- Maze validation, waypoint pathfinding
- 71 tests

---

## Roadmap

- [ ] Hexagonal grid mazes
- [ ] 3D maze generation (multi-layer)
- [ ] Animated GIF export of solution process
- [ ] Web-based interactive viewer
- [ ] More solving algorithms (jump point search, fringe search)
- [ ] Maze symmetries (rotational, reflective)
- [ ] Maze thinning/thickening operations
- [ ] Parallel generation for very large mazes
- [ ] Weighted mazes (non-uniform traversal costs)
- [ ] Maze export to LaTeX/TikZ

---

## License

MIT — see [LICENSE](LICENSE).