# Contributing to EvOpt

Thank you for your interest in contributing to EvOpt! This document outlines
the process for contributing bug reports, feature requests, and code changes.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/creative-projects.git
   cd creative-projects/evolutionary-optimizer
   ```
3. **Install** in development mode:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e . pytest numpy pyyaml
   ```
4. **Run tests** to verify everything works:
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

### Code Style

- Follow the existing code style (PEP 8 with some leniency).
- Use type hints for all function signatures.
- Add docstrings to all public functions, classes, and modules.
- Keep lines under 100 characters where possible.
- Use `from __future__ import annotations` for forward compatibility.

### Adding a New Algorithm

1. Create `evopt/algorithms/<algorithm_name>.py`.
2. Subclass `BaseAlgorithm` and implement:
   - `initialize()` — create the initial population.
   - `evolve_one_generation()` — run one step of the algorithm.
   - Override `update_best()` if the algorithm tracks best differently.
3. Add the algorithm to `evopt/algorithms/__init__.py`.
4. Add the algorithm to `evopt/__init__.py` and `__all__`.
5. Register it in `evopt/config.py` (`_ALGORITHM_REGISTRY`).
6. Add it to the CLI in `evopt/cli.py` (`ALGORITHMS` list and `create_algorithm`).
7. Write tests in `tests/test_new_features.py` or a new test file.
8. Add an example in `examples/`.

### Adding a New Problem

1. Create `evopt/problems/<problem_name>.py`.
2. Subclass `Problem`, `ContinuousProblem`, `CombinatorialProblem`, or
   `MultiObjectiveProblem`.
3. Implement `evaluate()` and `random_genome()`.
4. Add to `evopt/problems/__init__.py` and `evopt/__init__.py`.
5. Register in `evopt/config.py` and the CLI.
6. Write tests verifying the known global optimum.

### Adding a New Operator

1. Add the function to the appropriate file in `evopt/operators/`.
2. Add to `evopt/operators/__init__.py` and `evopt/__init__.py`.
3. Write tests verifying correctness (e.g., permutation validity).

### Writing Tests

- Place tests in `tests/` with descriptive names.
- Use pytest fixtures for common setup.
- Test both correctness and edge cases (empty inputs, boundary conditions).
- Ensure all tests pass before submitting:
  ```bash
  python -m pytest tests/ -v --tb=short
  ```

### Committing

- Use clear, descriptive commit messages.
- Reference issues in commit messages where applicable.
- One logical change per commit when possible.

## Pull Request Process

1. Ensure all tests pass.
2. Update the README.md if you've added new features.
3. Add yourself to the contributors list if you'd like.
4. Submit a PR with a clear description of what and why.

## Reporting Bugs

When reporting a bug, please include:

- Python version and OS.
- Minimal code to reproduce the issue.
- Expected and actual output.
- Full traceback if an exception occurred.

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.