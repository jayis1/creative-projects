# nbody-sim

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-brightgreen.svg)](../../.github/workflows/nbody-sim-ci.yml)
[![Tests: 92](https://img.shields.io/badge/tests-92%20passing-success.svg)](tests/)
[![Version: 3.0](https://img.shields.io/badge/version-3.0-orange.svg)](#changelog)

A high-performance **2D Barnes–Hut N-body gravity simulator** featuring three
symplectic and non-symplectic integrators, NumPy-accelerated force evaluation,
config-file support (YAML/JSON/TOML), structured logging, PPM frame rendering
with motion trails, seven built-in initial-condition presets, comprehensive
diagnostics, and a full-featured CLI.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [As a Library](#as-a-library)
  - [From the Command Line](#from-the-command-line)
  - [Config Files](#config-files)
- [Integrators](#integrators)
- [Presets](#presets)
- [Architecture](#architecture)
- [Diagnostics](#diagnostics)
- [Advanced Features](#advanced-features)
- [Examples](#examples)
- [Why Symplectic Matters](#why-symplectic-matters)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

- **Barnes–Hut quadtree** — O(N log N) force evaluation with configurable θ opening criterion
- **Three integrators**:
  - `leapfrog` — kick–drift–kick (KDK) symplectic, O(dt²), bounded energy error
  - `rk4` — classical 4th-order Runge–Kutta, O(dt⁴), high per-step accuracy
  - `forest-ruth` — 4th-order symplectic, O(dt⁴), bounded energy + high accuracy
- **7 presets**: two-body orbit, figure-eight choreography, Plummer sphere, random cloud, solar system, eccentric binary, Kuzmin disk
- **NumPy-accelerated brute force** — 100–500× faster than pure-Python O(N²)
- **Config files** — YAML, JSON, and TOML support
- **PPM frame renderer** with motion trails, mass/speed-based coloring
- **Adaptive timestep** based on max acceleration
- **COM-frame recentering** for zero bulk drift
- **Comprehensive diagnostics**: energy, momentum, angular momentum, virial ratio, min separation, max acceleration
- **JSON serialization** for full runs and snapshots
- **Benchmarking**: Barnes–Hut vs brute force comparison
- **Structured logging** with configurable verbosity
- **92-test pytest suite** with GitHub Actions CI
- **pip-installable** with `pyproject.toml`

---

## Installation

### From source (recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/nbody-sim

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[test]"
```

### As a standalone package

```bash
cd creative-projects/nbody-sim
pip install .
```

### Requirements

- Python 3.10+
- numpy ≥ 1.24
- PyYAML ≥ 6.0 (for YAML config files)
- pytest ≥ 7.0 (for tests, optional)

---

## Quick Start

```python
from nbody.simulation import Simulation

# Figure-eight: three equal masses on a shared orbit.
sim = Simulation.figure_eight(dt=0.001, theta=0.5, softening=0.0)
result = sim.run(2000)
print(f"dE/E = {abs(result.final_energy - result.initial_energy) / abs(result.initial_energy):.2e}")
# → dE/E ≈ 4e-8
```

From the CLI:

```bash
python3 -m nbody --preset two-body --steps 1000 --dt 0.01 --log energy.csv
```

---

## Usage

### As a Library

**Basic simulation:**

```python
from nbody.simulation import Simulation

sim = Simulation.two_body_orbit(dt=0.005, theta=0.5, softening=0.05)
result = sim.run(2000)
print(f"Energy drift: dE/E = {abs(result.final_energy - result.initial_energy) / abs(result.initial_energy):.2e}")
print(f"Final momentum: {result.final_momentum}")
```

**Using different integrators:**

```python
from nbody.simulation import Simulation

# Leapfrog (default, symplectic, O(dt²))
sim_lf = Simulation.two_body_orbit(dt=0.005, integrator="leapfrog")

# RK4 (non-symplectic, O(dt⁴), best for short high-accuracy runs)
sim_rk4 = Simulation.two_body_orbit(dt=0.005, integrator="rk4")

# Forest–Ruth (symplectic, O(dt⁴), best for long demanding runs)
sim_fr = Simulation.two_body_orbit(dt=0.005, integrator="forest-ruth")
```

**Adaptive timestep:**

```python
sim = Simulation.plummer_sphere(
    n=200, seed=42, adaptive_dt=True, adaptive_eta=0.01,
    dt_min=1e-6, dt_max=0.1, softening=0.5,
)
result = sim.run(2000, snapshot_every=20)
```

**Rendering frames:**

```python
from nbody.renderer import Renderer

sim = Simulation.random_cloud(n=120, seed=7, dt=0.02, theta=0.6, softening=0.8)
result = sim.run(400, snapshot_every=10)

r = Renderer(width=512, height=512, view_size=15.0, trails=True,
             color_by_mass=True)
paths = r.render_sequence(result.snapshots, "frames/")
# Convert to video: ffmpeg -framerate 30 -i frames/frame_%06d.ppm -c:v libx264 out.mp4
```

**NumPy-accelerated force evaluation:**

```python
from nbody.numpy_force import numpy_accelerations, numpy_energy
from nbody.body import Body

bodies = [Body(0, 0, 0, 0, 1), Body(2, 0, 0, 0, 1), Body(0, 2, 0, 0, 0.5)]
accels = numpy_accelerations(bodies, G=1.0, softening=0.1)  # 100× faster than pure Python
energy = numpy_energy(bodies, G=1.0, softening=0.1)
```

**Loading from a config file:**

```python
from nbody.config import load_config

cfg = load_config("configs/plummer_example.yaml")
print(f"preset={cfg.preset}, N={cfg.n_bodies}, steps={cfg.steps}")
```

### From the Command Line

```bash
# Two-body orbit with energy logging
python3 -m nbody --preset two-body --steps 1000 --dt 0.01 --log energy.csv

# Figure-eight with Forest–Ruth integrator
python3 -m nbody --preset figure-eight --steps 5000 --dt 0.002 \
    --integrator forest-ruth --snapshot-every 50 --render frames/ --view-size 2.0

# 200-body Plummer sphere, COM-recentered, mass-colored render
python3 -m nbody --preset plummer --n-bodies 200 --steps 2000 --dt 0.01 \
    --theta 0.7 --softening 0.5 --recenter-com \
    --snapshot-every 20 --render frames/ --color-by-mass

# Solar system
python3 -m nbody --preset solar-system --steps 5000 --dt 0.0001 \
    --softening 0.01 --snapshot-every 100 --render frames/ --view-size 2.0

# Eccentric binary system
python3 -m nbody --preset binary --steps 2000 --dt 0.005 --softening 0.1

# Kuzmin disk
python3 -m nbody --preset kuzmin-disk --n-bodies 100 --steps 1000 \
    --softening 0.5 --recenter-com --render frames/

# Adaptive timestep
python3 -m nbody --preset random --n-bodies 100 --adaptive-dt \
    --adaptive-eta 0.01 --steps 200 --snapshot-every 10 --render frames/

# Benchmark Barnes-Hut vs brute force
python3 -m nbody --preset random --n-bodies 400 --benchmark --theta 0.8

# Save full run to JSON
python3 -m nbody --preset figure-eight --steps 200 --snapshot-every 10 \
    --save-json run.json

# Run from a config file
python3 -m nbody --config configs/plummer_example.yaml

# Save current CLI config to a file
python3 -m nbody --preset plummer --n-bodies 200 --save-config my_sim.yaml
```

Run `python3 -m nbody --help` for the full option list.

### Config Files

Config files provide a declarative alternative to CLI flags. Supported
formats: **YAML**, **JSON**, **TOML**.

```yaml
# sim.yaml
preset: plummer
n_bodies: 200
seed: 42
dt: 0.01
theta: 0.7
softening: 0.5
G: 1.0
steps: 2000
recenter_com: true
snapshot_every: 20
render:
  enabled: true
  width: 512
  height: 512
  view_size: 15.0
  trails: true
  color_by_mass: true
  out_dir: frames
output:
  log_csv: energy.csv
  save_json: run.json
  verbose: false
```

Run with: `python3 -m nbody --config sim.yaml`

Example config files are in `configs/`:
- `plummer_example.yaml` — Plummer sphere with rendering
- `figure8_forest_ruth.yaml` — Figure-eight with Forest–Ruth integrator
- `binary_system.json` — Eccentric binary in JSON format

---

## Integrators

| Integrator | Order | Symplectic | Best For |
|---|---|---|---|
| `leapfrog` | O(dt²) | ✅ Yes | General-purpose, long runs |
| `rk4` | O(dt⁴) | ❌ No | Short, high-accuracy runs |
| `forest-ruth` | O(dt⁴) | ✅ Yes | Demanding long simulations |

**Energy conservation comparison** (two-body orbit, 2000 steps, dt=0.005):

| Integrator | dE/E |
|---|---|
| leapfrog | 2.1e-09 |
| rk4 | 1.6e-08 |
| forest-ruth | 2.9e-14 |

The Forest–Ruth integrator achieves **5 orders of magnitude** better energy
conservation than leapfrog at the same timestep, thanks to its 4th-order
symplectic structure.

---

## Presets

| Preset | Description |
|---|---|
| `two-body` | Two equal masses in a circular orbit about their COM. |
| `figure-eight` | Chenciner–Montgomery three-body choreography — three equal masses chasing each other along a figure-eight curve. |
| `plummer` | N bodies sampled from a Plummer density profile ρ ∝ (1+r²)^(-5/2), with near-virial velocities. |
| `random` | N bodies scattered uniformly in a square with random small velocities. |
| `solar-system` | Simplified inner solar system: Sun + Mercury, Venus, Earth, Mars with circular orbital velocities. |
| `binary` | Two bodies in an eccentric orbit (configurable eccentricity). |
| `kuzmin-disk` | N bodies in a Kuzmin thin-disk surface density profile with circular velocities. |

---

## Architecture

```
nbody-sim/
├── nbody/
│   ├── __init__.py          # Public API exports
│   ├── __main__.py          # python -m nbody entry point
│   ├── body.py              # Body dataclass
│   ├── vec.py               # 2D vector helpers
│   ├── barnes_hut.py        # Barnes-Hut quadtree + θ-opening force evaluator
│   ├── integrator.py        # Legacy leapfrog integrator
│   ├── integrators.py       # All integrators (leapfrog, RK4, Forest-Ruth)
│   ├── simulation.py        # Simulation orchestrator + 7 presets
│   ├── diagnostics.py       # Angular momentum, virial ratio, adaptive dt
│   ├── brute_force.py       # O(N²) ground truth + benchmark harness
│   ├── numpy_force.py       # NumPy-accelerated force evaluation
│   ├── renderer.py          # PPM frame renderer with trails + coloring
│   ├── serialize.py         # JSON snapshot/run serialization
│   ├── config.py            # YAML/JSON/TOML config system
│   ├── cli.py               # Argparse CLI with --config, --save-config
│   └── logging_utils.py    # Structured logging
├── examples/
│   ├── two_body.py          # Circular orbit demo
│   ├── figure_eight.py      # Figure-eight choreography
│   ├── cluster_collapse.py  # Random cloud collapse with rendering
│   ├── solar_system.py      # Solar system demo
│   ├── integrator_comparison.py  # Compare all three integrators
│   └── config_demo.py       # Config file loading demo
├── configs/
│   ├── plummer_example.yaml
│   ├── figure8_forest_ruth.yaml
│   └── binary_system.json
├── tests/
│   ├── test_barnes_hut.py   # Quadtree construction + force evaluation
│   ├── test_integrators.py  # All three integrators
│   ├── test_simulation.py   # Simulation, presets, run logic
│   ├── test_misc.py         # Config, numpy, serialize, renderer, diagnostics
│   └── test_bughunt.py      # Original bug-hunt tests (7 tests)
├── pyproject.toml           # Package metadata + pip-installable
├── LICENSE
├── CONTRIBUTING.md
└── README.md
```

### How It Works

#### Barnes–Hut Quadtree (`nbody/barnes_hut.py`)

The naive O(N²) all-pairs force calculation becomes prohibitive beyond a few
thousand bodies. Barnes–Hut replaces it with an O(N log N) approximation:

1. **Build a quadtree** over all body positions. Each node owns a square
   region of space and stores the total mass and center-of-mass.
2. **Walk the tree** for each body. When a node's angular size
   `size / distance` drops below the opening angle θ, treat the whole node
   as a single point mass — skip its children.

With θ = 0 the tree is fully traversed (exact brute-force). With θ ≈ 0.5–1.0
the approximation is typically within a fraction of a percent at large speedup.

A **Plummer softening** length ε prevents singular accelerations at very small
separations: the interaction distance becomes `sqrt(d² + ε²)`.

#### Symplectic Leapfrog (`nbody/integrators.py`)

Each step is a **kick–drift–kick** (KDK) leapfrog:

```
v_{1/2} = v_0    + ½·a(x_0)·dt     # kick (half)
x_1     = x_0    + v_{1/2}·dt      # drift (full)
v_1     = v_{1/2} + ½·a(x_1)·dt    # kick (half)
```

Leapfrog is *symplectic*: the energy error stays bounded over exponentially
long times rather than drifting secularly as with explicit Euler.

#### Forest–Ruth 4th-Order Symplectic (`nbody/integrators.py`)

Uses three concatenated leapfrog sub-steps with special timestep weights
derived from the Forest–Ruth coefficients:

```
θ = 1 / (2 - 2^(1/3)) ≈ 1.3512
w0 = -2^(1/3) / (2 - 2^(1/3))
w1 = 1 / (2 - 2^(1/3))
```

The step interleaves four drifts and three kicks with these weights, achieving
O(dt⁴) accuracy while remaining symplectic (bounded energy error).

#### Rendering (`nbody/renderer.py`)

The renderer maps world coordinates onto a pixel grid, draws each body as a
soft-edged disc whose radius scales (logarithmically) with mass, and optionally
keeps a persistent alpha buffer for **motion trails** that fade toward the
background color each step. Output is **PPM (P6)** — a trivial binary format.

---

## Diagnostics

The `Simulation` class exposes:
- `total_energy()` — kinetic + softened potential energy
- `total_momentum()` — conserved linear momentum vector
- `center_of_mass()` — COM position

Additional diagnostics in `nbody.diagnostics`:
- `total_angular_momentum(bodies, about)` — z-component of L
- `com_velocity(bodies)` — mass-weighted average velocity
- `virial_ratio(bodies, G, softening)` — 2T/|U|, equals 1 at virial equilibrium
- `min_separation(bodies)` — smallest pairwise distance
- `max_acceleration(bodies, G, softening)` — largest acceleration magnitude
- `adaptive_dt(bodies, ...)` — stable timestep from η·√(ε/a_max)

---

## Advanced Features

### COM-Frame Recentering (`--recenter-com`)

Subtracts the center-of-mass position and velocity from every body at start,
so the total momentum is exactly zero and the COM sits at the origin. Removes
spurious bulk drift from random clouds.

### Adaptive Timestep (`--adaptive-dt`)

Recomputes the step each iteration from the current maximum acceleration:
`dt = η · √(ε / a_max)`, clamped to `[dt_min, dt_max]`. The step shrinks during
close encounters and grows during quiet phases.

### Barnes–Hut vs Brute-Force Benchmark (`--benchmark`)

Builds both evaluators for the same configuration and reports wall-clock
times, speedup, and the max/mean relative force error.

### Mass- and Speed-Based Coloring

`--color-by-mass`: cool blue (low mass) → warm orange (high mass).
`--color-by-speed`: deep red (slow) → bright yellow (fast).

### JSON Serialization (`--save-json`)

Full runs (config + all snapshots + energy/momentum) can be saved to JSON
and reloaded for offline analysis or re-rendering.

### Config Files (`--config`)

Load simulation configuration from YAML, JSON, or TOML files. Use
`--save-config` to write the current CLI configuration to a file.

---

## Examples

Run any example from the `nbody-sim/` directory:

```bash
# Two-body orbit energy conservation
python3 examples/two_body.py

# Figure-eight choreography
python3 examples/figure_eight.py

# Cluster collapse with PPM rendering
python3 examples/cluster_collapse.py

# Solar system (Sun + inner planets)
python3 examples/solar_system.py

# Compare all three integrators
python3 examples/integrator_comparison.py

# Config file loading demo
python3 examples/config_demo.py
```

---

## Why Symplectic Matters

Naive Euler integration (`x += v·dt; v += a·dt`) injects energy into a
gravitational system at a rate proportional to `dt`, causing orbits to spiral
outward and clusters to evaporate. Leapfrog's staggered half-kicks make the
update a *canonical* (area-preserving) map, so the energy error oscillates
rather than accumulates. The figure-eight preset is a sensitive test: with
Euler it disintegrates within a few dozen steps, while with leapfrog it is
stable for tens of thousands.

The Forest–Ruth 4th-order symplectic integrator goes further: it achieves
dt⁴ local truncation error while preserving the symplectic structure,
resulting in energy drift ~5 orders of magnitude smaller than leapfrog at
the same timestep.

---

## Testing

```bash
# Run all 92 tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_integrators.py -v

# Run the original bug-hunt tests
pytest tests/test_bughunt.py -v
```

The test suite covers:
- Barnes–Hut quadtree construction, force evaluation, edge cases
- All three integrators (energy/momentum conservation, step correctness)
- Simulation construction, validation, run logic, presets
- Config file loading/saving (YAML, JSON)
- NumPy-accelerated force evaluation (matches pure Python)
- JSON serialization round-trips
- Renderer (PPM output, aspect ratio, coloring)
- Diagnostics (angular momentum, virial ratio, adaptive dt)
- Original bug-hunt regression tests (7 tests)

---

## Known Issues (Resolved)

All bugs found during the Phase 3 bug hunt have been fixed and verified by
tests in `tests/test_bughunt.py` (7 tests, all passing).

1. **`run()` initial snapshot used hardcoded `t=0.0` instead of `self.t`.**
   Fixed: use `self.step_count` and `self.t` for the initial snapshot.
2. **CLI missed the final snapshot** when `steps` was not a multiple of
   `--snapshot-every`. Fixed: pass `snapshot_every` directly to `run()`.
3. **Renderer distorted aspect ratio** when `width != height`. Fixed: use
   uniform scale based on the shorter image dimension.
4. **Unused imports** in `barnes_hut.py`. Fixed: removed.
5. **`plummer_sphere` could produce bodies at enormous radii.** Fixed: clamp
   `u` to 0.999 and cap `r` at `10 × R`.
6. **`Simulation` did not validate `dt` when `adaptive_dt` was enabled.** Fixed:
   the validation now only applies `dt <= 0.0` when `adaptive_dt` is False.

---

## Roadmap

- **3D extension** — extend the quadtree to an octree for 3D simulations
- **Fast Multipole Method (FMM)** — O(N) force evaluation for very large N
- **HDF5 serialization** — efficient binary format for large runs
- **Parallel tree build** — multi-threaded quadtree construction
- **GPU acceleration** — CUDA/OpenCL force evaluation
- **Interactive viewer** — real-time rendering with pan/zoom
- **Initial condition import** — load from CSV/HDF5/Gadget format
- **Collision handling** — merger/fragmentation events
- **External potential** — add fixed potential sources (e.g., galactic halo)
- **N-body + SPH** — smooth-particle hydrodynamics coupling

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding
conventions, and guidelines for adding new integrators, presets, and config
options.

---

## Changelog

### v3.0.0 (June 2026) — Comprehensive Improvement

**New Features:**
- Added RK4 4th-order Runge–Kutta integrator
- Added Forest–Ruth 4th-order symplectic integrator
- Added 3 new presets: solar-system, binary (eccentric), kuzmin-disk
- Added NumPy-accelerated brute-force force evaluation (`numpy_force.py`)
- Added config file system (YAML/JSON/TOML) with `--config` and `--save-config`
- Added structured logging module
- Added `--integrator` CLI flag for integrator selection
- Added `--quiet` CLI flag
- Added `--save-config` CLI flag

**Architecture:**
- Created `integrators.py` module with all three integrators + registry
- Created `config.py` module with `SimConfig`, `RenderConfig`, `OutputConfig`
- Created `numpy_force.py` module for vectorized force evaluation
- Created `logging_utils.py` module for structured logging
- Updated `simulation.py` to support integrator selection and new presets
- Updated `cli.py` with config file support, integrator selection, new presets
- Updated `__init__.py` with all new exports

**Project Infrastructure:**
- Added `pyproject.toml` (pip-installable, entry point `nbody`)
- Added GitHub Actions CI (Python 3.10/3.11/3.12)
- Added `CONTRIBUTING.md`
- Added `LICENSE` (MIT)
- Added `configs/` directory with example config files
- Added 3 new example scripts
- Added 85 new tests (92 total, all passing)

### v2.0.0 — Enhanced

- Added diagnostics module (angular momentum, virial ratio, adaptive dt)
- Added brute-force O(N²) evaluator + benchmark harness
- Added adaptive timestep mode
- Added COM-frame recentering
- Added mass/speed-based renderer coloring
- Added JSON snapshot/run serialization
- Added input validation
- Expanded CLI options

### v1.0.0 — Initial Release

- Barnes–Hut quadtree with θ-opening criterion
- Symplectic kick–drift–kick leapfrog integrator
- Plummer softening
- 4 presets (two-body, figure-eight, Plummer sphere, random cloud)
- PPM frame renderer with motion trails
- Energy/momentum diagnostics
- Argparse CLI

---

## License

MIT — see [LICENSE](LICENSE).