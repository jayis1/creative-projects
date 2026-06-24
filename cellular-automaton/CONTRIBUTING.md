# Contributing to the Cellular Automaton Simulator

Thank you for your interest in contributing! This document describes how to
set up the development environment and the conventions we follow.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects
cd creative-projects/cellular-automaton

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_multistate.py -v

# Run with coverage
python -m pytest tests/ --cov=cellular_automaton --cov-report=term-missing
```

## Project Structure

```
cellular-automaton/
├── cellular_automaton/         # Main package
│   ├── __init__.py             # Public API exports
│   ├── engine.py               # Core CA engine (stepping, stats, serialization)
│   ├── rules.py                # Rule classes + registry (256 elementary + 15 Life-like)
│   ├── multistate.py           # Multi-state CAs (Wireworld, Brian's Brain, etc.)
│   ├── patterns.py             # 19 builtin patterns + RLE parser
│   ├── vectorized.py           # NumPy-accelerated stepping
│   ├── visualizer.py           # ASCII / ANSI / SVG / PPM / PNG / spacetime renderers
│   ├── analysis.py             # Wolfram classification, entropy, density, sweeps
│   ├── config.py               # Config system (JSON/YAML/TOML)
│   └── cli.py                  # argparse CLI (15 subcommands)
├── examples/                   # Example scripts
├── tests/                      # Test suite
├── pyproject.toml              # Package metadata + dependencies
├── LICENSE                     # MIT license
├── CONTRIBUTING.md             # This file
└── README.md                   # Documentation
```

## Coding Conventions

- **Python 3.8+** compatibility required.
- **Type hints** on all public functions.
- **Docstrings** (Google style) on all classes and public methods.
- **Tests** for all new features.
- **No external dependencies** beyond numpy (optional: Pillow for PNG, PyYAML for YAML configs).

## Adding a New Rule

1. If it's a binary (0/1) rule, subclass `Rule` in `rules.py` and implement
   `apply()` and `name`. Add it to the `RULES` registry.

2. If it's a multi-state rule (3+ states), subclass `MultiStateRule` in
   `multistate.py` and implement `step()`. Add it to the `MULTISTATE_RULES`
   registry.

3. Add tests in `tests/`.

4. Update the README.md.

## Adding a New Pattern

1. Define the pattern as a list of `(x, y)` coordinates in `patterns.py`.
2. Add it to the `PATTERNS` dict.
3. Add a test verifying its behaviour (period, stability, etc.).

## Adding a New Renderer

1. Implement the render function in `visualizer.py`.
2. Export it from `__init__.py`.
3. Add a corresponding CLI format option if applicable.
4. Add tests.

## Pull Request Checklist

- [ ] Tests pass: `python -m pytest tests/ -v`
- [ ] New features have tests
- [ ] Docstrings added/updated
- [ ] README.md updated if needed
- [ ] No new external dependencies (or clearly justified and optional)