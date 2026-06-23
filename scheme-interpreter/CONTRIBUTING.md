# Contributing to scheme-interpreter

Thank you for your interest in contributing! This document outlines how to get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/scheme-interpreter

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_scheme.py -v
pytest tests/test_v2.py -v
```

## Architecture Overview

The interpreter is organized into these modules:

- `lexer.py` — Tokenizes Scheme source code
- `parser.py` — Recursive-descent parser producing s-expressions
- `types.py` — Core Scheme data types (Symbol, Pair, Nil, Bool, etc.)
- `environment.py` — Lexical scope chain for variable lookup
- `interpreter.py` — Tail-call-optimized evaluator with trampoline
- `primitives.py` — 150+ built-in procedures
- `macro_expander.py` — Hygienic syntax-rules macro system
- `repl.py` — Interactive read-eval-print loop
- `cli.py` — Command-line interface with argparse
- `stdlib.scm` — Standard library (auto-loaded on startup)

## How to Add a New Primitive

1. Open `scheme_interpreter/primitives.py`
2. Add a function inside `install_primitives()`
3. Register it with `reg("name", function)`

```python
def _my_primitive(x, y):
    """My new primitive."""
    return _num(x) + _num(y)

reg("my-primitive", _my_primitive)
```

## How to Add a New Special Form

1. Open `scheme_interpreter/interpreter.py`
2. Write a `_sf_<name>(interp, expr, env)` function
3. Add it to the `SPECIAL_FORMS` dispatch table

```python
def _sf_my_form(interp, expr, env):
    """My new special form."""
    # expr is the full (my-form args...) Pair
    return interp.seval(expr.cdr.car, env)

Interpreter.SPECIAL_FORMS["my-form"] = _sf_my_form
```

## Coding Standards

- Add type hints to all new Python code
- Write docstrings for all public functions and classes
- Add tests for all new features
- Ensure all tests pass before submitting: `pytest tests/ -v`
- Follow the existing code style (4-space indent, line length ~100)

## Reporting Bugs

When reporting a bug, please include:
1. The Scheme code that triggers the bug
2. The expected output
3. The actual output (including traceback)
4. Your Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.