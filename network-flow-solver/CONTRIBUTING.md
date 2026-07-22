# Contributing to Network Flow Solver

Thank you for your interest in contributing! This document outlines the
process for contributing to the network-flow-solver project.

## Getting Started

1. **Fork** the repository and clone your fork.
2. **Install** in development mode:
   ```bash
   cd network-flow-solver
   pip install -e .
   pip install pytest pytest-cov
   ```
3. **Run tests** to verify everything works:
   ```bash
   python -m pytest tests/ -v
   ```

## Development Guidelines

### Code Style

- Follow PEP 8 (use `ruff` or `flake8` to check).
- Use type hints on all public functions.
- Add docstrings to all classes and public methods (Google style preferred).
- Keep functions focused — if a function exceeds ~50 lines, consider refactoring.

### Testing

- Every new feature must include tests in `tests/`.
- Bug fixes must include a regression test.
- Aim for >90% test coverage on new code.
- Run `python -m pytest tests/ --cov=networkflow --cov-report=term-missing`.

### Algorithm Implementation

When adding a new algorithm:

1. Implement it as a class with a `solve(network, source, sink)` method.
2. Include a `MaxFlowSolver`-compatible interface (or appropriate protocol).
3. Add it to the `SOLVERS` dict in `cli.py` if it's a max-flow variant.
4. Export it from `networkflow/__init__.py`.
5. Add at least 3 test cases: simple path, no path, complex network.
6. Verify it produces the same result as existing solvers on random networks.
7. Document its time complexity in the README's algorithm reference table.

### I/O Format Support

When adding a new graph format:

1. Implement `read_<format>()` and `write_<format>()` functions.
2. Add them to `networkflow/io_formats.py`.
3. Export from `__init__.py`.
4. Add auto-detection to `cli.py:load_network()`.
5. Test roundtrip: write then read should preserve structure.

### Commit Messages

Use clear, descriptive commit messages:

- `Add <feature>: <brief description>`
- `Fix <bug>: <what was wrong and how>`
- `Enhance <module>: <what improved>`
- `Test <module>: <what's now covered>`

### Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`.
2. Make your changes, add tests.
3. Ensure all tests pass: `python -m pytest tests/ -v`.
4. Run the smoke test: `python smoke_test_new.py`.
5. Update the README if you added new features.
6. Submit a pull request with a clear description.

## Project Structure

```
network-flow-solver/
├── networkflow/
│   ├── __init__.py        # Package exports
│   ├── graph.py           # FlowNetwork, FlowEdge data structures
│   ├── maxflow.py         # Ford-Fulkerson, Edmonds-Karp, Dinic, Push-Relabel, Capacity Scaling
│   ├── advanced.py        # Boykov-Kolmogorov, Multi-Source/Sink, Cycle Canceling
│   ├── mincost.py         # Min-Cost Max-Flow, Min-Cost Fixed Flow
│   ├── matching.py        # Bipartite matching (Hopcroft-Karp), Assignment (Hungarian)
│   ├── mincut.py          # Min-Cut (duality), Stoer-Wagner
│   ├── connectivity.py    # Disjoint paths, edge connectivity, Gomory-Hu tree
│   ├── benchmark.py       # Network generators, solver comparison
│   ├── dimacs.py          # DIMACS format I/O
│   ├── io_formats.py      # Edge list, CSV, GraphML, LGF I/O
│   ├── visualization.py   # DOT, ASCII, flow decomposition
│   ├── config.py          # Configuration file support
│   ├── logging_config.py  # Structured logging
│   └── cli.py             # CLI with 14 subcommands
├── tests/
│   ├── test_all.py        # Original test suite (53 tests)
│   └── test_new_features.py  # New feature tests (32 tests)
├── examples/              # Usage demos (6 examples)
├── pyproject.toml
├── LICENSE
├── CONTRIBUTING.md
└── README.md
```

## Questions?

Open an issue on GitHub. We're happy to help!