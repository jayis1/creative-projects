# Contributing to KenKen Solver

Thank you for your interest in improving the KenKen Solver! This document
describes how to set up a development environment and the conventions we
follow.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- `pip` (or `uv` / `pipx`)

### Installation (development)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/kenken-solver

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running the tests

```bash
# Run all tests with pytest
pytest

# Run with coverage report
pytest --cov=kenken_solver --cov-report=term-missing

# Run a specific test file
pytest tests/test_kenken.py
```

### Running the CLI

```bash
# After installation
kenken generate --size 5

# Or directly via the module
python3 -m kenken_solver.cli generate --size 5

# Or via the legacy shim
python3 kenken.py generate --size 5
```

## Project Architecture

The codebase is organised into a modular package (`kenken_solver/`):

```
kenken_solver/
├── __init__.py     — public API re-exports
├── types.py        — shared type aliases & coordinate helpers
├── cage.py         — Cage class (cells, operator, target, evaluation)
├── puzzle.py       — KenKenPuzzle (immutable puzzle representation, validation, serialization)
├── solver.py       — KenKenSolver (backtracking with constraint propagation, MRV, hints)
├── generator.py    — KenKenGenerator (Latin squares, cage partitioning, operator selection, uniqueness verification)
├── analyzer.py     — PuzzleAnalyzer (difficulty scoring, solver complexity metrics)
├── render.py       — ASCII rendering functions
├── config.py       — GenerationConfig (JSON/YAML config file support)
└── cli.py          — argparse-based command-line interface
```

## Coding Conventions

1. **Type hints** — all public functions and methods must have complete type
   annotations.

2. **Docstrings** — use Google-style docstrings for all public API:
   ```python
   def foo(x: int, y: int) -> int:
       """Add two numbers.

       Parameters
       ----------
       x : int
           The first number.
       y : int
           The second number.

       Returns
       -------
       int
           The sum.
       """
   ```

3. **Error handling** — raise `ValueError` for invalid inputs with a clear
   message.  Never return silently on error.

4. **Logging** — use the `logging` module, not `print`, in library code.
   Reserve `print` for the CLI output.

5. **Tests** — every new feature or bug fix must include tests.  Place tests
   in the `tests/` directory following the `test_*.py` naming convention.

## How to Contribute

1. **Fork the repository** and create a feature branch.

2. **Make your changes** following the conventions above.

3. **Run the tests** and ensure they all pass:
   ```bash
   pytest
   ```

4. **Add tests** for any new functionality.

5. **Update the README.md** if your change adds user-facing features.

6. **Commit** with a descriptive message:
   ```bash
   git commit -m "Add support for N×N KenKen puzzles with modulo operator"
   ```

7. **Submit a pull request**.

## Reporting Bugs

Please open an issue on GitHub with:

- A clear description of the bug
- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the
MIT License (see `LICENSE`).