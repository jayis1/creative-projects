# Wavefront Planner

A dependency-free weighted-grid route planner using 8-connected A*. It supports blocked cells, terrain-dependent travel costs, diagonal movement without corner cutting, deterministic routes, and route/expansion metrics.

## How it works

A* orders candidate cells by accumulated travel cost plus an admissible octile-distance lower bound. Entering a cell costs its terrain weight (multiplied by √2 for a diagonal step). `None` represents an obstacle; all other terrain weights must be finite and positive. Diagonal moves are legal only when both adjoining cardinal cells are open, preventing movement through obstacle corners.

## Python API

```python
from planner import Grid, find_path

grid = Grid.from_rows([
    [1, 1, 1, 1],
    [1, None, 4, 1],
    [1, 1, 1, 1],
])
route = find_path(grid, (0, 0), (3, 2))
if route is None:
    print("No route")
else:
    print(route.points, route.cost, route.expanded)
```

Coordinates are `(x, y)`. `find_path` returns `None` when no route exists, otherwise a `Route` with endpoint-inclusive coordinates, total cost, and number of expanded cells. Start equals goal returns a zero-cost one-cell route. Invalid or blocked endpoints raise `ValueError`.

## JSON CLI

Scenario schema: one object with `grid` (rectangular array of positive costs or `null` obstacles), `start`, and `goal` coordinate arrays.

```sh
python3 cli.py example.json
# Prints one JSON object with reachable, path, cost, and expanded
```

The CLI exits 2 and prints a concise error to stderr for invalid JSON, invalid scenario data, or an unreadable file. Unreachable valid maps print `{"reachable":false}` and exit 0.

## Tests

Python 3.10+; standard library only. Run `python3 -m unittest -v` from this directory.

## Known Issues (Resolved)

- Source review and regression checks found no reproducible defects within the tested scope. No implementation bug was changed in the bug-hunt phase; the added tiny-cost test records supported boundary behavior rather than claiming a fix.
