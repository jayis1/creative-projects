# Contributing to tsp-solver

Thank you for your interest in contributing to **tsp-solver**! This document
outlines the process for submitting improvements, bug fixes, and new
algorithms.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Adding a New Algorithm](#adding-a-new-algorithm)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)

## Getting Started

1. **Clone the repo:**
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/tsp-solver
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   pip install pyyaml pytest
   ```

3. **Verify the test suite passes:**
   ```bash
   pytest test_suite.py -v
   ```

## Development Workflow

1. Create a branch for your feature/fix:
   ```bash
   git checkout -b feature/my-new-algorithm
   ```

2. Make your changes, ensuring all tests pass.
3. Add tests for any new functionality.
4. Commit with a clear message:
   ```bash
   git commit -m "Add LKH algorithm with candidate lists"
   ```
5. Push and open a pull request.

## Adding a New Algorithm

To add a new TSP algorithm:

1. **Implement** the algorithm in a new module or an existing one. The
   function signature must be:
   ```python
   def my_algorithm(instance: TSPInstance, **kwargs) -> Tour:
       ...
       return Tour(order, cost)
   ```

2. **Register** it in `tsp_solver/solver.py`:
   ```python
   from .my_module import my_algorithm
   _ALGORITHMS["my_algorithm"] = my_algorithm
   ```

3. **Categorize** it in the `_ALGORITHM_CATEGORIES` dict.

4. **Export** it in `tsp_solver/__init__.py`.

5. **Add tests** in `test_suite.py`:
   - Validity: produces a valid permutation
   - Non-worsening: doesn't increase tour length (for local search)
   - Correctness: matches known optimal for small instances (for exact)

6. **Update the README** with the new algorithm.

## Testing

We use `pytest`. Run the full suite:

```bash
pytest test_suite.py -v
```

Run a specific test class or test:

```bash
pytest test_suite.py -v -k "TestExactAlgorithms"
pytest test_suite.py -v -k "test_held_karp_optimal"
```

### Test Categories

- **Unit tests**: Instance creation, Tour operations, Config loading
- **Algorithm tests**: Validity, non-worsening, optimality (for exact)
- **Integration tests**: Solver dispatcher, benchmark, CLI
- **Edge case tests**: n=2, n=3, empty inputs

## Code Style

- Use **type hints** throughout (Python 3.9+ syntax).
- Follow **PEP 8** (line length 100).
- Add **docstrings** to all public functions and classes (Google style).
- Use `from __future__ import annotations` for forward references.
- Prefer **pure Python + NumPy** — no heavy external dependencies.
- Add **logging** via `from .logging_util import get_logger; log = get_logger(__name__)`.

## Pull Request Process

1. Ensure all tests pass: `pytest test_suite.py -v`
2. Update the README if you've added features.
3. Add an entry to the changelog section.
4. Request review from a maintainer.