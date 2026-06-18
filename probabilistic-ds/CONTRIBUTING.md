# Contributing to Probabilistic Data Structures Toolkit

Thank you for your interest in contributing! This document describes the
process for contributing to the `probabilistic-ds` toolkit.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects
cd creative-projects/probabilistic-ds

# Install in development mode with all extras
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v
```

## Code Style

- Follow the existing style: 4-space indentation, line length ≤ 100 chars.
- Every public class and function must have a docstring with:
  - A one-line summary
  - Parameters section (if applicable)
  - Examples section (for main structures)
- Use type hints (`from __future__ import annotations` at the top).
- Add `# comments` for tricky algorithms or non-obvious logic.

## Adding a New Data Structure

1. Create a new module `pds/<name>.py` with the implementation.
2. Export it in `pds/__init__.py` and add to `__all__`.
3. Add serialization support in `pds/serialization.py` (if the structure has
   meaningful state).
4. Register it in the config system (`pds/config.py` — `_STRUCTURE_REGISTRY`
   and `_PARAM_SPECS`).
5. Add benchmark support in `pds/benchmark.py`.
6. Add CLI support in `cli.py` (save/load subcommands).
7. Write comprehensive tests in `tests/test_new_structures.py`.
8. Update the README.md with the new structure.

## Testing

- All tests use `pytest`.
- Each structure must have tests for: construction, basic operations,
  edge cases, serialization roundtrip, and merge (if applicable).
- Run tests with: `python -m pytest tests/ -v`
- Aim for >90% coverage of new code.

## Pull Requests

1. Create a feature branch: `git checkout -b feature/new-structure`
2. Make your changes and commit with clear messages.
3. Ensure all tests pass: `python -m pytest tests/`
4. Push and create a pull request.

## Bug Reports

When reporting a bug, include:
- Python version and OS
- Minimal reproduction code
- Expected vs actual behavior
- The specific data structure involved