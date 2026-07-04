# Contributing to rigid-body-engine

Thank you for your interest in contributing! This document covers the basics.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects
cd creative-projects/rigid-body-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with test dependencies
pip install -e ".[test]"
```

## Running Tests

```bash
pytest tests/ -v
```

All 140+ tests should pass. If any fail, investigate before submitting a PR.

## Code Style

- **Type hints**: All new code should include type annotations.
- **Docstrings**: Every public class and function needs a docstring.
- **Imports**: Use `from __future__ import annotations` for forward references.
- **No external dependencies**: The core engine must remain pure Python
  (standard library only). Optional features (YAML serialization) may use
  dependencies guarded by `try/except ImportError`.
- **Line length**: Keep lines under 100 characters.

## Architecture

The engine follows a classic Box2D-style pipeline:

```
World.step(dt)
  ├── Apply force fields
  ├── Integrate forces → velocities (semi-implicit Euler)
  ├── Broad phase (sweep-and-prune)
  ├── Narrow phase (SAT collision detection)
  ├── Solve contact constraints (sequential impulses)
  ├── Solve joint constraints
  ├── Position correction (Baumgarte)
  └── Sleeping logic
```

Key modules:

| Module | Responsibility |
|--------|---------------|
| `core/vec2.py` | Immutable 2D vector |
| `core/mat22.py` | 2×2 matrix + linear solver |
| `core/shapes.py` | Circle, convex Polygon, AABB |
| `core/body.py` | RigidBody state + integration |
| `core/collision.py` | Narrow-phase collision (SAT, clipping) |
| `core/broadphase.py` | Sweep-and-prune |
| `core/fields.py` | Force fields (wind, drag, buoyancy) |
| `solver/contact_solver.py` | Sequential-impulse solver |
| `joints/joints.py` | Distance, revolute, weld, prismatic, mouse joints |
| `renderer/renderer.py` | ASCII + PPM renderers |
| `raycast.py` | Ray casting queries |
| `serialize.py` | JSON/YAML save/load |
| `diagnostics.py` | Energy/momentum tracking |
| `logger.py` | Logging configuration |
| `world.py` | World orchestrator |
| `cli.py` | Command-line interface |

## Adding a New Feature

1. **New shape**: Subclass `Shape`, implement `compute_mass()` and
   `compute_aabb()`, then add a dispatch case in `collision.py`.
2. **New joint**: Subclass `Joint`, implement `pre_solve()` and `solve()`.
3. **New force field**: Subclass `ForceField`, implement `apply()`.
4. **New renderer**: Add a class that takes `List[RigidBody]` and produces
   output; no engine coupling needed.

## Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] New features have tests
- [ ] No new external dependencies (or guarded with `importorskip`)
- [ ] Docstrings added/updated
- [ ] README updated if user-facing changes