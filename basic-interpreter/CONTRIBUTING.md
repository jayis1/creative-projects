# Contributing to BASIC Interpreter

Thank you for your interest in contributing! This document provides guidelines for contributing to the BASIC Interpreter project.

## How to Contribute

1. **Fork** the repository
2. **Create a branch** for your feature or fix: `git checkout -b my-feature`
3. **Make your changes** and add tests
4. **Run the test suite**: `pytest tests/ -v`
5. **Commit** with a clear message: `git commit -m "Add feature X"`
6. **Push** and open a **Pull Request**

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/basic-interpreter

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Code Style

- Follow PEP 8 for Python code
- Use type hints for function signatures
- Add docstrings to all public methods and classes
- Keep the monolithic `basic.py` in sync with the package version during development

## Adding New Features

When adding a new BASIC feature:

1. Add the token type to `lexer.py`
2. Add the AST node to `ast_nodes.py`
3. Add the parsing logic to `parser.py`
4. Add the execution logic to `interpreter.py`
5. Add tests in `tests/test_core.py`
6. Add an example in `examples/` if applicable
7. Update the README

## Reporting Bugs

Please open an issue with:
- The BASIC program that triggers the bug
- The expected output
- The actual output
- The Python version you're using

## Testing

Run the full test suite:

```bash
pytest tests/ -v
```

Run a specific test file:

```bash
pytest tests/test_core.py -v -k "test_for_next"
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.