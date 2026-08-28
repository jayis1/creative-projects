# Sokoban Solver Architecture

`sokoban-solver` is organized as a small toolkit rather than a single script.

## Modules

- `sokoban_solver/models.py` — immutable board and result dataclasses.
- `sokoban_solver/parser.py` — ASCII parsing, validation, and topology checks.
- `sokoban_solver/levels.py` — built-in demo/benchmark levels.
- `sokoban_solver/io.py` — single-level and multi-level pack loading.
- `sokoban_solver/config.py` — JSON/TOML runtime defaults.
- `sokoban_solver/analysis.py` — reachability, deadlock detection, explain overlays, and exact matching lower bound.
- `sokoban_solver/solver.py` — push-aware A* search and batch solving helpers.
- `sokoban_solver/cli.py` — argparse front-end and JSON export.

## Search flow

1. Parse the level into an immutable `Board`.
2. Compute static deadlock information once:
   - corner deadlocks
   - reverse-pull dead squares
3. Run push-aware A*:
   - states are `(player, frozenset(boxes))`
   - expansion first computes reachable player tiles with shortest walk strings
   - each legal push creates a successor state
4. Rank states with a lexicographic cost of pushes first, walking distance second.
5. Use an exact Manhattan assignment lower bound computed with bitmask DP.
6. Reconstruct both the push sequence and the full move sequence.

## Pack solving

`solve-pack` reads a text file containing multiple levels separated by blank lines. Optional metadata lines such as `; title` or `title: name` label each board. This makes it easy to benchmark hand-authored level sets without inventing a heavier file format.

## Explain overlays

The `explain` command renders a board with annotations:

- `c` = static corner deadlock
- `x` = reverse-pull dead square
- `·` = reachable floor tile for the starting player position

This is intended for debugging levels and understanding why the solver prunes certain branches.
