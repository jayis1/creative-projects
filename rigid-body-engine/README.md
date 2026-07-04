# rigid-body-engine

A 2D rigid body physics engine written in pure Python (no external dependencies).

## Overview

This project implements a complete 2D rigid body dynamics simulator from scratch —
no physics libraries, no NumPy, just the Python standard library.  It covers the full
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
  - Mouse joint (soft spring for interactive dragging)
- **Force fields**: uniform (wind/gravity), radial (gravity well), quadratic drag, buoyancy — pluggable via `ForceField` base class
- **Collision filtering**: layer/mask bitmasks for selective collision; sensor bodies detect overlap without response
- **Sleeping**: bodies at rest are put to sleep to save computation
- **Diagnostics**: energy (kinetic/potential/total), linear/angular momentum, energy drift tracking
- **Serialization**: save/load world state as JSON (bodies, joints, parameters)
- **Rendering**:
  - ASCII renderer — terminal-based top-down view
  - PPM renderer — writes P6 image frames for animation
- **CLI**: `run` (ASCII sim), `render` (PPM frames), `save`/`info` (scene files), `energy` (diagnostics)
- **Point queries**: find bodies containing a world-space point
- **pip-installable** with `pyproject.toml` and `rigid-body` entry point

## How It Works

### Integration

Semi-implicit (symplectic) Euler: forces → velocities → positions.  Damping is applied
as exponential decay (frame-rate independent).  Force fields are applied before
integration each step.

### Collision Detection

1. **Broad phase** — sweep-and-prune sorts body AABBs along the x-axis and tests
   y-overlap for active pairs, producing candidate body pairs.
2. **Narrow phase** — per shape pair, computes a contact manifold (normal + 1–2
   contact points with penetration depth).  Polygon-polygon uses SAT to find the
   minimum-overlap axis (among front-facing edges), identifies the reference and
   incident edges, then clips the incident edge against the reference edge's side
   planes (Sutherland-Hodgman) to produce up to 2 contact points.
3. **Collision filtering** — each body has a `collision_layer` and `collision_mask`.
   Two bodies collide only if `(a.mask & b.layer) != 0` AND `(b.mask & a.layer) != 0`.
   Sensor bodies (`is_sensor=True`) generate collision callbacks but no solver constraints.

### Constraint Solver

The solver converts each contact point into a normal constraint (non-penetration +
restitution) and a tangent constraint (Coulomb friction, clamped by `μ·N`).  It runs
multiple iterations of sequential impulses, warm-starting from the previous step's
accumulated impulses.  A Baumgarte bias term drives positional error toward zero each
step.  Joints are solved similarly with their own effective-mass matrices.

### Force Fields

`ForceField` subclasses are registered with `world.add_force_field()` and called once
per dynamic body per step.  Built-in fields:

- `UniformField` — constant acceleration (wind, extra gravity)
- `RadialField` — gravity well / repeller with configurable falloff
- `DragField` — quadratic velocity drag
- `BuoyancyField` — fluid buoyancy + drag below a surface level

### Diagnostics

`Diagnostics` tracks energy and momentum per step.  `energy_drift()` reports the
relative change in total energy — a key indicator of simulation quality.

## Installation

```bash
cd rigid-body-engine
pip install -e .   # optional — installs the `rigid-body` CLI command
# Or just run directly:
python3 examples/demo.py
```

## Usage

### Basic: drop a box on a floor

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

### Pendulum (revolute joint)

```python
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.joints import RevoluteJoint

world = World(gravity=Vec2(0.0, -9.81))
pivot = RigidBody(Polygon.box(0.4, 0.4), Vec2(0, 10), body_type=RigidBody.STATIC)
bob = RigidBody(Circle(0.5), Vec2(0, 7), body_type=RigidBody.DYNAMIC, density=5.0)
world.add_body(pivot)
world.add_body(bob)
world.add_joint(RevoluteJoint(pivot, Vec2.zero(), bob, Vec2(0, 3)))

for _ in range(300):
    world.step(1/60)
```

### Collision filtering & sensors

```python
from rigidbody import World, RigidBody, Vec2, Polygon

world = World(gravity=Vec2(0, -9.81))
floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
world.add_body(floor)

# This box only collides with layer 1 (floor is on layer 1)
box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), body_type=RigidBody.DYNAMIC)
box.collision_layer = 0x0001
box.collision_mask = 0x0001
world.add_body(box)

# This ghost box only collides with layer 2 — passes through everything
ghost = RigidBody(Polygon.box(1, 1), Vec2(0, 3), body_type=RigidBody.DYNAMIC)
ghost.collision_layer = 0x0002
ghost.collision_mask = 0x0002
world.add_body(ghost)

# Sensor: detects overlap but doesn't push back
sensor = RigidBody(Polygon.box(4, 0.2), Vec2(0, 2), body_type=RigidBody.STATIC)
sensor.is_sensor = True
world.add_body(sensor)
```

### Force fields

