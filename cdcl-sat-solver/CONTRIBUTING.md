# Contributing to CDCL SAT Solver

Thank you for your interest in contributing! This document provides guidelines for contributing to the CDCL SAT Solver project.

## Getting Started

1. **Fork & Clone**: Fork the repository and clone your fork locally.
2. **Install for Development**:
   ```bash
   cd cdcl-sat-solver
   python -m pip install -e ".[dev]"
   ```
3. **Run Tests**:
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes with tests
3. Ensure all tests pass: `python -m pytest tests/ -v`
4. Commit with a descriptive message
5. Push and create a pull request

## Code Style

- **Python 3.9+**: Use modern Python features
- **Type hints**: Add type hints to all new functions and methods
- **Docstrings**: Use Google-style docstrings for all public functions
- **Line length**: Keep lines under 100 characters
- **Imports**: Use absolute imports from `cdcl_sat` package

## Adding Features

- New solving heuristics go in `solver.py`
- New CNF generators go in `generator.py`
- New utilities go in `utils.py`
- Configuration options go in `config.py`
- CLI commands go in `cli.py`
- Tests go in `tests/test_solver.py`

## Reporting Bugs

When filing a bug report, please include:

1. Python version (`python --version`)
2. The DIMACS input or code that triggers the bug
3. Expected vs actual behavior
4. Full error traceback if applicable

## Performance Benchmarking

The solver includes benchmark instances for testing performance:

```bash
# Generate a pigeonhole instance
cdcl-sat generate --type php --n 5 --m 4 -o test.cnf

# Solve it with timing
cdcl-sat solve test.cnf -v 1

# Solve with statistics output
cdcl-sat solve test.cnf --stats-json stats.json
```