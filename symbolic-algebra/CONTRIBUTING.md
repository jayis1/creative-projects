# Contributing to Symbolic CAS

Thank you for your interest in contributing! This project welcomes contributions of all kinds.

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b my-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest tests/test_symbolic.py -v`
6. Submit a pull request

## Development Setup

```bash
# Clone and install in development mode
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/symbolic-algebra
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run the pytest suite
pytest tests/test_symbolic.py -v

# Run the legacy test suite
python3 tests.py

# Run with coverage
pytest tests/test_symbolic.py --cov=symbolic_cas
```

## Code Style

- Follow PEP 8
- Use type hints on all public functions
- Add docstrings to all public functions and classes
- Keep the single-file `symbolic.py` in sync with the package when making bug fixes

## Adding New Features

1. **New expression types**: Add a new class in `expr.py` inheriting from `Expr`, then add handling in all relevant modules (parser, simplify, evaluate, etc.)

2. **New functions**: Add the function name to `Func.KNOWN_FUNCS` in `expr.py`, then add evaluation and differentiation rules in `evaluate.py` and `calculus.py`

3. **New simplification rules**: Add rules to `_simplify_once()` in `simplify.py`

4. **New CLI commands**: Add the command to `cli.py`

## Bug Reports

When filing a bug report, please include:

1. The expression or command that caused the error
2. The expected result
3. The actual result
4. Python version

## License

By contributing, you agree that your contributions will be licensed under the MIT License.