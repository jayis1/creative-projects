# particle-life-sim

Particle Life is a generative artificial-life simulator where colored particle species attract and repel one another according to an interaction matrix. The result is a self-organizing system that produces swirling clusters, chases, rings, and unstable ecosystems from simple local rules.

## Features

- Toroidal 2D world with pairwise species interactions
- Deterministic seeding for reproducible runs
- Bundled presets: `aurora`, `petri`, `binary-star`
- Metrics output as JSON
- Renderers: ASCII, SVG, and text PPM
- Snapshot export for later analysis
- Packaged CLI via `python3 -m particle_life_sim` or `particle-life-sim`

## How it works

Each particle belongs to a species. For every simulation step, every particle:

1. Measures the wrapped displacement to every other particle.
2. Looks up an attraction/repulsion coefficient in the species interaction matrix.
3. Applies a short-range repulsion term to avoid collapse.
4. Updates velocity with drag and caps speed.
5. Wraps around the edges of the world.

This simple rule set is enough to generate visually rich emergent motion.

## Installation

```bash
cd particle-life-sim
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Usage

List presets:

```bash
python3 -m particle_life_sim presets
```

Run a preset and print metrics:

```bash
python3 -m particle_life_sim run --preset aurora --steps 200 --dt 0.1 --seed 7
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

Use a custom JSON config:

```json
{
  "width": 120,
  "height": 80,
  "drag": 0.05,
  "force_scale": 42,
  "interaction_radius": 18,
  "repulsion_radius": 3,
  "max_speed": 9,
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

Then run:

```bash
python3 -m particle_life_sim run --config my-config.json --steps 180 --dt 0.1
```
