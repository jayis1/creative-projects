# Lattice Boltzmann Fluid Dynamics Simulator

A high-performance 2D fluid dynamics simulator implementing the **Lattice Boltzmann Method (LBM)** with the D2Q9 lattice model and BGK collision operator. Simulates incompressible viscous flows around obstacles, through porous media, and in enclosures — producing vivid visualizations of vorticity, velocity, and pressure fields.

```
    ┌──────────────────────────────────────────────────────────────┐
    │  LBM D2Q9 Lattice Velocity Directions                       │
    │                                                              │
    │       6   2   5         Weights:                            │
    │        \  |  /           w₀ = 4/9  (rest)                    │
    │    3 ──  0  ── 1        w₁₋₄ = 1/9  (cardinal)             │
    │        /  |  \           w₅₋₈ = 1/36 (diagonal)             │
    │       7   4   8                                             │
    │                           cs² = 1/3  (speed of sound²)      │
    │   BGK Collision:          τ = ν/cs² + 0.5                   │
    │   f_out = f - ω(f - f_eq)  where ω = 1/τ                  │
    │                                                              │
    │   Equilibrium:                                              │
    │   f_eq_i = w_i·ρ·[1 + (e_i·u)/cs² + (e_i·u)²/(2cs⁴) - u²/(2cs²)]  │
    └──────────────────────────────────────────────────────────────┘
```

## Features

- **D2Q9 Lattice Model** — 9-velocity lattice for 2D incompressible flow
- **BGK Collision Operator** — single relaxation time with configurable viscosity
- **Boundary Conditions** — Zou-He velocity inlet, open/pressure outlet, bounce-back walls
- **Obstacle Types** — Circles, rectangles, NACA 4-digit airfoils, cylinder arrays
- **Real-Time Visualization** — Vorticity, speed, pressure, and density fields with multiple colormaps
- **GIF Animation** — Export time-evolution as animated GIFs
- **4 Classic Scenarios**:
  - 🌀 Von Kármán vortex street behind a cylinder
  - ✈️ Flow over a NACA 0012 airfoil at angle of attack
  - 🧽 Flow through a porous medium (staggered cylinder array)
  - 📦 Lid-driven cavity flow

## Physics Background

The Lattice Boltzmann Method solves the incompressible Navier-Stokes equations on a discrete lattice. Instead of directly solving for pressure and velocity, LBM tracks the evolution of particle distribution functions `f_i(x,t)` that stream along lattice velocity directions and relax toward Maxwell-Boltzmann equilibria via collision.

**Key relationships:**
- Kinematic viscosity: `ν = cs²(τ - 0.5)` where `τ` is the relaxation time
- Reynolds number: `Re = U·L/ν` — controls flow regime (laminar, transitional, turbulent)
- Mach number: `Ma = U/cs` — must be << 1 for incompressible assumption

**The algorithm per time step:**
1. **Collision**: `f ← f - ω(f - f_eq)` — relax toward equilibrium
2. **Streaming**: `f_i(x + e_i, t+1) = f_i(x, t)` — propagate along lattice links
3. **Bounce-back**: At solid boundaries, reflect distributions to their opposite direction
4. **Macroscopic update**: `ρ = Σf_i`, `u = Σf_i·e_i / ρ`

## Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/lattice-boltzmann-fluid-q4m2.git
cd lattice-boltzmann-fluid-q4m2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install numpy Pillow
```

## Usage

### Command Line

```bash
# Run Von Kármán vortex street (default)
python3 main.py vortex

# Run flow over airfoil at 15° angle of attack
python3 main.py airfoil

# Run flow through porous medium
python3 main.py porous

# Run lid-driven cavity
python3 main.py cavity

# Run all scenarios
python3 main.py all

# Custom options
python3 main.py vortex --steps 10000 --viscosity 0.01 --scale 3 --output ./results
python3 main.py cavity --steps 5000 --no-gif
```

**Options:**
| Flag | Default | Description |
|------|---------|-------------|
| `--steps N` | Varies | Number of simulation time steps |
| `--viscosity V` | 0.02 | Kinematic viscosity in lattice units |
| `--scale S` | 2 | Image upscale factor |
| `--output DIR` | `./output` | Output directory |
| `--fps FPS` | 30 | GIF frame rate |
| `--no-gif` | — | Skip GIF creation, save only final images |

### Python API

```python
from lbm import (
    LBMSimulation, CircleObstacle, FluidVisualizer,
    ZouHeVelocityBoundary, OpenBoundary, FullWayBounceBackBoundary
)

# Create simulation
sim = LBMSimulation(nx=300, ny=80, viscosity=0.02)

# Add a circular obstacle
sim.add_obstacle(CircleObstacle(cx=50, cy=40, radius=10))

# Set boundary conditions
sim.add_boundary_condition(FullWayBounceBackBoundary(top=True, bottom=True))
sim.add_boundary_condition(ZouHeVelocityBoundary(0.08, side='left'))
sim.add_boundary_condition(OpenBoundary(side='right'))

# Initialize with uniform flow
sim.set_inlet_velocity(0.08)

# Run simulation
sim.step(5000)

# Visualize
vis = FluidVisualizer(sim)
vis.save_frame('vorticity.png', 'vorticity', cmap='coolwarm', scale=2)
```

### Available Obstacles

```python
from lbm import CircleObstacle, RectangleObstacle, AirfoilObstacle
from lbm import MultiObstacle, CylinderArrayObstacle

