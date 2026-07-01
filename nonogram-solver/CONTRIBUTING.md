# Contributing to Nonogram Solver

Thank you for your interest in contributing! This document outlines the
process for contributing to the nonogram-solver project.

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/nonogram-solver
   ```

2. **Create a virtual environment and install:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Run the tests:**
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

### Code Style

- Follow PEP 8 (use `ruff` to check: `ruff check nonogram/`)
- Use type hints everywhere (the codebase uses `from __future__ import annotations`)
- Add docstrings to all public functions, classes, and methods
- Keep functions focused and small — prefer composition over inheritance

### Testing

- All new features must include tests in `tests/test_nonogram.py`
- Bug fixes must include a regression test
- Run `python -m pytest tests/ -v` before committing
- Aim for >90% coverage on new code

### Adding a New Feature

1. Create the module under `nonogram/` (e.g. `nonogram/new_feature.py`)
2. Export it from `nonogram/__init__.py`
3. Add CLI subcommand in `nonogram/cli.py` if user-facing
4. Write tests in `tests/test_nonogram.py`
5. Update the README.md
6. Run tests and ensure everything passes

### Adding a Preset Puzzle

1. Define the grid as a boolean 2D list in `nonogram/presets.py`
2. Use `_make_preset()` to add it to the `PRESETS` list
3. Verify it's solvable: `nonogram presets --name <name> --solve`
4. Verify uniqueness: `nonogram validate puzzles/<name>.json`

### Reporting Bugs

When reporting a bug, please include:
- The puzzle file (if applicable)
- The command you ran
- The expected vs actual output
- Python version and OS

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes and commit with clear messages
3. Ensure all tests pass: `python -m pytest tests/ -v`
4. Update the README if needed
5. Push and open a pull request

## Project Structure

```
nonogram-solver/
├── nonogram/           # Main package
│   ├── board.py        # Board and Cell data structures
│   ├── line_solver.py  # Per-line constraint propagation
│   ├── solver.py       # Full-board solver
│   ├── generator.py    # Random puzzle generator
│   ├── player.py       # Interactive player
│   ├── presets.py      # Curated puzzles
│   ├── analyzer.py     # Difficulty analyzer
│   ├── io.py           # File I/O (JSON, NON, PNG, SVG)
│   ├── renderer.py     # ANSI and HTML renderers
│   ├── cli.py          # CLI (12 subcommands)
│   ├── config.py       # Configuration management
│   ├── batch.py        # Batch solver
│   ├── benchmark.py    # Performance benchmarking
│   ├── stats.py        # Solver statistics
│   └── web.py          # Interactive web solver
├── tests/              # Test suite (100+ tests)
├── puzzles/            # Example puzzle files
├── examples/           # Usage examples
├── docs/               # Additional documentation
├── pyproject.toml      # Build & project config
└── README.md
```

## License

By contributing, you agree that your contributions will be licensed under
the MIT License.