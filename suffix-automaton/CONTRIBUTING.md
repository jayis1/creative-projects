# Contributing to suffix-automaton

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e . pytest
```

## Workflow

1. Add or update tests before changing behavior.
2. Run `pytest` locally.
3. Keep CLI help text and README examples aligned with code.
4. Prefer small algorithmic helpers over large CLI conditionals.

## Pull request checklist

- [ ] Tests added or updated
- [ ] README updated when UX or outputs change
- [ ] New config formats remain JSON/TOML compatible
- [ ] Error messages stay actionable for CLI users
