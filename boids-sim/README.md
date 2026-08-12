# Boids Flocking Simulation v2.0

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
- **Predator Evasion** — boids flee from predators within a panic radius (force amplifies as threat nears)
- **Goal Seeking** — boids steer toward a target position
- **Wander** — Reynolds-style constrained random walk (circle-ahead projection with angular drift)
- **Boundary Forces** — soft steering to keep boids within the simulation area, or toroidal wrapping

### Performance

Uses a **uniform-grid spatial hash** for O(n) neighbor queries instead of the naive O(n²) all-pairs check.
Each tick, boids are inserted into a grid; neighbor queries scan only nearby cells. The v2.0 engine
queries the grid once per boid (using the largest perception radius) and reuses results for all behaviors.

## Usage

### Python API

```python
from boids.simulation import BoidSimulation
from boids.config import SimulationConfig, get_preset
from boids.renderer import SVGRenderer, TrailSVGRenderer, ASCIIRenderer

# Use a preset
cfg = get_preset("fast-murmuration")
sim = BoidSimulation(cfg)

# Or custom config
cfg = SimulationConfig(num_boids=200, width=800, height=600, trail_length=15)
sim = BoidSimulation(cfg)

# Add obstacles and predators
sim.add_obstacle(400, 300, 50)
sim.add_predator(100, 100)

# Run the simulation
for _ in range(100):
    sim.step()

# Render
TrailSVGRenderer().render(sim, "frame.svg")  # with trails
SVGRenderer().render(sim, "frame.svg")       # without trails
print(ASCIIRenderer().render(sim))
print(sim.stats())

# Save/load full state
sim.save("state.json")
sim2 = BoidSimulation.load("state.json")
```

### CLI

```bash
# Run 200 steps and export SVG + PPM frames every 10 steps
python -m boids run -s 200 --svg --ppm -o output/

# Live ASCII animation
python -m boids ascii -s 100 --cols 100 --rows 30

# Use a preset
python -m boids run -s 200 --preset fast-murmuration --svg --trail

# Load config from file
python -m boids run -s 100 --config-file config.yaml --svg

# Run with obstacles and a predator
python -m boids run -s 100 --svg --obstacles 400 300 40 --predators 100 100

# Save final state
python -m boids save state.json -s 100 --predators 200 200

# Print statistics only
python -m boids stats -s 500 -n 300

# Parameter sweep
python -m boids sweep --param w_sep --values 0.5,1.0,1.5,2.0,3.0 -s 100 -n 150
python -m boids sweep --param max_speed --values 2:6:0.5 -s 100 -n 100 -o results.json

# List presets
python -m boids presets

# Save a config template
python -m boids config config.json -n 200 --sep 2.0 --trail 20
```

### Demo Script

```bash
python3 demo.py
```

Runs 50 steps with an obstacle and predator, saves `demo_frame.svg` and `demo_frame.ppm`.

## Presets

| Preset | Description |
|---|---|
| `default` | Balanced flocking behavior |
| `tight-flock` | Dense, cohesive flock with strong separation |
| `loose-swarm` | Large perception, strong cohesion, gentle alignment |
| `fast-murmuration` | Starling-like: 300 boids, fast, toroidal world |
| `schooling-fish` | Fish school: tight coordination, moderate speed |
| `chaos` | High separation, minimal alignment/cohesion, strong wander |
| `calm-glide` | Slow, relaxed flocking with low force |
| `predator-hunt` | Tuned for predator scenarios with high flee weight |

## Configuration

All parameters can be tuned via `SimulationConfig`, config files, or CLI flags:

