# Contributing to wavelet-transform

Thank you for your interest in contributing! This document covers the basics.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/wavelet-transform

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .
pip install pytest pyyaml

# Run tests
python -m pytest tests/ -v
```

## Project Structure

```
wavelet-transform/
├── wavelet/
│   ├── __init__.py        # Package exports
│   ├── wavelets.py        # Wavelet basis functions (Haar, db, sym, coif, bior)
│   ├── dwt.py             # Discrete Wavelet Transform (1-D, 2-D, multilevel)
│   ├── modwt.py           # Maximal Overlap DWT (translation-invariant)
│   ├── swt.py             # Stationary Wavelet Transform (à-trous)
│   ├── cwt.py             # Continuous Wavelet Transform (Morlet, MexHat, Paul, DOG)
│   ├── packets.py         # Wavelet packet decomposition + best-basis
│   ├── threshold.py       # Thresholding functions and estimation methods
│   ├── denoise.py         # Denoising pipelines (1-D, 2-D)
│   ├── compress.py        # Signal compression (RLE + binary serialization)
│   ├── signals.py         # Signal generation utilities
│   ├── analysis.py        # Coefficient analysis (stats, energy, variance)
│   ├── boundary.py        # Boundary extension strategies
│   ├── config.py          # Configuration (JSON, YAML, TOML)
│   ├── logging_utils.py   # Structured logging
│   ├── utils.py           # Quality metrics (MSE, SNR, PSNR, etc.)
│   └── cli.py             # Command-line interface (13 subcommands)
├── tests/
│   ├── test_wavelet.py    # Original test suite (44 tests)
│   └── test_v2.py         # New module tests (57 tests)
├── examples/              # Usage examples (7 scripts)
├── pyproject.toml
└── README.md
```

## Coding Standards

- **Pure Python**: No numpy/scipy dependencies — stdlib only
- **Type hints**: All public functions should have type annotations
- **Docstrings**: Use the NumPy/Google docstring style
- **Tests**: Add tests for all new features.  Run `pytest tests/ -v` before pushing
- **Filter convention**: Decomposition = convolution + downsample;
  Reconstruction = upsample + cross-correlation

## Adding a New Wavelet Family

1. Add the filter coefficients to `wavelet/wavelets.py` (verify against PyWavelets)
2. Create a subclass of `Wavelet` with `_dec_lo`, `_dec_hi`, `_rec_lo`, `_rec_hi`
3. Add the family to the `wavelet()` factory function
4. Add tests in `tests/test_v2.py`
5. Update the README wavelet table

## Adding a New Continuous Wavelet

1. Subclass `ContinuousWavelet` in `wavelet/cwt.py`
2. Implement `__call__` (the mother wavelet function)
3. Set `fourier_period_factor`
4. Add to the `_str_to_wavelet` factory
5. Add the reconstruction constant to `_reconstruction_constant()`
6. Add tests

## Running the CLI

```bash
wavelet-transform info -w db4
wavelet-transform decompose -s chirp -n 256 -w db4
wavelet-transform denoise -s blocks -n 512 --cycle-spin
wavelet-transform cwt -s chirp -w morlet
wavelet-transform analyze -s ecg -w db4
wavelet-transform compare -s doppler
```

## License

MIT — see LICENSE file.