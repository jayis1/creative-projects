# Contributing

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

## Development

- Keep changes scoped to `finite-element-solver/`.
- Add or update tests for every behavior change.
- Run `python3 -m pytest` before committing.
- Prefer small modules with explicit type hints and validation.

## Pull Requests

Include:

- problem statement
- implementation summary
- test evidence
- documentation updates for new CLI or model features
