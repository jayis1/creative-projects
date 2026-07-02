# Contributing to btreestore

Thank you for your interest in contributing to btreestore! This document outlines the process for contributing to the project.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/btree-store

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=btreestore --cov-report=term-missing
```

## Project Structure

```
btree-store/
├── btreestore/           # Main package
│   ├── __init__.py       # Public API
│   ├── store.py          # Store class (main entry point)
│   ├── tree.py           # B+Tree implementation
│   ├── transaction.py    # Transaction (MVCC)
│   ├── cursor.py         # Cursor iterator
│   ├── pages.py          # Page types and serialization
│   ├── wal.py            # Write-Ahead Log
│   ├── config.py         # Configuration management
│   └── logging_util.py   # Logging setup
├── tests/                # Test suite
├── examples/             # Usage examples
├── btreestore_cli.py     # CLI tool
├── pyproject.toml        # Package configuration
└── README.md             # Documentation
```

## Coding Standards

1. **Type hints**: All public functions should have type annotations.
2. **Docstrings**: All public classes and functions should have docstrings.
3. **Tests**: New features must include tests. Bug fixes should include regression tests.
4. **Error handling**: Use specific exception types with informative messages.
5. **No external dependencies**: The core library must remain dependency-free (except for optional TOML support on Python < 3.11).

## Pull Request Process

1. Fork the repository and create a feature branch.
2. Write tests for your changes.
3. Ensure all tests pass: `pytest tests/ -v`
4. Update the README if you've added new features.
5. Submit a pull request with a clear description of your changes.

## Reporting Bugs

Please include:
- Python version
- Operating system
- Minimal reproduction code
- Expected vs actual behavior
- Error traceback (if applicable)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.