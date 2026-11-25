# Coverage Path Lab

A dependency-free grid robot coverage planner. It generates a deterministic alternating-row (boustrophedon-style) sweep and uses four-neighbor A* to connect cells around obstacles. This is a practical baseline planner, not a globally shortest route optimizer.

## How it works

Input is a rectangular ASCII map: `.` is traversable and `#` is blocked. The planner first checks that the free-space graph is connected, then orders free cells in alternating horizontal sweeps. A* joins each successive target while respecting obstacles. The output includes the complete walk (including connector cells) and its Manhattan length.

## Usage

```python
from coverage import plan_coverage, render

map_rows = ["....", ".##.", "...."]
plan = plan_coverage(map_rows, start=(0, 0))
print(render(map_rows, plan))
print(f"steps: {plan.distance:g}; visited: {len(set(plan.cells))}")
```

Run the tests with `python3 -m unittest -v` from this folder. No third-party packages are needed.

Input must be a non-empty rectangular grid using only `.` and `#`. Disconnected free-space maps and blocked/out-of-bounds starts are rejected.
