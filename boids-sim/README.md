# Boids Flocking Simulation v3.0

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Tests: 250](https://img.shields.io/badge/tests-250-brightgreen.svg)
![Version: 3.0](https://img.shields.io/badge/version-3.0-orange.svg)

A from-scratch implementation of Craig Reynolds' classic **boids** flocking algorithm
(1987), simulating emergent flocking behavior through simple local steering rules. Pure
Python, zero external dependencies.

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Python API](#python-api)
- [Behaviors](#behaviors)
- [Spatial Indexes](#spatial-indexes)
- [Multi-Species Flocking](#multi-species-flocking)
- [Path Following](#path-following)
- [Event System](#event-system)
- [Stats Tracking](#stats-tracking)
- [Renderers](#renderers)
- [Presets](#presets)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Recent Improvements](#recent-improvements)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Each boid (bird-oid agent) follows three fundamental steering behaviors based on its
**local neighbors**:

| Behavior | Description |
|---|---|
| **Separation** | Steer away from nearby boids to avoid crowding |
| **Alignment** | Steer toward the average heading of neighbors |
| **Cohesion** | Steer toward the average position of neighbors |

These three rules produce emergent flocking behavior — no global controller, just local
interactions. The simulation also supports obstacle avoidance, predator evasion, goal
seeking, arrival, wander, path following, boundary forces, and toroidal wrapping.

### Key Features

- **Pluggable spatial indexes**: uniform-grid spatial hash or region quadtree
- **Multi-species flocking**: boids of different species only flock with their own kind
- **Path following**: boids follow waypoint paths with arrival radius and looping
- **Event/callback system**: hook into simulation lifecycle events
- **Stats time-series tracking**: record and analyze statistics over time
- **6 renderers**: ASCII, SVG, TrailSVG, PPM, AnimatedSVG, JSON
- **Config system**: JSON, YAML, TOML config files + 11 named presets
- **Save/load**: full simulation state serialization
- **250 tests** with pytest
- **Installable** via pip (pyproject.toml)

---

## Installation

```bash
# From the repo
cd creative-projects/boids-sim
pip install -e ".[dev]"

# Or just run without installing (add to PYTHONPATH)
export PYTHONPATH=.
python3 -m boids presets
```

---

## Quick Start

```python
from boids.simulation import BoidSimulation
from boids.config import SimulationConfig
from boids.renderer import SVGRenderer

# Create simulation with 200 boids
sim = BoidSimulation(SimulationConfig(num_boids=200, use_wrap=True))

# Add a predator
sim.add_predator(100, 100)

# Run 100 steps
for _ in range(100):
    sim.step()

# Render to SVG
SVGRenderer().render(sim, "flock.svg")

# Print stats
print(sim.stats())
```

---

## CLI Usage

The CLI provides 10 subcommands:

```bash
# Run 200 steps and export SVG frames every 10 steps
python -m boids run -s 200 --svg -o output/

# Live ASCII animation
python -m boids ascii -s 100 --cols 100 --rows 30

# Use a preset
python -m boids run -s 200 --preset fast-murmuration --svg --trail-svg

# Load config from file
python -m boids run -s 100 --config-file config.yaml --svg

# Run with obstacles, predators, and goal
python -m boids run -s 100 --svg \
    --obstacles 400 300 40 \
    --predators 100 100 \
    --goal 600 400

# Path following
python -m boids run -s 100 --svg --preset path-followers \
    --path 200 200 600 200 600 400 200 400 --path-loop

# Multi-species flocking
python -m boids run -s 200 --svg --preset multi-species

# Use quadtree spatial index
python -m boids run -s 100 --spatial-index quadtree -n 300 --svg

# Generate animated SVG (plays in browser!)
python -m boids animate -s 100 --fps 15 -o flock.svg

# Track time-series statistics
python -m boids track -s 500 -n 200 -o stats.json

# Benchmark spatial indexes
python -m boids benchmark -s 50 -n 300

# Print statistics as JSON
python -m boids stats -s 500 -n 300

# Parameter sweep
python -m boids sweep --param w_sep --values 0.5,1.0,1.5,2.0,3.0 -s 100 -n 150

# List presets
python -m boids presets

# Save a config template
python -m boids config config.json -n 200 --sep 2.0 --trail 20
```

### CLI Subcommands

| Command | Description |
|---|---|
| `run` | Run simulation and render frames (SVG/PPM/ASCII/JSON) |
| `stats` | Run N steps and print JSON statistics |
| `ascii` | Live terminal ASCII animation |
| `save` | Run and save final state to JSON |
| `sweep` | Parameter sweep with range or list values |
| `presets` | List available named presets |
| `config` | Save a config template file |
| `animate` | Generate animated SVG from simulation |
| `track` | Run simulation and output time-series statistics |
| `benchmark` | Benchmark spatial index performance (grid vs quadtree) |

---

## Python API

### Basic Usage

```python
from boids.simulation import BoidSimulation
from boids.config import SimulationConfig, get_preset

# Use a preset
cfg = get_preset("fast-murmuration")
sim = BoidSimulation(cfg)

# Or custom config
cfg = SimulationConfig(
    num_boids=200, width=800, height=600,
    trail_length=15, use_wrap=True,
    spatial_index="quadtree",
)
sim = BoidSimulation(cfg)

# Add obstacles and predators
sim.add_obstacle(400, 300, 50)
sim.add_predator(100, 100)

# Run the simulation
for _ in range(100):
    sim.step()

# Print stats
print(sim.stats())
```

### Multi-Species

```python
cfg = SimulationConfig(num_boids=150, num_species=3, use_wrap=True)
sim = BoidSimulation(cfg)
# Boids are assigned species 0, 1, 2 — they only flock with same species
sim.step()
```

### Path Following

```python
import math
cfg = SimulationConfig(num_boids=60, w_path=2.0, path_loop=True)
sim = BoidSimulation(cfg)

# Circular path with 8 waypoints
waypoints = [(400 + 200 * math.cos(i * math.tau / 8), 300 + 200 * math.sin(i * math.tau / 8))
             for i in range(8)]
sim.set_all_paths(waypoints, loop=True)

for _ in range(200):
    sim.step()
```

### Event System

```python
sim = BoidSimulation(SimulationConfig(num_boids=100))
sim.add_predator(100, 100)

# Track predator catches
def on_collision(predator, boid):
    print(f"  Boid {boid.id} caught by predator {predator.id}!")

sim.events.on("collision", on_collision)

# Track step events
sim.events.on("step_end", lambda tick: print(f"Tick {tick} complete"))

for _ in range(50):
    sim.step()
```

### Stats Tracking

```python
sim = BoidSimulation(SimulationConfig(num_boids=200, use_wrap=True))
for _ in range(500):
    sim.step()

tracker = sim.tracker
print(tracker.summary())
print(f"Alignment trend: {tracker.trend('alignment', window=50)}")
print(f"Converged at tick: {tracker.convergence_tick('alignment', 0.5, 20)}")
```

### Save/Load

```python
sim = BoidSimulation(SimulationConfig(num_boids=200))
for _ in range(100):
    sim.step()
sim.save("state.json")

sim2 = BoidSimulation.load("state.json")
print(f"Loaded {len(sim2.boids)} boids at tick {sim2.tick}")
```

---

## Behaviors

| Behavior | Method | Weight | Description |
|---|---|---|---|
| Separation | `boid.separation()` | `w_sep` | Steer away from crowding neighbors |
| Alignment | `boid.alignment()` | `w_ali` | Match average heading of neighbors |
| Cohesion | `boid.cohesion()` | `w_coh` | Steer toward average position of neighbors |
| Seek | `boid.seek()` | `w_seek` | Steer toward a target position |
| Arrive | `boid.arrive()` | `w_arrive` | Like seek but decelerates near target |
| Flee | `boid.flee()` | `w_flee` | Steer away from a threat (urgency scales) |
| Wander | `boid.wander()` | `w_wander` | Reynolds-style constrained random walk |
| Path Follow | `boid.follow_path()` | `w_path` | Follow waypoint sequence |
| Obstacle Avoid | `boid.avoid_obstacle()` | `w_avoid` | Steer away from circular obstacles |
| Boundary | `boid.boundary_force()` | `w_boundary` | Soft steering to stay inside area |

---

## Spatial Indexes

The simulation uses a spatial index for O(n) neighbor queries. Two implementations are
provided:

### Uniform Grid (Spatial Hash)

Default. Partitions space into uniform cells. Each tick, boids are inserted into cells;
neighbor queries scan only nearby cells. Excellent for uniform distributions.

```python
cfg = SimulationConfig(spatial_index="grid", cell_size=60.0)
```

### QuadTree

Region quadtree that recursively subdivides space. Better for non-uniform distributions
where objects cluster in certain regions. Also adapts dynamically as the distribution
changes.

```python
cfg = SimulationConfig(spatial_index="quadtree")
```

### Benchmark

```bash
$ python -m boids benchmark -s 50 -n 300

  grid         300 boids: 12.76 ms/step  (78 steps/s)
  quadtree     300 boids: 10.81 ms/step  (93 steps/s)
```

The quadtree is faster for larger populations with clustering, while the grid is faster
for small populations or uniform distributions.

---

## Multi-Species Flocking

Boids can be assigned to different species. When `num_species > 1`, each boid is assigned
a species ID, and the three core behaviors (separation, alignment, cohesion) only consider
same-species neighbors. This produces multiple independent flocks that ignore each other.

```python
cfg = SimulationConfig(num_boids=150, num_species=3, use_wrap=True)
sim = BoidSimulation(cfg)
# 50 boids per species, forming 3 separate flocks
```

---

## Path Following

Boids can follow a predefined path of waypoints. The path-following behavior seeks
toward the current waypoint and advances to the next when within `arrival_radius`. Paths
can loop or end at the final waypoint (with arrival deceleration).

```python
sim = BoidSimulation(SimulationConfig(num_boids=60, w_path=2.0))
waypoints = [(100, 100), (400, 100), (400, 400), (100, 400)]
sim.set_all_paths(waypoints, loop=True)
# All boids will follow the square path
```

Individual boids can also be assigned paths:

```python
sim.set_boid_path(0, [(100, 100), (200, 200)])  # only boid 0
```

---

## Event System

The simulation provides an event bus for hooking into lifecycle events without
modifying the core code:

| Event | Args | Description |
|---|---|---|
| `step_start` | `tick` | Fired at the beginning of each step |
| `step_end` | `tick` | Fired at the end of each step |
| `boid_added` | `boid` | Fired when a boid is added |
| `boid_removed` | `boid` | Fired when a boid is removed |
| `predator_added` | `predator` | Fired when a predator is added |
| `obstacle_added` | `obstacle` | Fired when an obstacle is added |
| `collision` | `predator, boid` | Fired when a predator catches a boid |

```python
sim.events.on("collision", lambda pred, boid: print(f"Caught boid {boid.id}!"))
```

Exceptions in listeners are caught and reported, so one bad listener can't crash the
simulation.

---

## Stats Tracking

The simulation automatically records statistics at each step via a `StatsTracker`:

```python
tracker = sim.tracker

# Basic queries
tracker.history()                    # list of stats dicts
tracker.column("alignment")         # single key across all snapshots
tracker.average("alignment")        # mean of a key
tracker.min_val("alignment")        # minimum
tracker.max_val("alignment")        # maximum

# Trend analysis
tracker.trend("alignment", window=50)  # linear regression slope
tracker.convergence_tick("alignment", threshold=0.5, window=20)
# → tick where alignment first stays above 0.5 for 20 consecutive steps

# Summary
tracker.summary()  # {"alignment": {"mean": ..., "min": ..., "max": ...}, ...}
```

---

## Renderers

| Renderer | Class | Output | Description |
|---|---|---|---|
| ASCII | `ASCIIRenderer` | String | Terminal-friendly 8-directional arrows |
| SVG | `SVGRenderer` | SVG file | Scalable vector graphics with triangle boids |
| TrailSVG | `TrailSVGRenderer` | SVG file | SVG with fading trail paths |
| PPM | `PPMRenderer` | PPM file | Binary P6 raster images (no deps) |
| AnimatedSVG | `AnimatedSVGRenderer` | SVG file | Multi-frame SMIL animation (browser-playable) |
| JSON | `JSONRenderer` | JSON file | Full simulation state serialization |

```python
from boids.renderer import ASCIIRenderer, SVGRenderer, TrailSVGRenderer, PPMRenderer, AnimatedSVGRenderer

# ASCII
print(ASCIIRenderer(cols=80, rows=24).render(sim))

# SVG
SVGRenderer().render(sim, "frame.svg")

# Trail SVG
TrailSVGRenderer().render(sim, "trails.svg")

# PPM
PPMRenderer().render(sim, "frame.ppm", scale=2.0)

# Animated SVG (runs in browser!)
AnimatedSVGRenderer(fps=15, loop=True).render(sim, "flock.svg", steps=100)
```

---

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
| `multi-species` | 3 species, 200 boids, wrapping, trails |
| `path-followers` | 80 boids following a looped path, quadtree index |
| `quadtree-demo` | 300 boids using quadtree spatial index |

---

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
| `w_path` | 1.0 | Path following weight |
| `w_arrive` | 0.5 | Arrival weight |
| `use_wrap` | False | Toroidal world wrapping |
| `trail_length` | 0 | Trail history length (0 = disabled) |
| `num_species` | 1 | Number of species (1 = no species filtering) |
| `spatial_index` | "grid" | Index type: "grid" or "quadtree" |
| `path_arrival_radius` | 20.0 | Waypoint arrival radius |
| `path_loop` | False | Loop paths |
| `predator_max_speed` | 6.0 | Predator max speed |
| `predator_chase_radius` | 200.0 | Predator chase detection radius |
| `predator_panic_dist` | 80.0 | Boid flee distance from predators |
| `background_color` | #1a1a2e | SVG/PPM background |
| `boid_color` | #e0e0e0 | Boid color |
| `predator_color` | #ff4444 | Predator color |
| `obstacle_color` | #888888 | Obstacle color |
| `goal_color` | #ffd700 | Goal marker color |

Config files support JSON, YAML, and TOML formats.

---

## Architecture

```
boids-sim/
├── boids/
│   ├── __init__.py        # Package exports
│   ├── __main__.py        # Entry point (python -m boids)
│   ├── vector.py          # 2D vector math (in-place + functional ops)
│   ├── boid.py            # Boid entity with steering behaviors + BoidState
│   ├── spatial_index.py   # SpatialIndex protocol (abstract interface)
│   ├── spatial_hash.py    # Uniform-grid spatial hash for neighbor queries
│   ├── quadtree.py        # Region quadtree spatial index
│   ├── config.py          # Config dataclass, presets, JSON/YAML/TOML I/O
│   ├── simulation.py      # Simulation engine (step, stats, save/load, events)
│   ├── renderer.py        # ASCII / SVG / TrailSVG / PPM / AnimatedSVG / JSON
│   ├── events.py          # Event/callback system (observer pattern)
│   ├── stats_tracker.py   # Time-series stats recording and analysis
│   └── cli.py             # Command-line interface (10 subcommands)
├── tests/                 # 250 pytest tests
│   ├── test_vector.py
│   ├── test_boid.py
│   ├── test_spatial_index.py
│   ├── test_simulation.py
│   ├── test_config.py
│   ├── test_renderers.py
│   ├── test_events.py
│   ├── test_stats_tracker.py
│   └── test_bug_hunt.py
├── examples/              # Usage demos
│   ├── multi_species.py
│   ├── path_following.py
│   ├── predator_prey_events.py
│   ├── animated_svg.py
│   ├── stats_tracking.py
│   └── benchmark.py
├── pyproject.toml         # Installable package config
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### Core Data Flow

```
Config → BoidSimulation._populate() → Boids with random positions
                                             ↓
BoidSimulation.step():
  1. _rebuild_grid()     → Insert all boids into spatial index
  2. For each boid:
     a. _get_neighbors() → Query spatial index
     b. separation()     → Steer away from crowd
     c. alignment()       → Match heading
     d. cohesion()        → Steer to center
     e. follow_path()     → Waypoint navigation (if path set)
     f. wander()          → Random walk
     g. avoid_obstacle()  → Steer from obstacles
     h. flee()            → Evade predators
     i. seek()            → Go to goal
     j. boundary_force() → Stay in bounds (or wrap)
     k. Sum forces × weights → apply_force() → update()
  3. _update_predator()   → Predators chase/wander
  4. _detect_catches()    → Collision detection → emit "collision" event
  5. tracker.record()     → Record stats snapshot
  6. emit "step_end"
```

---

## Examples

Six example scripts are provided in `examples/`:

```bash
# Multi-species flocking (3 separate flocks)
PYTHONPATH=. python3 examples/multi_species.py

# Circular path following
PYTHONPATH=. python3 examples/path_following.py

# Predator-prey with event callbacks
PYTHONPATH=. python3 examples/predator_prey_events.py

# Animated SVG export (plays in browser)
PYTHONPATH=. python3 examples/animated_svg.py

# Stats time-series tracking and convergence analysis
PYTHONPATH=. python3 examples/stats_tracking.py

# Spatial index benchmark
PYTHONPATH=. python3 examples/benchmark.py
```

### Demo Script

```bash
python3 demo.py
```

Runs 50 steps with an obstacle and predator, saves `demo_frame.svg` and `demo_frame.ppm`.

---

## Known Issues (Resolved)

All bugs identified during the Phase 3 bug hunt have been fixed. Each fix includes a test proving the fix works.

| # | Bug | Impact | Fix |
|---|-----|--------|-----|
| 1 | **SVG typo `sroke=` instead of `stroke=`** | Obstacle circles in SVG output had an invalid attribute name, causing SVG renderers to ignore it | Removed the redundant `sroke` attribute entirely (fill is sufficient for solid circles) |
| 2 | **ASCII arrows inverted on Y-axis** | Boids moving down (vy>0) showed ↑ instead of ↓; moving up showed ↓ instead of ↑. Screen Y increases downward, opposite to math Y | Negated the y-component before computing the arrow angle (`atan2(-vy, vx)`) and switched from `int()` to `round()` for proper rounding of negative angles |
| 3 | **Duplicate `max_force` key in `calm-glide` preset** | Dict literal had `max_force` twice; second value silently overwrote the first | Removed the duplicate key |
| 4 | **Unused `all_neighbors_cache` dict in `step()`** | Allocated a dict and populated it every tick but never read it, wasting memory and CPU | Removed the unused cache variable entirely |
| 5 | **`boundary_force()` ZeroDivisionError when `margin=0`** | If `boundary_margin` was set to 0 and a boid was outside the boundary, division by zero crashed the simulation | Added early return of zero vector when `margin <= 0` |
| 6 | **PPM renderer accepted `scale=0` and negative scale** | `scale=0` produced a 0×0 pixel PPM file (invalid); negative scale produced a PPM with negative dimensions in the header | Added input validation: `scale <= 0` now raises `ValueError` |

---

## Recent Improvements (v3.0)

### New Features

- **Pluggable spatial index**: QuadTree implementation alongside the existing SpatialHashGrid, selectable via config
- **Multi-species flocking**: Boids assigned to species only interact with same-species neighbors
- **Path following**: Reynolds-style waypoint navigation with arrival radius, looping, and deceleration
- **Arrival behavior**: Decelerating seek that slows down near the target
- **Event/callback system**: Observer pattern with 7 event types, exception-safe listener execution
- **Stats time-series tracking**: Automatic recording of per-step statistics with trend analysis, convergence detection, and summary
- **Animated SVG renderer**: Browser-playable SMIL animations, no JavaScript required
- **JSON renderer**: Full state export for external tooling
- **Benchmark CLI subcommand**: Compare grid vs quadtree performance
- **Track CLI subcommand**: Export time-series statistics
- **Animate CLI subcommand**: Generate animated SVGs from the CLI
- **Structured logging**: Python logging module integration throughout
- **11 presets** (3 new: multi-species, path-followers, quadtree-demo)

### Architecture Improvements

- Modular package with clear separation of concerns
- SpatialIndex protocol for swappable implementations
- Abstract base classes and protocols
- Full type hints with `from __future__ import annotations`
- Input validation on all public methods
- Comprehensive docstrings on every class and method

### Quality

- **250 tests** covering all modules (up from 25)
- GitHub Actions CI (3 Python versions)
- pyproject.toml — pip-installable
- CONTRIBUTING.md with development guide
- LICENSE file

---

## Roadmap

- **NumPy acceleration**: Optional NumPy backend for vectorized force computation
- **3D boids**: Extend to 3D with z-axis behaviors
- **WebGL renderer**: Real-time browser rendering via WebGL
- **Sound synthesis**: Generate audio from flock dynamics
- **Obstacle shapes**: Support for rectangular and polygonal obstacles
- **Flow fields**: Vector field following behavior
- **Leader-follower**: Hierarchical flocking with leader boids
- **Genetic tuning**: Evolve optimal weight parameters via genetic algorithm

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and guidelines
for adding new behaviors, renderers, and spatial indexes.

---

## License

MIT