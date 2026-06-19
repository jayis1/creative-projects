# Contributing to petri-net-sim

Thank you for your interest in contributing! This document outlines the process for contributing to the Petri net simulator and analysis toolkit.

## Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jayis1/creative-projects
   cd creative-projects/petri-net-sim
   ```

2. **Set up a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   pip install pyyaml  # optional, for YAML config support
   ```

3. **Run the tests**:
   ```bash
   python -m pytest --tb=short -v
   ```

4. **Try the CLI**:
   ```bash
   python -m petri.cli presets
   python -m petri.cli --preset workflow show
   ```

## Development Guidelines

### Code Style

- Use **type hints** on all public functions and methods.
- Write **docstrings** for all public classes and functions (Google or NumPy style).
- Keep functions focused — one function, one responsibility.
- Aim for **zero external dependencies** in the core package (YAML support is optional).

### Testing

- Every new feature or bug fix must include tests.
- Tests live in the `tests/` directory, named `test_*.py`.
- Run tests before committing:
  ```bash
  python -m pytest --tb=short -v --cov=petri
  ```
- Aim for >90% coverage on new code.

### Adding New Presets

To add a new preset net:

1. Add a function in `petri/presets.py` that builds and returns a `PetriNet`.
2. Register it in the `PRESETS` dict in `petri/cli.py`.
3. Add a test in `tests/test_new_features.py` verifying the net structure.

### Adding New Analysis Features

1. Implement the analysis function in `petri/analysis.py` (or a new module).
2. Add a dataclass for the result type.
3. Export it from `petri/__init__.py`.
4. Add a CLI subcommand if applicable.
5. Write tests.
6. Update the README.

### Adding New CLI Commands

1. Write a `cmd_<name>` function in `petri/cli.py`.
2. Add a subparser in `build_parser()`.
3. Test with `python -m petri.cli <command> --help`.

### Commit Messages

Follow conventional commits:

- `feat: add stochastic Petri net support`
- `fix: correct coverability tree re-expansion`
- `docs: update README with colored net examples`
- `test: add batch simulation tests`

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes, following the guidelines above.
3. Ensure all tests pass.
4. Update the README if needed.
5. Submit a pull request with a clear description.

## Architecture

The package is organized into focused modules:

```
petri/
├── net.py          # Core model: PetriNet, Place, Transition, Arc
├── simulator.py    # Token game simulation
├── analysis.py    # Reachability, invariants, boundedness, liveness
├── stochastic.py  # SPN, CTMC, steady-state, Monte Carlo
├── colored.py     # Colored Petri nets (typed tokens)
├── batch.py        # Batch simulation with statistics
├── config.py      # JSON/YAML config file support
├── pnml.py         # PNML (ISO/IEC 15909-2) import/export
├── presets.py     # Pre-built example nets
├── visualizer.py   # ASCII and DOT visualization
├── logging_util.py # Structured logging
└── cli.py          # Command-line interface
```

## License

MIT — see [LICENSE](LICENSE).