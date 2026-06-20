# Contributing to datalog-engine

Thank you for your interest in contributing! This document covers the
basics of getting started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/datalog-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
# Full pytest suite
pytest tests/ -v

# Legacy test scripts (smoke, enhanced, bug-hunt)
python test_smoke.py
python test_enhanced.py
python test_bug_hunt.py

# With coverage
pytest tests/ --cov=datalog --cov-report=term-missing
```

## Code Style

- Use type hints on all public functions.
- Add docstrings to all classes and public methods.
- Keep functions focused — if a function exceeds ~50 lines, consider
  splitting it.
- Use `from __future__ import annotations` at the top of every module.
- Follow the existing module structure:
  - `ast.py` — AST nodes (Term, Variable, Constant, Atom, Literal, Rule, Fact, Query, Program)
  - `parser.py` — Lexer + recursive-descent parser
  - `builtins.py` — Built-in predicate definitions and evaluators
  - `relation.py` — Relation storage with hash indexing
  - `stratification.py` — SCC computation and stratification
  - `evaluation.py` — Body evaluation (joins, built-in dispatch)
  - `aggregation.py` — Aggregate rule evaluation
  - `engine.py` — Engine class (coordinates all the above)
  - `config.py` — Configuration file loading (JSON/TOML/YAML)
  - `output.py` — Output formatting (binding/table/json/csv)
  - `errors.py` — Exception hierarchy
  - `cli.py` — CLI and REPL

## Adding a New Built-in

1. Add the predicate to the appropriate table in `builtins.py`
   (`BUILTIN_BINARY`, `BUILTIN_ARITH`, `BUILTIN_STRING`,
   `BUILTIN_TYPECHECK`, or `BUILTIN_AGGREG`).
2. If it binds variables, ensure the safety checker in `ast.py` handles
   it (the `is_safe` method already handles 2-arg and 3-arg binding
   builtins generically).
3. Add tests in `tests/test_datalog.py`.

## Adding a New Output Format

1. Add the format to `output.py`'s `format_results` function.
2. Add the format name to the CLI's `--format` choices in `cli.py`.
3. Add tests.

## Pull Request Process

1. Ensure all tests pass: `pytest tests/ -v`
2. Add tests for any new features.
3. Update the README if you add user-facing features.
4. Keep commits focused and write clear commit messages.