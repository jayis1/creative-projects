# Contributing to Waveform Synthesizer

Thank you for your interest in contributing! Here's how you can help:

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/creative-projects.git`
3. Navigate to the project: `cd creative-projects/waveform-synth`
4. Install in development mode: `pip install -e ".[dev]"`
5. Run tests: `pytest tests/ -v`

## Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `pytest tests/ -v`
4. Run the smoke test: `python smoke_test.py`
5. Commit with a descriptive message
6. Push and create a pull request

## Code Style

- Python 3.10+ (type hints recommended)
- Line length: 100 characters max
- Use docstrings for all public functions and classes
- Follow the existing module structure

## Adding New Features

### New Waveform Types
Add the enum value to `Waveform` in `core.py`, then implement in `Oscillator._base_wave()`.

### New Effects
1. Add the enum value to `EffectType` in `effects.py`
2. Add default parameters in `Effect.__init__`
3. Implement `_apply_<effect>` method
4. Add to the `process()` dispatch
5. Add tests in `tests/test_waveform.py`

### New Analysis Functions
Add to `analysis.py` and update `__init__.py` exports.

## Testing

- All new features must include tests
- Run the full suite: `pytest tests/ -v`
- Run coverage: `pytest tests/ --cov=waveform_synth`
- Aim for >90% coverage on new code

## Reporting Bugs

Open an issue with:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Any error messages or stack traces

## License

By contributing, you agree that your contributions will be licensed under the MIT License.