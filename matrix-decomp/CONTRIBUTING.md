# Contributing to matrix-decomp

Thank you for your interest in improving **matrix-decomp**! This is a
from-scratch linear algebra library written in pure Python with no
third-party dependencies (no NumPy, no SciPy). We welcome contributions of
all kinds: bug reports, new algorithms, test coverage, documentation, and
performance improvements.

## Getting Started

1. **Clone** the repo and navigate to the `matrix-decomp` subfolder:

   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/matrix-decomp
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install in editable mode** with test dependencies:

   ```bash
   pip install -e .
   pip install pytest
   ```

4. **Run the test suite**:

   ```bash
   python -m pytest tests/ -v
   ```

   All 170+ tests should pass. If any fail, please open an issue.

## Design Principles

- **No third-party dependencies.** Everything must run on the Python
  standard library alone. Do not add imports of NumPy, SciPy, pandas, etc.
- **Readable, educational code.** The goal is clarity over micro-optimization.
  Algorithms should match textbook notation as closely as possible.
- **Type hints.** All public functions should have type annotations.
- **Comprehensive tests.** Every new feature or bug fix should include
  tests that would fail without the change.
- **Single-purpose modules.** Each algorithm family lives in its own
  module (e.g., `lu.py`, `qr.py`, `svd.py`). If you add a new algorithm,
  create a new module rather than stuffing it into an existing one.

## Adding a New Algorithm

1. Create a new module `matrix_decomp/<your_algo>.py`.
2. Implement the algorithm with full type hints, a docstring explaining
   the math, and input validation.
3. Export the public API from `matrix_decomp/__init__.py`.
4. Write tests in `tests/test_<your_algo>.py`.
5. If the algorithm has a CLI use case, add a subcommand to `cli.py`.
6. Update the README with usage examples.
7. Run the full test suite and ensure everything passes.

## Code Style

- Use `from __future__ import annotations` at the top of every module.
- Prefer `float()` coercion of inputs over assuming a specific type.
- Raise `ValueError` with descriptive messages for invalid inputs.
- Raise `SingularMatrixError` (from `lu.py`) for numerical singularity.
- Keep functions under ~80 lines where possible; extract helpers.
- Use `math.sqrt` over `** 0.5` for clarity in numerical code.

## Running Tests

```bash
# Full suite
python -m pytest tests/ -v

# A specific module
python -m pytest tests/test_iterative.py -v

# With coverage (if installed)
python -m pytest tests/ --cov=matrix_decomp --cov-report=term-missing
```

## Reporting Bugs

Please open a GitHub issue with:

1. A minimal reproduction (input matrix + function call).
2. The expected vs. actual output.
3. The Python version and OS.
4. The full traceback if an exception is raised.

## License

By contributing, you agree that your contributions will be licensed under
the MIT License (see `LICENSE`).