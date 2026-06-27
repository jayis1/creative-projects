# Contributing to delaunay-voronoi

Thank you for your interest in contributing! This document outlines the
process for contributing to the delaunay-voronoi computational geometry
toolkit.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/creative-projects.git
   cd creative-projects/delaunay-voronoi
   ```
3. **Set up** a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

## Development Workflow

1. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes**. Follow the existing code style:
   - Use `from __future__ import annotations` at the top of every module.
   - Add type hints to all public functions.
   - Write docstrings for all public classes and functions.
   - Keep the stdlib-only constraint — no required external dependencies.

3. **Write tests** for your changes. Tests live in `tests/` and use pytest:
   ```bash
   python3 -m pytest tests/ -v
   ```

4. **Run the examples** to make sure nothing broke:
   ```bash
   python3 examples/generate_diagram.py
   python3 examples/mesh_quality_report.py
   ```

5. **Commit** with a clear message:
   ```bash
   git commit -m "Add <feature>: <description>"
   ```

6. **Push** and open a pull request.

## Code Style

- **Python ≥ 3.10**: use modern syntax (`match`, `|` unions, etc.).
- **No required external dependencies**: the core toolkit must work with
  only the Python standard library. Optional dependencies (e.g. `pyyaml`)
  go in `[project.optional-dependencies]` in `pyproject.toml`.
- **Type hints**: all public functions should have complete type annotations.
- **Docstrings**: use triple-quoted docstrings with a summary line and
  parameter/return descriptions.
- **Tests**: every new feature or bugfix should include test coverage.

## Project Structure

```
delaunay-voronoi/
├── delaunay_voronoi/       # Main package
│   ├── geometry.py         # Core primitives & predicates
│   ├── delaunay.py         # Bowyer-Watson triangulation
│   ├── voronoi.py          # Voronoi dual construction
│   ├── convex_hull.py      # Monotone-chain hull
│   ├── lloyd.py            # Lloyd relaxation
│   ├── refine.py           # Ruppert's refinement
│   ├── spatial.py          # Walking-based spatial queries
│   ├── spatial_hash.py     # Grid-based spatial index
│   ├── polygon.py          # Polygon utilities
│   ├── render.py           # SVG + PPM rendering
│   ├── animate.py          # Animated SVG
│   ├── serialize.py        # JSON serialization
│   ├── metrics.py          # Mesh quality metrics
│   ├── exporters.py        # OBJ, STL, PNG, boundary extraction
│   ├── config.py           # Configuration management
│   ├── logging_utils.py    # Structured logging
│   └── cli.py              # Command-line interface
├── examples/               # Usage demos
├── tests/                  # Test suite (pytest)
├── pyproject.toml          # Package metadata
└── README.md
```

## Reporting Bugs

Open a GitHub issue with:
- A clear title and description.
- A minimal reproducible example.
- The expected vs actual behaviour.
- Your Python version and OS.

## License

By contributing, you agree that your contributions will be licensed under
the MIT License.

## Questions?

Feel free to open an issue with the `question` label.