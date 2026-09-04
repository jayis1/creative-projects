# Architecture

## Modules

- `particle_life_sim.engine` validates configs, spawns particles, advances the physics, and produces core metrics.
- `particle_life_sim.analysis` computes higher-level emergent-behavior metrics and parameter-sweep reports.
- `particle_life_sim.render` renders ASCII, SVG, and PPM previews.
- `particle_life_sim.io` handles JSON, TOML, YAML, and CSV I/O.
- `particle_life_sim.cli` wires the package into task-oriented commands.

## Data flow

1. Config or preset data is loaded and validated.
2. The engine builds particles and a wrapped spatial hash.
3. Each step computes wrapped pairwise forces within the interaction radius.
4. Integrators update velocities and positions with drag and speed clamps.
5. Analysis and rendering consume the live particle state without mutating it.

## Design choices

- Toroidal wrapping keeps density consistent at the boundaries.
- Spatial hashing keeps neighbor discovery local.
- Snapshot files are portable JSON so simulations can be resumed and compared.
- Analysis metrics are intended for experimentation, not just visualization.
