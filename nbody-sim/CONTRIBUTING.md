# Contributing to nbody-sim

Thank you for your interest in improving nbody-sim! This document describes
how to set up a development environment and the conventions for contributing.

## Development Setup

```bash
# Clone the monorepo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/nbody-sim

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install in development mode
pip install -e ".[test]"
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_integrators.py -v

# Run with coverage (optional)
pytest tests/ --cov=nbody --cov-report=term-missing
```

## Project Structure

```
nbody-sim/
├── nbody/
│   ├── __init__.py          # Public API exports
│   ├── __main__.py          # python -m nbody entry point
│   ├── body.py              # Body dataclass
│   ├── vec.py               # 2D vector helpers
│   ├── barnes_hut.py        # Barnes-Hut quadtree force evaluator
│   ├── integrator.py        # Legacy leapfrog integrator (single class)
│   ├── integrators.py       # All integrators (leapfrog, RK4, Forest-Ruth)
│   ├── simulation.py        # Simulation orchestrator + presets
│   ├── diagnostics.py       # Angular momentum, virial ratio, adaptive dt
│   ├── brute_force.py       # O(N²) ground truth + benchmark
│   ├── numpy_force.py       # NumPy-accelerated force evaluation
│   ├── renderer.py          # PPM frame renderer
│   ├── serialize.py         # JSON serialization
│   ├── config.py            # YAML/JSON/TOML config system
│   ├── cli.py               # Argparse CLI
│   └── logging_utils.py     # Structured logging
├── examples/
│   ├── two_body.py
│   ├── figure_eight.py
│   └── cluster_collapse.py
├── tests/
│   ├── test_barnes_hut.py
│   ├── test_integrators.py
│   ├── test_simulation.py
│   ├── test_misc.py
│   └── test_bughunt.py
├── configs/
│   └── plummer_example.yaml
├── pyproject.toml
├── LICENSE
├── CONTRIBUTING.md
└── README.md
```

## Coding Conventions

- **Python 3.10+**: Use `from __future__ import annotations` for forward refs.
- **Type hints**: All public functions and methods should have type hints.
- **Docstrings**: Use triple-quote docstrings with Parameters/Returns sections.
- **Testing**: Every new feature or bug fix should include tests.
- **No external dependencies** beyond numpy and pyyaml (standard library
  preferred).

## Adding a New Integrator

1. Create a class in `nbody/integrators.py` with `step(bodies, dt)`,
   `total_energy(bodies)`, `total_momentum(bodies)`, and `center_of_mass(bodies)`
   methods.
2. Register it in the `INTEGRATORS` dict.
3. Add a test in `tests/test_integrators.py`.
4. Update the CLI choices in `nbody/cli.py`.

## Adding a New Preset

1. Add a `@classmethod` to `Simulation` in `nbody/simulation.py`.
2. Add it to the `PRESETS` dict in `nbody/cli.py`.
3. Add tests in `tests/test_simulation.py`.
4. Update the README presets table.

## Adding a New Config Option

1. Add the field to `SimConfig` in `nbody/config.py`.
2. Update `to_dict()` and `from_dict()`.
3. Wire it through the CLI in `nbody/cli.py`.
4. Add a test in `tests/test_misc.py`.

## Commit Message Conventions

Use clear, descriptive commit messages:

- `Add forest-ruth integrator: 4th-order symplectic`
- `Fix plummer radius divergence: clamp u to 0.999`
- `Enhance CLI: add --config flag for config files`
- `Test: add integrator energy conservation tests`