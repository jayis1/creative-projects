# sokoban-solver

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/sokoban-solver.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions/workflows/sokoban-solver.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

A polished Sokoban toolkit for parsing ASCII warehouse levels, analyzing static structure, solving puzzles with push-aware A* search, explaining deadlocks visually, solving multi-level packs, exporting solution traces, and benchmarking curated built-in levels.

---

## Table of Contents

- [Highlights](#highlights)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Configuration Files](#configuration-files)
- [ASCII Demo](#ascii-demo)
- [Architecture](#architecture)
- [Examples and Docs](#examples-and-docs)
- [Recent Improvements](#recent-improvements)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Highlights

- Push-aware A* solver optimized lexicographically for pushes first, walking distance second
- Exact Manhattan assignment lower bound via dynamic-programming bipartite matching
- Static deadlock pruning using both corner analysis and reverse-pull dead-square detection
- Explain mode with annotated overlays for reachable cells and pruned dead squares
- Multi-level pack solving with human-readable titles
- JSON solution export suitable for tooling or replay UIs
- Built-in benchmark levels for smoke testing and performance checks
- Pure stdlib Python 3.11+

## Installation

```bash
cd sokoban-solver
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .[dev]
```

### Run the test suite

```bash
pytest
```

## Quick Start

### Solve a built-in level

```bash
python3 -m sokoban_solver solve --builtin tiny-one --json
```

### Explain why a level is hard

```bash
python3 -m sokoban_solver explain --builtin corridor
```

### Solve a small level pack

```bash
python3 -m sokoban_solver solve-pack --file examples/tutorial-pack.txt --json
```

### Export a full solution trace

```bash
python3 -m sokoban_solver solve \
  --builtin tiny-one \
  --show-frames \
  --output examples/tiny-one-solution.json
```

### Use a TOML config file

```bash
python3 -m sokoban_solver \
  --config examples/default-config.toml \
  solve --builtin detour-two
```

## CLI Reference

### Commands

- `solve` — solve one level
- `render` — render one level as ASCII
- `analyze` — report counts and deadlock information
- `explain` — render annotated reachability/deadlock overlays
- `solve-pack` — solve every level in a text pack
- `benchmark` — solve all built-in levels
- `list-levels` — list built-in levels
- `version` — print the package version

### Solve examples

```bash
python3 -m sokoban_solver solve --file example_level.txt
python3 -m sokoban_solver solve --builtin room-shift --show-frames
python3 -m sokoban_solver solve --builtin mini-warehouse --max-states 400000 --json
```

### Analyze examples

```bash
python3 -m sokoban_solver analyze --builtin corridor --json
python3 -m sokoban_solver analyze --builtin corridor --show-overlay
python3 -m sokoban_solver explain --builtin detour-two
```

### Pack examples

```bash
python3 -m sokoban_solver solve-pack --file examples/tutorial-pack.txt
python3 -m sokoban_solver benchmark --json
```

## Configuration Files

`--config` accepts JSON or TOML. Example:

```toml
[solver]
max_states = 50000

[output]
json = true
show_frames = false

[logging]
level = "INFO"
```

Supported keys:

- `solver.max_states`
- `output.json`
- `output.show_frames`
- `logging.level`

## ASCII Demo

Input level:

```text
########
#@ $ . #
#  ##  #
#      #
########
```

Explain overlay:

```text
########
#@·$·.x#
#x·##·x#
#xxxxxx#
########
```

Legend:

- `·` reachable empty floor
- `c` static corner deadlock
- `x` reverse-pull dead square

## Architecture

The project is intentionally modular:

- `models.py` — immutable board and result dataclasses
- `parser.py` — ASCII parsing, validation, and topology checks
- `io.py` — single-level input and pack parsing
- `config.py` — runtime defaults from JSON/TOML
- `analysis.py` — reachability, deadlocks, overlays, assignment lower bound
- `solver.py` — push-aware A* search and pack solving helpers
- `cli.py` — argparse front-end, logging setup, JSON export

### How solving works

1. Parse and validate the board.
2. Compute static deadlock structures once.
3. Expand states by reachable player positions and legal pushes.
4. Rank frontier states by push count, walking distance, and heuristic lower bound.
5. Reconstruct both the compact push string and the full move string.

See also: [`docs/architecture.md`](./docs/architecture.md)

## Examples and Docs

- [`examples/default-config.toml`](./examples/default-config.toml)
- [`examples/tutorial-pack.txt`](./examples/tutorial-pack.txt)
- [`examples/demo.md`](./examples/demo.md)
- [`docs/architecture.md`](./docs/architecture.md)
- [`docs/github-actions-workflow.yml`](./docs/github-actions-workflow.yml) — ready-to-enable GitHub Actions workflow template

## Recent Improvements

### v0.3.0

- Added `solve-pack` for multi-level batch solving
- Added `explain` overlays for reachable cells, corner deadlocks, and reverse-pull dead squares
- Added JSON/TOML config-file support
- Added logging and solution export to JSON files
- Replaced factorial heuristic assignment with an exact dynamic-programming matcher
- Expanded the built-in level catalog with larger examples
- Split the code into dedicated `analysis`, `config`, `io`, and `constants` modules
- Added CI workflow template, examples, docs, `.gitignore`, and a much larger 15-test suite

### Earlier work

- Lexicographic optimization for pushes then walking distance
- Full movement reconstruction with lowercase walks and uppercase pushes
- Reverse-pull dead-square analysis
- Replay frame generation for solved plans
- Parser validation for malformed or disconnected maps

## Known Issues (Resolved)

- **Ragged ASCII maps created phantom floor tiles**: omitted cells are now treated as void, not traversable floor.
- **Rendered boards could lose rectangular alignment**: rendering now preserves board width for replay alignment.

## Roadmap

- Add stronger dynamic deadlock detection for frozen box groups
- Support standard Sokoban level-set formats beyond the lightweight text pack
- Add optional HTML/SVG replay export
- Introduce macro moves / tunnel compression for larger maps
- Add benchmark history tracking for solver regressions

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## License

MIT. See [`LICENSE`](./LICENSE).
