# Contributing

Thanks for your interest in improving `convolutional-codec`.

## Development setup

```bash
cd convolutional-codec
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e .[dev]
pytest
```

## Guidelines

- Prefer small, well-tested changes.
- Add regression tests for every bug fix.
- Keep CLI features backed by library APIs, not duplicated logic.
- Preserve pure-Python compatibility unless a compelling benchmark justifies otherwise.
- Document user-facing changes in `README.md` and deeper design notes in `docs/`.

## Pull requests

1. Create a feature branch.
2. Add or update tests.
3. Run `pytest` locally.
4. Include a short explanation of motivation, approach, and verification.