```python
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.core.fields import RadialField, DragField

world = World(gravity=Vec2(0, -9.81))
# Gravity well pulling toward origin
world.add_force_field(RadialField(Vec2(0, 0), strength=50, falloff=2.0))
# Air drag
world.add_force_field(DragField(coefficient=0.1))
```

### Serialization

```python
from rigidbody import world_to_json, world_from_json

world_to_json(world, "scene.json")     # save
world = world_from_json("scene.json")  # load
```

### ASCII rendering

```python
from rigidbody.renderer import AsciiRenderer
renderer = AsciiRenderer(width=72, height=28)
print(renderer.render(world.bodies))
```

### Diagnostics

```python
from rigidbody import Diagnostics

diag = Diagnostics()
for _ in range(300):
    world.step(1/60)
    diag.sample(world.bodies)
print(f"Energy drift: {diag.energy_drift():.2%}")
```

## CLI

```bash
# Run the built-in demo (ASCII animation)
rigid-body run --frames 300

# Save a scene as JSON
rigid-body save scene.json

# Simulate from a scene file
rigid-body run --scene scene.json --frames 600

# Render PPM frames for video
rigid-body render --scene scene.json --frames 300 --output-dir frames/
# Then: ffmpeg -framerate 60 -i frames/frame_%04d.ppm out.gif

# Energy diagnostics
rigid-body energy --frames 500

# Scene info
rigid-body info scene.json
```

### Running the demo

```bash
# 3-second simulation (180 frames at 60 FPS)
python3 examples/demo.py 180
```

The demo includes a 5-box stack, a rolling ball, a pendulum, and a ramp.

## Project Structure

```
rigid-body-engine/
├── pyproject.toml           # pip install + CLI entry point
├── rigidbody/
│   ├── __init__.py          # Public API
│   ├── world.py             # World: orchestrates the simulation
│   ├── cli.py               # CLI (run/render/save/info/energy)
│   ├── diagnostics.py       # Energy/momentum tracking
│   ├── serialize.py         # JSON save/load
│   ├── core/
│   │   ├── vec2.py          # 2D vector
│   │   ├── mat22.py         # 2×2 matrix + linear solver
│   │   ├── shapes.py       # Circle, Polygon, AABB
│   │   ├── body.py          # RigidBody: state + integration + collision filter
│   │   ├── collision.py     # Narrow-phase collision (SAT, manifolds)
│   │   ├── broadphase.py    # Sweep-and-prune
│   │   └── fields.py        # Force fields (uniform/radial/drag/buoyancy)
│   ├── solver/
│   │   └── contact_solver.py # Sequential-impulse solver
│   ├── joints/
│   │   └── joints.py        # Distance, revolute, weld, mouse joints
│   └── renderer/
│       └── renderer.py      # ASCII + PPM renderers
├── examples/
│   └── demo.py              # Stack + ball + pendulum demo
├── tests/
│   └── ...
└── README.md
```

## API Reference

### `World(gravity, velocity_iterations=10, position_iterations=5, joint_iterations=5)`
- `add_body(body)` → index
- `add_joint(joint)`
- `add_force_field(field)`
- `step(dt)` — advance the simulation
- `bodies_at(point)` → list of body indices containing the point
- `on_collision` — callback `(index_a, index_b, manifold)`

### `RigidBody(shape, position, angle=0, body_type=DYNAMIC, density=1, restitution=0.2, friction=0.3)`
- `apply_force(force, point=None)` / `apply_impulse(impulse, point=None)`
- `to_world(local)` / `to_local(world)`
- `velocity_at_point(world_point)`
- `collision_layer` / `collision_mask` — bitmasks for filtering
- `is_sensor` — detect but don't respond to collisions
- `gravity_scale` — per-body gravity multiplier

### Shapes
- `Circle(radius, offset=None)`
- `Polygon(vertices)` / `Polygon.box(w, h)` / `Polygon.regular_polygon(sides, radius)`

### Joints
- `DistanceJoint(body_a, local_a, body_b, local_b, length=None, stiffness=1.0)`
- `RevoluteJoint(body_a, local_a, body_b, local_b, motor_enabled=False, motor_speed=0, max_motor_force=0)`
- `WeldJoint(body_a, local_a, body_b, local_b, frequency=8, damping=0.5)`
- `MouseJoint(body, target, frequency=8, damping=0.5, max_force=1000)`

### Force Fields
- `UniformField(acceleration)`
- `RadialField(center, strength, falloff=2.0, max_radius=inf, min_radius=0.1)`
- `DragField(coefficient=0.5)`
- `BuoyancyField(fluid_level, fluid_density=1.0, gravity=Vec2(0,-9.81), drag=0.3)`

### Diagnostics
- `Diagnostics()` — `sample(bodies)`, `report()`, `energy_drift()`
- `compute_energy(bodies)` → `{kinetic, potential, total}`
- `compute_momentum(bodies)` → `{px, py, angular}`

### Serialization
- `world_to_json(world, path)` / `world_from_json(path)`
- `world_to_dict(world)` / `world_from_dict(dict)`
- `body_to_dict(body)` / `body_from_dict(dict)`

## License

MIT