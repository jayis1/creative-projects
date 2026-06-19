# nbody-sim

A 2-D **Barnes–Hut N-body gravity simulator** with symplectic leapfrog
integration, PPM frame rendering, energy/momentum diagnostics, and four
built-in initial-condition presets (two-body circular orbit, figure-eight
choreography, Plummer sphere, random cloud).

The simulator is pure-Python and dependency-free — it only uses the standard
library. It is designed to be both a teaching tool (clear, well-commented
implementation of the Barnes–Hut algorithm) and a usable experimental harness
for small-to-medium 2-D gravity systems.

## How it works

### Barnes–Hut quadtree (`nbody/barnes_hut.py`)

The naive O(N²) all-pairs force calculation becomes prohibitive beyond a few
thousand bodies. Barnes–Hut replaces it with an O(N log N) approximation:

1. **Build a quadtree** over all body positions. Each node owns a square
   region of space and stores the total mass and center-of-mass of everything
   inside it.
2. **Walk the tree** for each body. When a node's angular size
   `size / distance` drops below the opening angle θ, treat the whole node as
   a single point mass at its center-of-mass — skip its children. Otherwise
   recurse into the four children.

With θ = 0 the tree is always fully traversed and the result is exact
(brute-force). With θ ≈ 0.5–1.0 the approximation is typically within a
fraction of a percent of the exact answer at a large speedup.

A **Plummer softening** length ε is applied: the interaction distance becomes
`sqrt(d² + ε²)`, which prevents singular accelerations when two bodies get
very close. The same softening is used consistently in both the tree force
evaluator and the brute-force energy diagnostic so the two agree.

### Symplectic leapfrog integrator (`nbody/integrator.py`)

Each step is a **kick–drift–kick** (KDK) leapfrog:

```
v_{1/2} = v_0    + ½·a(x_0)·dt     # kick (half)
x_1     = x_0    + v_{1/2}·dt      # drift (full)
v_1     = v_{1/2} + ½·a(x_1)·dt    # kick (half)
```

Leapfrog is *symplectic*: the energy error stays bounded over exponentially
long times rather than drifting secularly as with explicit Euler. This is why
the figure-eight orbit (below) stays on its trajectory for thousands of steps.

### Rendering (`nbody/renderer.py`)

The renderer maps world coordinates onto a pixel grid, draws each body as a
soft-edged disc whose radius scales (logarithmically) with mass, and
optionally keeps a persistent alpha buffer so successive frames build up
**motion trails** that fade toward the background color each step. Output is
**PPM (P6)** — a trivial binary format that needs no encoder library. A
sequence of frames can be turned into a video with e.g.:

```
ffmpeg -framerate 30 -i frame_%06d.ppm -c:v libx264 -pix_fmt yuv420p out.mp4
```

## Project layout

```
nbody-sim/
├── nbody/
│   ├── __init__.py        # public API
│   ├── __main__.py        # python3 -m nbody entry point
│   ├── vec.py             # 2-D vector helpers
│   ├── body.py            # Body dataclass
│   ├── barnes_hut.py      # quadtree + θ-opening force evaluator
│   ├── integrator.py      # leapfrog (KDK) integrator
│   ├── simulation.py      # Simulation orchestrator + presets
│   ├── renderer.py        # PPM frame renderer with trails
│   └── cli.py             # argparse CLI
├── examples/
│   ├── two_body.py        # circular orbit demo
│   ├── figure_eight.py    # Chenciner–Montgomery choreography
│   └── cluster_collapse.py
└── README.md
```

## Usage

### As a library

```python
from nbody.simulation import Simulation

# Figure-eight: three equal masses on a single shared orbit.
sim = Simulation.figure_eight(dt=0.001, theta=0.5, softening=0.0)
result = sim.run(2000)
print(f"dE/E = {abs(result.final_energy - result.initial_energy) / abs(result.initial_energy):.2e}")
# → dE/E ≈ 4e-8  (energy drift over 2000 steps)
```

### From the command line

```bash
# Run a two-body orbit and log energy/momentum to CSV.
python3 -m nbody --preset two-body --steps 1000 --dt 0.01 --log energy.csv

# Render the figure-eight to a sequence of PPM frames.
python3 -m nbody --preset figure-eight --steps 500 --dt 0.005 \
    --snapshot-every 5 --render frames/ --width 512 --height 512

# Simulate a 200-body Plummer sphere.
python3 -m nbody --preset plummer --n-bodies 200 --steps 2000 --dt 0.01 \
    --theta 0.7 --softening 0.5
```

Run `python3 -m nbody --help` for the full option list.

## Presets

| Preset | Description |
|---|---|
| `two-body` | Two equal masses in a circular orbit about their COM. |
| `figure-eight` | The Chenciner–Montgomery three-body choreography — three equal masses chasing each other along a single figure-eight curve. |
| `plummer` | N bodies sampled from a Plummer density profile `ρ ∝ (1+r²)^{-5/2}`, with near-virial velocities. |
| `random` | N bodies scattered uniformly in a square with random small velocities — a stress test for the tree. |

## Diagnostics

The :class:`Simulation` exposes:

- `total_energy(bodies)` — kinetic + softened potential energy.
- `total_momentum(bodies)` — conserved vector (should be constant).
- `center_of_mass(bodies)` — for COM-relative rendering.

The CLI prints the initial/final energy, the relative drift `dE/E`, and both
momentum vectors; with `--log energy.csv` it writes a per-snapshot CSV with
columns `step, t, energy, px, py`.

## Why symplectic matters

Naive Euler integration (`x += v·dt; v += a·dt`) injects energy into a
gravitational system at a rate proportional to `dt`, causing orbits to spiral
outward and clusters to evaporate. Leapfrog's staggered half-kicks make the
update a *canonical* (area-preserving) map, so the energy error oscillates
rather than accumulates. The figure-eight preset is a sensitive test: with
Euler it disintegrates within a few dozen steps, while with leapfrog it is
stable for tens of thousands.

## License

MIT — see the repository root.