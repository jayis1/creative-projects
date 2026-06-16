# Contributing to RISC-V Emulator

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork** the repository and clone your fork
2. **Install** the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```
3. **Run tests** to make sure everything works:
   ```bash
   pytest tests/ -v
   ```

## Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Add tests for any new functionality
4. Ensure all tests pass: `pytest tests/ -v`
5. Commit with a descriptive message
6. Push and create a Pull Request

## Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Add docstrings to all public functions and classes
- Keep lines under 100 characters
- Use `python3` (not `python`) for any Python scripts

## Adding New Features

### New Instructions

1. Add the instruction to `cpu.py` in the `_execute` method
2. Add assembler support in `assembler.py` (if applicable)
3. Add disassembler support in `disassembler.py`
4. Add tests in `tests/test_emulator.py`

### New MMIO Devices

1. Create a class inheriting from `MMIODevice` in `devices.py`
2. Implement `read()`, `write()`, `tick()`, and `reset()` methods
3. Add tests in `tests/test_new_features.py`
4. Document the device in the README

### New CLI Commands

1. Add the command handler in `cli.py`
2. Add the argparse subparser configuration
3. Add tests
4. Update the README with usage examples

## Testing

- All new code must have corresponding tests
- Run the full test suite before submitting a PR:
  ```bash
  pytest tests/ -v --tb=short
  ```
- Aim for >90% coverage on new code

## Reporting Bugs

- Open an issue with a clear title and description
- Include: Python version, OS, steps to reproduce, expected vs actual behavior
- If possible, include a minimal test case

## Pull Request Process

1. Ensure all tests pass
2. Update the README if you've added features
3. Update the version in `__init__.py` and `pyproject.toml` if appropriate
4. Add a changelog entry
5. One approval required before merging