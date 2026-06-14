# Reaction-Diffusion Pattern Simulator

A pure-Python simulator for **Turing patterns** — the mesmerizing organic patterns that emerge from chemical reaction-diffusion systems. This implements multiple classic models (Gray-Scott, FitzHugh-Nagumo, Gierer-Meinhardt, Brusselator) with high-performance numerical solvers and real-time visualization.

## What Are Reaction-Diffusion Systems?

In 1952, Alan Turing showed that stable chemical patterns (spots, stripes, labyrinths) can emerge when two chemicals react and diffuse at different rates. The general form is:

```
∂u/∂t = Du·∇²u + f(u, v)
∂v/∂t = Dv·∇²v + g(u, v)
```

where `u` and `v` are chemical concentrations, `Du < Dv` (the inhibitor diffuses faster), and `f, g` define the reaction kinetics.

## Features

- **4 Classic Models**: Gray-Scott (spots/labyrinths), FitzHugh-Nagumo (pulse waves), Gierer-Meinhardt (spot splitting), Brusselator (oscillating patterns)
- **Efficient Solver**: Vectorized NumPy computation with 9-point isotropic Laplacian stencil via scipy convolution
- **Boundary Conditions**: Periodic, Dirichlet (fixed), Neumann (zero-flux)
- **Integration Methods**: Forward Euler and RK2 (midpoint) time integration
- **Adaptive Time Stepping**: CFL-like adaptive dt for numerical stability
- **Field Clamping**: Model-specific concentration bounds to prevent overflow
- **Seeded Perturbations**: Point, ring, cross, random, corner, and multi-spot perturbations
- **20+ Parameter Presets**: Curated presets for stunning patterns across all models
- **Visualization**: Static PNG, animated GIF, snapshot grids, with multiple field views (u, v, composite, difference, gradient)
- **CLI Interface**: Full control from the command line with preset overrides
- **Checkpoint/Resume**: Save and load simulation state as compressed NumPy archives
- **Statistics**: Compute and export field statistics (min, max, mean, std) as JSON

## Quick Start

```bash
# Install dependencies
pip install numpy scipy matplotlib pillow

# Run with a preset (coral growth pattern)
python3 rd_sim.py --preset coral

# Gray-Scott mitosis (splitting spots)
python3 rd_sim.py --preset mitosis

# FitzHugh-Nagumo traveling waves
python3 rd_sim.py --model fhn --preset pulse

# Custom parameters with explicit grid/step overrides
python3 rd_sim.py --preset spots --grid 256 --steps 10000

# Animated GIF output
python3 rd_sim.py --preset labyrinth --gif output.gif --gif-frames 50

# Grid of snapshots showing progression
python3 rd_sim.py --preset coral --grid-view --grid-rows 4 --grid-cols 4

# View the gradient field (edge detection)
python3 rd_sim.py --preset mitosis --field gradient -o gradient.png

# Save statistics to JSON
python3 rd_sim.py --preset waves --stats --stats-file stats.json

# Resume from checkpoint
python3 rd_sim.py --resume checkpoint.npz --steps 2000

# Use RK2 integration for better accuracy
python3 rd_sim.py --preset coral --method rk2

# Adaptive time stepping
python3 rd_sim.py --preset spots --adaptive
```

## Models & Presets

| Model | Preset | Key Params | Pattern |
|-------|--------|-----------|---------|
| Gray-Scott | spots | F=0.035, k=0.065 | Solitary spots |
| Gray-Scott | mitosis | F=0.028, k=0.062 | Dividing spots |
| Gray-Scott | coral | F=0.0545, k=0.062 | Branching coral |
| Gray-Scott | labyrinth | F=0.029, k=0.057 | Fingerprint maze |
| Gray-Scott | waves | F=0.014, k=0.045 | Pulsating waves |
| Gray-Scott | finger | F=0.026, k=0.051 | Growing fingers |
| Gray-Scott | holes | F=0.039, k=0.058 | Inverse spots |
| Gray-Scott | stripes | F=0.04, k=0.06 | Stripe formation |
| Gray-Scott | worms | F=0.046, k=0.059 | Worm-like interlace |
| Gray-Scott | chaos | F=0.018, k=0.051 | Chaotic splitting |
| Gray-Scott | solitons | F=0.03, k=0.062 | Stable soliton spots |
| Gray-Scott | nucleation | F=0.025, k=0.06 | Slow nucleation |
| FitzHugh-Nagumo | pulse | ε=0.04, β=0.5 | Traveling pulse |
| FitzHugh-Nagumo | spiral | ε=0.02, β=0.5 | Spiral wave |
| Gierer-Meinhardt | spots_gm | ρ=0.001, μ=0.02 | Self-amplifying spots |
| Gierer-Meinhardt | stripes_gm | ρ=0.002, μ=0.03 | Stripe formation |
| Brusselator | brusselator | A=1.0, B=3.0 | Oscillating pattern |
| Brusselator | brusselator_hex | A=1.0, B=2.5 | Hexagonal pattern |

## How It Works

### Numerical Method

1. **Initialization**: Set up a uniform concentration field with localized perturbations
2. **Laplacian**: Compute spatial derivatives using a 9-point stencil convolution (more isotropic than 5-point)
3. **Time Stepping**: Euler or RK2 (midpoint) method with optional adaptive dt
4. **Clamping**: Model-specific concentration bounds prevent numerical overflow
5. **Visualization**: Render concentration fields as colormapped images

### 9-Point Isotropic Laplacian

The stencil provides better rotational symmetry than the standard 5-point stencil:
```
[1/6, 4/6, 1/6]
[4/6, -20/6, 4/6]
[1/6, 4/6, 1/6]
```

### Stability

- **Field clamping**: Each model has appropriate concentration bounds (e.g., Gray-Scott stays in [0,1], Gierer-Meinhardt clamps to [0, ∞))
- **Adaptive stepping**: Optional CFL-like adaptive dt based on maximum reaction rate
- **Division-by-zero protection**: Gierer-Meinhardt clamps v to minimum 1e-10

## Project Structure

```
reaction-diffusion-sim/
├── rd_sim.py          # Main entry point with CLI
├── models.py          # Reaction kinetics implementations
├── solver.py          # PDE solver engine (Laplacian, stepping, checkpoints)
├── presets.py         # Parameter presets for all models
├── visualization.py  # Rendering, GIF, animation, colormaps
├── tests.py           # Comprehensive test suite (52+ tests)
└── README.md
```

## Testing

```bash
python3 tests.py
```

## Known Issues (Resolved)

- **Gierer-Meinhardt overflow**: Fixed by clamping u to [0, ∞) and v to [1e-10, ∞) in reaction kinetics
- **Brusselator overflow**: Fixed by clamping fields to [-10, 10] in reaction kinetics
- **Grid/step override**: CLI `--grid` and `--steps` now correctly override preset values
- **multi_spot perturbation**: Fixed v-indexing bug (was using `ry + s` instead of `ry - s` for column slice)

## License

MIT