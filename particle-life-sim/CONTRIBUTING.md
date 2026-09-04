# Contributing

## Development setup

```bash
cd particle-life-sim
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

## Running checks

```bash
pytest
python3 -m particle_life_sim presets
python3 -m particle_life_sim analyze --preset aurora --steps 40 --dt 0.1
```

## Contribution guidelines

- Keep changes scoped to `particle-life-sim/`.
- Add or update tests for behavior changes.
- Prefer small, composable functions over one large command handler.
- Preserve deterministic behavior when a seed is supplied.
- Update the project README when adding user-facing commands or config fields.

## Pull request checklist

- [ ] Tests pass locally.
- [ ] CLI help text reflects new options.
- [ ] Examples or docs were added for new features.
- [ ] Error messages are actionable.
