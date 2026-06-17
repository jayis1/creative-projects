# Contributing to Waveform Synthesizer

Thank you for your interest in contributing! Here's how you can help.

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
5. Run the new feature examples: `python examples/advanced_v4.py`
6. Commit with a descriptive message
7. Push and create a pull request

## Code Style

- Python 3.10+ (type hints required on all public functions)
- Line length: 100 characters max
- Use docstrings for all public functions and classes (Google-style preferred)
- Follow the existing module structure
- All new code must include tests

## Adding New Features

### New Waveform Types
Add the enum value to `Waveform` in `core.py`, then implement in `Oscillator._base_wave()`.

### New Effects
1. Add the enum value to `EffectType` in `effects.py`
2. Add default parameters in `Effect.__init__`
3. Implement `_apply_<effect>` method
4. Add to the `process()` dispatch
5. Add to the CLI effects parser in `cli.py` (`_parse_effects`)
6. Add tests in `tests/test_new_features.py`

### New Analysis Functions
Add to `analysis.py` and update `__init__.py` exports.

### New Synthesis Modules (v4.0+)
1. Create a new module file in `waveform_synth/` (e.g., `mysynth.py`)
2. Export from `__init__.py`
3. Add CLI subcommand in `cli.py`
4. Add comprehensive tests in `tests/test_new_features.py`
5. Add example in `examples/`
6. Update README.md with module documentation

### New Noise Colors
Add to `NoiseColor` enum in `noise.py` and implement the `_color_sample()` method.

### New Wavetable Presets
Add a `@classmethod` factory method to `Wavetable` in `wavetable.py`.

## Testing

- All new features must include tests
- Run the full suite: `pytest tests/ -v`
- Run coverage: `pytest tests/ --cov=waveform_synth`
- Aim for >90% coverage on new code
- Test edge cases: empty input, invalid parameters, boundary conditions
- Test reproducibility for seeded random operations

### Test File Organization

| File | Covers |
|------|--------|
| `tests/test_waveform.py` | Core oscillators, utilities, ADSR, FM, effects (v1-v3) |
| `tests/test_dsp.py` | DSP module: FFT, filters, windows, convolution |
| `tests/test_midi.py` | MIDI export module |
| `tests/test_config.py` | Configuration system |
| `tests/test_audio_io.py` | Audio I/O: AIFF, raw PCM, format detection |
| `tests/test_new_features.py` | All v4.0 features: LFO, wavetable, noise, modulation, spectral, granular, MIDI import, new effects |

## CI

GitHub Actions runs all tests on Python 3.10, 3.11, 3.12, and 3.13 for every push and PR.
See `.github/workflows/waveform-synth-ci.yml`.