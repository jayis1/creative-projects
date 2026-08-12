# Contributing to boids-sim

Thank you for your interest in improving boids-sim! This guide covers how to
set up the development environment and contribute changes.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/boids-sim

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ -v --cov=boids --cov-report=term-missing

# Run a single test class
python3 -m pytest tests/test_boids.py::TestSeparation -v
```

## Code Style

- Use `from __future__ import annotations` for forward references
- Type hints are required for all public methods
- Docstrings should describe behavior, parameters, and return values
- Keep functions focused — one behavior per method
- Use `__slots__` for performance-critical classes (Boid, Vector2, etc.)

## Adding a New Behavior

1. Add the method to the `Boid` class in `boids/boid.py`
2. Add a weight parameter to `SimulationConfig` in `boids/config.py`
3. Wire it into `BoidSimulation.step()` in `boids/simulation.py`
4. Add tests in `tests/`
5. Update the README with the new behavior

## Adding a New Renderer

1. Create a class with a `render(sim, ...)` method in `boids/renderer.py`
2. Export it from `boids/__init__.py`
3. Add a CLI flag if applicable in `boids/cli.py`
4. Add tests
5. Update the README

## Adding a New Spatial Index

1. Implement the `SpatialIndex` protocol from `boids/spatial_index.py`
2. Add the type string to `_make_spatial_index()` in `boids/simulation.py`
3. Add tests
4. Update the README

## Commit Messages

Use conventional commit format:
- `Add <feature>: <description>`
- `Enhance <feature>: <description>`
- `Fix <bug>: <description>`
- `Bug hunt <project>: fix N bugs, add tests`

## Pull Requests

1. Ensure all tests pass: `python3 -m pytest tests/ -v`
2. Add tests for new features
3. Update documentation (README.md)
4. Keep changes focused and minimal