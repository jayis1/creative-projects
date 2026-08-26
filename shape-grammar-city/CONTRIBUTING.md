# Contributing

Thanks for improving `shape-grammar-city`.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
pytest
```

## Guidelines

- Keep the project pure-stdlib unless a dependency has a clear payoff.
- Preserve deterministic behavior for seeded generation.
- Add tests for every behavioral change or bug fix.
- Update `README.md` and `docs/architecture.md` when CLI or data formats change.
- Prefer small, composable functions over monolithic logic.

## Pull Requests

1. Create a focused branch.
2. Add or update tests.
3. Run `pytest`.
4. Include before/after examples when changing rendering or city semantics.
