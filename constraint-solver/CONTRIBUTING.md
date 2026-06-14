# Contributing to CSP Solver

Thank you for your interest in contributing to the CSP Solver project! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/constraint-solver
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   ```

3. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## Code Style

- Follow PEP 8 conventions
- Use type hints for all function signatures
- Write docstrings for all public functions and classes (Google style)
- Maximum line length: 100 characters
- Use `__slots__` for performance-critical classes

## Project Structure

```
constraint-solver/
├── csp_solver/           # Main package
│   ├── __init__.py       # Public API exports
│   ├── csp.py            # Core data structures (Variable, Constraint, CSP)
│   ├── ac3.py            # AC-3 algorithm
│   ├── backtrack.py      # Backtracking solver with heuristics
│   ├── solver.py         # High-level solver interface
│   ├── problems.py       # Built-in problem generators
│   ├── problems_extra.py # Additional problem generators
│   ├── cli.py            # Command-line interface
│   ├── config.py         # Configuration management
│   ├── logging_utils.py  # Logging and progress tracking
│   ├── visualization.py  # Pretty rendering
│   └── serialization.py  # JSON export/import
├── tests/
│   ├── test_solver.py    # Core test suite
│   └── test_bug_hunt.py  # Bug regression tests
├── examples/             # Usage examples
├── pyproject.toml        # Package configuration
├── CONTRIBUTING.md       # This file
└── README.md             # Project documentation
```

## Adding a New Problem Generator

1. Create your generator function in `problems.py` or `problems_extra.py`
2. Follow the pattern: create CSP, add variables and constraints, return CSP
3. Add a `format_*` function for rendering
4. Export it from `__init__.py`
5. Add tests in `tests/test_solver.py`
6. Add CLI support in `cli.py`
7. Update README.md

## Adding Tests

- All tests use `pytest`
- Place tests in the `tests/` directory
- Test file naming: `test_*.py`
- Use descriptive test class/method names
- Include edge cases and error conditions
- Aim for >90% coverage on new code

## Commit Messages

Use clear, descriptive commit messages:
- `Add job shop scheduling problem generator`
- `Fix AC-3 empty domain detection`
- `Improve README with architecture section`

## Reporting Bugs

When reporting a bug, please include:
1. Python version
2. Minimal reproduction code
3. Expected vs actual behavior
4. Any error traceback

## License

By contributing, you agree that your contributions will be licensed under the MIT License.