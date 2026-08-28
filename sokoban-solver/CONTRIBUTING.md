# Contributing to sokoban-solver

Thanks for contributing.

## Development setup

```bash
cd sokoban-solver
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .[dev]
pytest
```

## Project conventions

- Keep solver behavior deterministic.
- Prefer small, composable modules over monolithic helpers.
- Add regression tests for every bug fix and every new CLI feature.
- Preserve pure-stdlib compatibility.
- Update `README.md` and `docs/architecture.md` when architecture or commands change.

## Pull request checklist

1. Run `pytest` locally.
2. Run at least one CLI smoke test, for example:
   `python3 -m sokoban_solver benchmark --json`
3. Document any new user-visible flags or config keys.
4. Keep examples in `examples/` in sync with the current CLI.
