# Contributing to FM-Index

Thank you for your interest in contributing! This document covers the basics.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/fm-index

# Install in development mode
pip install -e .

# Install test dependencies
pip install pytest pytest-cov
```

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=fmindex --cov-report=term-missing

# Run a specific test module
python3 -m pytest tests/test_rle.py -v
```

## Running Examples

```bash
python3 examples/basic_usage.py
python3 examples/approx_wildcard.py
python3 examples/advanced_search.py
python3 examples/stats_and_viz.py
python3 examples/backend_and_config.py
```

## Code Style

- Use type hints on all public functions.
- Add docstrings to every public class and function.
- Keep functions focused — one responsibility per function.
- Follow the existing module organization (see "Module Layout" in the README).
- Run `python3 -m py_compile <file>` before committing to catch syntax errors.

## Adding a New Feature

1. **Create or extend a module** under `fmindex/`.
2. **Add tests** under `tests/` — aim for >90% coverage of new code.
3. **Update `__init__.py`** to export new public symbols.
4. **Update the CLI** (`cli.py`) if the feature has a command-line interface.
5. **Update `README.md`** with documentation and examples.
6. **Add an example script** under `examples/` if the feature is user-facing.
7. **Run all tests** and ensure they pass.

## Bug Reports

When filing a bug report, please include:
- The minimal text and pattern that reproduces the issue.
- The expected and actual output.
- The Python version and OS.
- The backend used (wavelet_tree or wavelet_matrix).

## Pull Requests

- Keep PRs focused — one feature or fix per PR.
- Include tests for any new functionality.
- Ensure all existing tests still pass.
- Update documentation as needed.

## Architecture Overview

```
fmindex/
├── suffix_array.py    # SA construction (prefix-doubling + naive)
├── bwt.py             # BWT encode/decode via LF-mapping
├── wavelet.py         # BitArray + balanced wavelet tree
├── wavelet_matrix.py  # Level-ordered wavelet matrix
├── index.py           # FMIndex: ties everything together
├── searchers.py       # High-level search (regex, MUMs, repeats)
├── rle.py             # Run-length encoding for BWT compression
├── serialize.py       # JSON + binary serialization
├── analysis.py        # Match clustering & coverage
├── text_stats.py      # Information-theoretic statistics
├── visualize.py       # ASCII visualizations
├── config.py          # YAML/JSON/TOML configuration
├── logging_utils.py   # Logging and timing
├── errors.py          # Exception hierarchy
└── cli.py             # Command-line interface (20 subcommands)
```

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.