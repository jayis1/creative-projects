# Maze Generator & Solver

A comprehensive Python toolkit for generating and solving mazes, featuring **7 generation algorithms** and **5 solving algorithms** with ASCII rendering, path highlighting, and statistical analysis.

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

### Solving Algorithms (5)

| Solver | Strategy | Guarantees |
|--------|----------|------------|
| **BFS** | Breadth-first search | Shortest path |
| **DFS** | Depth-first search | Any path (not shortest) |
| **A*** | Heuristic-guided | Shortest path (with admissible heuristic) |
| **Dijkstra** | Priority queue | Shortest path |
| **Bidirectional BFS** | Two-frontier BFS | Shortest path, faster convergence |

## How It Works

### Maze Representation

The maze uses a **grid-of-cells** model. Each `Cell` stores:
- **Position** `(x, y)` in the grid
- **Walls** — a set of `Direction` enums (NORTH, EAST, SOUTH, WEST) that are *present*
- **Visited** flag used during generation and solving

Initially every cell is fully walled (all four walls present). Generation algorithms remove walls to carve passages, producing a **perfect maze** (exactly one path between any two cells).

### Rendering

The ASCII renderer maps each cell to a 2×2 character block in a character grid of size `(width*2+1) × (height*2+1)`. Walls are drawn as `|` (vertical) and `-` (horizontal), with `+` at corners. Solution paths are overlaid with `·` markers.

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

# Generate with analysis statistics
python3 maze.py -W 30 -H 15 -g wilsons --analyze --seed 123

# Use a specific solver
python3 maze.py -W 10 -H 10 -g kruskals -s dijkstra --solve
```

**Options:**
- `-W, --width` — Maze width in cells (default: 20)
- `-H, --height` — Maze height in cells (default: 10)
- `-g, --generator` — Generation algorithm (default: recursive_backtracking)
- `-s, --solver` — Solving algorithm (default: bfs)
- `--seed` — Random seed for reproducibility
- `--solve` — Solve and display the solution path
- `--analyze` — Print maze statistics (dead ends, corridors, junctions, solution length)
- `--no-display` — Suppress maze rendering

### Python API

```python
from maze import Maze

# Create a 20×10 maze
maze = Maze(20, 10, seed=42)

# Generate using Prim's algorithm
maze.generate("prims")

# Solve using A*
solution = maze.solve("astar")
print(f"Solution has {len(solution)} steps")

# Render the maze with the solution path highlighted
print(maze._render_clean(solution=solution))

# Analyze maze properties
stats = maze.analyze()
print(f"Dead ends: {stats['dead_ends']}")
print(f"Junctions: {stats['junctions']}")

# Set custom start/end points
maze.set_start(0, 0)
maze.set_end(19, 9)
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

## Analysis

The `analyze()` method reports:
- **Total walls remaining** — fewer = more open maze
- **Dead ends** — cells with only 1 opening (useful for difficulty assessment)
- **Corridors** — cells with exactly 2 openings
- **Junctions** — cells with 3+ openings (decision points)
- **Solution length** — shortest path length from start to end

## Algorithm Notes

- **Recursive Backtracking** produces the most "maze-like" feel with long corridors
- **Wilson's** generates a mathematically uniform random spanning tree (slow on large mazes)
- **Eller's** is memory-efficient, needing only O(width) memory regardless of height
- **Binary Tree** and **Sidewinder** are biased but extremely fast
- **A\*** with Euclidean distance heuristic is the fastest solver on typical mazes
- **Bidirectional BFS** can be faster than standard BFS on large mazes by meeting in the middle

## License

MIT