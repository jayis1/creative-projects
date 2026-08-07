# Contributing to logicmin

Thank you for your interest in contributing to **logicmin**! This document
describes how to set up the development environment and the conventions to
follow.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/logic-minimizer

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run a single test class
pytest tests/test_new_features.py::TestBDD -v
```

## Project Structure

```
logic-minimizer/
├── logicmin/
│   ├── __init__.py        # Public API exports
│   ├── boolean.py         # Core: BooleanFunction, TruthTable, Implicant
│   ├── quine_mccluskey.py # Exact QM minimizer
│   ├── petrick.py         # Petrick's method for cyclic cover
│   ├── espresso.py        # Heuristic Espresso minimizer
│   ├── multi_output.py    # Multi-output minimization
│   ├── pos.py             # POS minimization (De Morgan)
│   ├── factorizer.py      # Multi-level algebraic factorization
│   ├── kmap.py            # Karnaugh map rendering (ASCII)
│   ├── bdd.py             # ROBDD construction, ITE, SOP extraction
│   ├── analysis.py        # Sensitivity, boolean difference, unate analysis
│   ├── pla.py             # PLA format reader/writer
│   ├── dc_optimize.py     # Don't-care assignment optimization
│   ├── htmlviz.py         # HTML visualization (truth tables, K-maps, reports)
│   ├── batch.py           # Batch processing of multiple functions
│   ├── serialize.py       # JSON serialization
│   ├── benchmark.py       # QM vs Espresso benchmarking
│   ├── config.py          # JSON/TOML/YAML config system
│   ├── parser.py          # Input format parsers
│   ├── exceptions.py      # Custom exception hierarchy
│   ├── logging_config.py  # Structured logging
│   └── cli.py             # CLI (19 subcommands)
├── tests/
│   ├── test_bug_hunt.py   # Original 34 tests
│   └── test_new_features.py  # 59 tests for new features
├── examples/
│   └── ...                 # Usage examples
├── pyproject.toml
└── README.md
```

## Coding Conventions

- **Type hints**: All new code must have type hints.
- **Docstrings**: All public functions/classes must have docstrings (Google style).
- **Tests**: All new features must have tests.  Run `pytest tests/ -v` before
  committing.
- **Pure stdlib**: No third-party dependencies (except pytest for testing).
- **Error handling**: Use the custom exception hierarchy from `exceptions.py`.
- **CLI**: New features with a user interface should add a CLI subcommand.

## Adding a New Minimizer

1. Create a new module in `logicmin/` (e.g., `logicmin/my_minimizer.py`).
2. Implement a class with a `minimize(func: BooleanFunction) -> MinimizationResult`
   method.
3. Export it from `logicmin/__init__.py`.
4. Add a CLI subcommand in `logicmin/cli.py`.
5. Add tests in `tests/test_new_features.py`.
6. Update the README with usage examples.

## Pull Request Process

1. Ensure all tests pass: `pytest tests/ -v`
2. Add tests for any new features.
3. Update the README if needed.
4. Keep the commit message format: `Add <feature>: <description>`

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.