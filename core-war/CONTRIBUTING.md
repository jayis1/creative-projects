# Contributing to Core War

Thank you for your interest in contributing to the Core War MARS simulator! This document outlines the process for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/creative-projects.git
   cd creative-projects/core-war
   ```
3. **Set up a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   pip install pyyaml
   ```
4. **Run the tests** to verify everything works:
   ```bash
   python3 -m pytest tests/ -v
   ```

## Development Workflow

### Code Style

- Follow PEP 8 conventions
- Use type hints for all function signatures
- Add docstrings to all public functions and classes
- Keep lines under 100 characters
- Use `from __future__ import annotations` for forward references

### Testing

- All new features must include tests
- Run tests before committing:
  ```bash
  python3 -m pytest tests/ -v --tb=short
  ```
- Aim for >80% test coverage on new code
- Test both success and error cases

### Adding a New Feature

1. **Create a branch**: `git checkout -b feature/my-feature`
2. **Write the code** with proper type hints and docstrings
3. **Write tests** in `tests/test_new_modules.py` (or a new test file)
4. **Update the README** if the feature is user-facing
5. **Run all tests**: `python3 -m pytest tests/ -v`
6. **Commit**: `git commit -m "Add my-feature: description"`
7. **Push and create a PR**

### Adding a New Warrior

1. Write a `.red` file in the `warriors/` directory
2. Test it with the CLI:
   ```bash
   python3 -m core_war.cli validate warriors/my-warrior.red
   python3 -m core_war.cli analyze warriors/my-warrior.red
   python3 -m core_war.cli --rounds 5 battle warriors/my-warrior.red warriors/dwarf.red
   ```
3. Add the warrior to the README's warrior table

### Adding a New Opcode or Addressing Mode

1. Add the enum value in `core_war/opcodes.py`
2. Update `OPCODE_NAMES` or address mode mappings
3. Update `DEFAULT_MODIFIERS` if adding an opcode
4. Implement execution in `core_war/mars.py` `_execute_instruction`
5. Update the parser if needed
6. Add tests for the new opcode/mode
7. Update the disassembler and visualizer

## Architecture Overview

```
core_war/
├── opcodes.py          # Opcode, Modifier, AddressMode enums
├── instruction.py      # Instruction dataclass (core memory cell)
├── parser.py           # Redcode source parser
├── mars.py             # MARS virtual machine (execution engine)
├── scheduler.py        # Battle scheduler (multi-round, tournaments)
├── disassembler.py     # Instruction → Redcode text
├── visualizer.py       # Core memory visualization
├── loader.py           # Warrior file loading
├── config.py           # Configuration management (YAML/JSON)
├── logging_config.py   # Structured logging setup
├── strategy_analyzer.py # Warrior strategy analysis
├── replay.py           # Battle recording and replay
├── mutator.py          # Genetic algorithm for warrior evolution
└── cli.py              # Command-line interface (9 subcommands)
```

## Pull Request Process

1. Ensure all tests pass
2. Update the README.md with details of changes if needed
3. Update the root project README table if adding a new project
4. The PR will be reviewed before merging

## Reporting Bugs

Use the GitHub Issues tab to report bugs. Include:
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/tracebacks

## License

By contributing, you agree that your contributions will be licensed under the MIT License.