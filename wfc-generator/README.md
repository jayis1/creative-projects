# WFC Generator

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests: 120](https://img.shields.io/badge/tests-120%20passing-brightgreen.svg)](#testing)
[![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-orange.svg)](#changelog)

> A **Wave Function Collapse** (WFC) procedural generation engine in pure Python.
> Generate terrain maps, dungeons, cities, circuits, mazes, villages and
> fantasy islands that locally respect the adjacency rules you define — or
> learn those rules automatically from a sample pattern.

```
~~~~~~~~~~~~~~~~~~~~  ─→  ggghgTTggTggTggg.gggg
~~~~~~~~~~.~~~~~.g       ggTg.~.~.g.~.gg.g
~~~~~~~~~~~~~~.gg       ─ WFC turns a uniform
~~~~~~~~~~~~~.~...       "superposition" into a
~~~~~~~~~~~~.g...        locally-consistent map
```

---

## Table of Contents

- [Overview](#overview)
- [Key features](#key-features)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Generation modes](#generation-modes)
- [CLI reference](#cli-reference)
- [Configuration files](#configuration-files)
- [Python API](#python-api)
- [Selection strategies](#selection-strategies)
- [Rendering formats](#rendering-formats)
- [Architecture](#architecture)
- [Examples](#examples)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [License](#license)

---

## Overview

WFC is an algorithm inspired by quantum mechanics: every cell of the output
starts in a *superposition* of all possible tiles. The engine repeatedly:

1. finds the uncollapsed cell with the **lowest entropy** (fewest options),
2. **collapses** it to a single tile via weighted random choice,
3. **propagates** the resulting constraints to neighbours (arc consistency),

until every cell is collapsed, or an unrecoverable contradiction triggers
backtracking / a fresh restart. The result is a pattern that *locally* looks
like the rules you provided — a dungeon that walls off rooms, a terrain that
transitions water → sand → grass → forest → mountain, a circuit whose wires
actually connect, and so on.

This engine supports both the **tiled model** (explicit per-side adjacency
constraints) and the **overlap model** (constraints learned from a sample).

## Key features

- 🎛️ **7 built-in preset tile sets** — terrain, dungeon, city, circuit, maze,
  plus the new **village** and **islands** presets.
- 🧠 **Overlap model** — learn adjacency rules automatically from a 2D sample.
- 🔁 **Backtracking + restarts** — recover from contradictions without failing.
- 🔁 **Periodic (toroidal) boundaries** for seamless tiling textures.
- 🎯 **4 selection strategies** — `min_entropy` (Shannon), `mrv`
  (minimum-remaining-values), `random`, `lexical`.
- ⚡ **Optional entropy cache** for faster large-grid generation.
- 🎨 **5 renderers** — ANSI terminal, plain text, HTML, SVG, PNG (Pillow).
- 📝 **Configuration system** — JSON, YAML and TOML config files.
- 🖥️ **Full CLI** — argparse subcommands, `--help`, `--version`, `-v` logging.
- 💾 **Serialization** — dump a generated grid + stats to JSON.
- 📦 **Installable** — `pip install -e .` provides a `wfc` console script.
- 🧪 **120 tests** — 71 pytest cases + 49 legacy assertions, all green.
- 🏗️ **Modular package** — `wfc_generator/` with one module per concern.
- 🔌 **Backward compatible** — `from wfc import ...` still works via a shim.

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/jayis1/creative-projects
cd creative-projects/wfc-generator

python3 -m venv .venv
source .venv/bin/activate          # .venv\Scripts\activate on Windows

pip install -e ".[dev]"             # installs wfc-generator + pytest + pyyaml
```

This gives you a `wfc` console script on your `$PATH`.

### Optional extras

| Extra       | Install command                | Adds                                |
|-------------|--------------------------------|-------------------------------------|
| `yaml`      | `pip install ".[yaml]"`        | PyYAML config-file support          |
| `png`       | `pip install ".[png]"`         | Pillow for PNG rendering            |
| `dev`       | `pip install ".[dev]"`        | pytest + pyyaml (for contributors)  |

### No dependencies required

The core engine is **pure Python (≥3.9)** with zero required dependencies.
PyYAML and Pillow are strictly optional.

## Quick start

```bash
# Generate a 40x25 terrain map with a fixed seed
wfc terrain --width 40 --height 25 --seed 42

# Generate a dungeon and write SVG output
wfc dungeon --width 30 --height 20 --output dungeon.svg

# Generate a village using the MRV selection strategy, with stats
wfc village --width 25 --height 20 --selection mrv --stats

# Generate from a sample using the overlap model
wfc overlap --sample sample.json --width 20 --height 20 --n 3

# Generate from a custom tile set, auto-symmetrizing constraints
wfc custom --tileset tiles.json --width 20 --height 12 --symmetrize

# Run from a YAML/JSON/TOML config file
wfc run examples/config_village.yaml --output out.svg

# List available presets
wfc list-presets --detail

# Validate a custom tile set
wfc validate-tileset tiles.json

# Generate + serialize the grid to JSON
wfc serialize --preset maze --width 12 --height 8 --output grid.json
```

The original entry point also still works:

```bash
python3 wfc.py terrain --width 40 --height 25 --seed 42
```

## Generation modes

| Mode       | Description                                          | Tiles |
|------------|------------------------------------------------------|-------|
| `terrain`  | Natural terrain with elevation transitions           | deep_water, shallow_water, sand, grass, forest, hill, mountain, snow |
| `dungeon`  | Dungeon maps with rooms and corridors                | floor, wall, corridor, door, pillar, stairs, treasure |
| `city`     | City layouts with roads and buildings                 | road_h, road_v, intersection, building, park, sidewalk, parking |
| `circuit`  | Circuit board patterns with wires and components    | empty, wire_h/v, wire corners (NE/NW/SE/SW), junction, component, via |
| `maze`     | Maze-like patterns                                   | path, wall, dead_end |
| `village`  | 🆕 Cozy medieval village: houses, trees, fountains    | grass, path, building, tree, flower, fountain, market, gate |
| `islands`  | 🆕 Fantasy archipelago with volcanic & frozen tiles  | deep_water, shallow_water, sand, grass, tree, hill, lava, ice |
| `overlap`  | Learn constraints from a sample pattern              | auto-extracted from the sample |
| `custom`   | Load tile definitions from JSON                      | user-defined |

## CLI reference

```
wfc [--version] [-v|-vv] <mode> [options]
```

| Option               | Description                                              | Default |
|----------------------|----------------------------------------------------------|---------|
| `--width`            | Grid width                                               | 30      |
| `--height`           | Grid height                                              | 20      |
| `--seed`             | Random seed for reproducibility                          | random  |
| `--periodic`         | Use periodic (toroidal) boundaries                       | off     |
| `--backtrack-limit`  | Max full restarts on contradiction                       | 10      |
| `--selection`        | Cell selection strategy (`min_entropy`/`mrv`/`random`/`lexical`) | `min_entropy` |
| `--cache-entropy`    | Maintain an entropy cache (faster on large grids)        | off     |
| `--output`           | Output file (`.html`/`.svg`/`.png`/`.txt`/`.json`)        | stdout  |
| `--cell-size`        | Cell size in px for html/svg/png                         | 16      |
| `--stats`            | Print generation statistics                              | off     |
| `--config`           | Load base config from a JSON/YAML/TOML file             | —       |
| `-v` / `-vv`         | Increase logging verbosity (INFO / DEBUG)               | WARNING |

Mode-specific options:

| Mode      | Extra options                                            |
|-----------|----------------------------------------------------------|
| `overlap` | `--sample PATH` (required), `--n INT` (pattern size)    |
| `custom`  | `--tileset PATH` (required), `--symmetrize`              |
| `serialize`| `--preset NAME` (required)                              |
| `run`     | `config FILE` (positional), `--output PATH`             |

Run `wfc <mode> --help` for the full per-mode help text.

## Configuration files

Any generation run can be described in a config file (JSON / YAML / TOML):

```yaml
# config_village.yaml
mode: village
width: 40
height: 25
seed: 42
selection: min_entropy
output: out.svg
cell_size: 18
stats: true
```

```bash
wfc run config_village.yaml
```

See [`examples/config_village.yaml`](./examples/config_village.yaml) and
[`examples/config_islands.json`](./examples/config_islands.json) for complete
working examples. CLI flags always override config values.

## Python API

```python
from wfc_generator import (
    Tile, TileSet, WFCGrid, OverlapModel, Renderer,
    WFCConfig, SelectionStrategy,
    create_terrain_tileset, create_village_tileset,
)

# 1. Use a preset tile set
tileset = create_terrain_tileset()
grid = WFCGrid(tileset, width=30, height=20, seed=42,
               selection=SelectionStrategy.MIN_ENTROPY)
if grid.run():
    result = grid.get_result()
    print(Renderer.render_plain(result))
    print(grid.stats)            # GenerationStats(...)
    print(grid.to_json())        # full grid + stats as JSON

# 2. Define custom tiles
ts = TileSet()
sky = Tile("sky", weight=10, color="#87ceeb", data=" ")
ground = Tile("ground", weight=8, color="#8B4513", data="█")
sky.add_constraint("bottom", ["sky", "ground"])
ground.add_constraint("top", ["sky", "ground"])
ts.add_tile(sky); ts.add_tile(ground)
ts.make_all_symmetric()          # bidirectional constraints

g = WFCGrid(ts, 20, 10, seed=7)
assert g.run()
print(Renderer.render_colored(g.get_result()))

# 3. Overlap model: learn from a sample
sample = [
    ["~", "~", ".", "#"],
    [".", "#", "#", "T"],
    ["#", "T", "T", "^"],
]
model = OverlapModel(sample, n=2)
out = model.generate(width=15, height=10, seed=42)
for row in out:
    print("".join(row))
```

### Progress callback

```python
from wfc_generator import WFCGrid, create_dungeon_tileset

def on_progress(fraction):
    print(f"\rProgress: {fraction:.1%}", end="", flush=True)

grid = WFCGrid(create_dungeon_tileset(), 50, 40, on_progress=on_progress)
grid.run()
print()  # newline after progress
```

### Backward compatibility

`from wfc import ...` still works — `wfc.py` is now a thin shim that
re-exports the `wfc_generator` package, so existing code keeps running
unchanged.

## Selection strategies

| Strategy       | How it picks the next cell to collapse            | Good for |
|----------------|---------------------------------------------------|----------|
| `min_entropy`  | Shannon entropy + small noise (default)           | balanced quality |
| `mrv`          | Fewest remaining options; random tie-break        | tight constraints |
| `random`       | Uniformly random uncollapsed cell                 | chaotic variety |
| `lexical`      | First uncollapsed cell in row-major order         | deterministic debug |

```bash
wfc dungeon --width 30 --height 20 --selection mrv --stats
```

## Rendering formats

| Format | Extension | Description                       |
|--------|-----------|-----------------------------------|
| ANSI   | (stdout)  | Colored terminal output           |
| Plain  | `.txt`    | Simple character grid             |
| HTML   | `.html`   | Colored HTML table                |
| SVG    | `.svg`    | Scalable vector graphics          |
| PNG    | `.png`    | Raster image (requires Pillow)    |
| JSON   | `.json`   | Grid + stats serialized (via `serialize` / `--output`) |

## Architecture

```
wfc_generator/
├── __init__.py         # public re-exports + __version__
├── tile.py             # Tile + SIDES / OPPOSITE_SIDE constants
├── tileset.py          # TileSet: validation, JSON I/O, symmetry, rotation
├── stats.py            # GenerationStats (with to_dict serialization)
├── grid.py             # WFCGrid: the core algorithm
│   ├── entropy()         - Shannon entropy with noise tie-break
│   ├── propagate()       - arc-consistency propagation (deque-based)
│   ├── _backtrack()      - state restoration on contradiction
│   ├── _select_cell()    - pluggable SelectionStrategy dispatch
│   ├── run()             - full generation with restart support
│   └── to_json()         - serialize grid + stats
├── overlap.py          # OverlapModel: learn constraints from a sample
├── renderer.py         # Renderer: ANSI / plain / HTML / SVG / PNG
├── presets.py          # create_*_tileset() factories (7 presets)
├── config.py           # WFCConfig: JSON / YAML / TOML loading
├── logging_utils.py    # structured logging setup
└── cli.py              # argparse CLI (subcommands + --config)
```

The original single-file `wfc.py` is preserved as a **backward-compatibility
shim** that re-exports the package, so `from wfc import Tile, WFCGrid, ...`
and `python3 wfc.py terrain ...` keep working.

## Examples

The [`examples/`](./examples) directory contains runnable demos:

| File                              | What it does                                          |
|-----------------------------------|-------------------------------------------------------|
| `generate_terrain.py`             | Terrain map → plain text + SVG                         |
| `overlap_from_sample.py`          | Learn 3×3 patterns from a sample, generate new grid   |
| `compare_strategies.py`           | Benchmark all 4 selection strategies side by side     |
| `config_village.yaml`             | Config-driven village generation (SVG output)          |
| `config_islands.json`             | Config-driven islands generation (JSON output)        |

```bash
python3 examples/compare_strategies.py
```
```
strategy        time(s)   cells/s  backtracks  restarts
-------------------------------------------------------
min_entropy       2.763       217           0         0
mrv              2.486       241           0         0
random           2.419       248           0         0
lexical          2.482       242           0         0
```

## Testing

Two complementary suites, both green:

```bash
# new pytest suite (package-aware, parametrized)
python3 -m pytest tests/ -q          # 71 passed

# legacy self-contained runner (imports via the wfc.py shim)
python3 test_wfc.py                  # 49 passed
```

Total: **120 tests passing**. CI runs both suites on Python 3.9–3.12
(see [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)).

## Contributing

Contributions are welcome! See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the
development setup, project layout, coding standards, and how to add a new
preset tile set. The short version:

```bash
pip install -e ".[dev]"
python3 -m pytest tests/ -q
python3 test_wfc.py
```

## Roadmap

- [ ] 3D / multi-layer support (overlapping volumes)
- [ ] GPU-accelerated propagation via NumPy
- [ ] More sample-learning options (reflections, rotations in the overlap model)
- [ ] Interactive TUI viewer with live collapse stepping
- [ ] More presets (cave systems, road networks, space-station interiors)
- [ ] Animated GIF / WebM output of the collapse process
- [ ] Tile auto-derivation from sprite sheets (image → constraints)

## Known Issues (Resolved)

The following bugs were identified during code review of the original single-file
implementation and have been fixed (tests verify each fix):

1. **`add_rotated_variants` didn't remap tile name references** — rotated
   variants still referenced the base tile name in their constraints. Fixed:
   the method now remaps internal references to their rotated counterparts.
2. **`OverlapModel` didn't validate pattern size `n`** — `n` larger than the
   sample (non-periodic) or `n < 1` caused cryptic failures. Fixed: explicit
   validation with clear error messages.
3. **Custom mode didn't check generation success** — `get_result()` was called
   without checking `run()`. Fixed: success check + error handling added.
4. **Empty constraint sets treated as "skip"** — semantically ambiguous. Fixed:
   empty constraints now explicitly mean "allow all tiles" (wildcard), documented.
5. **Negative tile weights accepted** — broke weighted random selection. Fixed:
   validation in `WFCGrid.__init__` and `TileSet.from_json`.
6. **JSON tileset loading lacked validation** — missing `name` caused a bare
   `KeyError`. Fixed: `from_json` validates each tile and rejects bad weights.

The modular rewrite in v2.0 additionally:
- replaced the recursion-prone propagation with a **deque-based** worklist;
- pre-computed adjacency as **frozensets** for faster intersection;
- added the **entropy cache** for large grids;
- factored the 1727-line monolith into focused, testable modules.

## Changelog

### v2.0.0 — Comprehensive improvement

- **Modular package** `wfc_generator/` (10 modules) replacing the 1727-line
  `wfc.py` monolith, with a backward-compat shim preserving `from wfc import`.
- **2 new presets**: `village` (medieval village with houses, trees, fountains,
  markets, gates) and `islands` (fantasy archipelago with lava & ice tiles).
- **4 pluggable selection strategies** (`min_entropy`, `mrv`, `random`,
  `lexical`) selectable via API and CLI.
- **Entropy cache** option for faster large-grid generation.
- **Configuration system** (`WFCConfig`) with JSON / YAML / TOML loading and
  `wfc run <config>` subcommand.
- **CLI overhaul**: `--version`, `-v`/`-vv` logging, `--backtrack-limit`,
  `--selection`, `--cache-entropy`, `--config`, plus new `list-presets`,
  `validate-tileset`, `serialize`, and `run` subcommands.
- **JSON serialization** of generated grids + stats (`WFCGrid.to_json()`).
- **Structured logging** via `logging_utils.setup_logging`.
- **pyproject.toml** — installable with `pip install -e .`, provides a `wfc`
  console script, optional `[yaml]` / `[png]` / `[dev]` extras.
- **GitHub Actions CI** on Python 3.9–3.12 running both test suites.
- **Examples directory** with 5 runnable demos + config files.
- **71-test pytest suite** (parametrized) alongside the legacy 49-test runner.
- **CONTRIBUTING.md**, **LICENSE**, **.gitignore**.
- Dramatically expanded, professional **README** (this file).

### v1.x — original single-file implementation

Tiled + overlap models, backtracking, periodic boundaries, 5 presets,
JSON tile sets, ANSI/HTML/SVG/PNG rendering, CLI, 49 legacy tests, 6 bug fixes.

## License

[MIT](./LICENSE) — © creative-projects contributors.