# Contributing to MCTS Engine

Thank you for your interest in contributing! This document outlines the
process for contributing to the MCTS Engine project.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/mcts-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode with test dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_mcts.py -v

# Run with coverage
python -m pytest tests/ --cov=mcts --cov-report=term-missing
```

## Code Style

- Follow PEP 8 (enforced via the linter in the development workflow).
- Use type hints on all public functions and methods.
- Add docstrings to all classes, methods, and module-level functions.
- Keep functions focused — if a function exceeds ~50 lines, consider
  refactoring into smaller helpers.

## Adding a New Game

1. Create a new class in `mcts/games.py` that inherits from `GameState`
   (or `GridGame` for grid-based games).
2. Implement all abstract methods: `current_player()`, `legal_moves()`,
   `apply()`, `winner()`, `is_terminal()`, `hash_key()`, `display()`.
3. If using `GridGame` with custom attributes, override
   `_copy_extra_attrs()` to ensure attributes survive `apply()`.
4. Add a heuristic function in `mcts/heuristics.py` and register it in
   the `HEURISTICS` dict.
5. Add the game to the `GAMES` dict in `mcts/cli.py`.
6. Write tests in `tests/test_mcts.py`.

## Adding a New Selection Policy

1. Create a new class inheriting from `SelectionPolicy` in `mcts/uct.py`.
2. Implement `select_child()` and the `name` property.
3. Add tests demonstrating the policy works with the engine.

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`.
2. Make your changes, ensuring all tests pass.
3. Add tests for any new functionality.
4. Update the README if you've added user-facing features.
5. Commit with a clear message: `Add feature: description`.
6. Push and open a pull request.

## Reporting Bugs

When reporting a bug, please include:
- Python version and OS
- Steps to reproduce
- Expected vs. actual behavior
- A minimal code example