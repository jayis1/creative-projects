# Contributing to mcengine

Thank you for your interest in contributing to **mcengine**! This document
describes how to set up the project, run tests, and submit changes.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/marching-cubes

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run the full test suite
pytest

# Run with coverage report
pytest --cov=mcengine --cov-report=term-missing

# Run a specific test file
pytest tests/test_marching_cubes.py -v
```

## Code Style

- **Type hints**: All public functions and methods should have type annotations.
- **Docstrings**: Use triple-quote docstrings with parameter descriptions for
  all public API functions.
- **Pure Python**: No external dependencies beyond the standard library.
  This is a core design constraint — do not add NumPy, scipy, or other deps.
- **Error handling**: Validate inputs at public API boundaries and raise
  `ValueError` or `TypeError` with descriptive messages.

## Adding a New Sampler

1. Create a class inheriting from `Sampler` in `mcengine/samplers.py`.
2. Implement `sample(self, x, y, z) -> float`.
3. Optionally override `gradient(self, x, y, z)` for Dual Contouring accuracy.
4. Register it in `SAMPLERS` dict in `mcengine/cli.py`.
5. Register it in `SAMPLER_CLASSES` in `mcengine/config.py`.
6. Add tests in `tests/test_samplers.py`.
7. Update the README's sampler list.

## Adding a New Export Format

1. Implement a `write_<format>(mesh, path)` function in `mcengine/export.py`.
2. Register it in `EXPORTERS` in `mcengine/cli.py` and `mcengine/batch.py`.
3. Add a reader in `mcengine/mesh_io.py` if applicable.
4. Add tests in `tests/test_export.py`.

## Submitting Changes

1. Create a feature branch: `git checkout -b my-feature`
2. Make your changes and add tests.
3. Ensure all tests pass: `pytest`
4. Commit with a descriptive message.
5. Push and open a pull request.

## Project Structure

```
mcengine/
├── __init__.py          # Public API exports
├── cli.py               # Command-line interface (argparse)
├── mesh.py              # Mesh dataclass, lerp, normals
├── vec3.py              # 3D vector math
├── tables.py            # MC lookup tables + cube topology
├── mc_triangle_table.json  # Verified 256-entry triangle table
├── samplers.py          # 12 implicit surface functions
├── volume_sampler.py    # Trilinear-interpolated volume data
├── marching_cubes.py    # MC algorithm (vertex sharing, asymptotic decider)
├── marching_tetrahedra.py  # MT algorithm (5-tetrahedra decomposition)
├── dual_contouring.py   # DC algorithm (QEF minimisation)
├── export.py            # OBJ/OFF/PLY/STL/glTF writers
├── mesh_io.py           # OBJ/OFF/PLY/STL readers
├── diagnostics.py       # Euler characteristic, watertightness, area
├── simplify.py          # Edge-collapse simplification
├── subdivision.py       # Loop subdivision
├── transforms.py        # Geometric transformations
├── ascii_preview.py     # ASCII art renderer
├── config.py            # JSON/TOML config + presets
├── batch.py             # Batch rendering engine
└── logging_util.py      # Logging utilities
```