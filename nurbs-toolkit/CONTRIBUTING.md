# Contributing to NURBS Toolkit

Thank you for your interest in contributing! This document outlines the process for contributing to the NURBS Toolkit project.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/your-username/creative-projects.git
   cd creative-projects/nurbs-toolkit
   ```
3. **Install** in development mode:
   ```bash
   pip install -e ".[dev]"
   ```
4. **Run tests** to verify everything works:
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

1. Create a branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes, following the code style guidelines below.
3. Add or update tests for your changes.
4. Run the full test suite:
   ```bash
   python -m pytest tests/ -v --tb=short
   ```
5. Run example scripts to verify nothing broke:
   ```bash
   python examples/circle.py
   python examples/curvature_analysis.py
   ```
6. Commit with a clear message:
   ```bash
   git commit -m "Add feature: description"
   ```
7. Push and create a pull request.

## Code Style

- **Python 3.10+**: Use `from __future__ import annotations` for forward references.
- **Type hints**: Add type hints to all public functions.
- **Docstrings**: Use NumPy-style docstrings for all public APIs.
- **Pure stdlib**: No external runtime dependencies (optional: pyyaml for YAML config).
- **Testing**: Every new feature or bug fix should include tests.
- **Error handling**: Use the custom exception hierarchy (`NURBSError` subclasses).

## Architecture

The toolkit is organized into focused modules:

```
nurbs/
├── bspline.py          # Core B-spline basis & curve
├── nurbs_curve.py      # Rational B-spline curves
├── nurbs_surface.py    # Tensor-product surfaces
├── bezier.py           # Bezier curves
├── operations.py       # Knot insertion, degree elevation, decomposition
├── fitting.py          # Curve fitting (least-squares)
├── surface_fitting.py  # Surface fitting
├── projection.py       # Point projection, arc length
├── curvature.py        # Curvature, torsion, inflections
├── offset.py           # Offset, reverse, split, concatenate
├── trimming.py         # Intersection, trimming loops
├── presets.py          # Circle, sphere, torus, cylinder, cone
├── export.py           # OBJ, PLY export
├── stl_export.py       # STL export (ASCII & binary)
├── svg_render.py       # SVG rendering
├── serialization.py    # JSON serialization
├── config.py           # Configuration management
├── logging_utils.py    # Logging utilities
├── exceptions.py       # Exception hierarchy
└── cli.py              # Command-line interface
```

## Reporting Bugs

When reporting a bug, please include:
- Python version
- Minimal reproduction code
- Expected vs actual output
- Any error messages/tracebacks

## License

All contributions are licensed under the MIT License.