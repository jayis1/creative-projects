# Contributing to gc-simulator

Thank you for your interest in contributing to the GC Simulator! This document
outlines the process for contributing code, reporting bugs, and suggesting
improvements.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/gc-simulator

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run the full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=gc_sim

# Run only the enhancement tests
pytest tests/test_enhancements.py -v

# Run a specific test
pytest tests/test_gc_sim.py::TestMarkSweep -v
```

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) with a line length of 100
  characters.
- Use type hints on all public functions and methods.
- Write docstrings on all public classes and functions (Google/Sphinx style).
- Prefer `from __future__ import annotations` for forward references.
- Add `# pragma: no cover` to trivial `__repr__` methods.

## Adding a New Collector

1. Create a new class inheriting from `Collector` in `collectors.py`.
2. Implement the `collect()` method returning a `CollectionStats`.
3. Register the collector in the `_COLLECTORS` dict.
4. Add tests in `tests/test_gc_sim.py` or a new test file.
5. Update the README and `available_collectors()` list.
6. Ensure all tests pass: `pytest tests/ -v`.

## Adding a New Scenario

1. Add a `scenario_<name>()` method to `GCSimulator` in `simulator.py`.
2. Add the scenario name to the CLI `_run_scenario()` function in `cli.py`.
3. Add tests verifying the scenario creates the expected object graph.
4. Update the README with the new scenario.

## Adding a New Allocator

1. Create a new class inheriting from `Allocator` in `allocators.py`.
2. Implement `allocate()` and `reset()`.
3. Add the allocator to `GCSimulator.__init__()`.
4. Add tests.
5. Update the README.

## Reporting Bugs

When reporting a bug, please include:

1. Python version (`python3 --version`)
2. Steps to reproduce (minimal code snippet)
3. Expected vs. actual behavior
4. Full traceback if an exception occurred

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes, ensuring all tests pass.
3. Add tests for new functionality.
4. Update the README if needed.
5. Commit with a clear message: `Add feature: description` or `Fix: description`.
6. Submit a pull request.

## License

By contributing, you agree that your contributions will be licensed under the
MIT License that covers the entire project.