# wavelet-transform

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 101](https://img.shields.io/badge/tests-101%20passing-brightgreen.svg)](#tests)
[![Pure Python](https://img.shields.io/badge/pure%20Python-stdlib%20only-success.svg)](#pure-python)

> A from-scratch wavelet transform toolkit implementing **five transforms** (DWT, MODWT, SWT, CWT, Wavelet Packets), denoising, compression, and coefficient analysis — all in **pure Python with zero external dependencies**.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
  - [Python API](#python-api)
  - [CLI](#cli)
- [Architecture](#architecture)
- [Supported Wavelets](#supported-wavelets)
- [Transforms](#transforms)
- [Denoising](#denoising)
- [Compression](#compression)
- [Configuration](#configuration)
- [Examples Directory](#examples-directory)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [License](#license)

## Features

- **5 transform types**: DWT, MODWT, SWT, CWT, Wavelet Packets
- **5 wavelet families**: Haar, Daubechies (db1–db10), Symlet (sym2–sym5), Coiflet (coif1–coif3), Biorthogonal (6 types)
- **4 continuous wavelets**: Morlet, Mexican Hat, Paul, DOG
- **1-D and 2-D** transforms (separable, multilevel)
- **Translation-invariant denoising** via MODWT and cycle-spinning
- **Wavelet packets** with best-basis selection (Shannon entropy, dynamic programming)
- **4 threshold methods**: VisuShrink, SureShrink, BayesShrink, Minimax
- **4 thresholding functions**: soft, hard, non-negative garrote, firm
- **Signal compression** with RLE encoding and binary serialization
- **Coefficient analysis**: per-scale statistics, energy distribution, wavelet variance, scale correlation
- **18 signal generators**: sine, chirp, blocks, bumps, heaviSine, Doppler, ECG, noise types, etc.
- **Boundary extensions**: periodic, symmetric, zero-pad, constant, reflect
- **Config files**: JSON, YAML, TOML
- **Structured logging** with configurable verbosity
- **13-subcommand CLI** with full help text
- **101 tests** (pytest + unittest)
- **7 example scripts** demonstrating all features
- **Pure Python**: No numpy, scipy, or any external dependency — stdlib only

## Installation

```bash
cd wavelet-transform
pip install -e .
```

For YAML config support (optional):
```bash
pip install -e ".[yaml]"
```

For development:
```bash
pip install -e ".[dev]"
```

**Requirements**: Python ≥ 3.9. No runtime dependencies.

## Quick Start

```python
from wavelet import DWT, wavelet, denoise1d, generate, add_noise

# Generate a noisy signal
clean = generate("blocks", 512)
noisy = add_noise(clean, 0.5, seed=42)

# Denoise with BayesShrink + cycle spinning
denoised = denoise1d(noisy, wavelet="db4", threshold_method="bayes")

# Or use translation-invariant cycle-spinning denoising
from wavelet import cycle_spin_denoise, Threshold
denoised_ti = cycle_spin_denoise(noisy, "db4", threshold_method=Threshold.BAYES, n_shifts=16)
```

## Usage Examples

### Python API

#### DWT — Discrete Wavelet Transform

```python
from wavelet import DWT, wavelet

w = wavelet("db4")
dwt = DWT(w)

# 1-D multilevel decomposition
result = dwt.decompose(signal, level=4)
print(result)  # DWTResult(level=4, wavelet='db4', sizes=[128, 64, 32, 16, 16])

# Access coefficients
approx = result.approx      # Final-level approximation
details = result.details    # List of detail arrays (finest to coarsest)

# Perfect reconstruction
reconstructed = dwt.reconstruct(result)
# Error < 1e-15
```

#### 2-D DWT (Image Processing)

```python
from wavelet import DWT

dwt = DWT("haar")
matrix = [[float(i * 8 + j) for j in range(8)] for i in range(8)]

# 2-D decomposition (separable: rows then columns)
decomp = dwt.decompose2(matrix, level=2)
# decomp["subbands"][0] = {"LH": ..., "HL": ..., "HH": ...}
# decomp["LL"] = final approximation

# 2-D reconstruction
reconstructed = dwt.reconstruct2(decomp)
```

#### MODWT — Translation-Invariant Transform

```python
from wavelet import MODWT

mod = MODWT("db4")
result = mod.decompose(signal, level=4)

# Output length = input length at every level (non-decimated)
assert len(result.approx) == len(signal)
assert all(len(d) == len(signal) for d in result.details)

reconstructed = mod.reconstruct(result)
```

#### SWT — Stationary Wavelet Transform (à-Trous)

```python
from wavelet import SWT

swt = SWT("db4")
result = swt.decompose(signal, level=4)
reconstructed = swt.reconstruct(result)
# Perfect reconstruction (error < 1e-15)
```

#### CWT — Continuous Wavelet Transform (Scalogram)

```python
from wavelet import cwt, icwt, Morlet, MexicanHat

# Compute scalogram with Morlet wavelet
result = cwt(signal, "morlet", dt=1.0, dj=0.125)

# Access the time-scale representation
power = result.power     # |W(s,t)|² scalogram
real = result.real       # Real part (amplitude)
print(f"Scales: {result.n_scales}, Shape: {len(result.coefficients)}x{result.input_length}")

# Approximate reconstruction
reconstructed = icwt(result)

# Other continuous wavelets
result_mh = cwt(signal, "mexhat")   # Mexican Hat (real)
result_paul = cwt(signal, "paul")   # Paul (complex, phase analysis)
result_dog = cwt(signal, "dog4")    # 4th derivative of Gaussian
```

#### Wavelet Packets with Best-Basis Selection

```python
from wavelet import WaveletPacket

wp = WaveletPacket("db4")
result = wp.decompose(signal, level=4)

# Full binary tree: 2^4 = 16 leaf nodes, 31 total
print(len(result["packets"]))  # 31

# Best-basis selection (Shannon entropy + dynamic programming)
best = wp.best_basis(result)
print(f"Optimal basis: {best}")
```

#### Denoising

```python
from wavelet import denoise1d, denoise2d, cycle_spin_denoise, Threshold

# Standard DWT denoising
denoised = denoise1d(noisy, wavelet="db4",
                     threshold_method=Threshold.BAYES,
                     threshold_func="soft")

# MODWT (translation-invariant) denoising
denoised_modwt = denoise1d(noisy, wavelet="db4", transform="modwt")

# Cycle-spinning denoising (best artifact reduction)
denoised_cs = cycle_spin_denoise(noisy, "db4",
                                 threshold_method=Threshold.BAYES,
                                 n_shifts=16)

# 2-D image denoising
denoised_img = denoise2d(noisy_matrix, wavelet="haar")
```

#### Compression

```python
from wavelet import compress1d, decompress1d, serialize, deserialize

# Compress: keep only the top 10% of wavelet coefficients
compressed = compress1d(signal, wavelet="db4", keep_ratio=0.1)
print(f"Compression ratio: {compressed.compression_ratio:.1f}x")
print(f"Sparsity: {compressed.sparsity:.1%}")

# Decompress
reconstructed = decompress1d(compressed)

# Binary serialization for storage/transmission
data = serialize(compressed)
compressed2 = deserialize(data)
```

#### Signal Generation

```python
from wavelet import generate, list_signals, add_noise

# List all available signals
print(list_signals())
# ['blocks', 'brown_noise', 'bumps', 'chirp', 'doppler', 'ecg',
#  'gaussian', 'heavisine', 'multi', 'pink_noise', 'pulse', 'ramp',
#  'sawtooth', 'sine', 'square', 'step', 'triangle', 'white_noise']

# Generate test signals (Donoho-Johnstone benchmark suite)
blocks = generate("blocks", 512)
doppler = generate("doppler", 512)
heavisine = generate("heavisine", 512)
bumps = generate("bumps", 512)

# Add noise
noisy = add_noise(clean, sigma=0.3, seed=42)
```

#### Coefficient Analysis

```python
from wavelet import DWT, analyze, compare_wavelets

dwt = DWT("db4")
result = dwt.decompose(signal, level=4)
analysis = analyze(result)

print(analysis.summary())
# Wavelet Analysis Summary (4 scales)
# ==================================================
# Total energy: 128.000000
#
#  Scale      N       Mean        Std       Energy    Entropy   Sparsity
# ------------------------------------------------------------------------
#      0    128     0.0000     0.0452     0.261444     3.0123     12.50%
#      1     64     0.0010     0.1205     0.928384     2.4567     18.75%
#      ...

# Compare wavelet families
comparison = compare_wavelets(signal, ["haar", "db4", "sym4", "coif2"], level=4)
```

### CLI

```bash
# Show wavelet filter information
wavelet-transform info -w db8

# Decompose a signal
wavelet-transform decompose -s chirp -n 256 -w db4 -l 4

# Denoise a signal (with cycle spinning for best results)
wavelet-transform denoise -s blocks -n 512 -w db4 --method bayes --cycle-spin

# Compress a signal
wavelet-transform compress -s sine -n 512 -w db4 --keep-ratio 0.1 -o compressed.bin

# Decompress
wavelet-transform decompress -i compressed.bin -o reconstructed.json

# Wavelet packet decomposition with best-basis
wavelet-transform packets -s doppler -n 256 -w db4 -l 4 --best-basis

# ASCII visualization of coefficients
wavelet-transform visualize -s chirp -n 64 -w haar -l 3

# CWT scalogram (ASCII)
wavelet-transform cwt -s chirp -n 256 -w morlet

# Analyze coefficient statistics
wavelet-transform analyze -s ecg -n 256 -w db4

# List available test signals
wavelet-transform signals --list

# Compare wavelets on the same signal
wavelet-transform compare -s doppler -n 256

# Benchmark transform speed
wavelet-transform benchmark -n 1024 -i 10

# Generate a config file
wavelet-transform config --generate config.json -w sym4 -l 3

# Validate a config file
wavelet-transform config --validate config.json

# Enable verbose logging
wavelet-transform -v denoise -s blocks -n 256
```

## Architecture

### Filter Convention

The toolkit uses a consistent filter convention across all discrete transforms:

- **Decomposition**: convolution + downsample
  ```
  a[i] = Σ_j dec_lo[j] · signal[(2i − j) mod n]
  d[i] = Σ_j dec_hi[j] · signal[(2i − j) mod n]
  ```

- **Reconstruction**: upsample + cross-correlation (adjoint of decomposition)
  ```
  x[m] = Σ_j rec_lo[j] · up[(m + j) mod N] + Σ_j rec_hi[j] · up[(m + j) mod N]
  ```

For **orthogonal** wavelets: `rec_lo = dec_lo`, `rec_hi = dec_hi`.
For **biorthogonal** wavelets: reconstruction filters are the time-reversed PyWavelets rec filters.

This convention achieves **perfect reconstruction** with roundtrip errors of ~1e-16 for all supported wavelets.

### Module Overview

```
┌─────────────────────────────────────────────────────────┐
│                     wavelet package                      │
├─────────────┬─────────────┬──────────────┬──────────────┤
│  wavelets   │    dwt      │    modwt     │     swt      │
│  (filters)  │  (decimated)│ (non-decim.) │  (à-trous)   │
├─────────────┼─────────────┴──────────────┴──────────────┤
│   cwt       │         packets (binary tree)              │
│ (continuous)│    + best-basis (entropy + DP)             │
├─────────────┼────────────────────────────────────────────┤
│  threshold  │  denoise (1-D, 2-D, cycle-spinning)        │
│  (4 methods,│  compress (RLE + binary)                   │
│   4 funcs)  │                                            │
├─────────────┼────────────────────────────────────────────┤
│  signals    │  analysis (stats, energy, variance, corr)  │
│  (18 types) │  boundary (5 modes)                        │
├─────────────┼────────────────────────────────────────────┤
│   config    │  logging  │  utils  │  cli (13 commands)   │
│ (JSON/YAML/ │           │(metrics)│                      │
│   TOML)     │           │         │                      │
└─────────────┴───────────┴─────────┴──────────────────────┘
```

### Transform Comparison

| Transform | Decimated | Translation-Invariant | Output Length | Use Case |
|-----------|-----------|----------------------|---------------|----------|
| DWT | Yes | No | n/2^j per level | Compression, fast analysis |
| MODWT | No | Yes | n (all levels) | Denoising, variance analysis |
| SWT | No | Yes | n (all levels) | Denoising (à-trous) |
| CWT | No | Yes | n × n_scales | Time-frequency analysis |
| Packets | Yes | No | Full binary tree | Best-basis, adaptive decomposition |

## Supported Wavelets

### Discrete Wavelets

| Family | Names | Filter Length | Vanishing Moments |
|--------|-------|---------------|-------------------|
| Haar | haar, db1 | 2 | 1 |
| Daubechies | db1–db10 | 2N | N |
| Symlet | sym2–sym5 | 2N | N |
| Coiflet | coif1–coif3 | 6N | N |
| Biorthogonal | bior1.1, bior1.3, bior1.5, bior2.2, bior3.1, bior3.3 | varies | varies |

All filter coefficients are verified against PyWavelets reference values.

### Continuous Wavelets

| Wavelet | Type | Parameters | Good For |
|---------|------|------------|----------|
| Morlet | Complex | ω₀ = 6 (default) | Oscillatory signals, time-frequency |
| Mexican Hat | Real | — | Peak/edge detection |
| Paul | Complex | Order m = 4 (default) | Phase analysis |
| DOG | Real | Order m = 1,2,4,6 | General peak detection |

## Denoising

### Pipeline

1. Forward transform (DWT, MODWT, or SWT)
2. Estimate noise σ from finest-level detail coefficients via MAD
3. Compute threshold using the selected method
4. Apply thresholding function to detail coefficients
5. Inverse transform

### Threshold Methods

| Method | Description |
|--------|-------------|
| Universal (VisuShrink) | T = σ√(2 ln n) — simple, universal |
| SURE (SureShrink) | Minimizes Stein's Unbiased Risk Estimate |
| Bayes (BayesShrink) | Adapts to subband signal variance: T = σ²/σ_signal |
| Minimax | Minimax risk threshold |

### Cycle Spinning

Cycle-spinning denoising (Coifman & Donoho, 1995) averages denoised results over all circular shifts of the input, dramatically reducing the pseudo-Gibbs artifacts that plague ordinary wavelet denoising:

```python
from wavelet import cycle_spin_denoise, Threshold
denoised = cycle_spin_denoise(noisy, "db4", threshold_method=Threshold.BAYES, n_shifts=16)
```

## Compression

1. Forward DWT decomposition
2. Soft-threshold detail coefficients (keep only the largest k%)
3. Run-length encode the sparse coefficient arrays
4. Serialize to a compact binary format (struct-packed)

```python
from wavelet import compress1d, serialize
compressed = compress1d(signal, wavelet="db4", keep_ratio=0.1)
data = serialize(compressed)
# Typical: 80% space saving with < 1% reconstruction error
```

## Configuration

Configuration files (JSON, YAML, TOML) enable reproducible analysis pipelines:

```json
{
    "wavelet": "db4",
    "level": 4,
    "transform": "dwt",
    "denoise": {
        "method": "bayes",
        "threshold_func": "soft",
        "cycle_spinning": true,
        "n_shifts": 16
    },
    "compress": {
        "keep_ratio": 0.1
    }
}
```

```python
from wavelet import load_config, save_config
config = load_config("config.json")
errors = config.validate()
```

## Examples Directory

| Script | Description |
|--------|-------------|
| `01_basic_dwt.py` | DWT decomposition and reconstruction |
| `02_denoising.py` | Compare denoising methods and transforms |
| `03_cwt_scalogram.py` | CWT time-scale analysis with ASCII visualization |
| `04_compression.py` | Signal compression with different keep ratios |
| `05_wavelet_packets.py` | Wavelet packet decomposition and best-basis |
| `06_analysis.py` | Coefficient analysis and wavelet comparison |
| `07_config.py` | Configuration files (JSON, TOML) |

Run any example:
```bash
python3 examples/01_basic_dwt.py
```

## Testing

```bash
# Run all 101 tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_v2.py::TestSWT -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=wavelet --cov-report=term-missing
```

### Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_wavelet.py` | 44 | Original: wavelets, DWT, MODWT, packets, thresholding, denoising, compression, utils |
| `test_v2.py` | 57 | New: extended wavelets, SWT, CWT, signals, analysis, boundary, config, cycle-spinning, integration |

**Total: 101 tests, all passing.**

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and how to add new wavelet families or transforms.

## Roadmap

- [ ] More wavelet families (db11–db20, sym6–sym10, coif4–coif5, more biorthogonal)
- [ ] Lifting scheme implementation (second-generation wavelets)
- [ ] Wavelet coherence and cross-wavelet transform
- [ ] 2-D CWT for image analysis
- [ ] Adaptive wavelet design (data-driven)
- [ ] GPU acceleration (optional, via numpy/cupy)
- [ ] WAV/audio file I/O for real-world signals
- [ ] SVG/PNG scalogram export
- [ ] Benchmark against PyWavelets for validation

## Changelog

### v2.0.0 (2026-07-08) — Comprehensive Improvement

**New Modules:**
- `cwt.py` — Continuous Wavelet Transform (Morlet, Mexican Hat, Paul, DOG) with scalogram and reconstruction
- `swt.py` — Stationary Wavelet Transform (à-trous algorithm) with cycle-spinning denoising
- `signals.py` — 18 signal generators (sine, chirp, blocks, bumps, heaviSine, Doppler, ECG, noise types, etc.)
- `analysis.py` — Coefficient analysis (per-scale statistics, energy distribution, wavelet variance, scale correlation, wavelet comparison)
- `boundary.py` — 5 boundary extension strategies (periodic, symmetric, zero, constant, reflect)
- `config.py` — Configuration system (JSON, YAML, TOML) with validation
- `logging_utils.py` — Structured logging with configurable verbosity

**Extended Wavelets:**
- Daubechies db5–db10 added (verified against PyWavelets, perfect reconstruction)

**CLI Enhancements:**
- 5 new subcommands: `cwt`, `analyze`, `signals`, `config`, `compare`
- `--cycle-spin` and `--n-shifts` flags for denoising
- `--verbose` global flag
- Uses `wavelet.signals` for signal generation (18 signal types vs 7 before)

**Testing:**
- 57 new tests (total: 101, all passing)
- Integration tests combining multiple modules

**Project Files:**
- 7 example scripts in `examples/`
- GitHub Actions CI configuration
- CONTRIBUTING.md
- LICENSE (MIT)
- Updated pyproject.toml with optional dependencies

### v1.0.0 — Initial Release

- 5 wavelet families (Haar, db1–db4, sym2–sym5, coif1–coif3, 6 biorthogonal)
- DWT (1-D and 2-D, multilevel) with periodic boundary
- MODWT (translation-invariant)
- Wavelet packets with best-basis selection
- 4 threshold methods + 4 thresholding functions
- Denoising (1-D, 2-D) with DWT and MODWT backends
- Compression with RLE and binary serialization
- 8-subcommand CLI
- 44 tests

## License

MIT — see [LICENSE](LICENSE).