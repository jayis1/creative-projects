# Contributing to soft-rasterizer

Thank you for your interest in contributing! This document outlines the
process for contributing to the project.

## Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/soft-rasterizer
   ```

2. **Set up a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Run the tests**:
   ```bash
   pytest tests/ -v
   ```

## Code Style

- Follow PEP 8 conventions.
- Use type hints wherever possible.
- Add docstrings to all public functions and classes.
- Keep functions focused — if a function exceeds ~80 lines, consider splitting it.
- Use descriptive variable names (avoid single letters except in tight math loops).

## Adding a New Shader

1. Create the shader class in `soft_rasterizer/shaders.py` implementing the
   `Shader` protocol (`vertex()` and `fragment()` methods).
2. Add the shader to `__all__` and `__init__.py`.
3. Add the shader to the `SHADERS` dict in `cli.py`.
4. Add the shader to `_SHADER_FACTORIES` in `config.py`.
5. Write tests in `tests/test_rasterizer.py`.
6. Update the README with the new shader.

## Adding a New Primitive

1. Add the `make_*` function in `soft_rasterizer/primitives.py`.
2. Export it in `__init__.py` and `__all__`.
3. Add it to `PRIMITIVES` in `cli.py` and `_PRIMITIVES` in `config.py`.
4. Write tests in `tests/test_scene_config.py`.
5. Update the README.

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=soft_rasterizer --cov-report=term-missing

# Specific test file
pytest tests/test_math3d.py -v
```

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes, ensuring all tests pass.
3. Add tests for any new functionality.
4. Update documentation (README, docstrings).
5. Commit with a clear message following the existing style:
   `Add <feature>: <description>` or `Fix <bug>: <description>`
6. Push and open a pull request.

## Reporting Bugs

When reporting a bug, please include:
- Python version
- Operating system
- Minimal reproduction code
- Expected vs actual output
- Error traceback (if applicable)