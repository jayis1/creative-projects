# Contributing to the Turing Machine Simulator

Thank you for your interest in contributing! This document covers the
development workflow and conventions.

## Getting Started

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/turing-machine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Development Workflow

1. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/my-new-machine
   ```

2. **Write code** following the existing style:
   - Use type hints on all public functions
   - Add docstrings to all classes and public methods
   - Keep functions focused — prefer small composable units
   - Follow the existing file/module organization

3. **Write tests** for new features:
   - Place test files in `tests/` with the `test_*.py` naming convention
   - Aim for meaningful coverage of edge cases, not just happy paths
   - Run tests locally: `pytest tests/ -v`

4. **Update documentation**:
   - Update the README if you add features or change the API
   - Add example files to `examples/` for new machine definitions

5. **Commit with clear messages**:
   ```bash
   git commit -m "Add binary multiplier machine with carry propagation"
   ```

## Code Style

- **Python version**: 3.10+ (uses `from __future__ import annotations`)
- **Type hints**: required on all public APIs
- **Docstrings**: Google style for modules, classes, and functions
- **Line length**: keep lines under ~100 characters
- **Imports**: standard library → third-party → local (alphabetical within groups)
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes

## Adding a New Built-in Machine

1. Add a factory function in `turing_machine/machines.py`:
   ```python
   def my_machine() -> Program:
       """Description of what the machine does."""
       rules = [
           Transition("s0", "0", "0", R, "s0"),
           # ...
       ]
       return Program(rules)
   ```

2. Register it in the `MACHINES` dict at the bottom of `machines.py`.

3. Add CLI metadata in `cli.py` (`INITIAL_STATES` and `MACHINE_BLANKS`).

4. Write tests in `tests/test_machines.py`.

5. Add an example `.tm` definition file in `examples/`.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=turing_machine --cov-report=term-missing

# Run a single test file
pytest tests/test_machines.py -v

# Run a single test class
pytest tests/test_machines.py::TestBinaryIncrementer -v
```

## CLI Smoke Tests

After making changes, verify the CLI works:

```bash
python -m turing_machine.cli list
python -m turing_machine.cli run binary_incrementer --input 1011
python -m turing_machine.cli check 101
python -m turing_machine.cli analyze binary_incrementer --input 1011
python -m turing_machine.cli visualize binary_incrementer --input 1011 --format text
```

## Reporting Issues

When reporting a bug, please include:
- Python version
- Steps to reproduce
- Expected vs actual behavior
- The machine definition (if applicable)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.