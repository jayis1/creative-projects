# Contributing to orbital-mechanics

Thank you for your interest in improving this project!  This document
describes the development workflow and conventions.

## Development setup

```bash
cd orbital-mechanics
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
# Smoke tests (no pytest needed)
python3 demo.py

# Full pytest suite
pytest tests/ -v
```

## Code style

- Use **type hints** on all public functions.
- Add **docstrings** (NumPy/SciPy style) to every public function and class.
- Keep functions focused; prefer small composable units over large monoliths.
- Use `from __future__ import annotations` at the top of every module.
- Validate inputs with explicit `ValueError` messages — never fail silently.

## Adding a new feature

1. Implement the feature in a new or existing module under `orbital/`.
2. Export the public API from `orbital/__init__.py`.
3. Add at least one test in `tests/test_<feature>.py`.
4. Update `README.md` with usage examples.
5. Run `pytest tests/ -v` and `python3 demo.py` — both must pass.
6. Commit with a descriptive message: `Add <feature>: <description>`.

## Pull request checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Smoke tests pass (`python3 demo.py`)
- [ ] Type hints added
- [ ] Docstrings written
- [ ] README updated if needed

## Reporting bugs

Open an issue with:
1. A minimal reproducer (Python code).
2. Expected vs actual output.
3. Python version and NumPy version.