# Contributing to bplus-db

Thank you for your interest in contributing to bplus-db! This document provides guidelines for contributing.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/bplus-db
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## How to Contribute

### Bug Reports

- Open an issue with a clear description of the bug
- Include steps to reproduce, expected behavior, and actual behavior
- Specify your Python version and OS

### Feature Requests

- Open an issue with the prefix `[Feature]`
- Describe the use case and proposed API

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes with tests
4. Ensure all tests pass (`pytest tests/ -v`)
5. Add documentation if applicable
6. Submit a pull request

## Code Style

- Follow PEP 8
- Use type hints for public APIs
- Add docstrings to all public methods and classes
- Keep functions focused and small

## Testing

- All new features must include tests
- Bug fixes must include regression tests
- Run the full test suite before submitting:
  ```bash
  pytest tests/ -v
  ```

## Commit Messages

- Use imperative mood ("Add feature" not "Added feature")
- Keep the first line under 72 characters
- Reference issues when applicable

## Architecture

```
bplus_db/
├── __init__.py       # Package exports
├── bplus_tree.py     # Core B+ tree (insert, delete, search, range, bulk load)
├── database.py       # Database layer (CRUD, transactions, WAL, TTL, cache)
├── serializer.py     # Type-aware value serialization
├── query_parser.py   # SQL-like query tokenizer and parser
├── cache.py          # LRU read cache
├── config.py         # Configuration management (dataclasses + JSON/TOML)
├── cursor.py         # Cursor-based pagination
├── ttl.py            # Key-level TTL/expiration manager
├── io.py             # Import/export (CSV, JSONL, Pickle)
└── cli.py            # Interactive shell and CLI
```

## Release Process

1. Update `__version__` in `__init__.py` and `pyproject.toml`
2. Update the CHANGELOG section in README.md
3. Run all tests
4. Commit and push