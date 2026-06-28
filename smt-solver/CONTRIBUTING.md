# Contributing to SMT Solver

Thank you for your interest in contributing! This document describes how to set up
your development environment and submit changes.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/jayis1/creative-projects
cd creative-projects/smt-solver

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with test dependencies
pip install -e ".[test]"

# Run the test suite
python3 -m pytest tests/ -v
```

## Code Style

- Use Python 3.9+ features (type hints, dataclasses, f-strings)
- Follow PEP 8 with 4-space indentation
- Add type hints to all public functions
- Write docstrings for all classes and public methods
- Keep functions focused and modular

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run a specific test class
python3 -m pytest tests/test_solver.py::TestLRA -v

# Run with coverage
pip install pytest-cov
python3 -m pytest tests/ --cov=smt_solver --cov-report=term-missing
```

## Adding a New Theory

1. Create `smt_solver/theory_<name>.py` with a theory class
2. Implement `assert_atom()`, `assert_negation()`, `check()` methods
3. Add theory detection in `solver.py` (`_is_<name>_atom()`)
4. Add routing in `_check_theory()`
5. Add tests in `tests/test_solver.py`
6. Update the README with the new theory

## Adding Examples

1. Create a `.smt2` file in `examples/`
2. Add a comment with `; expected: sat` or `; expected: unsat`
3. Update the examples table in README.md

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Ensure all tests pass (`python3 -m pytest tests/ -v`)
5. Commit with a clear message
6. Push and open a Pull Request

## Reporting Bugs

Please include:
- A minimal SMT-LIB input that reproduces the issue
- Expected vs actual output
- Python version and OS