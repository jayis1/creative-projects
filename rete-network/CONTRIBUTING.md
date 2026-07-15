# Contributing to Rete Network

Thank you for your interest in contributing to the Rete Network project! This document outlines the process for contributing code, reporting issues, and submitting improvements.

## Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/rete-network
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or: .venv\Scripts\activate  # Windows
   ```

3. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_core.py -v

# Run a specific test
python -m pytest tests/test_core.py::TestFact::test_fact_creation -v

# Run smoke tests
python smoke_test.py
python enhanced_test.py
```

### Code Style

- Follow PEP 8 with 4-space indentation.
- Use type hints on all public functions and methods.
- Add docstrings to all public classes, methods, and functions.
- Keep lines under 100 characters where possible.
- Use `from __future__ import annotations` at the top of modules for forward references.

### Adding a New Feature

1. **Write the implementation** in the appropriate module under `rete/`.
2. **Add tests** in `tests/test_<feature>.py`.
3. **Update the README** with documentation and examples.
4. **Run the full test suite** to ensure nothing is broken.
5. **Commit with a clear message**: `Add <feature>: <description>`.

### Adding a New Test

- Place test files in the `tests/` directory.
- Name files `test_<area>.py` (e.g., `test_negation.py`).
- Group tests in classes by feature area.
- Use descriptive test method names: `test_<scenario>_<expected_behavior>`.
- Use `pytest` fixtures for shared setup.

### Reporting Bugs

When reporting a bug, please include:

1. A minimal reproducible example.
2. The expected behavior vs. actual behavior.
3. Python version and OS.
4. The full error traceback (if applicable).

## Architecture Overview

The Rete engine consists of:

- **`rete/engine.py`** — Core engine, network nodes, conflict resolution, TMS.
- **`rete/serialization.py`** — JSON/YAML loading and saving.
- **`rete/cli.py`** — Command-line interface.
- **`rete/exceptions.py`** — Custom exception hierarchy.
- **`tests/`** — Comprehensive test suite organized by feature area.

### Rete Network Structure

```
Fact → Alpha net (one-input) → Join/Beta net (two-input) → Production nodes
       type + field tests       variable-binding joins       (rules → agenda)
```

## License

This project is licensed under the MIT License. By contributing, you agree that your contributions will be licensed under the same terms.