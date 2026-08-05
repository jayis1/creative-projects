# Contributing to the TDA Toolkit

Thank you for your interest in contributing! This document outlines the
process for contributing to the Topological Data Analysis toolkit.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/creative-projects.git
   cd creative-projects/topological-data-analysis
   ```
3. **Install** in editable mode:
   ```bash
   pip install -e .
   ```
4. **Run** the test suite to verify everything works:
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

### Code Style

- Follow PEP 8 (use `flake8` or `ruff` to check).
- Use type hints for all function signatures.
- Add docstrings (Google or NumPy style) for all public functions and classes.
- Keep line length ≤ 100 characters.

### Testing

- All new features must include tests in `tests/`.
- Run the full test suite before committing:
  ```bash
  python -m pytest tests/ -v --tb=short
  ```
- Aim for > 90% coverage on new code.
- Test both edge cases (empty input, single element, degenerate geometry)
  and typical use cases.

### Adding a New Module

1. Create the module file in `tda/` (e.g. `tda/new_feature.py`).
2. Add imports and `__all__` entries in `tda/__init__.py`.
3. Write comprehensive tests in `tests/test_new_features.py`.
4. Add an example script in `examples/`.
5. Update the README.md with documentation.
6. Update `pyproject.toml` if new dependencies are needed.

### Adding a CLI Subcommand

1. Implement the command function `cmd_<name>(args)` in `tda/cli.py`.
2. Add a subparser in `build_parser()`.
3. Test with the existing CLI test framework.
4. Document in the README.md CLI section.

### Commit Messages

Follow the conventional commit format:

- `Add <feature>: <description>` — new features
- `Enhance <feature>: <description>` — improvements
- `Fix <module>: <description>` — bug fixes
- `Docs: <description>` — documentation changes
- `Test: <description>` — test additions/fixes

### Pull Requests

1. Create a feature branch: `git checkout -b feature/my-feature`.
2. Make your changes, ensuring all tests pass.
3. Add new tests for any new functionality.
4. Update the README.md if needed.
5. Submit a pull request with a clear description of the changes.

## Architecture

The toolkit is organized into these layers:

```
┌───────────────────────────────────────────────┐
│  CLI (cli.py)                                  │
├───────────────────────────────────────────────┤
│  Config / Logging / Exceptions                  │
├───────────────────────────────────────────────┤
│  Batch / Kernels / Statistics                   │
├───────────────────────────────────────────────┤
│  Distance / Wasserstein / Curves / Images       │
├───────────────────────────────────────────────┤
│  Diagram / Matrix (persistence computation)     │
├───────────────────────────────────────────────┤
│  Complexes (Rips, Cech, Alpha, Sublevel)       │
├───────────────────────────────────────────────┤
│  Simplex / SimplexTree (data structures)        │
└───────────────────────────────────────────────┘
```

When adding a new complex type, implement the `build() -> SimplexTree`
interface. When adding a new distance metric, accept `PersistenceDiagram`
objects and return a float.

## Roadmap

- [ ] Delaunay triangulation for efficient alpha complexes
- [ ] Zigzag persistence
- [ ] Multipersistence (2-parameter persistence)
- [ ] GPU-accelerated boundary matrix reduction
- [ ] SVG/Matplotlib plot export (optional dependency)
- [ ] Integration with scikit-learn transformers

## Questions?

Open an issue on GitHub with the `question` label.