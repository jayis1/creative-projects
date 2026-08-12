# Boids Flocking Simulation

A from-scratch implementation of Craig Reynolds' classic **boids** flocking algorithm (1987),
simulating emergent flocking behavior through simple local steering rules.

## How It Works

Each boid (agent) follows three fundamental steering behaviors based on its **local neighbors**:

| Behavior | Description |
|---|---|
| **Separation** | Steer away from nearby boids to avoid crowding |
| **Alignment** | Steer toward the average heading of neighbors |
| **Cohesion** | Steer toward the average position of neighbors |

These three rules produce emergent flocking behavior — no global controller, just local interactions.

### Additional Behaviors

- **Obstacle Avoidance** — boids steer away from circular obstacles with urgency proportional to proximity
- **Predator Evasion** — boids flee from predators within a panic radius
- **Goal Seeking** — boids steer toward a target position
- **Boundary Forces** — soft steering to keep boids within the simulation area, or toroidal wrapping

### Performance

Uses a **uniform-grid spatial hash** for O(n) neighbor queries instead of the naive O(n²) all-pairs check.
Each tick, boids are inserted into a grid; neighbor queries scan only nearby cells.

## Usage

### Python API

```python
from boids.simulation import BoidSimulation, SimulationConfig
from boids.renderer import SVGRenderer, ASCIIRenderer

cfg = SimulationConfig(num_boids=200, width=800, height=600)
sim = BoidSimulation(cfg)

# Add obstacles and predators
sim.add_obstacle(400, 300, 50)
sim.add_predator(100, 100)

# Run the simulation
for _ in range(100):
    sim.step()

# Render
SVGRenderer().render(sim, "frame.svg")
print(ASCIIRenderer().render(sim))
print(sim.stats())
```

### CLI

```bash
# Run 200 steps and export SVG + PPM frames every 10 steps
python -m boids run -s 200 --svg --ppm -o output/

# Live ASCII animation
python -m boids ascii -s 100 --cols 100 --rows 30

# Run with obstacles and a predator
python -m boids run -s 100 --svg --obstacles 400 300 40 --predators 100 100

# Print statistics only
python -m boids stats -s 500 -n 300

# Custom behavior weights
python -m boids run -s 100 --sep 2.0 --ali 0.5 --coh 0.5 --svg
```

### Demo Script

```bash
python3 demo.py
```

Runs 50 steps with an obstacle and predator, saves `demo_frame.svg` and `demo_frame.ppm`.

## Architecture

```
boids/
├── __init__.py        # Package exports
├── __main__.py        # Entry point (python -m boids)
├── vector.py          # 2D vector math (in-place + functional ops)
├── boid.py            # Boid entity with steering behaviors
├── spatial_hash.py    # Uniform-grid spatial hash for neighbor queries
├── simulation.py      # Simulation engine (config, step, stats)
├── renderer.py        # ASCII / SVG / PPM renderers
└── cli.py             # Command-line interface (argparse)
```

## Configuration

All parameters can be tuned via `SimulationConfig`:

| Parameter | Default | Description |
|---|---|---|
| `num_boids` | 150 | Number of boids |
| `width` | 800 | World width |
| `height` | 600 | World height |
| `max_speed` | 4.0 | Maximum boid speed |
| `max_force` | 0.2 | Maximum steering force |
| `w_sep` | 1.5 | Separation weight |
| `w_ali` | 1.0 | Alignment weight |
| `w_coh` | 1.0 | Cohesion weight |
| `w_boundary` | 1.0 | Boundary force weight |
| `w_avoid` | 2.0 | Obstacle avoidance weight |
| `w_flee` | 3.0 | Predator evasion weight |
| `w_seek` | 0.5 | Goal seeking weight |
| `use_wrap` | False | Toroidal world wrapping |

## Renderers

- **ASCII**: Terminal-friendly arrow visualization (8-directional)
- **SVG**: Scalable vector graphics with triangle boids
- **PPM**: Binary P6 raster images (no external dependencies)

## License

MIT