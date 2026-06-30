# Contributing to hmm-toolkit

Thank you for your interest in contributing! This document outlines the
process for contributing to the hmm-toolkit project.

## Getting Started

1. **Fork** the repository and clone your fork.
2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install in development mode:
   ```bash
   cd hmm-toolkit
   pip install -e ".[dev]"
   ```

## Development Workflow

1. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Write code** following the existing style:
   - Pure Python (stdlib only) for core functionality
   - Type hints on all public functions
   - Docstrings on all public classes and functions
   - Keep functions focused and modular

3. **Write tests** for any new functionality:
   - Place tests in `tests/test_*.py`
   - Use pytest fixtures for common HMM setups
   - Test both valid inputs and edge cases / error conditions

4. **Run tests**:
   ```bash
   python3 -m pytest tests/ -v
   ```

5. **Run examples** to verify nothing broke:
   ```bash
   PYTHONPATH=. python3 examples/dishonest_casino.py
   ```

6. **Commit** with a clear message:
   ```bash
   git commit -m "Add Gaussian HMM Baum-Welch convergence check"
   ```

## Code Style

- Follow PEP 8 (line length up to 100 characters)
- Use `from __future__ import annotations` for forward references
- Prefer composition over inheritance
- Document complex algorithms with references to the literature

## Adding New Features

### New Algorithm
1. Add the implementation in the appropriate module (`algorithms.py`, `analysis.py`, etc.)
2. Export it from `hmm/__init__.py`
3. Add a CLI subcommand if user-facing
4. Write tests in `tests/`
5. Update README.md

### New Example
1. Create `examples/<name>.py`
2. Include a docstring explaining the scenario
3. Make it runnable with `PYTHONPATH=. python3 examples/<name>.py`

## Reporting Bugs

Open an issue with:
- Python version
- Minimal reproduction code
- Expected vs actual output
- Full traceback if applicable

## Pull Requests

- Keep PRs focused — one feature or bugfix per PR
- Include tests
- Update documentation
- Ensure CI passes

## License

By contributing, you agree that your contributions are licensed under the MIT
license.