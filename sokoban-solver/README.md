# sokoban-solver

A from-scratch Sokoban toolkit that parses ASCII warehouse levels, validates them, analyzes static structure, renders boards, and solves box-pushing puzzles with push-aware A* search plus deadlock pruning.

## Highlights

- ASCII Sokoban level parser with validation
- Immutable board model and renderer
- Push-aware A* search over player/box states
- Reachability flood fill for legal push generation
- Static corner deadlock pruning
- CLI commands for `solve`, `render`, and `analyze`
- Pure stdlib Python 3.11+

## How it works

The solver represents each state as `(player_position, frozenset(box_positions))`. For each expanded state, it computes every floor tile the player can reach without moving boxes. Whenever the player can stand behind a box and the destination square beyond that box is free, the solver generates a push successor.

Search uses A* with a push-first cost model. The heuristic estimates remaining work by summing Manhattan distances from boxes to goals. For small box counts, it checks all box-goal assignments for a tighter lower bound. Static non-goal corner tiles are precomputed and treated as deadlocks: if a box is pushed into one of those corners, the state is discarded immediately.

## Installation

```bash
cd sokoban-solver
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
```

## Usage

### Solve a level

```bash
python3 -m sokoban_solver solve --level "#####\n#@$.#\n#####" --json
```

### Render a level

```bash
python3 -m sokoban_solver render --level "#####\n#@$.#\n#####"
```

### Analyze a level

```bash
python3 -m sokoban_solver analyze --level "#####\n#@$.#\n#####"
```

## Example level

```text
#####
#@$.#
#####
```

Expected solution: `R`.

## Project layout

- `sokoban_solver/models.py` — board and result dataclasses
- `sokoban_solver/parser.py` — ASCII parser and validation
- `sokoban_solver/solver.py` — state search and deadlock pruning
- `sokoban_solver/cli.py` — command-line interface
- `tests/test_solver.py` — smoke tests

## Limitations

Phase 1 intentionally focuses on single-level solving with simple static deadlocks. More advanced analysis and usability improvements can be layered on later.
