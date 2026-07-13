# Contributing to lalr-parser-gen

Thank you for your interest in contributing! This document outlines the process
for contributing to the LALR(1) parser generator.

## Getting Started

1. **Fork** the repository and clone your fork.
2. **Set up a virtual environment**:
   ```bash
   cd lalr-parser-gen
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. **Run the tests** to make sure everything works:
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

1. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes**. Follow the existing code style:
   - Use `from __future__ import annotations` for forward references.
   - Add type hints to all public functions and methods.
   - Write docstrings for all public classes and functions.
   - Keep functions focused; split large functions into helpers.

3. **Add tests** for your changes:
   - Place test files in `tests/` with `test_*.py` naming.
   - Use pytest fixtures where appropriate.
   - Aim for full coverage of new code paths.

4. **Run the test suite**:
   ```bash
   python -m pytest tests/ -v --tb=short
   ```

5. **Run the examples** to make sure nothing breaks:
   ```bash
   python3 examples/calculator.py
   python3 examples/json_parser.py
   ```

6. **Update documentation**:
   - Update the README.md if you add features or change behavior.
   - Add new examples to the `examples/` directory for significant features.

7. **Commit and push**:
   ```bash
   git add -A
   git commit -m "Add feature: <description>"
   git push origin feature/my-new-feature
   ```

8. **Open a Pull Request** with a clear description of your changes.

## Code Style

- **Python version**: Target Python 3.9+.
- **Line length**: Keep lines under 100 characters where possible.
- **Imports**: Standard library first, then third-party, then local.
- **Type hints**: Use `typing` module types. Use `Optional[X]` for nullable.
- **Error handling**: Use custom exceptions (`ParseError`, `LexError`, etc.).
- **Logging**: Use the `logging` module, not `print()` (except in CLI/examples).

## Architecture

The project is organized into focused modules:

```
lalr/
├── grammar.py         # Grammar representation, FIRST/FOLLOW/nullable
├── table.py           # LR(0) automaton, LALR(1) lookahead, ACTION/GOTO tables
├── slr_table.py       # SLR(1) table for comparison
├── precedence.py      # Precedence/associativity for conflict resolution
├── parser.py          # LR parser driver with semantic actions
├── bnf_loader.py      # BNF grammar file parser
├── lexer.py           # Configurable regex-based lexer framework
├── error_recovery.py  # Panic-mode error recovery
├── transform.py       # Grammar transformations (left-recursion removal, etc.)
├── visualize.py       # Graphviz DOT visualization, HTML tables
├── config.py          # JSON configuration management
└── cli.py             # Command-line interface
```

When adding a new module, register it in `lalr/__init__.py` and add corresponding
tests.

## Testing Guidelines

- Write tests that exercise both the happy path and edge cases.
- For bug fixes, add a test that fails before the fix and passes after.
- Use descriptive test names: `test_<scenario>_<expected_behavior>`.
- Group related tests in classes.
- Avoid testing implementation details; test behavior.

## Reporting Issues

When reporting a bug, please include:
1. The grammar or input that triggers the bug.
2. The expected vs actual behavior.
3. The full error traceback if applicable.
4. The Python version and OS you're using.

## License

All contributions are licensed under the MIT License.