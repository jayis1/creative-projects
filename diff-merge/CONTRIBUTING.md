# Contributing to diff-merge

Thank you for your interest in improving **diff-merge**! This document
describes how to set up a development environment and submit changes.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/diff-merge

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# (Optional) Install test dependencies
pip install pytest
```

## Running Tests

```bash
# Run the full test suite (116 tests)
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_improvements.py -v

# Run with coverage
python3 -m pytest tests/ --cov=diff_merge --cov-report=term-missing
```

## Code Style

- Use **type hints** on all public functions.
- Add **docstrings** to all public classes and functions (triple-quoted).
- Follow **PEP 8** (line length ≤ 100 characters).
- Use `from __future__ import annotations` at the top of each module.
- Keep the **stdlib-only** constraint — no external runtime dependencies.

## Adding a New Feature

1. Create a new module in `diff_merge/` (or extend an existing one).
2. Add exports to `diff_merge/__init__.py`.
3. Write comprehensive tests in `tests/`.
4. If the feature has CLI exposure, add a subcommand in `cli.py`.
5. Update this README and the `Architecture` section.
6. Run `python3 -m pytest tests/` to ensure everything passes.

## Adding a New Diff Algorithm

1. Create `diff_merge/<algorithm>.py`.
2. Implement a function that takes `(a, b) -> List[DiffOp]`.
3. Register it in `format.py`'s algorithm dispatch and in `cli.py`'s
   `_get_diff_fn`.
4. Add tests comparing output with the existing algorithms on
   identical inputs (they should produce equivalent diffs).

## Bug Reports

Include:
- Minimal reproduction code
- Expected vs actual output
- Python version and OS

## Pull Requests

- Keep changes focused — one feature or fix per PR.
- Ensure all tests pass: `python3 -m pytest tests/`
- Add tests for any new functionality.
- Update the README if user-visible behaviour changes.

## License

By contributing, you agree your contributions are licensed under the MIT
License.