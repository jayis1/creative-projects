# Contributing to wfc-generator

Thanks for your interest in improving **wfc-generator**! This project is part
of the [`creative-projects`](https://github.com/jayis1/creative-projects)
monorepo. Contributions of bug reports, fixes, new preset tile sets, renderers
and performance improvements are all welcome.

## Development setup

```bash
git clone https://github.com/jayis1/creative-projects
cd creative-projects/wfc-generator

# create a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\activate on Windows

# install dev dependencies
pip install -e ".[dev]"

# run the test suites
python3 -m pytest tests/ -q          # new pytest suite (71 tests)
python3 test_wfc.py                 # legacy self-contained suite (49 tests)
```

## Project layout

```
wfc-generator/
├── wfc_generator/         # the package (modular)
│   ├── __init__.py         # public re-exports
│   ├── tile.py             # Tile + side constants
│   ├── tileset.py          # TileSet: validation, JSON, symmetry, rotation
│   ├── stats.py            # GenerationStats
│   ├── grid.py             # WFCGrid: the core algorithm + selection strategies
│   ├── overlap.py          # OverlapModel: learn from a sample
│   ├── renderer.py         # ANSI / plain / HTML / SVG / PNG renderers
│   ├── presets.py          # create_*_tileset() factory functions
│   ├── config.py           # WFCConfig (JSON / YAML / TOML)
│   ├── logging_utils.py    # structured logging setup
│   └── cli.py              # argparse CLI
├── wfc.py                  # backward-compat shim re-exporting the package
├── tests/                  # pytest suite
├── examples/               # runnable demos + config files
├── test_wfc.py             # legacy self-contained test runner
├── pyproject.toml          # packaging metadata
└── README.md
```

## Coding standards

- **Python 3.9+** (uses `from __future__ import annotations`, `dataclasses`).
- Type hints throughout the package; keep them accurate.
- Every public function/class has a docstring.
- Keep the **backward-compatibility shim** (`wfc.py`) working — existing
  users import `from wfc import ...`. If you rename a public symbol, re-export
  the old name from `wfc_generator/__init__.py`.
- Add a test for any new feature or bug fix. The pytest suite under `tests/`
  is the source of truth; the legacy `test_wfc.py` must keep passing too.

## Adding a new preset tile set

1. Write a `create_<name>_tileset()` factory in `wfc_generator/presets.py`
   that returns a fully-constrained, symmetrized `TileSet`.
2. Register it in the `PRESET_FACTORIES` dict at the top of
   `wfc_generator/cli.py` so it gets a CLI subcommand automatically.
3. Add symbol/color entries to the maps in `wfc_generator/renderer.py`.
4. Add a parametrized test case in `tests/test_wfc_generator.py`
   (`TestPresets.test_preset_has_tiles_and_runs`).
5. Update the preset table in the README.

## Submitting changes

1. Fork the monorepo and create a feature branch.
2. Make your changes; keep commits focused.
3. Run **both** test suites locally (`pytest tests/` and `python3 test_wfc.py`)
   — they must both be green.
4. Open a pull request describing **what** changed and **why**.

## Reporting bugs

Open an issue with:
- the exact command you ran (or a minimal code snippet),
- the Python version,
- the full traceback (if any), and
- the smallest reproduction case you can manage.

## License

By contributing you agree your contributions are licensed under the project's
[MIT license](./LICENSE).