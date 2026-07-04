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
- **Contact solver**: sequential-impulse with Baumgarte position stabilization, Coulomb friction, restitution
- **Joints**:
  - Distance joint (rod/constraint with configurable stiffness)
  - Revolute (pin) joint with optional angular motor
  - Weld joint (locks relative position and angle)
  - Mouse joint (soft spring for interactive dragging)
- **Sleeping**: bodies at rest are put to sleep to save computation
- **Rendering**:
  - ASCII renderer — terminal-based top-down view
  - PPM renderer — writes P6 image frames for animation
- **Point queries**: find bodies containing a world-space point

## How It Works

### Integration

Semi-implicit (symplectic) Euler: forces → velocities → positions.  Damping is applied
as exponential decay (frame-rate independent).

### Collision Detection

1. **Broad phase** — sweep-and-prune sorts body AABBs along the x-axis and tests
   y-overlap for active pairs, producing candidate body pairs.
2. **Narrow phase** — per shape pair, computes a contact manifold (normal + 1–2
   contact points with penetration depth).  Polygon-polygon uses SAT to find the
   minimum-overlap axis, identifies the reference and incident edges, then clips the
   incident edge against the reference edge's side planes (Sutherland-Hodgman) to
   produce up to 2 contact points.

### Constraint Solver

The solver converts each contact point into a normal constraint (non-penetration +
restitution) and a tangent constraint (Coulomb friction, clamped by `μ·N`).  It runs
multiple iterations of sequential impulses, warm-starting from the previous step's
accumulated impulses.  A Baumgarte bias term drives positional error toward zero each
step.  Joints are solved similarly with their own effective-mass matrices.

## Installation

```bash
cd rigid-body-engine
# No installation needed — just run from the project root.
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

### ASCII rendering

```python
from rigidbody.renderer import AsciiRenderer
renderer = AsciiRenderer(width=72, height=28)
print(renderer.render(world.bodies))
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
├── rigidbody/
│   ├── __init__.py          # Public API
│   ├── world.py             # World: orchestrates the simulation
│   ├── core/
│   │   ├── vec2.py          # 2D vector
│   │   ├── mat22.py         # 2×2 matrix + linear solver
│   │   ├── shapes.py       # Circle, Polygon, AABB
│   │   ├── body.py          # RigidBody: state + integration
│   │   ├── collision.py     # Narrow-phase collision (SAT, manifolds)
│   │   └── broadphase.py    # Sweep-and-prune
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
- `step(dt)` — advance the simulation
- `bodies_at(point)` → list of body indices containing the point

### `RigidBody(shape, position, angle=0, body_type=DYNAMIC, density=1, restitution=0.2, friction=0.3)`
- `apply_force(force, point=None)`
- `apply_impulse(impulse, point=None)`
- `to_world(local)` / `to_local(world)`
- `velocity_at_point(world_point)`

### Shapes
- `Circle(radius, offset=None)`
- `Polygon(vertices)` / `Polygon.box(w, h)` / `Polygon.regular_polygon(sides, radius)`

### Joints
- `DistanceJoint(body_a, local_a, body_b, local_b, length=None, stiffness=1.0)`
- `RevoluteJoint(body_a, local_a, body_b, local_b, motor_enabled=False, motor_speed=0, max_motor_force=0)`
- `WeldJoint(body_a, local_a, body_b, local_b, frequency=8, damping=0.5)`
- `MouseJoint(body, target, frequency=8, damping=0.5, max_force=1000)`

## License

MIT