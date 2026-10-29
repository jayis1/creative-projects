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

## API

```python
from tiling import TilingSolver
board = [(0, 0), (0, 1)]
pieces = [[(0, 0)], [(0, 0)]]
solutions = TilingSolver(board, pieces).solve(limit=2)
```

Pass `reflections=False` to disallow mirror images. Piece identities are distinct, even when shapes are identical. `render(board, solution)` prints piece labels; boards may be disconnected or sparse.
