# Contributing to typeinfer

Thank you for your interest in contributing to `typeinfer`! This document
outlines the development workflow and conventions.

## Getting Started

```bash
# Clone the repo
gh repo clone jayis1/creative-projects
cd creative-projects/typeinfer

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode
pip install -e .
pip install pytest
```

## Running Tests

```bash
# Run the full test suite
python -m pytest -v

# Run a specific test class
python -m pytest tests/test_features.py::TestMatch -v

# Run with coverage (if pytest-cov is installed)
python -m pytest --cov=typeinfer --cov-report=term-missing
```

## Code Style

- Use `from __future__ import annotations` at the top of every module.
- Follow PEP 8 with a line length of 100 characters.
- Add type hints to all public functions.
- Write docstrings for all public classes and functions.

## Adding New Features

### New AST Node
1. Add the dataclass in `parser.py`.
2. Add parsing logic in the `_Parser` class.
3. Add inference logic in `inference.py` (`_infer` function).
4. Add tests in `tests/test_features.py`.
5. Update the README.

### New Built-in Primitive
1. Add the type scheme in `primitives.py`.
2. Add tests in `tests/test_features.py`.
3. Update the README's primitive table.

### New Language Construct
1. Add lexer tokens if needed in `lexer.py`.
2. Add AST nodes in `parser.py`.
3. Add parsing logic.
4. Add inference logic in `inference.py`.
5. Add tests.
6. Add an example in `examples/`.
7. Update the README.

## Commit Messages

Follow the existing convention:
- `Add <feature>: <description>`
- `Enhance <feature>: <description>`
- `Fix <bug>: <description>`
- `Bug hunt <project>: fix N bugs, add tests`

## Pull Requests

1. Ensure all tests pass: `python -m pytest -v`
2. Ensure the CLI works: `python -m typeinfer --version`
3. Update the README if needed.
4. Add tests for any new functionality.

## License

By contributing, you agree that your contributions will be licensed under
the MIT License.