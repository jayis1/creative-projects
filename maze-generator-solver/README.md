# Maze Generator & Solver

A comprehensive Python toolkit for generating and solving mazes, featuring **7 generation algorithms**, **6 solving algorithms**, braid maze support, JSON serialization, PNG export, distance heatmaps, multi-solver benchmarking, maze validation, and statistical analysis.

## Features

### Generation Algorithms (7)

| Algorithm | Style | Characteristics |
|----------|-------|----------------|
| **Recursive Backtracking** | DFS-based | Long winding corridors, few junctions |
| **Prim's** | Frontier-growth | Branching, many dead ends |
| **Kruskal's** | Union-Find | Uniform, unbiased structure |
| **Eller's** | Row-by-row | Memory-efficient O(width) |
| **Wilson's** | Loop-erased random walk | Uniform spanning tree |
| **Binary Tree** | Bias-based | Diagonal bias, trivially solvable |
| **Sidewinder** | Run-based | Top row straight, slight bias |

### Solving Algorithms (6)

| Solver | Strategy | Guarantees |
|--------|----------|------------|
| **BFS** | Breadth-first search | Shortest path |
| **DFS** | Depth-first search | Any path (not shortest) |
| **A\*** | Heuristic-guided | Shortest path (with admissible heuristic) |
| **Dijkstra** | Priority queue | Shortest path |
| **Bidirectional BFS** | Two-frontier BFS | Shortest path, faster convergence |
| **Greedy Best-First** | Heuristic-only | Fast, not guaranteed shortest |

### Additional Capabilities

- **Braid Mazes** — Remove dead ends to create loops and multiple paths
- **JSON Serialization** — Save/load mazes with full round-trip fidelity
- **PNG Export** — Pure-stdlib PNG writer (zlib + struct, no dependencies)
- **Distance Heatmap** — ANSI 256-color visualization of BFS distances from any cell
- **Multi-Solver Benchmark** — Compare all solvers on the same maze (time, explored cells, path length)
- **Maze Validation** — Check if a maze is perfect (connected, no cycles)
- **Waypoint Pathfinding** — Find paths visiting multiple points in sequence
- **Distance Map** — Compute BFS distance from any source to all cells
- **3 Heuristics** — Manhattan, Euclidean, Chebyshev for A*/greedy solvers
- **Custom Start/End** — Override default start/end points per solve

## How It Works

### Maze Representation

The maze uses a **grid-of-cells** model. Each `Cell` stores:
- **Position** `(x, y)` in the grid
- **Walls** — a set of `Direction` enums (NORTH, EAST, SOUTH, WEST) that are *present*
- **Visited** flag used during generation and solving

Initially every cell is fully walled (all four walls present). Generation algorithms remove walls to carve passages, producing a **perfect maze** (exactly one path between any two cells).

### Rendering

The ASCII renderer maps each cell to a 2×2 character block in a character grid of size `(width*2+1) × (height*2+1)`. Walls are drawn as `|` (vertical) and `-` (horizontal), with `+` at corners. Solution paths are overlaid with `·` markers. Start and end are marked with `S` and `E`.

### Braid Mazes

A **braid** maze has no dead ends — every cell has at least two openings, creating loops and multiple paths. The `braid(probability)` method opens walls at dead-end cells to random neighbors. A probability of 1.0 braids all dead ends; lower values braids a fraction.

### Validation

`is_perfect()` checks two conditions:
1. **Connectivity** — Every cell is reachable from every other (verified via BFS)
2. **No cycles** — The number of removed walls (edges) equals `n - 1` where `n` is the cell count (spanning tree property)

## Installation

No dependencies beyond the Python standard library. Requires Python 3.10+.

```bash
# Just run it directly
python3 maze.py --help
```

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

# Export as PNG
python3 maze.py -W 20 -H 15 -g sidewinder --png maze.png --no-display

# Distance heatmap
python3 maze.py -W 10 -H 5 -g recursive_backtracking --heatmap

# Use A* with Euclidean heuristic
python3 maze.py -W 15 -H 10 -g prims -s astar --heuristic euclidean --solve
```

**Options:**
- `-W, --width` — Maze width in cells (default: 20)
- `-H, --height` — Maze height in cells (default: 10)
- `-g, --generator` — Generation algorithm (default: recursive_backtracking)
- `-s, --solver` — Solving algorithm (default: bfs)
- `--heuristic` — Heuristic for A*/greedy: manhattan, euclidean, chebyshev (default: manhattan)
- `--seed` — Random seed for reproducibility
- `--solve` — Solve and display the solution path
- `--analyze` — Print maze statistics (dead ends, corridors, junctions, solution length, braid ratio)
- `--braid [P]` — Braid the maze (remove dead ends). Optional probability 0-1 (default 1.0)
- `--benchmark` — Benchmark all solvers on this maze
- `--heatmap` — Print a distance heatmap from the start cell
- `--save FILE` — Save the maze to a JSON file
- `--load FILE` — Load a maze from a JSON file (ignores -g)
- `--png FILE` — Export the maze as a PNG image
- `--validate` — Check if the maze is a perfect maze
- `--no-display` — Suppress maze rendering

### Python API

```python
from maze import Maze

# Create a 20×10 maze
maze = Maze(20, 10, seed=42)

# Generate using Prim's algorithm
maze.generate("prims")

# Solve using A* with Euclidean heuristic
solution = maze.solve("astar", heuristic="euclidean")
print(f"Solution has {len(solution)} steps")

# Render the maze with the solution path highlighted
print(maze.render(solution=solution))

# Analyze maze properties
stats = maze.analyze()
print(f"Dead ends: {stats['dead_ends']}")
print(f"Is perfect: {stats['is_perfect']}")
print(f"Braid ratio: {stats['braid_ratio']}")

