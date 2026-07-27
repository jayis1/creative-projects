# Changelog

All notable changes to the **KenKen Solver** project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] — 2026-07-27

### Added — Comprehensive Improvement

- **Modular package architecture**: Split the monolithic 1,310-line `kenken.py`
  into a proper `kenken_solver/` package with separate modules:
  - `types.py` — shared type aliases (`Cell`, `Assignment`) and coordinate
    helpers (`neighbors`, `is_contiguous`)
  - `cage.py` — `Cage` class with evaluation, serialization, and analysis
  - `puzzle.py` — `KenKenPuzzle` with validation, JSON/text serialization
  - `solver.py` — `KenKenSolver` with constraint propagation, MRV, hints
  - `generator.py` — `KenKenGenerator` with Latin square generation, cage
    partitioning, operator selection, uniqueness verification
  - `analyzer.py` — `PuzzleAnalyzer` with difficulty scoring and metrics
  - `render.py` — ASCII rendering functions
  - `config.py` — `GenerationConfig` with JSON/YAML config file support
  - `cli.py` — Enhanced argparse-based CLI with subcommands

- **Interactive solving mode**: New `interactive` subcommand provides a
  REPL-like session for filling cells, getting hints, checking validity,
  and revealing the solution.

- **Config file support**: `generate --config <file>` loads generation
  parameters from JSON or YAML files. CLI arguments override config values.

- **Logging**: Structured logging throughout the library via the `logging`
  module. Control verbosity with `--verbose` / `--quiet` CLI flags.

- **Type hints**: Complete type annotations on all public API functions and
  methods. `py.typed` marker included for PEP 561 compliance.

- **pyproject.toml**: Full PEP 621 project metadata, making the package
  installable via `pip install .` with a `kenken` console script entry point.

- **GitHub Actions CI**: Automated test workflow running on Python 3.9–3.12
  with coverage reporting.

- **Examples directory**: Four example scripts demonstrating the API:
  - `generate_and_solve.py` — basic generation, solving, and analysis
  - `serialization.py` — JSON/text round-trip serialization
  - `hint_demo.py` — progressive hint-based solving
  - `batch_analyze.py` — batch generation with difficulty analysis

- **CONTRIBUTING.md**: Development setup, coding conventions, architecture
  overview, and contribution guidelines.

- **LICENSE**: MIT license file.

- **Changelog**: This file.

- **Input validation**: Enhanced validation in `from_text()` for invalid
  operators (delegated to `Cage` constructor).

### Changed

- **Backward compatibility**: The original `kenken.py` is now a thin shim that
  re-exports the new package API. All existing `from kenken import ...` code
  continues to work unchanged.

- **CLI refactored**: The CLI is now in `kenken_solver/cli.py` with a clean
  `build_parser()` / `main()` separation. Handler functions are individually
  testable.

- **Batch generation**: Added `--no-singletons` and `--max-cage-size` options
  to the `batch` subcommand. Progress reporting for each generated puzzle.

### Improved

- **README.md**: Dramatically expanded with badges, table of contents,
  detailed installation instructions, extensive usage examples, architecture
  section, roadmap, contributing section, and changelog.

## [2.0.0] — 2026-07-27

### Added — Enhancement Phase

- Puzzle analyzer with difficulty scoring and solver complexity metrics
- Hint system for partially solved puzzles with conflict detection
- Batch generation with timing statistics
- Cage contiguity validation
- No-singletons generation mode
- Compact text format with comment support
- Enhanced rendering (cage map, solved puzzle overlay)
- Input validation (operator, target, cell bounds, overlapping cages)

## [1.0.0] — 2026-07-27

### Added — Initial Release

- `Cage` class with support for `+`, `-`, `*`, `/`, `=` operators
- `KenKenPuzzle` immutable puzzle representation with validation
- `KenKenSolver` backtracking solver with MRV heuristic and constraint propagation
- `KenKenGenerator` with guaranteed unique-solution generation
- JSON serialization
- CLI with `generate`, `solve`, `verify`, `analyze`, `batch`, `hint` subcommands