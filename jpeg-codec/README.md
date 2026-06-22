# jpeg-codec

> A from-scratch implementation of the baseline (sequential DCT) JPEG codec with quality metrics, config files, and benchmarking.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-66%20passed-brightgreen.svg)
![NumPy](https://img.shields.io/badge/numpy-required-orange.svg)
![Pillow](https://img.shields.io/badge/pillow-optional-yellow.svg)

This project implements the complete JPEG pipeline — encoding and
decoding — without using any image-processing libraries. Only NumPy is
used for array operations; all JPEG-specific logic (DCT, quantization,
Huffman coding, bit-level I/O, JFIF file format) is implemented from
first principles.

The encoder produces standard JFIF `.jpg` files decodable by any
conforming JPEG reader (Pillow/libjpeg, web browsers, image viewers),
and the decoder can read JPEG files produced by those same libraries.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [Command Line](#command-line)
  - [Configuration Files](#configuration-files)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
  - [Encoding Pipeline](#encoding-pipeline)
  - [Decoding Pipeline](#decoding-pipeline)
- [Quality Metrics](#quality-metrics)
- [Benchmarking](#benchmarking)
- [Cross-Compatibility](#cross-compatibility)
- [Examples](#examples)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

### Core Codec
- **Full baseline JPEG encode/decode** — produces standard JFIF `.jpg` files
  that can be decoded by any JPEG reader (Pillow/libjpeg, web browsers)
- **RGB and grayscale** support
- **Chroma subsampling**: 4:4:4, 4:2:2, 4:2:0, 4:1:1
- **Quality control**: 1–100 (libjpeg-compatible scaling)
- **Standard JPEG Huffman and quantization tables** (Annex K)
- **Canonical Huffman coding** with proper byte-stuffing (0xFF → 0xFF 0x00)
- **8×8 Type-II DCT** via separable matrix multiplication
- **Vectorized batch DCT** using NumPy einsum for performance
- **Zig-zag scan ordering** for run-length encoding efficiency
- **Differential DC coding** (diff from previous block)
- **Run-length + magnitude-category AC coding** with ZRL and End-of-Block

### Advanced Features
- **Comment (COM) marker** embedding and extraction
- **Restart markers (DRI/RST0–RST7)** for error-resilient streaming
- **DPI/pixel density metadata** in JFIF header
- **Comprehensive metadata inspection** — parse dimensions, components,
  quantization tables, Huffman tables, markers, comments, restart intervals
- **Quality metrics** — PSNR, SSIM (Wang et al. 2004), MSE, RMSE,
  compression ratio, bits per pixel
- **Configuration files** — JSON, YAML, and TOML support
- **Benchmarking** — encode/decode throughput, quality sweeps, sampling
  comparison
- **Custom exception hierarchy** — fine-grained error types for robust
  error handling
- **Structured logging** — configurable verbosity for debugging

### Developer Experience
- **Comprehensive CLI** — encode, decode, roundtrip, info, sweep, bench,
  compare, config management
- **Installable package** — `pip install -e .` or `pyproject.toml`
- **66-test pytest suite** — covering all modules, edge cases, and
  cross-compatibility
- **GitHub Actions CI** — automated testing on Python 3.9–3.12
- **Type hints** on all public functions
- **Docstrings** on all modules, classes, and functions
- **Example scripts** — 5 runnable demonstrations
- **CONTRIBUTING.md** with development setup and architecture overview

---

## Installation

### From source (recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/jpeg-codec

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with pip
pip install -e .

# Or install dependencies directly
pip install numpy pillow pytest
```

### Dependencies

| Dependency | Required | Purpose |
|-----------|----------|---------|
| numpy ≥ 1.20 | Yes | Array operations |
| pillow ≥ 9.0 | No | CLI image I/O (PNG/JPEG files) |
| pyyaml ≥ 6.0 | No | YAML config file support |
| pytest ≥ 7.0 | No | Running the test suite |

---

## Quick Start

```python
import numpy as np
from jpeg_codec import encode, decode
from jpeg_codec.metrics import psnr, ssim

# Create or load an image (H×W×3 uint8)
image = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)

# Encode to JPEG bytes
jpeg_bytes = encode(image, quality=85, sampling="4:2:0")

# Decode back to numpy array
reconstructed = decode(jpeg_bytes)

# Check quality
print(f"PSNR: {psnr(image, reconstructed):.2f} dB")
print(f"SSIM: {ssim(image, reconstructed):.4f}")
print(f"Compression: {image.nbytes / len(jpeg_bytes):.1f}:1")
```

---

## Usage

### Python API

#### Basic Encode/Decode

```python
from jpeg_codec import encode, decode

# RGB image
jpeg = encode(image, quality=90, sampling="4:2:0")
recon = decode(jpeg)

# Grayscale
jpeg_gray = encode(gray_image, quality=80)
recon_gray = decode(jpeg_gray)
```

#### With Comment and Restart Markers

```python
jpeg = encode(image, quality=85, comment="My photo",
              restart_interval=8, dpi=(300, 300))
```

#### Quality Metrics

```python
from jpeg_codec import quality_report

report = quality_report(original, reconstructed,
                        original.nbytes, len(jpeg))
print(f"PSNR:  {report['psnr_db']:.2f} dB")
print(f"SSIM:  {report['ssim']:.4f}")
print(f"Ratio: {report['compression_ratio']:.2f}:1")
print(f"BPP:   {report['bits_per_pixel']:.2f}")
```

#### Metadata Inspection

```python
from jpeg_codec import get_info

info = get_info(jpeg_bytes)
print(f"Dimensions: {info.width}x{info.height}")
print(f"Components:  {info.num_components}")
print(f"Sampling:    {info.sampling_string}")
print(f"Comment:     {info.comment}")
print(f"Markers:     {len(info.markers)}")
for name, offset in info.markers:
    print(f"  {name:12s} at offset {offset}")
```

#### Batch DCT (Vectorized)

```python
from jpeg_codec.batch_dct import channel_to_blocks, batch_dct2d, batch_idct2d

# Process all 8x8 blocks at once (5-10x faster than per-block loop)
blocks = channel_to_blocks(channel)  # (N, 8, 8)
dct_blocks = batch_dct2d(blocks)     # (N, 8, 8) DCT coefficients
reconstructed = batch_idct2d(dct_blocks)
```

### Command Line

```bash
# Encode an image to JPEG
python -m jpeg_codec.cli encode input.png output.jpg \
    --quality 85 --sampling 4:2:0 --comment "My photo"

# Decode a JPEG to an image
python -m jpeg_codec.cli decode input.jpg output.png

# Round-trip test with full quality metrics
python -m jpeg_codec.cli roundtrip input.png --quality 85 --metrics

# Inspect JPEG metadata and marker structure
python -m jpeg_codec.cli info input.jpg

# Quality sweep across multiple quality levels
python -m jpeg_codec.cli sweep input.png --qualities 10,25,50,75,90,95

# Benchmark encode/decode throughput
python -m jpeg_codec.cli bench input.png --runs 5

# Compare subsampling modes at the same quality
python -m jpeg_codec.cli compare input.png --quality 85

# Config file management
python -m jpeg_codec.cli config init settings.json --quality 90 --sampling 4:4:4
python -m jpeg_codec.cli config show --config settings.json

# Verbose (debug) output
python -m jpeg_codec.cli -v encode input.png output.jpg

# Use a config file for encoding
python -m jpeg_codec.cli encode input.png output.jpg --config settings.json
```

### Configuration Files

Create a JSON config file (`settings.json`):

```json
{
    "quality": 85,
    "sampling": "4:2:0",
    "restart_interval": 0,
    "comment": "Encoded by jpeg-codec",
    "dpi": [72, 72],
    "units": 1
}
```

Use it programmatically:

```python
from jpeg_codec import EncodingConfig, load_config, encode

config = load_config("settings.json")
kwargs = {k: v for k, v in config.to_dict().items()
          if k != "optimize_huffman"}
jpeg = encode(image, **kwargs)
```

Or via CLI:

```bash
python -m jpeg_codec.cli encode input.png output.jpg --config settings.json
```

YAML and TOML formats are also supported (requires `pyyaml` or
Python 3.11+ `tomllib` respectively).

---

## Architecture

```
jpeg_codec/
├── __init__.py       # Public API exports (v2.0.0)
├── color.py          # RGB ↔ YCbCr (ITU-R BT.601), level shift
├── dct.py            # Forward/inverse 8×8 DCT-II (separable matrix)
├── batch_dct.py      # Vectorized batch DCT via NumPy einsum
├── quantize.py       # Standard JPEG quantization tables + quality scaling
├── zigzag.py         # Canonical JPEG zig-zag scan ordering
├── huffman.py        # Standard Huffman tables, canonical codes, magnitude coding
├── entropy.py        # DC differential + AC run-length entropy coding
├── bitio.py          # MSB-first bit reader/writer with byte-stuffing
├── subsample.py      # Chroma up/downsampling (4:4:4, 4:2:2, 4:2:0, 4:1:1)
├── encoder.py        # Full JFIF encoder (SOI/APP0/DQT/SOF0/DHT/SOS/EOI)
├── decoder.py        # Full JFIF decoder with marker parsing
├── cli.py            # Command-line interface (8 subcommands)
├── metrics.py        # PSNR, SSIM, MSE, RMSE, quality reports
├── config.py         # JSON/YAML/TOML configuration management
├── info.py           # JPEG metadata inspection (JPEGInfo dataclass)
├── restart.py        # Restart markers (DRI/RST) and COM segments
├── benchmark.py      # Performance benchmarking and quality sweeps
├── exceptions.py     # Custom exception hierarchy
└── logging_setup.py  # Configurable logging
```

### Module Dependencies

```
encoder.py ─┬─ color.py
            ├─ dct.py / batch_dct.py
            ├─ quantize.py ── zigzag.py
            ├─ huffman.py
            ├─ entropy.py ── bitio.py
            ├─ subsample.py
            ├─ restart.py
            └─ exceptions.py

decoder.py ─┬─ (same core modules)
            ├─ info.py
            └─ exceptions.py

cli.py ────── encoder.py + decoder.py + metrics.py + config.py + info.py
```

---

## How It Works

### Encoding Pipeline

```
Input (H×W×3 RGB)
    │
    ▼
1. Color Transform: RGB → YCbCr (ITU-R BT.601)
    │
    ▼
2. Chroma Subsampling: Cb/Cr downsampled by averaging
    │
    ▼
3. Block Splitting: Each channel split into 8×8 blocks
    │
    ▼
4. Level Shift: [0,255] → [-128,127]
    │
    ▼
5. Forward DCT: 2D Type-II DCT (C·block·Cᵀ)
    │
    ▼
6. Quantization: DCT coefficients ÷ quant table, rounded
    │
    ▼
7. Zig-zag Scan: Reorder coefficients for run-length efficiency
    │
    ▼
8. Entropy Coding:
   • DC: differential from previous block → (SIZE, VALUE) Huffman
   • AC: run-length of zeros + (RUN, SIZE, VALUE) Huffman
   • Special: EOB (0x00), ZRL (0xF0 for 16 zeros)
    │
    ▼
9. Bit Packing: MSB-first with JPEG byte-stuffing (0xFF→0xFF 0x00)
    │
    ▼
10. JFIF Writing: SOI → APP0 → DQT → SOF0 → DHT → [DRI] → [COM] → SOS → data → EOI
```

### Decoding Pipeline

The reverse: parse markers → read quantization/Huffman tables →
entropy decode → dequantize → inverse DCT → level unshift →
upsample chroma → YCbCr → RGB → clip to [0,255] → uint8.

---

## Quality Metrics

The package provides several image quality metrics:

| Metric | Range | Perfect Score | Description |
|--------|-------|---------------|-------------|
| PSNR | 0–∞ dB | ∞ (identical) | Peak signal-to-noise ratio |
| SSIM | -1 to 1 | 1.0 | Structural similarity (Wang et al. 2004) |
| MSE | 0–∞ | 0 | Mean squared error |
| RMSE | 0–255 | 0 | Root mean squared error |
| BPP | 0–24 | Lower is better | Bits per pixel (compressed) |

### Typical PSNR Values

| PSNR (dB) | Quality |
|-----------|---------|
| > 40 | Excellent (nearly lossless) |
| 30–40 | Good |
| 20–30 | Acceptable |
| < 20 | Poor |

---

## Benchmarking

```python
from jpeg_codec.benchmark import benchmark, quality_sweep, compare_sampling

# Throughput benchmark
result = benchmark(image, quality=85, runs=5)
print(f"Encode: {result['encode_mpix_per_s']:.1f} Mpix/s")
print(f"Decode: {result['decode_mpix_per_s']:.1f} Mpix/s")

# Quality sweep across quality levels
results = quality_sweep(image, qualities=[10, 25, 50, 75, 90, 95])

# Compare subsampling modes
results = compare_sampling(image, quality=85)
```

---

## Cross-Compatibility

The encoder produces standard JFIF JPEG files that are decodable by:
- Pillow / libjpeg
- Web browsers
- Image viewers
- Any standard JPEG decoder

The decoder can read JPEG files produced by:
- This codec
- Pillow / libjpeg
- Most baseline JPEG encoders

**Verified results** (256×256 smooth gradient, quality 90):

| Direction | PSNR |
|-----------|------|
| Our encode → our decode | 49.34 dB |
| Pillow encode → our decode | 49.89 dB |
| Our encode → Pillow decode | 49.99 dB |

---

## Examples

Five runnable example scripts are provided in `examples/`:

| Script | Description |
|--------|-------------|
| `basic_roundtrip.py` | Simple encode/decode with PSNR/SSIM |
| `quality_sweep.py` | PSNR/SSIM across quality 10–95 |
| `compare_sampling.py` | Compare 4:4:4, 4:2:2, 4:2:0, 4:1:1 |
| `config_and_metadata.py` | Config file + JPEG metadata inspection |
| `grayscale_restart.py` | Grayscale encoding with restart markers |

Run them with:

```bash
cd jpeg-codec
PYTHONPATH=. python3 examples/basic_roundtrip.py
```

### Sample Output (Quality Sweep)

```
 Quality |  PSNR (dB) | SSIM    |  Size  |   Ratio  |   BPP
--------|------------|---------|--------|----------|--------
     10 |      26.07 |  0.7584 |   1067 |    46.07 |   0.17
     25 |      27.84 |  0.8532 |   1375 |    35.75 |   0.22
     50 |      32.80 |  0.9331 |   1537 |    31.98 |   0.25
     75 |      33.95 |  0.9388 |   1784 |    27.55 |   0.29
     85 |      35.16 |  0.9525 |   2197 |    22.37 |   0.36
     90 |      35.96 |  0.9657 |   2590 |    18.98 |   0.42
     95 |      36.47 |  0.9699 |   2962 |    16.59 |   0.48
```

---

## Quality and Subsampling Guide

| Quality | Use Case | Typical Compression |
|---------|----------|-------------------|
| 10–30 | Thumbnails, previews | 50:1 – 100:1 |
| 40–60 | Web images | 20:1 – 40:1 |
| 70–85 | Good quality photos | 10:1 – 20:1 |
| 90–95 | High quality | 5:1 – 10:1 |
| 100 | Near-lossless | 2:1 – 5:1 |

| Subsampling | Chroma Resolution | Best For |
|-------------|------------------|----------|
| 4:4:4 | Full | Computer graphics, sharp edges |
| 4:2:2 | Horizontal ½ | Video, photography |
| 4:2:0 | Horizontal+Vertical ½ | General photos (default) |
| 4:1:1 | Horizontal ¼ | Low-quality, high compression |

---

## Testing

```bash
# Run all 66 tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=jpeg_codec --cov-report=term-missing

# Run specific test class
python -m pytest tests/test_jpeg_codec.py::TestDCT -v
```

Test coverage includes:
- Color conversion roundtrips
- DCT/inverse DCT accuracy (single + batch)
- Quantization/dequantization
- Zig-zag/inverse zig-zag
- Huffman encoding/decoding
- Bit I/O with byte-stuffing
- Subsample/upsample
- Full encode/decode roundtrips (RGB, grayscale, various qualities/sampling)
- Cross-compatibility with Pillow
- Quality metrics (PSNR, SSIM, MSE)
- Config file loading/saving
- Exception handling
- Metadata inspection
- Comment and restart markers
- Edge cases (odd dimensions, 1×1 images, uniform images)

---

## Roadmap

- [ ] **Progressive JPEG** (SOF2) — multi-scan encoding for progressive
      display
- [ ] **Optimized Huffman tables** — generate Huffman tables from actual
      coefficient statistics
- [ ] **12-bit precision** — support 12-bit sample depth
- [ ] **Arithmetic coding** — alternative entropy coding mode
- [ ] **EXIF metadata** — parse and write EXIF/APP1 segments
- [ ] **ICC color profiles** — embed ICC profile (APP2)
- [ ] **Numba/Cython acceleration** — JIT compilation for performance
- [ ] **MS-SSIM** — multi-scale structural similarity metric
- [ ] **Fuzz testing** — robustness against malformed input
- [ ] **Streaming encoder/decoder** — process images in chunks for
      memory-constrained environments

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code
style, and areas for contribution.

---

## Changelog

### v2.0.0 — Comprehensive Improvement

**New Modules:**
- `metrics.py` — PSNR, SSIM (Wang et al. 2004), MSE, RMSE, quality reports
- `batch_dct.py` — Vectorized batch DCT using NumPy einsum
- `config.py` — JSON/YAML/TOML configuration file support
- `info.py` — JPEG metadata inspection (JPEGInfo dataclass)
- `restart.py` — Restart markers (DRI/RST) and COM segment utilities
- `benchmark.py` — Performance benchmarking and quality sweeps
- `exceptions.py` — Custom exception hierarchy
- `logging_setup.py` — Configurable logging

**Encoder Enhancements:**
- Comment (COM marker) embedding
- Restart markers (RST0–RST7) with DRI segment
- DPI/pixel density metadata in JFIF header
- Comprehensive input validation
- Image value clipping to [0, 255]
- Structured logging

**Decoder Enhancements:**
- COM marker parsing
- DRI/restart interval parsing
- Restart marker handling during decode
- JFIF metadata extraction (version, density)
- Non-baseline SOF detection with `UnsupportedFeatureError`
- Robust error handling with custom exceptions
- Structured logging

**CLI Enhancements:**
- `--metrics` flag for full quality reports
- `sweep` subcommand for quality sweeps
- `bench` subcommand for benchmarking
- `compare` subcommand for sampling mode comparison
- `config` subcommand for config file management
- `--verbose` / `-v` flag for debug logging
- `--config` flag for config file input

**Developer Experience:**
- 66-test pytest suite (10 test classes)
- GitHub Actions CI (Python 3.9–3.12)
- `pyproject.toml` for installable package
- Type hints on all public functions
- Comprehensive docstrings
- 5 example scripts
- `CONTRIBUTING.md` with architecture overview
- `LICENSE` (MIT)

### v1.0.0 — Initial Release

- Baseline JPEG encoder/decoder from scratch
- 11 core modules
- CLI with encode/decode/roundtrip/info
- Standard Huffman and quantization tables
- Cross-compatibility with Pillow/libjpeg
- RGB and grayscale support
- 4:4:4, 4:2:2, 4:2:0, 4:1:1 subsampling

---

## License

MIT License — see [LICENSE](LICENSE).