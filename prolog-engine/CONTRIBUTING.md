# Contributing to mini-Prolog Engine

Thank you for your interest in contributing! This guide covers how to set up
the development environment, run tests, and submit changes.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/prolog-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=prolog_engine --cov-report=term-missing

# Run a specific test file
python3 -m pytest tests/test_engine.py -v
```

## Project Structure

```
prolog-engine/
├── prolog_engine/          # Main package
│   ├── __init__.py         # Public API & exports
│   ├── ast_nodes.py        # AST node definitions
│   ├── lexer.py            # Tokenizer
│   ├── parser.py           # Recursive-descent parser
│   ├── unifier.py          # Robinson's unification
│   ├── engine.py           # SLD-resolution engine
│   ├── builtins.py         # ~60 built-in predicates
│   ├── cli.py              # Interactive REPL & CLI
│   ├── config.py           # Configuration management
│   ├── errors.py           # Exception hierarchy
│   └── logging_setup.py    # Logging configuration
├── tests/
│   ├── test_engine.py      # Core engine tests
│   ├── test_bugs.py        # Bug-specific regression tests
│   └── test_improvements.py # New feature tests
├── examples/               # Example Prolog programs
├── .github/workflows/      # CI configuration
├── pyproject.toml           # Package metadata
├── README.md                # This file
├── LICENSE                  # MIT License
└── CONTRIBUTING.md          # This file
```

## Coding Standards

- **Python 3.11+** minimum version
- **Type hints** on all public functions
- **Docstrings** on all public classes and functions
- **Tests** for any new features or bug fixes
- Follow the existing code style (100-char line length)

## Adding New Built-in Predicates

1. Add the predicate function to `builtins.py` with a docstring
2. Register it in `register_builtins()`
3. Add tests in `tests/test_improvements.py`
4. Update the README's predicate table

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## Reporting Bugs

Please open a GitHub issue with:
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Any relevant error messages