# Circular cylinder
circle = CircleObstacle(cx=50, cy=40, radius=10)

# Rectangular block
rect = RectangleObstacle(x0=40, y0=30, width=20, height=10)

# NACA 0012 airfoil at 10° angle of attack
airfoil = AirfoilObstacle(cx=50, cy=40, chord=60, thickness=0.12, angle_deg=10)

# Combine multiple obstacles
multi = MultiObstacle([circle, rect])

# Staggered cylinder array (porous medium)
porous = CylinderArrayObstacle(spacing=30, radius=5, stagger=True)

# Add any obstacle to simulation
sim.add_obstacle(circle)
```

### Available Boundary Conditions

| Class | Description |
|-------|-------------|
| `FullWayBounceBackBoundary` | No-slip walls at domain edges |
| `BounceBackBoundary(mask)` | No-slip on arbitrary obstacle mask |
| `ZouHeVelocityBoundary(u, side)` | Prescribed velocity inlet |
| `ZouHePressureBoundary(rho, side)` | Prescribed density outlet |
| `OpenBoundary(side)` | Zero-gradient extrapolation outlet |
| `PeriodicBoundary` | Periodic BC (implicit in streaming) |

### Visualization

```python
from lbm import FluidVisualizer

vis = FluidVisualizer(sim)

# Render individual fields
img = vis.render_vorticity(cmap='coolwarm', vmin=-0.05, vmax=0.05, scale=2)
img = vis.render_speed(cmap='jet', scale=2)
img = vis.render_pressure(cmap='ocean', scale=2)
img = vis.render_density(cmap='plasma', scale=2)

# Save to file
vis.save_frame('output.png', 'vorticity', cmap='coolwarm', scale=2)

# Create animated GIF
frames = []
for step in range(0, 5000, 50):
    sim.step(50)
    frames.append(vis.render_vorticity(scale=2))

FluidVisualizer.create_gif(frames, 'animation.gif', duration=33)
```

**Colormaps:** `jet`, `viridis`, `coolwarm`, `hot`, `ocean`, `plasma`

## Project Structure

```
lattice-boltzmann-fluid-q4m2/
├── main.py                  # CLI demo with 4 scenarios
├── lbm/
│   ├── __init__.py          # Package exports
│   ├── lattice.py           # D2Q9 lattice constants & operations
│   ├── simulation.py        # LBM simulation engine (collision, streaming, BCs)
│   ├── boundaries.py        # Boundary condition implementations
│   ├── obstacles.py         # Obstacle geometry definitions
│   └── visualization.py     # Rendering & colormap engine
├── tests/
│   └── test_lbm.py          # Comprehensive unit test suite
└── README.md
```

## Simulation Scenarios

### 1. Von Kármán Vortex Street (`vortex`)

Flow past a circular cylinder at Re ≈ 100. Above Re ≈ 47, the symmetric wake becomes unstable and alternately sheds vortices — the mesmerizing Von Kármán vortex street.

```
Flow →  ═══╤═══════╤══════════════════
            │  ○   │    ∿∿∿∿∿∿∿∿∿
         ═══╧═══════╧══════════════════  → outlet
```

### 2. NACA 0012 Airfoil (`airfoil`)

Flow over a NACA 0012 symmetric airfoil at 15° angle of attack. Demonstrates flow separation, boundary layer behavior, and wake formation.

```
Flow →  ═════════════╤═══════════════════
                  ╱‾‾‾‾╲     ∿∿∿∿∿∿
                 ╱ NACA ╲___╱
         ═════════════╧═══════════════════  → outlet
```

### 3. Porous Medium (`porous`)

Flow through a staggered array of circular cylinders, modeling porous media. Shows tortuous flow paths and pressure drops across the medium.

```
Flow →  ══○──○──○──○═══════════════════
              ○──○──○                    
         ═══○──○──○──○══════════════════  → outlet
```

### 4. Lid-Driven Cavity (`cavity`)

The classic CFD benchmark: a square cavity with a moving lid. Develops a primary recirculation vortex and corner eddies. Used for validating numerical methods.

```
         ────────→ moving lid (u = u_lid)
         ┌────────────────┐
         │    ╭───→╮      │
         │    │     │      │
         │    ╰←───╯      │
         └────────────────┘
         (no-slip walls on 3 sides)
```

## Test Suite

```bash
cd lattice-boltzmann-fluid-q4m2
source venv/bin/activate
PYTHONPATH=. python3 tests/test_lbm.py
```

12 tests covering:
- Lattice constant validation
- Equilibrium mass & momentum conservation
- Streaming periodicity
- BGK collision relaxation
- Obstacle mask generation
- Simulation initialization & stepping
- Boundary conditions
- Visualization rendering
- Reynolds number calculation

## Key Parameters

| Parameter | Typical Range | Description |
|-----------|--------------|-------------|
| `viscosity` | 0.005–0.1 | Kinematic viscosity (lower → higher Re) |
| `u₀` | 0.02–0.1 | Inlet velocity (keep Ma << 1) |
| `τ` | 0.51–2.0 | Relaxation time (τ < 0.5 is unstable) |
| `Re` | 1–1000+ | Reynolds number (flow regime indicator) |

**Stability rules of thumb:**
- `τ > 0.5` (always; τ = 0.5 is zero viscosity and unstable)
- `Ma < 0.3` (preferably < 0.1) for incompressible assumption
- `ρ` should stay within ~5% of 1.0

## License

MIT License — free for research, education, and hobby use.