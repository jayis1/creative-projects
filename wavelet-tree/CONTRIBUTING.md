# Contributing to Wavelet Tree

Thank you for your interest in contributing! This document outlines the
process for contributing to the wavelet tree succinct data structure library.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/your-username/creative-projects.git
   cd creative-projects/wavelet-tree
   ```
3. **Set up** a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e . pytest
   ```
4. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/my-feature
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_wavelet_tree.py -v

# Run with coverage
python -m pytest tests/ --cov=wavelet_tree --cov-report=html
```

### Code Style

- Follow PEP 8 conventions
- Use type hints (`from __future__ import annotations` for forward refs)
- Add docstrings to all public functions, classes, and methods
- Keep functions focused — if a function exceeds ~50 lines, consider refactoring
- Use descriptive variable names (avoid single letters except for loop counters)

### Adding New Features

1. **Wavelet structure variants**: Inherit from `WaveletBase` and implement
   `access`, `rank`, `select`, `__len__`, and the `alphabet` property.
   The base class provides `__iter__`, `__getitem__`, `__contains__`, `count`,
   `index`, `positions`, `to_list`, `__eq__`, and `__hash__` for free.

2. **New query types**: Add functions to `queries.py`. Queries should work
   with any `WaveletBase` implementation. Add tests to `test_new_queries.py`.

3. **New BitVector implementations**: Inherit from `BitVector` and override
   `rank1` and `select1`. The base `rank0`, `select0`, `count1`, `count0`
   will work automatically. Add tests to `test_rrr_bitvector.py` or a new
   test file.

### Testing Guidelines

- Write tests for all new features and bug fixes
- Use parametrized tests with multiple sequences (including edge cases:
  empty, single-symbol, all-same, all-distinct)
- Test both `use_blocked=True` and `use_blocked=False` for structures
- Add random tests with fixed seeds for thorough coverage
- Ensure all tests pass before submitting a PR:
  ```bash
  python -m pytest tests/ -q
  ```

### CI

GitHub Actions runs tests on Python 3.10–3.13. Ensure your changes work on
all supported versions. The CI config is in `.github/workflows/ci.yml`.

## Pull Request Process

1. Ensure all tests pass
2. Update the README.md if you add new features
3. Add a changelog entry in the "Recent Improvements" section
4. Write a clear PR description explaining what and why

## License

By contributing, you agree that your contributions will be licensed under
the MIT License.