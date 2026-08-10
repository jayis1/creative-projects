# Contributing to Seam Carving

Thank you for your interest in improving this project! This document describes
how to set up a development environment and the conventions to follow.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/seam-carving

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run the full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=seamcarving --cov-report=term-missing

# Run a specific test class
pytest tests/test_seamcarving.py::TestSeamRemoval -v
```

## Code Style

- Follow PEP 8 (use `flake8` or `ruff` to check).
- Add type hints to all public functions.
- Write docstrings (NumPy/Google style) for all public classes and functions.
- Keep functions focused — one function, one responsibility.
- Add `# fmt: off` / `# fmt: on` only when formatting would break readability.

## Architecture

The package is organised into focused modules:

```
seamcarving/
├── __init__.py       — Public API exports
├── __main__.py       — `python -m seamcarving` entry point
├── carver.py         — SeamCarver class, seam operations, resize helpers
├── energy.py         — Energy functions and EnergyType enum
├── io.py             — PPM/PGM/PNG image I/O
├── cli.py            — argparse CLI with subcommands
├── config.py         — CarverConfig dataclass, JSON/YAML/TOML loading
├── exceptions.py      — Exception hierarchy
└── logging.py        — Structured logging with JSON support
```

## Adding a New Energy Function

1. Implement the function in `energy.py` — it should take a grayscale
   `(H, W)` float64 array and return an energy map of the same shape.
2. Add an entry to the `EnergyType` enum.
3. Register it in the `ENERGY_FUNCTIONS` dict.
4. Add tests in `tests/test_seamcarving.py`.

## Pull Request Checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] New features have tests
- [ ] Docstrings are updated
- [ ] No new flake8 warnings
- [ ] README is updated if needed