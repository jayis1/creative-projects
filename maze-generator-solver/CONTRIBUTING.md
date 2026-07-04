# Contributing to maze-generator-solver

Thank you for your interest in contributing! This document outlines the
process for contributing to the maze-generator-solver project.

## Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/maze-generator-solver
   ```

2. **Set up a virtual environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install pytest pyyaml
   ```

3. **Run the existing tests** to make sure everything works:
   ```bash
   python3 -m pytest test_maze.py test_maze_v2.py -v
   ```

## Code Style

- Follow PEP 8 conventions.
- Use type hints on all public functions.
- Add docstrings to all public classes and functions (Google style).
- Keep lines under 100 characters.
- Add comments explaining non-obvious algorithm steps.

## Adding a New Generation Algorithm

1. Add the implementation to `maze_solver/generators.py`.
2. Add the algorithm name to `GENERATOR_NAMES` in the same file.
3. Add a dispatch method `_gen_<name>` to the `Maze` class in
   `maze_solver/core.py` and register it in `GENERATORS`.
4. Add tests in `test_maze_v2.py` (the parametrized generator tests
   will automatically pick it up from `GENERATOR_NAMES`).
5. Update the README.md table.

## Adding a New Solving Algorithm

1. Add the implementation to `maze_solver/solvers.py`.
2. Add the algorithm name to `SOLVER_NAMES`.
3. Add a dispatch method `_solve_<name>` to the `Maze` class and
   register it in `SOLVERS`.
4. Add tests in `test_maze_v2.py`.
5. Update the README.md table.

## Adding a New Renderer

1. Add the implementation to `maze_solver/renderers.py`.
2. Add a convenience method to the `Maze` class (e.g. `to_<format>`).
3. Add tests.
4. Update the README.md.

## Testing

- All new features must include tests.
- Run the full test suite before submitting:
  ```bash
  python3 -m pytest test_maze.py test_maze_v2.py -v
  ```
- Ensure tests pass on Python 3.10, 3.11, and 3.12.

## Commit Messages

Use clear, descriptive commit messages:
- `Add <feature>: <brief description>`
- `Fix <component>: <what was fixed>`
- `Enhance <component>: <what was improved>`
- `Document <component>: <what was documented>`

## Pull Requests

1. Create a feature branch from `main`.
2. Make your changes with appropriate tests.
3. Ensure all tests pass.
4. Submit a pull request with a clear description of what was changed
   and why.