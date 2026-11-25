# Wavefront Planner

A dependency-free weighted-grid route planner using 8-connected A*. It supports blocked cells, terrain-dependent travel costs, diagonal movement without corner cutting, deterministic routes, and route/expansion metrics.

## How it works

A* orders candidate cells by accumulated travel cost plus an admissible octile-distance lower bound. Entering a cell costs its terrain weight (multiplied by √2 for a diagonal step). `None` represents an obstacle; all other terrain weights must be finite and positive. Diagonal moves are legal only when both adjoining cardinal cells are open, preventing movement through obstacle corners.

## Usage

```python
from planner import Grid, find_path

grid = Grid.from_rows([[1, 1, 1], [1, None, 1], [1, 1, 1]])
route = find_path(grid, (0, 0), (2, 2))
print(route.points, route.cost, route.expanded)
```

Coordinates are `(x, y)`. `find_path` returns `None` when no route exists, otherwise a `Route` with endpoint-inclusive coordinates, total cost, and number of expanded cells. Start equals goal returns a zero-cost one-cell route. Invalid or blocked endpoints raise `ValueError`.

Run tests from this directory with `python3 -m unittest -v` (Python 3.10+; standard library only).
