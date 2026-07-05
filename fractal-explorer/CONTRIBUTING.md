# Contributing to Fractal Explorer

Thank you for your interest in improving Fractal Explorer! This document
describes how to set up a development environment and contribute changes.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/fractal-explorer

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode with test dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run the full test suite
python3 -m pytest tests/ -v

# Run only the new-feature tests
python3 -m pytest tests/test_new_features.py -v

# Run with coverage (if pytest-cov is installed)
python3 -m pytest tests/ --cov=fractal_explorer --cov-report=term-missing
```

All 135 tests should pass. The suite covers:

- Palette generation and custom hex gradients
- All fractal iterators (Mandelbrot, Julia, Burning Ship, Tricorn, Celtic,
  Phoenix, Magnet, Newton, periodic)
- Coloring modes (smooth, flat, DE, trap, root, histogram)
- Orbit traps (point, line, circle, cross, stripe, spiral)
- Rendering (single-threaded and parallel)
- I/O formats (PNG, PPM, SVG, ASCII, TGA)
- Deep zoom with Decimal arithmetic
- Buddhabrot, Lyapunov, and IFS fractals
- Post-processing filters
- Animation renderers
- Preset management
- CLI subcommands
- Backward-compatibility shim

## Code Style

- Follow PEP 8 with a line length of 88 characters.
- Use type hints where practical.
- Add docstrings to all public functions and classes.
- Keep the library dependency-free (Python stdlib only) for the core
  package. Optional dependencies (PyYAML, tomli) are allowed behind feature
  flags.

## Architecture

The package is split into focused modules:

```
fractal_explorer/
├── __init__.py      # Public API re-exports
├── palettes.py      # Colour palette generation
├── iterators.py     # Fractal iteration functions
├── periodicity.py   # Brent cycle detection for interior points
├── traps.py         # Orbit-trap classes
├── viewport.py      # Complex-plane viewport
├── coloring.py      # Per-pixel colour computation
├── render.py        # Rendering engine (parallel + histogram)
├── hp.py            # High-precision Decimal rendering
├── io_writers.py    # PNG/PPM/SVG/ASCII/TGA writers
├── zoom.py          # Zoom-sequence batch renderer
├── julia.py         # Julia-grid explorer
├── benchmark.py     # Throughput benchmarking
├── config.py        # Config file loading (JSON/YAML/TOML)
├── buddhabrot.py    # Buddhabrot / Anti-Buddhabrot
├── lyapunov.py      # Lyapunov fractal
├── ifs.py           # Iterated Function System fractals
├── filters.py       # Post-processing image filters
├── animation.py     # Animation frame sequences
├── presets.py       # Named render presets
└── cli.py           # Argparse CLI with subcommands
```

## Adding a New Fractal

1. Add an iterator function in `iterators.py` following the pattern of the
   existing ones (returns `(iter_count, extra)`).
2. Register it in the `FRACTALS` dict.
3. If it supports distance-estimation, add it to `DE_CAPABLE`.
4. If it has a unique orbit formula for trap coloring, add a branch in
   `_compute_pixel` under `coloring == "trap"`.
5. Add tests in `tests/test_fractal.py`.
6. Update the README's fractal table.

## Adding a New Palette

1. Write a function in `palettes.py` that takes `size` and returns a list of
   RGB tuples.
2. Register it in `PALETTES`.
3. Add a test in `tests/test_fractal.py`.

## Adding a New Filter

1. Write a function in `filters.py` that takes `(pixels, width, height)` and
   returns a new pixel list.
2. Register it in `FILTERS`.
3. Add a test in `tests/test_new_features.py`.

## Pull Request Checklist

- [ ] All tests pass (`python3 -m pytest tests/`)
- [ ] New code has docstrings and type hints
- [ ] New features have tests
- [ ] README is updated if needed
- [ ] No new external dependencies added (or they are optional)

## Reporting Bugs

Please open an issue with:

1. The command or code that triggered the bug
2. The full traceback
3. The Python version and OS
4. The expected vs actual behaviour