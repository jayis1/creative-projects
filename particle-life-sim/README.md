# particle-life-sim

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-pytest-informational)

A reusable Particle Life toolkit for simulating, analyzing, resuming, rendering, and tuning emergent multi-species motion in a toroidal 2D world.

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick start](#quick-start)
- [CLI reference](#cli-reference)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Examples and docs](#examples-and-docs)
- [Recent improvements](#recent-improvements)
- [Known issues (resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Overview

Particle Life uses a species-to-species interaction matrix to turn local attraction and repulsion rules into large-scale behavior: swarms, rotating lanes, predator-prey loops, and clustered textures. This project started as a simulation and now includes experiment-management tools around it.

```text
..........1....22........
......1.............2....
...1.......3.............
........33......2........
1=cyan 2=violet 3=gold
```

## Features

- Toroidal simulation space with wrapped neighbor lookups
- Deterministic seeding for reproducible runs
- Euler and midpoint integration modes
- Spatial-hash acceleration for local force evaluation
- JSON, TOML, YAML, and snapshot loading
- ASCII, SVG, and PPM rendering
- Snapshot export and resume workflow
- Advanced analysis metrics: occupancy entropy, wrapped pairwise distance, momentum, species spread, speed deviation
- Parameter sweep command for scanning seeds, force scales, and drags
- JSON and CSV report output for automation
- Installable package with console entry point
- Examples, architecture notes, contribution guide, and license

## Installation

### Editable install

```bash
cd particle-life-sim
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

### Verify the install

```bash
particle-life-sim presets
pytest
```

## Quick start

List presets:

```bash
particle-life-sim presets
```

Export a preset to YAML, edit it, then run it:

```bash
particle-life-sim export-preset aurora --output aurora.yaml
particle-life-sim run --config aurora.yaml --steps 150 --dt 0.1 --seed 7
```

Render an SVG preview:

```bash
particle-life-sim render --preset petri --steps 250 --dt 0.08 --format svg --output out/petri.svg
```

Write a metrics timeline as CSV:

```bash
particle-life-sim timeline --preset aurora --steps 120 --dt 0.1 --sample-every 20 --output out/timeline.csv
```

Run advanced analysis:

```bash
particle-life-sim analyze --preset binary-star --steps 180 --dt 0.1 --bins 10
```

Resume from a saved snapshot:

```bash
particle-life-sim snapshot --preset aurora --steps 50 --dt 0.1 --output out/snap.json
particle-life-sim resume out/snap.json --steps 50 --dt 0.1 --save-snapshot out/snap-100.json
```

Search for interesting parameter combinations:

```bash
particle-life-sim sweep \
  --preset aurora \
  --steps 90 \
  --dt 0.1 \
  --seeds 1 2 3 \
  --force-scales 32 40 48 \
  --drags 0.03 0.05 0.08 \
  --output out/sweep.json
```

## CLI reference

### `presets`
Print bundled preset names.

### `export-preset`
Export a bundled preset to `.json`, `.yaml`, or `.yml`.

### `run`
Run a simulation and emit final metrics. Optional `--output` writes JSON.

### `timeline`
Run a simulation and emit sampled metrics over time. `--output` supports `.json` or `.csv`.

### `render`
Render ASCII, SVG, or PPM output after a run.

### `snapshot`
Save the current simulation state as JSON for later replay.

### `resume`
Load a snapshot, continue simulating, optionally save a new snapshot.

### `analyze`
Emit higher-level emergent-behavior metrics on top of the engine’s base metrics.

### `sweep`
Batch-run combinations of seeds, drag values, and force scales, then rank results by a novelty heuristic.

## Configuration

The CLI accepts `.json`, `.toml`, `.yaml`, and `.yml` configs.

### YAML example

```yaml
width: 120
height: 80
drag: 0.04
force_scale: 46
interaction_radius: 18
repulsion_radius: 3
max_speed: 9
integrator: midpoint
species:
  - name: cyan
    color: "#3ad5ff"
    count: 24
  - name: violet
    color: "#9d5cff"
    count: 22
  - name: gold
    color: "#ffd166"
    count: 18
interactions:
  - [0.7, -0.9, 0.6]
  - [0.8, 0.4, -0.8]
  - [-0.7, 0.9, 0.2]
```

### Analysis output fields

Beyond the core metrics, `analyze` adds:

- `occupancy_entropy` — how evenly particles fill the coarse grid
- `pairwise_mean_distance` — wrapped average spacing across all particle pairs
- `speed_stddev` — velocity dispersion
- `momentum` — net motion vector and magnitude
- `species_spread` — wrapped average spread around each species centroid
- `microsteps` — total internal integrator updates

## Architecture

The project is split into focused modules:

- `particle_life_sim.engine` — config validation, particle stepping, snapshots, base metrics
- `particle_life_sim.analysis` — experiment metrics and parameter sweeps
- `particle_life_sim.render` — ASCII, SVG, and PPM renderers
- `particle_life_sim.io` — JSON/TOML/YAML/CSV helpers
- `particle_life_sim.cli` — user-facing command entry points

More detail lives in [`docs/architecture.md`](docs/architecture.md).

## Examples and docs

- [`examples/aurora-variant.yaml`](examples/aurora-variant.yaml) — editable YAML preset example
- [`examples/resume-demo.sh`](examples/resume-demo.sh) — snapshot, resume, and analyze workflow
- [`docs/architecture.md`](docs/architecture.md) — package structure and data flow
- [`docs/github-actions.yml.example`](docs/github-actions.yml.example) — workflow example scoped to this project folder

## Recent improvements

- Added YAML config and preset export support
- Added `analyze`, `resume`, and `sweep` CLI commands
- Added JSON and CSV report output paths for automation
- Added wrapped-centroid calculations so boundary-crossing clusters are measured correctly
- Added snapshot validation for out-of-range species ids
- Added advanced analysis metrics and experiment-ranking heuristics
- Added examples, architecture docs, contribution guide, and MIT license
- Expanded the pytest suite to cover new commands and edge cases

## Known issues (resolved)

- **Substep accounting mismatch**: `step_count` no longer inflates when `substeps > 1`.
- **Spatial-hash duplicate neighbors**: wrapped bucket scans no longer double count in tiny worlds.
- **CLI output path failures**: render, snapshot, and preset export commands now create parent directories.
- **Wrapped centroid drift**: species centered near both edges of the torus no longer report a false midpoint through the world center.
- **Unsafe snapshot species ids**: snapshot resume now rejects particles with invalid species indices.

## Roadmap

- Add animation export for frame sequences or GIF/MP4 pipelines
- Add richer preset-generation tools for procedural exploration
- Add alternate force laws and boundary modes
- Add browser-based visualization for live parameter tuning
- Add benchmarking commands for larger populations

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). For a ready-to-adapt workflow file, see [`docs/github-actions.yml.example`](docs/github-actions.yml.example).

## License

MIT. See [`LICENSE`](LICENSE).
