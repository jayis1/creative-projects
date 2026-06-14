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
- **Efficient Solver**: Vectorized NumPy computation with Laplacian via scipy convolution
- **Boundary Conditions**: Periodic, Dirichlet (fixed), Neumann (zero-flux)
- **Seeded Perturbations**: Point, ring, cross, random, and custom perturbations
- **Parameter Presets**: 20+ built-in parameter presets for stunning patterns
- **Visualization**: Real-time animation with matplotlib or headless PNG output
- **CLI Interface**: Full control from the command line
- **Checkpoint/Resume**: Save and load simulation state as compressed NumPy archives

## Quick Start

```bash
# Install dependencies
pip install numpy scipy matplotlib

# Run with a preset (coral growth pattern)
python3 rd_sim.py --preset coral

# Gray-Scott mitosis (splitting spots)
python3 rd_sim.py --preset mitosis

# FitzHugh-Nagumo traveling waves
python3 rd_sim.py --model fhn --preset pulse

# Custom parameters
python3 rd_sim.py --model gray-scott --feed 0.035 --kill 0.065 --grid 256 --steps 5000

# Save frames as PNGs
python3 rd_sim.py --preset labyrinth --frames-dir ./frames --steps 3000 --every 100

# Resume from checkpoint
python3 rd_sim.py --resume checkpoint.npz --steps 2000
```

## Models & Presets

| Model | Preset | Feed | Kill | Pattern |
|-------|--------|------|------|---------|
| Gray-Scott | spots | 0.035 | 0.065 | Solitary spots |
| Gray-Scott | mitosis | 0.028 | 0.062 | Dividing spots |
| Gray-Scott | coral | 0.0545 | 0.062 | Branching coral |
| Gray-Scott | labyrinth | 0.029 | 0.057 | Fingerprint maze |
| Gray-Scott | waves | 0.014 | 0.045 | Pulsating waves |
| FitzHugh-Nagumo | pulse | 0.034 | — | Traveling pulse |
| Gierer-Meinhardt | spots_gm | — | — | Self-amplifying spots |
| Brusselator | brusselator | — | — | Oscillating spots |

## How It Works

1. **Initialization**: Set up a uniform concentration field with localized perturbations
2. **Laplacian**: Compute spatial derivatives using a 9-point stencil convolution (more isotropic than 5-point)
3. **Time Stepping**: Euler method with configurable dt (adaptive option available)
4. **Visualization**: Render concentration fields as colormapped images

The 9-point Laplacian stencil for isotropy:
```
[1/6, 4/6, 1/6]
[4/6, -20/6, 4/6]
[1/6, 4/6, 1/6]
```

## Project Structure

```
reaction-diffusion-sim/
├── rd_sim.py          # Main entry point with CLI
├── models.py          # Reaction kinetics implementations
├── solver.py          # PDE solver engine
├── presets.py         # Parameter presets
├── visualization.py   # Rendering and animation
├── tests.py           # Test suite
└── README.md
```

## License

MIT