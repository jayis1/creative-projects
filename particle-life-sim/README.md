# particle-life-sim

Particle Life is a generative artificial-life simulator where colored particle species attract and repel one another according to an interaction matrix. The system turns simple local rules into swarming bands, orbiting clusters, predator-prey chases, and soft cellular-looking textures.

## Features

- Toroidal 2D world with species-to-species interaction matrix
- Deterministic seeding for reproducible runs
- Two integrators: `euler` and `midpoint`
- Spatial-hash acceleration for local neighbor lookups
- Bundled presets: `aurora`, `petri`, `binary-star`
- JSON and TOML config loading
- Metrics output as JSON, including nearest-neighbor and neighborhood statistics
- Timeline sampling for long runs
- Renderers: ASCII, SVG, and text PPM
- Snapshot export and snapshot restore API
- Packaged CLI via `python3 -m particle_life_sim` or `particle-life-sim`

## How it works

Each particle belongs to a species. On every step the simulator:

1. Uses a spatial hash to find nearby candidate particles instead of scanning the full population blindly.
2. Computes wrapped displacement in a toroidal world.
3. Looks up an attraction/repulsion coefficient from the interaction matrix.
4. Adds a short-range repulsion term to prevent collapse.
5. Integrates velocity and position with drag and speed clamping.
6. Wraps positions back into the domain.

The `midpoint` integrator samples the force field twice per step for smoother motion than basic Euler updates.

## Project layout

- `particle_life_sim/engine.py` — config validation, spatial hash, simulator, metrics
- `particle_life_sim/render.py` — ASCII, SVG, PPM renderers
- `particle_life_sim/presets.py` — bundled preset definitions
- `particle_life_sim/io.py` — JSON/TOML loading and JSON writing helpers
- `particle_life_sim/cli.py` — command-line interface
- `tests/test_particle_life.py` — regression and behavior tests

## Installation

```bash
cd particle-life-sim
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
pip install pytest
```

## Usage

List presets:

```bash
python3 -m particle_life_sim presets
```

Export a bundled preset to edit it:

```bash
python3 -m particle_life_sim export-preset aurora --output aurora.json
```

Run a preset and print final metrics:

```bash
python3 -m particle_life_sim run --preset aurora --steps 200 --dt 0.1 --substeps 2 --seed 7
```

Emit a sampled metrics timeline:

```bash
python3 -m particle_life_sim timeline --preset petri --steps 100 --dt 0.08 --sample-every 20
```

Render SVG output:

```bash
python3 -m particle_life_sim render --preset petri --steps 250 --dt 0.08 --format svg --output petri.svg
```

Render ASCII output:

```bash
python3 -m particle_life_sim render --preset binary-star --steps 80 --dt 0.1 --format ascii --output binary-star.txt
```

Save a snapshot:

```bash
python3 -m particle_life_sim snapshot --preset aurora --steps 120 --dt 0.1 --output snapshot.json
```

## Config format

The CLI accepts `.json` and `.toml` configs.

### JSON example

```json
{
  "width": 120,
  "height": 80,
  "drag": 0.05,
  "force_scale": 42,
  "interaction_radius": 18,
  "repulsion_radius": 3,
  "max_speed": 9,
  "integrator": "midpoint",
  "species": [
    {"name": "a", "color": "#ff5577", "count": 20},
    {"name": "b", "color": "#55ddff", "count": 20}
  ],
  "interactions": [
    [0.7, -0.8],
    [-0.8, 0.7]
  ]
}
```

### TOML example

```toml
width = 120
height = 80
drag = 0.05
force_scale = 42
interaction_radius = 18
repulsion_radius = 3
max_speed = 9
integrator = "euler"

[[species]]
name = "a"
color = "#ff5577"
count = 20

[[species]]
name = "b"
color = "#55ddff"
count = 20

interactions = [[0.7, -0.8], [-0.8, 0.7]]
```

Then run:

```bash
python3 -m particle_life_sim run --config my-config.toml --steps 180 --dt 0.1
```

## Output metrics

Typical metrics include:

- `mean_speed`
- `max_speed`
- `mean_radius`
- `neighbor_checks`
- `species_energy`
- `species_centers`
- `nearest_neighbor`

These are useful when tuning interaction matrices for desired emergent behavior.
