# Contributing to jpeg-codec

Thank you for your interest in contributing! This document covers the
basics of setting up a development environment and submitting changes.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/jpeg-codec

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install numpy pillow pytest pytest-cov

# Install in development mode
pip install -e .
```

## Running Tests

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=jpeg_codec --cov-report=term-missing

# Run a specific test class
python -m pytest tests/test_jpeg_codec.py::TestDCT -v
```

## Code Style

- Follow PEP 8 (use `flake8` or your editor's linter)
- Add type hints to all public functions
- Add docstrings to all public functions and classes
- Keep functions focused — if a function exceeds ~50 lines, consider
  splitting it

## Submitting Changes

1. Create a branch for your feature or fix
2. Write tests for any new functionality
3. Ensure all tests pass: `python -m pytest tests/ -v`
4. Write a clear commit message
5. Push and open a pull request

## Areas for Contribution

- **Optimized Huffman tables**: Implement Huffman table optimization
  based on actual coefficient statistics (currently uses standard tables)
- **Progressive JPEG**: Add support for SOF2 progressive encoding
- **Optimized baseline**: Implement sequential encoding with optimized
  Huffman tables (SOF0 + optimized DHT)
- **12-bit precision**: Support 12-bit sample precision (SOF0 with
  precision=12)
- **Arithmetic coding**: Support arithmetic coding as an alternative
  to Huffman coding
- **Performance**: Further optimize the encode/decode pipeline, possibly
  with Cython or Numba
- **More metrics**: Add MS-SSIM, VIF, or other perceptual quality metrics
- **Fuzzing**: Add fuzz tests for the decoder to ensure robustness
  against malformed input

## Architecture Overview

The codec is organized into focused modules:

```
jpeg_codec/
├── __init__.py       # Public API exports
├── color.py          # RGB ↔ YCbCr, level shift
├── dct.py            # Forward/inverse 8×8 DCT-II
├── batch_dct.py      # Vectorized batch DCT (einsum)
├── quantize.py       # Quantization tables and scaling
├── zigzag.py         # Zig-zag scan order
├── huffman.py        # Huffman tables, magnitude-category coding
├── entropy.py        # DC/AC coefficient entropy coding
├── bitio.py          # Bit-level reader/writer with byte-stuffing
├── subsample.py      # Chroma up/downsampling
├── encoder.py        # Full JPEG encoder
├── decoder.py        # Full JPEG decoder
├── cli.py            # Command-line interface
├── metrics.py        # PSNR, SSIM, MSE, quality reports
├── config.py         # Configuration file support
├── info.py           # JPEG metadata inspection
├── restart.py        # Restart markers and COM segments
├── benchmark.py      # Performance benchmarking
├── exceptions.py     # Custom exception hierarchy
└── logging_setup.py  # Logging configuration
```

When adding a new feature, try to keep it in a focused module and
export it from `__init__.py`.