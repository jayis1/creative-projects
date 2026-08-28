# sokoban-solver

A from-scratch Sokoban toolkit that parses ASCII warehouse levels, validates them, analyzes static structure, benchmarks built-in puzzles, renders boards, replays solutions, and solves box-pushing puzzles with push-aware A* search plus deadlock pruning.

## Highlights

- ASCII Sokoban parser with validation and topology checks
- Immutable board model and renderer
- Push-aware A* search optimized lexicographically for pushes then walking distance
- Reachability flood fill with actual walk-path reconstruction
- Static corner deadlocks plus reverse-pull dead-square analysis
- Built-in sample level catalog and benchmark mode
- Solution replay frames for debugging and demos
- CLI commands for `solve`, `render`, `analyze`, `list-levels`, and `benchmark`
- Pure stdlib Python 3.11+

## How it works

The solver represents each state as `(player_position, frozenset(box_positions))`. For each expanded state, it computes every floor tile the player can reach without moving boxes and remembers the exact walking path to each tile. Whenever the player can stand behind a box and the destination square beyond that box is free, the solver emits a push successor.

Search uses A* with lexicographic cost `(pushes, walking_steps)`, which makes the solver prefer minimal pushes and then prefer shorter movement plans among equal-push candidates. The heuristic estimates remaining work by matching boxes to goals using Manhattan distance; for small levels it checks every assignment for a tighter lower bound.

Static deadlock analysis happens in two layers:

1. **Corner deadlocks**: non-goal tiles trapped against perpendicular walls.
2. **Dead squares**: tiles from which a hypothetical box cannot be reverse-pulled to any goal.

These checks prune obviously doomed states early, making the solver significantly faster and more informative.

## Installation

```bash
cd sokoban-solver
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
```

## Usage

### Solve a built-in level

```bash
python3 -m sokoban_solver solve --builtin tiny-one --json
```

### Replay a solution as ASCII frames

```bash
python3 -m sokoban_solver solve --builtin tiny-one --show-frames
```

### Render a level from file

```bash
python3 -m sokoban_solver render --file example_level.txt
```

### Analyze dead squares and topology

```bash
python3 -m sokoban_solver analyze --builtin corridor --json
```

### Benchmark all built-in levels

```bash
python3 -m sokoban_solver benchmark --json
```

### List built-in levels

```bash
python3 -m sokoban_solver list-levels
```

## Built-in levels

- `tiny-one` — one-push smoke-test level
- `tiny-two` — compact two-box micro puzzle
- `corridor` — narrow passage puzzle with dead-square analysis
- `room-shift` — two-box room shuffling puzzle

## Example level

```text
#####
#@$.#
#####
```

Expected solution: `R`.

## Project layout

- `sokoban_solver/models.py` — board and result dataclasses
- `sokoban_solver/parser.py` — ASCII parser, validation, and topology checks
- `sokoban_solver/levels.py` — built-in level catalog
- `sokoban_solver/solver.py` — search, deadlocks, replay, and heuristics
- `sokoban_solver/cli.py` — command-line interface
- `tests/test_solver.py` — regression and feature tests

## Enhancements added in Phase 2

- Lexicographic optimization for pushes and walking distance
- Reconstructed movement sequences with lowercase walks and uppercase pushes
- Reverse-pull dead-square analysis
- Built-in level catalog and multi-level benchmark mode
- Replay frame generation for solved plans
- Extra parser validation for unreachable boxes and goals
- Expanded tests and docs

## Limitations

The solver is still geared toward small and medium handcrafted levels. It does not yet include advanced pattern databases, macro moves, or canonical tunnel compression.
