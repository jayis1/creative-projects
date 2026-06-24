# Contributing to chess-engine

Thank you for your interest in improving chess-engine! This document covers the basics.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/chess-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with test dependencies
pip install -e ".[test]"
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Verifying Move Generation

Perft (performance test) is the gold standard for verifying chess move generation.
Run the built-in perft suite:

```bash
PYTHONPATH=. python -m chess_engine.cli perft-suite --depth 3
```

All perft values should match the known reference values.

## Code Style

- Use type hints on all public functions.
- Add docstrings to all modules, classes, and public methods.
- Follow the existing module structure:
  - `board.py` — board representation, move generation
  - `search.py` — alpha-beta search with optimizations
  - `evaluate.py` — position evaluation
  - `notation.py` — SAN/FEN notation
  - `pgn.py` — PGN read/write
  - `uci.py` — UCI protocol handler
  - `opening_book.py` — opening book
  - `game.py` — game manager (human vs engine, engine vs engine)
  - `config.py` — configuration file support

## Adding New Features

### New search heuristic
1. Add a `use_<feature>` flag to `Search.__init__`.
2. Implement the heuristic in `_negamax` or `_quiescence`.
3. Add a test in `tests/test_improvements.py`.
4. Update the README and config defaults.

### New evaluation term
1. Add the evaluation function to `evaluate.py`.
2. Call it from `_evaluate_absolute`.
3. Add a test comparing positions with/without the feature.
4. Document the weight constants.

### New CLI subcommand
1. Implement `cmd_<name>(args)` in `cli.py`.
2. Add a subparser in `build_parser()`.
3. Test the parser in `TestCLIParser`.

## Reporting Bugs

When reporting a bug, please include:
- The FEN string of the position
- The moves played (UCI or SAN)
- Expected vs. actual behavior
- Steps to reproduce (CLI commands or Python code)

## License

By contributing, you agree that your contributions are licensed under the MIT License.