# Contributing to earley-parser

Thank you for your interest in contributing! This document outlines the
process for contributing to the project.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/earley-parser

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest -v
```

## Code Style

- Follow PEP 8 conventions.
- Use type hints on all public functions.
- Add docstrings to all public classes and functions.
- Keep functions focused — prefer small, composable functions over large ones.
- Use `from __future__ import annotations` at the top of each module.

## Testing

- All new features must include tests in the `tests/` directory.
- Run the full test suite before submitting:
  ```bash
  pytest -v --tb=short
  ```
- Aim for >90% coverage of new code.

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes, including tests and documentation.
3. Ensure all tests pass.
4. Update the README if you've added user-facing features.
5. Write a clear commit message describing what and why.

## Project Structure

```
earley-parser/
├── earley_parser/       # Main package
│   ├── __init__.py      # Public API exports
│   ├── grammar.py       # Grammar, GrammarLoader
│   ├── parser.py        # EarleyParser, Chart, Item, ParseNode
│   ├── tokenizer.py     # Tokenizer, TokenSpec
│   ├── errors.py        # ParseError and related exceptions
│   ├── cyk.py           # CYK parser (alternative algorithm)
│   ├── analysis.py      # LL(1) analysis, FOLLOW sets, ambiguity detection
│   ├── config.py        # Configuration management
│   └── cli.py           # Command-line interface
├── tests/               # Test suite
├── examples/            # Example grammar files and scripts
├── docs/                # Documentation
├── pyproject.toml       # Package metadata
└── README.md
```

## Reporting Bugs

Use the GitHub Issues tab. Include:
- A minimal reproducer
- Expected vs actual behavior
- Python version and OS