# Braid the maze (remove dead ends)
braided_count = maze.braid(probability=1.0)
print(f"Removed {braided_count} dead ends")

# Validate maze is perfect
print(f"Perfect: {maze.is_perfect()}")

# Benchmark all solvers
results = maze.benchmark()
for r in results:
    print(f"{r['algorithm']}: {r['time_ms']}ms, {r['explored']} explored")

# Distance map from start
dist = maze.distance_map()
print(f"Distance to (5,3): {dist[3][5]}")

# Waypoint pathfinding
path = maze.solve_waypoints([(0, 0), (10, 5), (19, 9)], algorithm="bfs")

# Save and load
maze.save("my_maze.json")
loaded = Maze.load("my_maze.json")

# Export as PNG
maze.to_png("maze.png", cell_size=15, wall_thickness=2)

# Custom start/end points
maze.set_start(0, 0)
maze.set_end(19, 9)
solution = maze.solve("astar")
```

### Example Output

```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|S····|·······|···········|   |
+-+-+·+·+-+-+·+·+-+-+-+-+·+-+ +
|   |···|   |···|       |·····|
+ +-+-+-+-+ +-+-+ +-+-+ +-+-+·+
|   |         |       | |   |·|
+ + + +-+ +-+ + +-+-+ + + + +·+
| | |   |   | | |     |   | |·|
+ + +-+ +-+ + +-+ + +-+-+ +-+·+
| |   |   | |     | |   | |···|
+ +-+ +-+ + +-+-+-+-+ + +-+·+-+
|   |     | |       | |   |·| |
+-+ +-+-+-+ + +-+-+ + +-+ +·+ +
|   |     |   |   |   |   |···|
+ +-+ +-+ +-+-+-+ +-+-+ +-+-+·+
|     |               |      E|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Solution length: 28 steps
```

### Benchmark Output

```
--- Solver Benchmark ---
Algorithm        Found  Length   Explored   Time (ms)
----------------------------------------------------
bfs              True   28       31         0.0916
dfs              True   28       30         0.0677
astar            True   28        0         0.1275
dijkstra         True   28        0         0.1204
bidirectional    True   28        0         0.1378
greedy           True   28        0         0.0868
```

## Analysis

The `analyze()` method reports:
- **Total walls remaining** — fewer = more open maze
- **Dead ends** — cells with only 1 opening (useful for difficulty assessment)
- **Corridors** — cells with exactly 2 openings
- **Junctions** — cells with 3+ openings (decision points)
- **Solution length** — shortest path length from start to end
- **Is perfect** — whether the maze is a perfect maze (connected, no cycles)
- **Braid ratio** — fraction of non-dead-end cells

## Algorithm Notes

- **Recursive Backtracking** produces the most "maze-like" feel with long corridors
- **Wilson's** generates a mathematically uniform random spanning tree (slow on large mazes)
- **Eller's** is memory-efficient, needing only O(width) memory regardless of height
- **Binary Tree** and **Sidewinder** are biased but extremely fast
- **A\*** with Manhattan distance is the fastest optimal solver on 4-connected grids
- **Bidirectional BFS** can be faster than standard BFS on large mazes by meeting in the middle
- **Greedy Best-First** is the fastest but may not find the shortest path
- **Braid mazes** are easier to navigate but harder to solve optimally (multiple paths)

## Known Issues (Resolved)

The following bugs were identified during the bug hunt phase and have been fixed:

1. **Benchmark explored count was 0 for A\*, Dijkstra, greedy, and bidirectional solvers** — These solvers used their own internal `closed`/`visited` sets instead of the `cell.visited` flag. The `benchmark()` method counted explored cells via `cell.visited`, resulting in 0 for these solvers. **Fix**: All solvers now set `cell.visited = True` when they visit a cell, ensuring the benchmark reports accurate exploration counts.

2. **Kruskal's algorithm removed walls even when cells were already connected** — The generator always called `remove_wall()` without checking the return value of `union()`, creating cycles (non-perfect mazes with extra openings). **Fix**: `remove_wall()` is now only called when `union()` returns `True` (cells were in different sets).

3. **`distance_map()` returned all -1 when called after `solve()` or `is_perfect()`** — The BFS in `distance_map()` relied on `cell.visited` flags, but previous operations (solve, is_perfect) left these flags set to `True`. The BFS immediately terminated because all neighbors appeared visited. **Fix**: `distance_map()` now calls `reset_visited()` before starting the BFS.

4. **`from_dict()` didn't validate wall data dimensions or wall names** — Malformed JSON could cause cryptic `IndexError` or `KeyError` exceptions instead of clear error messages. **Fix**: Added dimension validation (rows/columns match declared width/height) and wall name validation with descriptive error messages.

5. **Misleading comment in `to_png()`** — Comment said "RGBA pixel buffer" but the buffer is actually RGB (3 bytes per pixel). **Fix**: Corrected comment to "RGB pixel buffer (3 bytes per pixel, row-major, top-to-bottom)".

## Testing

The project includes a comprehensive test suite (`test_maze.py`) with 71 tests covering:

- Direction and Cell unit tests
- Maze construction and validation
- All 7 generation algorithms (perfect maze + solvability checks)
- All 6 solving algorithms (path validity, shortest path verification)
- Heuristic functions (Manhattan, Euclidean, Chebyshev)
- Braid functionality
- JSON serialization (round-trip, file I/O, invalid data)
- Maze validation (perfect maze check)
- Distance maps
- Waypoint pathfinding
- ASCII rendering
- PNG export
- Benchmarking (explored count correctness)
- Edge cases (1×1, 2×2, 1×N, N×1 mazes)

```bash
# Run the test suite
python3 -m pytest test_maze.py -v

# Or run directly
python3 test_maze.py
```

## License

MIT