# Contributing to mcmc-sampler

Thank you for your interest in contributing! This document outlines the
process for contributing to the mcmc-sampler project.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/mcmc-sampler

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All tests must pass before submitting a pull request.

## Code Style

- Follow PEP 8 with a line length of 100 characters.
- Use type hints on all public functions.
- Add docstrings to all public classes and functions (NumPy style).
- Add `from __future__ import annotations` at the top of every module.

## Adding a New Sampler

1. Create a new file in `mcmc_sampler/` or add to `samplers.py`.
2. Subclass `_BaseSampler` (from `samplers.py`).
3. Implement the `sample()` method returning a `Trace`.
4. Export from `__init__.py`.
5. Add CLI support in `cli.py`.
6. Write tests in `tests/`.
7. Update the README.

## Adding a New Distribution

1. Subclass `Target` (from `distributions.py`).
2. Implement `_logpdf(x) -> float`.
3. Validate parameters in `__init__`.
4. Export from `__init__.py`.
5. Add CLI support if applicable.
6. Write tests.
7. Update the README.

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes and commit with a clear message.
3. Ensure all tests pass: `python -m pytest tests/`
4. Push and open a pull request with a description of changes.

## Reporting Bugs

Open an issue with:
- A clear title and description
- Minimal reproducing code
- Expected vs actual behaviour
- Python version and OS