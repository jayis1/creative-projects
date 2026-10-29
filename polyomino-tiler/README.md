# Polyomino Tiler

A dependency-free exact-cover solver for tiling arbitrary finite cell boards with supplied polyominoes. It generates unique rotations/reflections, enumerates legal placements as bit masks, then uses Algorithm X-style recursive search with a minimum-remaining-values cell heuristic.

## Run

From this directory:

```sh
python3 main.py --demo
python3 main.py --limit 3
python3 -m unittest discover -s tests -v
```

The demo constructs a 4×5 rectangle and twenty monominoes, reports the number of solutions found (up to `--limit`), and prints one ASCII tiling. `--help` lists options. No external packages or input files are needed.

## How it works

Each board cell and each piece is an exact-cover constraint. A placement covers its cells and consumes its piece. The solver branches on the uncovered cell with the fewest currently legal placements, pruning dead ends early. Coordinates are integer `(row, column)` pairs; reflections are enabled by default.

## Known Issues (Resolved)

- Negative-coordinate boards previously generated no placements because translation anchors started at zero. `test_negative_coordinate_board_tiles` reproduced the failure; placement bounds now include negative anchors and the regression test passes.

## API

```python
from tiling import TilingSolver
board = [(0, 0), (0, 1)]
pieces = [[(0, 0)], [(0, 0)]]
solutions = TilingSolver(board, pieces).solve(limit=2)
```

Pass `reflections=False` to disallow mirror images. `solve(limit=...)` bounds result accumulation, and constructor validation rejects duplicate board or piece coordinates and area mismatches. The constructor also accepts one-shot iterables such as generators.
