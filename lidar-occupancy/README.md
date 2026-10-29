# Lidar Occupancy

Build a bounded 2D occupancy grid from planar range measurements. This dependency-free Python project demonstrates the mapping core used by mobile robots: each beam clears traversed cells and adds evidence at a return endpoint.

Run the deterministic demo:

```sh
python3 main.py --demo
```

Output:

```text
_______________
____#__________
_____._____.#__
______.__..____
_______..______
________.._____
__________.#___
_______________
_______________
```

## How it works

The map stores log-odds evidence per cell. A ray is rasterized with integer Bresenham line traversal. For a hit, every traversed cell before the last receives free-space evidence, while the endpoint receives occupied evidence. A miss treats the full traversed ray as free. Updates saturate to a bounded interval, preventing numeric growth while naturally accumulating repeated observations. World coordinates are translated by map origin and cell resolution; out-of-map endpoints are clipped against the map rectangle.

## Usage

```python
from main import Grid

map_ = Grid.create(40, 30, resolution=0.25, origin_x=-5, origin_y=-3.75)
map_.trace_ray((0.0, 0.0), (2.1, 1.2), hit=True)
print(map_.render())
```

## Acceptance checks

- Rasterize rays in all octants with contiguous cells.
- Distinguish free traversal, hit endpoints, and no-return beams.
- Reject invalid dimensions, non-finite coordinates, and excessive map allocation.
- Keep accumulated cell evidence bounded.

Run tests with `python3 -m unittest discover -s . -p 'test_*.py' -v`.

## Enhancements

- `integrate_scan()` ingests angle/range beams, clamps no-return beams to a maximum range, and bounds scans to 100,000 beams.
- Per-scan free and occupied log-odds increments are configurable through both ray and scan APIs.
- `summary()` reports occupied/free/unknown counts and evidence limits; `to_json()` provides deterministic metadata and cell export.
- ASCII rendering uses `#` for occupied, `.` for free, and `_` for unknown cells.

## Known Issues (Resolved)

- An in-map ray endpoint was initially treated as a hit even when the measured endpoint lay beyond the grid; this falsely marked the clipped map edge as occupied. Regression test: `test_out_of_map_hit_does_not_invent_boundary_obstacle`. Clipped out-of-map endpoints now only update traversed cells as free space.