| Parameter | Default | Description |
|---|---|---|
| `num_boids` | 150 | Number of boids |
| `width` | 800 | World width |
| `height` | 600 | World height |
| `max_speed` | 4.0 | Maximum boid speed |
| `max_force` | 0.2 | Maximum steering force |
| `radius` | 3.0 | Boid radius |
| `w_sep` | 1.5 | Separation weight |
| `w_ali` | 1.0 | Alignment weight |
| `w_coh` | 1.0 | Cohesion weight |
| `w_boundary` | 1.0 | Boundary force weight |
| `w_avoid` | 2.0 | Obstacle avoidance weight |
| `w_flee` | 3.0 | Predator evasion weight |
| `w_seek` | 0.5 | Goal seeking weight |
| `w_wander` | 0.1 | Wander weight |
| `use_wrap` | False | Toroidal world wrapping |
| `trail_length` | 0 | Trail history length (0 = disabled) |
| `predator_max_speed` | 6.0 | Predator max speed |
| `predator_chase_radius` | 200.0 | Predator chase detection radius |
| `predator_panic_dist` | 80.0 | Boid flee distance from predators |
| `background_color` | #1a1a2e | SVG/PPM background |
| `boid_color` | #e0e0e0 | Boid color |
| `predator_color` | #ff4444 | Predator color |
| `obstacle_color` | #888888 | Obstacle color |
| `goal_color` | #ffd700 | Goal marker color |

Config files support JSON, YAML, and TOML formats.

## Renderers

- **ASCII**: Terminal-friendly 8-directional arrow visualization
- **SVG**: Scalable vector graphics with triangle boids and configurable colors
- **TrailSVG**: SVG with fading trail paths for visualizing movement history
- **PPM**: Binary P6 raster images (no external dependencies)

## Architecture

```
boids/
├── __init__.py        # Package exports
├── __main__.py        # Entry point (python -m boids)
├── vector.py          # 2D vector math (in-place + functional ops)
├── boid.py            # Boid entity with steering behaviors + BoidState
├── spatial_hash.py    # Uniform-grid spatial hash for neighbor queries
├── config.py          # Config dataclass, presets, JSON/YAML/TOML I/O
├── simulation.py      # Simulation engine (step, stats, save/load)
├── renderer.py        # ASCII / SVG / TrailSVG / PPM renderers
└── cli.py             # Command-line interface (argparse, 7 subcommands)
```

## CLI Subcommands

| Command | Description |
|---|---|
| `run` | Run simulation and render frames (SVG/PPM/ASCII/JSON) |
| `stats` | Run N steps and print JSON statistics |
| `ascii` | Live terminal ASCII animation |
| `save` | Run and save final state to JSON |
| `sweep` | Parameter sweep with range or list values |
| `presets` | List available named presets |
| `config` | Save a config template file |

## Known Issues (Resolved)

All bugs identified during Phase 3 bug hunt have been fixed. Each fix includes a test proving the fix works.

| # | Bug | Impact | Fix |
|---|-----|--------|-----|
| 1 | **SVG typo `sroke=` instead of `stroke=`** | Obstacle circles in SVG output had an invalid attribute name, causing SVG renderers to ignore it | Removed the redundant `sroke` attribute entirely (fill is sufficient for solid circles) |
| 2 | **ASCII arrows inverted on Y-axis** | Boids moving down (vy>0) showed ↑ instead of ↓; moving up showed ↓ instead of ↑. Screen Y increases downward, opposite to math Y | Negated the y-component before computing the arrow angle (`atan2(-vy, vx)`) and switched from `int()` to `round()` for proper rounding of negative angles |
| 3 | **Duplicate `max_force` key in `calm-glide` preset** | Dict literal had `max_force` twice; second value silently overwrote the first. Both were 0.1 so no runtime impact, but dead code that could mask future bugs | Removed the duplicate key |
| 4 | **Unused `all_neighbors_cache` dict in `step()`** | Allocated a dict and populated it every tick but never read it, wasting memory and CPU for no benefit | Removed the unused cache variable entirely |
| 5 | **`boundary_force()` ZeroDivisionError when `margin=0`** | If `boundary_margin` was set to 0 and a boid was outside the boundary (e.g. negative position), division by zero crashed the simulation | Added early return of zero vector when `margin <= 0` |
| 6 | **PPM renderer accepted `scale=0` and negative scale** | `scale=0` produced a 0×0 pixel PPM file (invalid); negative scale produced a PPM with negative dimensions in the header (also invalid) | Added input validation: `scale <= 0` now raises `ValueError` |

## License

MIT