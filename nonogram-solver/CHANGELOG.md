# Changelog

## v3.0.0 — Comprehensive Improvement (2026-07-01)

### New Features
- **Web server** (`nonogram/web.py`): Interactive browser-based solver using
  only stdlib `http.server`. Supports cell clicking, hints, checking, solving,
  and reset. Dark-themed responsive UI with clue display.
- **Batch solver** (`nonogram/batch.py`): Solve multiple puzzle files at once
  with glob patterns or directory input. Generates JSON/CSV summary reports.
  Optional uniqueness checking per puzzle.
- **Benchmark suite** (`nonogram/benchmark.py`): Performance benchmarking
  against all preset puzzles and generated puzzles. Warmup support, JSON
  export, human-readable summary table.
- **Solver statistics** (`nonogram/stats.py`): Detailed tracking of
  propagation rounds, line solves, cache hit ratio, backtrack nodes,
  dead ends, and per-section timing. `StatsCollector` context manager.
- **Configuration management** (`nonogram/config.py`): Typed dataclass-based
  configuration with JSON, YAML, and TOML support. Validation for all
  settings (solver, generator, rendering, logging). `load_config` /
  `save_config` functions. `setup_logging` helper.
- **4 new CLI subcommands**: `batch`, `benchmark`, `web`, `config`.
  Total: 12 subcommands (up from 8).
- **Global CLI options**: `--config FILE`, `--verbose`, `--quiet` for
  logging control.
- **GitHub Actions CI** (`.github/workflows/ci.yml`): Tests on Python 3.10,
  3.11, 3.12. Includes CLI smoke tests and lint step.
- **Example scripts** (`examples/`): 5 documented usage examples covering
  solving, generating, interactive play, export, and batch/benchmark.
- **Example config file** (`config.example.json`): Ready-to-use configuration
  template.
- **Architecture documentation** (`docs/ARCHITECTURE.md`): Detailed
  explanation of the module structure and algorithm data flow.
- **CONTRIBUTING.md**: Contribution guidelines and development workflow.
- **LICENSE**: MIT license file.

### Improvements
- Version bumped to 3.0.0 (from 1.0.0)
- `pyproject.toml` fixed: corrected build-backend, added optional deps
  (`[yaml]`, `[dev]`), added classifiers, added `wheel` build requirement
- `__init__.py` expanded: exports all new modules (BatchSolver,
  BenchmarkSuite, SolverStats, AppConfig, etc.)
- CLI: added logging setup via `_setup_logging_from_args()`
- All new modules have full type hints and docstrings
- README.md completely rewritten with badges, TOC, architecture, roadmap

### Tests
- **89 new tests** added in `tests/test_nonogram.py` (total: 100 tests)
  - Board: 15 tests
  - LineSolver: 9 tests
  - Solver: 9 tests
  - Generator: 6 tests
  - Player: 8 tests
  - I/O: 7 tests
  - Renderer: 2 tests
  - Analyzer: 2 tests
  - Presets: 13 tests (parametrized)
  - Batch: 4 tests
  - Benchmark: 2 tests
  - Stats: 5 tests
  - Config: 10 tests
- All 100 tests passing (11 from bug hunt + 89 new)

## v2.0.0 — Enhancement & Bug Hunt (2026-07-01)

### Enhancements
- MRV heuristic for backtracking
- Solution counter and unique-solution checker
- 10 curated preset puzzles
- Difficulty analyzer
- NON format I/O
- PNG export (pure stdlib), SVG export, ANSI rendering, HTML rendering
- 8 CLI subcommands

### Bug Fixes (8 bugs, 11 tests)
- Dead code in `save_png`
- Misleading `_propagate` docstring
- `Board.from_dict` grid dimension validation
- `PuzzleIO.load_non` line count validation
- `Player.check()` with no grid
- `LineSolver` empty clue handling
- `LineSolver` FILLED cell coverage in leftmost/rightmost
- `arrow.json` unsolvable puzzle replaced

## v1.0.0 — Initial Release (2026-07-01)

- Core nonogram solver with overlap method + constraint propagation
- Backtracking solver
- Random puzzle generator
- Interactive player
- JSON I/O