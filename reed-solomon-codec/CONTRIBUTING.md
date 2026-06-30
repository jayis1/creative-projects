# Contributing to reed-solomon-codec

Thank you for your interest in contributing! This document describes the
development workflow and conventions.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects
cd creative-projects/reed-solomon-codec

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode with test dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Full test suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=reed_solomon --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_rs_codec.py -v

# Run a specific test class
python -m pytest tests/test_rs_codec.py::TestErrorCorrection -v
```

## Project Structure

```
reed-solomon-codec/
├── reed_solomon/          # Main package
│   ├── __init__.py        # Public API exports
│   ├── __main__.py        # python -m reed_solomon entry point
│   ├── gf.py              # GF(2^8) arithmetic & polynomial ops
│   ├── codec.py           # RS encoder, decoder, interleaving, RSCode class
│   ├── config.py          # Configuration system (JSON/YAML/TOML)
│   └── cli.py             # argparse CLI (9 subcommands)
├── tests/                 # pytest test suite
│   ├── test_rs_codec.py   # Core codec tests (78 tests)
│   ├── test_bug_hunt.py   # Bug regression tests (11 tests)
│   ├── test_config.py     # Config system tests
│   └── test_cli.py        # CLI tests
├── examples/              # Usage examples
│   ├── basic_encode_decode.py
│   ├── erasure_correction.py
│   ├── burst_error.py
│   ├── file_protection.py
│   └── config_example.py
├── .github/workflows/     # CI configuration
├── pyproject.toml         # Package metadata & build config
├── gf.py                  # Backward-compat shim → reed_solomon.gf
├── rs_codec.py            # Backward-compat shim → reed_solomon.codec
├── cli.py                 # Backward-compat CLI shim → reed_solomon.cli
└── README.md
```

## Coding Conventions

1. **Type hints**: All public functions and methods must have type hints.
2. **Docstrings**: Use Google-style docstrings for all public APIs.
3. **Tests**: Every new feature or bug fix must include tests.
4. **Imports**: Use absolute imports (`from reed_solomon.codec import ...`).
5. **Error handling**: Validate inputs early with clear error messages.

## Pull Request Checklist

- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] New features have tests
- [ ] README.md is updated if needed
- [ ] Code has type hints and docstrings
- [ ] No external dependencies added (keep it stdlib-only for core)

## Reporting Bugs

Please include:
1. Python version
2. Minimal reproduction code
3. Expected vs actual output
4. Full error traceback