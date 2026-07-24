# Contributing to kalman-estimator

Thank you for your interest in contributing! This document describes the
development workflow and guidelines.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/kalman-estimator

# Create a virtual environment
python3 -m venv .venv
source .venv/bin activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=kalman_estimator --cov-report=term-missing

# Run a specific test file
pytest tests/test_new_features.py -v
```

## Code Style

- **Type hints**: All public methods should have type annotations.
- **Docstrings**: Use NumPy-style docstrings for all public functions and classes.
- **Imports**: Use `from __future__ import annotations` for forward references.
- **Error handling**: Raise descriptive `ValueError` for invalid inputs. Never
  let raw `LinAlgError` propagate — catch and re-raise with context.
- **Numerical stability**: Use Joseph-form covariance updates. Symmetrize
  covariance matrices after updates: `P = (P + P.T) / 2`.

## Adding a New Filter

1. Create a new module `kalman_estimator/your_filter.py`.
2. Inherit from `BaseEstimator` and implement `predict()`, `update()`,
   `state`, and `covariance`.
3. Add the class to `kalman_estimator/__init__.py` and `__all__`.
4. Write comprehensive tests in `tests/test_your_filter.py`.
5. Add an example in `examples/`.
6. Update the README.

## CI

GitHub Actions runs all tests on Python 3.9–3.12 for every push/PR that
touches the `kalman-estimator/` directory. Ensure all tests pass locally
before pushing.

## Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] New features have tests
- [ ] Docstrings are complete
- [ ] Type hints are present
- [ ] README is updated if needed