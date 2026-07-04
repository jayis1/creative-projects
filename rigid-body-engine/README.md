# rigid-body-engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Tests: 142](https://img.shields.io/badge/tests-142%20passing-brightgreen.svg)](./tests)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-success.svg)](#installation)

A 2D rigid body physics engine written in pure Python (no external dependencies).

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Basic Simulation](#basic-simulation)
  - [Joints](#joints)
  - [Force Fields](#force-fields)
  - [Collision Filtering & Sensors](#collision-filtering--sensors)
  - [Ray Casting](#ray-casting)
  - [Spatial Queries](#spatial-queries)
  - [Serialization (JSON/YAML)](#serialization-jsonyaml)
  - [Diagnostics](#diagnostics)
  - [Rendering](#rendering)
- [CLI](#cli)
- [Examples](#examples)
- [Architecture](#architecture)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [License](#license)

---

## Overview

This project implements a complete 2D rigid body dynamics simulator from scratch —
no physics libraries, no NumPy, just the Python standard library. It covers the full
pipeline from force integration through collision detection to constraint solving,
modelled after the architecture used by production engines like Box2D (Erin Catto's
sequential-impulse solver).

### Features

- **Shapes**: circles and convex polygons (boxes, regular polygons, custom)
- **Body types**: dynamic (full simulation), static (immovable), kinematic (moves but unaffected by forces)
- **Collision detection**:
  - Circle × circle — distance-based
  - Polygon × polygon — SAT (Separating Axis Theorem) with reference/incident edge clipping for 2-point contact manifolds
  - Circle × polygon — closest-point-on-polygon with interior/exterior cases
- **Broad phase**: sweep-and-prune (sort & sweep) on AABBs
- **Contact solver**: sequential-impulse with Baumgarte position stabilization, Coulomb friction, restitution, warm starting
- **Joints**:
  - Distance joint (rod/constraint with configurable stiffness)
  - Revolute (pin) joint with optional angular motor
  - Weld joint (locks relative position and angle)
  - Prismatic (slider) joint with optional linear motor
  - Mouse joint (soft spring for interactive dragging)
- **Force fields**: uniform (wind/gravity), radial (gravity well), quadratic drag, buoyancy — pluggable via `ForceField` base class
- **Collision filtering**: layer/mask bitmasks for selective collision; sensor bodies detect overlap without response
- **Ray casting**: ray vs circle/polygon with closest-hit queries and AABB acceleration
- **Spatial queries**: point-in-body, AABB overlap, ray cast
- **Sleeping**: bodies at rest are put to sleep to save computation
- **Diagnostics**: energy (kinetic/potential/total), linear/angular momentum, energy drift tracking
- **Serialization**: save/load world state as JSON or YAML (bodies, joints, parameters)
- **Logging**: configurable logging via Python's `logging` module
- **Rendering**:
  - ASCII renderer — terminal-based top-down view
  - PPM renderer — writes P6 image frames for animation
- **CLI**: `run` (ASCII sim), `render` (PPM frames), `save`/`info` (scene files), `energy` (diagnostics), `raycast` (ray query)
- **pip-installable** with `pyproject.toml` and `rigid-body` entry point
- **142 tests** covering all modules
- **CI**: GitHub Actions workflow testing Python 3.10–3.12

---

## Installation

```bash
cd rigid-body-engine
pip install -e .           # installs the `rigid-body` CLI command

# With optional dependencies:
pip install -e ".[yaml]"  # YAML scene support
pip install -e ".[test]"  # pytest + pyyaml
pip install -e ".[dev]"   # pytest + pytest-cov + pyyaml
```

Or just run directly without installing:
```bash
python3 examples/demo.py
```

**Requirements**: Python 3.10+. No runtime dependencies (PyYAML is optional).

---

## Quick Start

```python
from rigidbody import World, RigidBody, Vec2, Polygon

world = World(gravity=Vec2(0.0, -9.81))
floor = RigidBody(Polygon.box(20.0, 1.0), Vec2(0.0, -0.5), body_type=RigidBody.STATIC)
box = RigidBody(Polygon.box(1.0, 1.0), Vec2(0.0, 5.0), body_type=RigidBody.DYNAMIC, density=1.0)

world.add_body(floor)
world.add_body(box)

dt = 1.0 / 60.0
for _ in range(300):
    world.step(dt)

print(f"Box settled at y={box.position.y:.3f}")  # ≈ 0.49
```

---

## Usage

### Basic Simulation

```python
from rigidbody import World, RigidBody, Vec2, Polygon

world = World(gravity=Vec2(0.0, -9.81))
floor = RigidBody(Polygon.box(20.0, 1.0), Vec2(0.0, -0.5), body_type=RigidBody.STATIC)
box = RigidBody(Polygon.box(1.0, 1.0), Vec2(0.0, 5.0), body_type=RigidBody.DYNAMIC, density=1.0)

world.add_body(floor)
world.add_body(box)

dt = 1.0 / 60.0
for _ in range(300):
    world.step(dt)

print(f"Box settled at y={box.position.y:.3f}")  # ≈ 0.49
```

### Joints

```python
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.joints import RevoluteJoint, DistanceJoint, PrismaticJoint

world = World(gravity=Vec2(0.0, -9.81))

# Pendulum (revolute joint)
pivot = RigidBody(Polygon.box(0.4, 0.4), Vec2(0, 10), body_type=RigidBody.STATIC)
bob = RigidBody(Circle(0.5), Vec2(0, 7), body_type=RigidBody.DYNAMIC, density=5.0)
world.add_body(pivot)
world.add_body(bob)
world.add_joint(RevoluteJoint(pivot, Vec2.zero(), bob, Vec2(0, 3)))

# Revolute joint with motor
world.add_joint(RevoluteJoint(a, Vec2.zero(), b, Vec2.zero(),
                               motor_enabled=True, motor_speed=5.0,
                               max_motor_force=100))

# Distance joint (rope/constraint)
world.add_joint(DistanceJoint(a, Vec2.zero(), b, Vec2.zero(), length=3.0))

# Prismatic (slider) joint
world.add_joint(PrismaticJoint(a, Vec2.zero(), b, Vec2.zero(),
                                axis=Vec2(1, 0),
                                motor_enabled=True, motor_speed=3.0,
                                max_motor_force=50))
```

### Force Fields

```python
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.core.fields import RadialField, DragField, BuoyancyField, UniformField

world = World(gravity=Vec2(0, -9.81))

# Gravity well pulling toward origin
world.add_force_field(RadialField(Vec2(0, 0), strength=50, falloff=2.0))

# Wind
world.add_force_field(UniformField(Vec2(5, 0)))

# Air drag
world.add_force_field(DragField(coefficient=0.1))

# Buoyancy (fluid surface at y=0)
world.add_force_field(BuoyancyField(fluid_level=0, fluid_density=1.0, drag=0.3))
```

### Collision Filtering & Sensors

```python
world = World(gravity=Vec2(0, -9.81))

# This box only collides with layer 1
box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), body_type=RigidBody.DYNAMIC)
box.collision_layer = 0x0001
box.collision_mask = 0x0001
world.add_body(box)

# Ghost box passes through everything
ghost = RigidBody(Polygon.box(1, 1), Vec2(0, 3), body_type=RigidBody.DYNAMIC)
ghost.collision_layer = 0x0002
ghost.collision_mask = 0x0002
world.add_body(ghost)

# Sensor: detects overlap but doesn't push back
sensor = RigidBody(Polygon.box(4, 0.2), Vec2(0, 2), body_type=RigidBody.STATIC)
sensor.is_sensor = True
world.add_body(sensor)

# Collision callback
def on_collide(a_idx, b_idx, manifold):
    print(f"Collision: bodies {a_idx} and {b_idx}")
world.on_collision = on_collide
```

### Ray Casting

```python
from rigidbody import World, RigidBody, Vec2, Circle

world = World(gravity=Vec2(0, 0))
wall = RigidBody(Circle(1), Vec2(5, 0), body_type=RigidBody.STATIC)
world.add_body(wall)
world.step(1/60)

# Cast a ray from origin toward +x
hit = world.ray_cast(Vec2(0, 0), Vec2(1, 0))
if hit:
    print(f"Hit body {hit.body_index} at {hit.point}, normal={hit.normal}")

# Skip certain bodies
hit = world.ray_cast(Vec2(0, 0), Vec2(1, 0), ignore={0})

# Direct ray cast on body list
from rigidbody import ray_cast
hit = ray_cast(world.bodies, Vec2(0, 0), Vec2(1, 0), max_distance=50)
```

### Spatial Queries

```python
# Find bodies containing a point
indices = world.bodies_at(Vec2(3, 3))

# Find bodies overlapping an AABB
indices = world.bodies_in_aabb(Vec2(-1, -1), Vec2(1, 1))

# Find a body by its user_data tag
body = world.find_body("box0")
```

### Serialization (JSON/YAML)

```python
from rigidbody import world_to_json, world_from_json, world_to_yaml, world_from_yaml
from rigidbody import world_to_file, world_from_file

# JSON
world_to_json(world, "scene.json")
world = world_from_json("scene.json")

# YAML (requires pyyaml)
world_to_yaml(world, "scene.yaml")
world = world_from_yaml("scene.yaml")

# Auto-detect by extension
world_to_file(world, "scene.json")   # → JSON
world_to_file(world, "scene.yaml")  # → YAML
world = world_from_file("scene.json")
```

### Diagnostics

```python
from rigidbody import Diagnostics

diag = Diagnostics()
for _ in range(300):
    world.step(1/60)
    diag.sample(world.bodies)
print(f"Energy drift: {diag.energy_drift():.2%}")

report = diag.report()
print(f"Kinetic energy: {report['kinetic_min']:.3f} – {report['kinetic_max']:.3f}")
```

### Rendering

```python
from rigidbody.renderer import AsciiRenderer, PPMRenderer

# ASCII rendering
renderer = AsciiRenderer(width=72, height=28)
print(renderer.render(world.bodies))

# PPM frames for video
ppm = PPMRenderer(output_dir="frames/", width=320, height=240)
for _ in range(300):
    world.step(1/60)
    ppm.render_frame(world.bodies)
# Then: ffmpeg -framerate 60 -i frames/frame_%04d.ppm out.gif
```

---

## CLI

```bash
# Run the built-in demo (ASCII animation)
rigid-body run --frames 300

# Save a scene as JSON or YAML
rigid-body save scene.json
rigid-body save scene.yaml

# Simulate from a scene file
rigid-body run --scene scene.json --frames 600
rigid-body run --scene scene.yaml --frames 600

# Render PPM frames for video
rigid-body render --scene scene.json --frames 300 --output-dir frames/
# Then: ffmpeg -framerate 60 -i frames/frame_%04d.ppm out.gif

# Energy diagnostics
rigid-body energy --frames 500

# Scene info
rigid-body info scene.json

# Ray casting
rigid-body raycast --origin 0 10 --direction 0 -1
rigid-body raycast --origin -5 0 --direction 1 0 --max-distance 50
```

---

## Examples

The `examples/` directory contains runnable demos:

| File | Description |
|------|-------------|
| `demo.py` | Stack of boxes, rolling ball, pendulum, ramp |
| `domino_chain.py` | Domino chain reaction with 12 upright boxes |
| `buoyancy.py` | Floating vs sinking boxes in fluid |
| `gravity_well.py` | Planetary orbits around a central star |
| `ray_casting.py` | Ray casting against various obstacles |

```bash
python3 examples/demo.py 180
python3 examples/domino_chain.py 300
python3 examples/buoyancy.py 400
python3 examples/gravity_well.py 600
python3 examples/ray_casting.py
```

### ASCII Demo Output

```
+------------------------------------------------------------------------+
|                                                                        |
|                                                                        |
|                                                                        |
|                        #                                               |
|                        #                                               |
|                        #                                               |
|                        #                                               |
|                        #                                               |
|                        #                                               |
|                        #                                               |
|          ##                                                            |
|          ##                                                            |
|          ##                                                            |
|          ##         ##                            o                    |
|          ##         ##                            o                    |
|          ##         ##                            o                    |
|          ##         ##                            o                    |
|          ##         ##                            o                    |
|          ##         ##                            o                    |
|          ##         ##                            o                    |
|HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH|
+------------------------------------------------------------------------+
```

(`#` = dynamic, `H` = static, `o` = rolling ball)

---

## Architecture

```
World.step(dt)
  ├── Apply force fields → body.force
  ├── Integrate forces → velocities (semi-implicit Euler)
  ├── Broad phase (sweep-and-prune on AABBs)
  ├── Narrow phase (SAT collision detection → manifolds)
  ├── Solve contact constraints (sequential impulses + friction)
  ├── Solve joint constraints (distance, revolute, weld, prismatic, mouse)
  ├── Position correction (Baumgarte stabilization)
  └── Sleeping logic
```

### Project Structure

```
rigid-body-engine/
├── pyproject.toml              # pip install + CLI entry point + optional deps
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── rigidbody/
│   ├── __init__.py             # Public API (40+ exports)
│   ├── world.py                # World: orchestrates the simulation
│   ├── cli.py                  # CLI (run/render/save/info/energy/raycast)
│   ├── diagnostics.py          # Energy/momentum tracking
│   ├── serialize.py            # JSON/YAML save/load
│   ├── raycast.py              # Ray casting (circle, polygon, AABB)
│   ├── logger.py               # Logging configuration
│   ├── core/
│   │   ├── vec2.py             # 2D vector (immutable, operators)
│   │   ├── mat22.py            # 2×2 matrix + Cramer's rule solver
│   │   ├── shapes.py           # Circle, Polygon, AABB
│   │   ├── body.py             # RigidBody: state + integration
│   │   ├── collision.py        # Narrow-phase (SAT, manifolds, clipping)
│   │   ├── broadphase.py       # Sweep-and-prune
│   │   └── fields.py           # Force fields (uniform/radial/drag/buoyancy)
│   ├── solver/
│   │   └── contact_solver.py   # Sequential-impulse + Baumgarte
│   ├── joints/
│   │   └── joints.py           # Distance, revolute, weld, prismatic, mouse
│   └── renderer/
│       └── renderer.py         # ASCII + PPM renderers
├── examples/
│   ├── demo.py                 # Stack + ball + pendulum + ramp
│   ├── domino_chain.py         # Domino chain reaction
│   ├── buoyancy.py             # Floating/sinking boxes
│   ├── gravity_well.py         # Planetary orbits
│   └── ray_casting.py          # Ray casting demo
└── tests/
    ├── test_vec2.py            # 30 tests
    ├── test_mat22.py           # 8 tests
    ├── test_shapes.py         # 16 tests
    ├── test_body.py            # 20 tests
    ├── test_collision.py       # 13 tests
    ├── test_world.py           # 16 tests
    ├── test_joints.py          # 7 tests
    ├── test_fields.py          # 8 tests
    ├── test_serialize.py       # 6 tests
    ├── test_diagnostics.py     # 8 tests
    └── test_raycast.py         # 10 tests
```

### Integration

Semi-implicit (symplectic) Euler: forces → velocities → positions. Damping is applied
as exponential decay (frame-rate independent). Force fields are applied before
integration each step.

### Collision Detection

1. **Broad phase** — sweep-and-prune sorts body AABBs along the x-axis and tests
   y-overlap for active pairs, producing candidate body pairs.
2. **Narrow phase** — per shape pair, computes a contact manifold (normal + 1–2
   contact points with penetration depth). Polygon-polygon uses SAT to find the
   minimum-overlap axis, identifies the reference and incident edges, then clips
   the incident edge against the reference edge's side planes (Sutherland-Hodgman)
   to produce up to 2 contact points.
3. **Collision filtering** — each body has a `collision_layer` and `collision_mask`.
   Two bodies collide only if `(a.mask & b.layer) != 0` AND `(b.mask & a.layer) != 0`.
   Sensor bodies (`is_sensor=True`) generate collision callbacks but no solver constraints.

### Constraint Solver

The solver converts each contact point into a normal constraint (non-penetration +
restitution) and a tangent constraint (Coulomb friction, clamped by `μ·N`). It runs
multiple iterations of sequential impulses, warm-starting from the previous step's
accumulated impulses. A Baumgarte bias term drives positional error toward zero each
step. Joints are solved similarly with their own effective-mass matrices.

---

## Testing

```bash
pip install -e ".[test]"
pytest tests/ -v
```

All 142 tests pass. The test suite covers:

- Vec2 arithmetic, geometry, comparison
- Mat22 operations and linear solver
- Shape mass/AABB computation and validation
- Body construction, forces, integration, sleeping
- Collision detection (circle×circle, polygon×polygon, circle×polygon)
- World simulation, collision filtering, sleeping, spatial queries
- All joint types (distance, revolute, weld, prismatic, motor)
- Force fields (uniform, radial, drag, buoyancy)
- Ray casting (hit, miss, closest, ignore)
- Serialization round-trips (JSON and YAML)
- Energy/momentum diagnostics

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, code style,
and architecture details. Pull requests welcome!

Key guidelines:
- Pure Python only (no runtime dependencies for core)
- Type hints and docstrings required
- Add tests for new features
- All tests must pass

---

## Roadmap

- [ ] **Dynamic BVH broad phase** — bounding volume hierarchy for large scenes
- [ ] **Continuous collision detection** (CCD) — prevent tunneling at high speeds
- [ ] **Soft constraints** — frequency/damping for all joint types
- [ ] **Compound shapes** — multiple shapes per body
- [ ] **Chain/rope constraint** — segmented distance joints
- [ ] **PNG/SVG renderer** — direct image output without ffmpeg
- [ ] **WebGL renderer** — browser-based visualization
- [ ] **Substepping** — automatic timestep subdivision for stability
- [ ] **Restitution slope** — configurable velocity threshold for bounce
- [ ] **Contact persistence** — graph-based contact tracking for islanding
- [ ] **Multi-threading** — parallel solver iterations

---

## Changelog

### v3.0.0 — Comprehensive Improvement

**New Features:**
- **Ray casting** — `ray_cast()` for ray vs circle/polygon with closest-hit queries, AABB acceleration, and ignore sets
- **Prismatic (slider) joint** — constrains relative translation to one axis with optional linear motor
- **YAML serialization** — `world_to_yaml()` / `world_from_yaml()` (optional pyyaml dependency)
- **Auto-detect file format** — `world_to_file()` / `world_from_file()` choose JSON/YAML by extension
- **AABB query** — `World.bodies_in_aabb()` for region queries
- **Logging** — `rigidbody.logger` module with `configure_logging()` and `get_logger()`
- **`raycast` CLI subcommand** — cast rays from the command line
- **Input validation** — World constructor validates iteration counts

**Bug Fixes:**
- **Distance joint impulse clamp** — fixed `max(0, ...)` to `min(0, ...)` so the joint actually pulls bodies together (was a no-op, bodies fell freely)
- **Ray cast unit confusion** — fixed fraction/distance mixing that caused all world-level ray casts to miss

**Improvements:**
- 142-test pytest suite covering all modules
- GitHub Actions CI (Python 3.10–3.12)
- CONTRIBUTING.md with development guidelines
- LICENSE file
- 4 new example scripts (domino chain, buoyancy, gravity well, ray casting)
- Optional dependencies in pyproject.toml (`[yaml]`, `[test]`, `[dev]`)
- Enhanced pyproject.toml classifiers
- Type hints and docstrings throughout new code
- World ray cast convenience method

### v2.0.0 — Enhancement Phase

- Force fields (uniform, radial, drag, buoyancy)
- Collision filtering (layer/mask bitmasks)
- Sensor bodies
- Diagnostics (energy, momentum, drift)
- JSON serialization
- CLI with 5 subcommands
- pyproject.toml with `rigid-body` entry point

### v1.0.0 — Initial Release

- Core engine: Vec2, Mat22, shapes, bodies
- SAT collision detection with clipping
- Sequential-impulse solver with Baumgarte
- Distance, revolute, weld, mouse joints
- Sweep-and-prune broad phase
- Sleeping
- ASCII and PPM renderers
- Semi-implicit Euler integration

---

## License

MIT — see [LICENSE](./LICENSE).