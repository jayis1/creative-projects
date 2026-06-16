# Contributing to CHIP-8 Emulator

Thank you for your interest in contributing! This document provides guidelines for contributing to the CHIP-8 emulator project.

## Getting Started

1. **Fork the repository** and clone your fork locally.
2. **Set up the development environment:**
   ```bash
   cd chip8-emulator
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev,yaml]"
   ```

3. **Run the test suite** to make sure everything works:
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear, focused commits.

3. **Write tests** for any new functionality. We aim for high test coverage.

4. **Run all tests** before pushing:
   ```bash
   python -m pytest tests/ -v
   ```

5. **Push and create a Pull Request** with a clear description of your changes.

## Code Style

- **Python 3.10+** — use modern type hints and f-strings.
- **Docstrings** — every public class, method, and function should have a docstring.
- **Type hints** — all function signatures should include type annotations.
- **Line length** — keep lines under 100 characters.
- **Imports** — use `from __future__ import annotations` for forward references.
- **Logging** — use `logging.getLogger(__name__)` rather than `print()` for diagnostic output.

## Project Structure

```
chip8-emulator/
├── chip8_emulator/          # Main package
│   ├── __init__.py          # Package exports
│   ├── cpu.py               # CPU core (fetch-decode-execute)
│   ├── memory.py            # 4 KiB address space
│   ├── display.py           # 64×32 pixel display
│   ├── keypad.py            # 16-key hex keypad
│   ├── timer.py              # Delay timer
│   ├── sound.py              # Sound timer
│   ├── opcodes.py            # Opcode dispatch table
│   ├── debugger.py           # Step-through debugger
│   ├── validator.py          # ROM validation
│   ├── assembler.py          # CHIP-8 assembler
│   ├── tracer.py             # Execution profiler
│   ├── recorder.py           # Trace record/replay
│   ├── config.py             # Configuration file support
│   ├── cli.py                # CLI interface
│   └── roms.py               # Built-in test ROMs
├── tests/                   # Test suite
│   ├── test_cpu.py
│   ├── test_memory.py
│   ├── test_display.py
│   ├── test_assembler.py
│   ├── test_tracer.py
│   ├── test_recorder.py
│   ├── test_config.py
│   └── ...
├── examples/                # Usage examples
├── .github/workflows/       # CI configuration
├── pyproject.toml           # Project metadata & build config
├── LICENSE                  # MIT license
├── CONTRIBUTING.md          # This file
└── README.md                # Project documentation
```

## Adding New Features

### New Opcodes
1. Add the handler method to `CPU` in `cpu.py`.
2. Register it in `OpcodeTable._build()` in `opcodes.py`.
3. Add disassembly support in `cli.py` (`_disassemble_opcode`).
4. Add validator recognition in `validator.py`.
5. Write tests in `tests/test_cpu.py` and `tests/test_extensions.py`.

### New CLI Commands
1. Add a new subparser in `cli.py`'s `main()`.
2. Write tests in `tests/test_cli.py`.

### New Modules
1. Create the module file in `chip8_emulator/`.
2. Add exports to `__init__.py`.
3. Write comprehensive tests in `tests/`.
4. Update `pyproject.toml` if new dependencies are needed.
5. Update `README.md` with usage examples.

## Testing Guidelines

- **Unit tests** for every module — aim for >90% coverage.
- **Edge cases** — test boundary conditions (overflow, underflow, wrapping).
- **Integration tests** — test complete workflows (load ROM → run → check state).
- **Fixtures** — use `build_test_rom()` to create test ROMs from instruction lists.

## Bug Reports

When filing a bug report, please include:

1. **Python version** (`python --version`)
2. **Steps to reproduce** — a minimal ROM or code snippet
3. **Expected vs. actual behavior**
4. **Error messages** or stack traces

## License

By contributing, you agree that your contributions will be licensed under the MIT License.