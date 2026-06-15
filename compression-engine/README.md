# 🔧 Compression Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 203](https://img.shields.io/badge/tests-203%20passing-brightgreen.svg)](tests/)
[![Code Style: Type Hints](https://img.shields.io/badge/code%20style-type%20hinted-orange.svg)](compression_engine/)

A **from-scratch** data compression engine implementing **8 codecs** with codec pipelines, analysis tools, benchmarking, configuration, and CRC32 integrity verification — all in pure Python with zero external compression dependencies.

---

## 📑 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Codecs](#codecs)
- [Codec Pipelines](#codec-pipelines)
- [Analysis Tools](#analysis-tools)
- [Benchmarking](#benchmarking)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Architecture](#architecture)
- [Data Formats](#data-formats)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **8 compression codecs**: Huffman, LZ77, BWT, DEFLATE, RLE, Delta, LZW, Arithmetic — all from scratch
- **Codec pipelines**: Chain codecs like `rle+huffman` for multi-pass compression
- **Analysis tools**: Shannon entropy, compressibility scoring, byte histograms, redundancy metrics
- **Benchmarking**: Compare codecs on any input with timing, compression ratio, and throughput
- **CRC32 integrity**: Every codec verifies data integrity on decompression
- **Abstract base class**: Enforced interface with `Codec` ABC for consistent API
- **Configuration**: JSON/YAML config files for codec presets and pipeline definitions
- **CLI**: Full command-line interface with compress, decompress, benchmark, analyze, and compare modes
- **203 tests**: Comprehensive test suite covering all codecs, edge cases, and error handling

---

## Quick Start

```python
from compression_engine import DeflateCodec, create_pipeline, analyze

# Simple compression
codec = DeflateCodec()
compressed = codec.compress(b"hello world " * 100)
original = codec.decompress(compressed)
assert original == b"hello world " * 100
print(f"Compressed {len(b'hello world ' * 100)} → {len(compressed)} bytes")

# Pipeline compression (chain codecs)
pipe = create_pipeline("rle+huffman")
compressed = pipe.compress(data)
original = pipe.decompress(compressed)

# Analysis
result = analyze(b"some data to analyze")
print(f"Entropy: {result['entropy_bits']:.2f} bits/symbol")
print(f"Compressibility: {result['compressibility']:.1%}")
```

---

## Installation

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/compression-engine

# Install in development mode
pip install -e .

# With dev dependencies (pytest, etc.)
pip install -e ".[dev]"

# Verify installation
python3 -m compression_engine --help

# Run tests
python3 -m pytest tests/ -v
```

### Requirements

- **Python 3.10+** (uses `match` statement, type hints, `X | Y` union syntax)
- **No external compression libraries** — everything is from scratch
- Optional: `pyyaml` for YAML config support (JSON works out of the box)

---

## Codecs

| Codec | Description | Best For | Ratio | Speed |
|-------|-------------|----------|-------|-------|
| **Huffman** | Canonical Huffman coding with optimal prefix codes | Skewed byte distributions | ⭐⭐⭐ | ⚡⚡⚡ |
| **LZ77** | Sliding-window dictionary with configurable window | Repeated patterns in text | ⭐⭐⭐ | ⚡⚡ |
| **BWT** | Burrows-Wheeler Transform + MTF + RLE | Context-dependent patterns | ⭐⭐⭐⭐ | ⚡ |
| **DEFLATE** | LZ77 tokenization + static Huffman coding | General-purpose balanced | ⭐⭐⭐⭐ | ⚡⚡ |
| **RLE** | Run-Length Encoding with escape sequences | Long runs of identical bytes | ⭐⭐ | ⚡⚡⚡ |
| **Delta** | Delta + zigzag varint (byte/uint16/uint32/auto) | Time-series, sorted, audio | ⭐⭐⭐ | ⚡⚡⚡ |
| **LZW** | Lempel-Ziv-Welch with GIF-style variable width | General-purpose, GIF-like | ⭐⭐⭐ | ⚡⚡ |
| **Arithmetic** | Adaptive arithmetic coding with freq model | Highly skewed distributions | ⭐⭐⭐⭐ | ⚡ |

### Codec Details

#### Huffman Coding
```python
from compression_engine import HuffmanCodec
codec = HuffmanCodec()
compressed = codec.compress(data)
```
- Builds canonical Huffman tree from byte frequencies
- Stores code-length table for decompressor reconstruction
- Includes EOF symbol for clean stream termination

#### LZ77
```python
from compression_engine import LZ77Codec
codec = LZ77Codec(window_size=4096, min_match=3)  # configurable
compressed = codec.compress(data)
```
- Configurable sliding window (default 4096 bytes)
- Configurable minimum match length
- Offset/length bit widths stored in header for correct decompression

#### BWT (Burrows-Wheeler Transform)
```python
from compression_engine import BWTCodec
compressed = BWTCodec().compress(data)
```
- Applies BWT → Move-to-Front → RLE pipeline
- Similar to bzip2's first two stages
- O(n log² n) suffix-sorted implementation

#### LZW (Lempel-Ziv-Welch)
```python
from compression_engine import LZWCodec
codec = LZWCodec(max_bits=16)  # configurable dictionary size
compressed = codec.compress(data)
```
- GIF-style variable code width (9–16 bits, default 16)
- Automatic dictionary reset when full (CLEAR_CODE)
- KwKwK special case handling for decoder synchronization

#### Arithmetic Coding
```python
from compression_engine import ArithmeticCodec
compressed = ArithmeticCodec().compress(data)
```
- 32-bit integer arithmetic with adaptive frequency model
- Near-optimal compression for skewed distributions
- Handles all byte values including extreme distributions

---

## Codec Pipelines

Chain codecs for multi-pass compression. Pipelines apply codecs left-to-right on compress, and right-to-left on decompress.

```python
from compression_engine import create_pipeline

# Create pipeline from string
pipe = create_pipeline("rle+huffman")
compressed = pipe.compress(data)
original = pipe.decompress(compressed)

# Available pipelines
pipe = create_pipeline("rle+huffman")    # RLE pre-processing → Huffman
pipe = create_pipeline("rle+lz77")       # RLE → LZ77
pipe = create_pipeline("delta+huffman")   # Delta → Huffman (great for time-series)
pipe = create_pipeline("delta+deflate")   # Delta → DEFLATE (best overall for numeric)
pipe = create_pipeline("bwt+huffman")     # BWT → Huffman
pipe = create_pipeline("rle+deflate")     # RLE → DEFLATE
```

---

## Analysis Tools

```python
from compression_engine import analyze, shannon_entropy, byte_histogram

# Full analysis
result = analyze(data)
print(f"Entropy: {result['entropy_bits']:.2f} bits/symbol")
print(f"Optimal ratio: {result['optimal_ratio']:.2%}")
print(f"Compressibility: {result['compressibility']:.2%}")
print(f"Unique bytes: {result['unique_bytes']}")
print(f"Redundancy: {result['redundancy']:.2%}")

# Individual metrics
entropy = shannon_entropy(data)          # bits per symbol
hist = byte_histogram(data)             # dict of byte → count
```

---

## Benchmarking

```python
from compression_engine import run_benchmark, benchmark_codec

# Benchmark all codecs
report = run_benchmark(data)
print(report.to_table())

# Benchmark specific codecs
report = run_benchmark(data, codecs=["deflate", "lzw", "huffman"])

# Single codec benchmark
result = benchmark_codec(DeflateCodec(), data)
print(f"Ratio: {result.ratio:.2%}, Time: {result.compress_time:.4f}s")
print(f"Space saving: {result.space_saving:.1%}")
```

Or via CLI:
```bash
python3 -m compression_engine benchmark input.txt
python3 -m compression_engine benchmark input.txt --codecs deflate,lzw,huffman
```

---

## Configuration

Create JSON or YAML config files for codec presets and pipeline definitions:

```python
from compression_engine import save_config, load_config, get_codec_config

# Save default config
save_config("compression_config.json")

# Load config
config = load_config("compression_config.json")

# Get codec settings
deflate_config = get_codec_config("deflate", config)
# Returns: {"window_size": 4096, "min_match": 3}
```

Example config file:
```json
{
  "codecs": {
    "deflate": {"window_size": 8192, "min_match": 3},
    "lzw": {"max_bits": 14},
    "delta": {"mode": "auto"}
  },
  "pipelines": {
    "fast": "rle+huffman",
    "best": "bwt+deflate"
  },
  "default_codec": "deflate"
}
```

---

## CLI Reference

```bash
# Compress
python3 -m compression_engine compress input.txt -c deflate -o output.bin
python3 -m compression_engine compress input.txt -p rle+huffman -o output.bin

# Decompress
python3 -m compression_engine decompress output.bin -c deflate -o restored.txt
python3 -m compression_engine decompress output.bin -p delta+huffman -o restored.txt

# Benchmark all codecs
python3 -m compression_engine benchmark input.txt

# Benchmark specific codecs
python3 -m compression_engine benchmark input.txt --codecs deflate,lzw,huffman

# Analyze compressibility
python3 -m compression_engine analyze input.txt

# Compare two codecs
python3 -m compression_engine compare input.txt -c1 huffman -c2 deflate

# Use config file
python3 -m compression_engine compress input.txt -c deflate --config myconfig.json

# JSON output (for scripting)
python3 -m compression_engine benchmark input.txt --format json
```

---

## Architecture

```
compression_engine/
├── __init__.py        # Public API exports
├── __main__.py        # python3 -m entry point
├── base.py           # Abstract Codec base class, exceptions, CRC32
├── bitio.py           # Bit-level I/O (BitWriter, BitReader)
├── huffman.py         # Canonical Huffman coding
├── lz77.py            # LZ77 sliding-window compression
├── bwt.py             # BWT + Move-to-Front + RLE
├── deflate.py         # DEFLATE (LZ77 + static Huffman)
├── rle.py             # Run-Length Encoding
├── delta.py           # Delta + zigzag varint encoding
├── lzw.py             # LZW with variable-width codes
├── arithmetic.py      # Adaptive arithmetic coding
├── pipeline.py        # Codec chaining framework
├── analysis.py        # Entropy & compressibility analysis
├── benchmark.py       # Benchmarking utilities
├── config.py          # Configuration file handling
├── logger.py          # Structured logging
└── cli.py             # Command-line interface
```

### Abstract Base Class

All codecs inherit from `Codec` which enforces a consistent interface:

```python
from compression_engine.base import Codec

class MyCodec(Codec):
    name = "my_codec"
    
    def compress(self, data: bytes) -> bytes:
        ...
    
    def decompress(self, data: bytes) -> bytes:
        ...
```

CRC32 integrity checking is built into the `Codec` base class — every codec automatically computes and verifies checksums.

### Exception Hierarchy

```
CompressionError (base)
├── IntegrityError  — CRC32 mismatch on decompression
└── FormatError     — Invalid compressed data format
```

---

## Data Formats

Every codec stores a header before the compressed payload:

| Field | Size | Description |
|-------|------|-------------|
| Original Length | 4 bytes | Little-endian data size |
| CRC32 | 4 bytes | Checksum of original data |

Some codecs add additional header fields:
- **LZ77**: window size (2 bytes), min_match (1 byte), offset/length bit widths
- **LZW**: max_bits (1 byte)
- **Delta**: mode (1 byte), n_vals (2 bytes for uint16/uint32 modes)
- **BWT**: additional transform metadata

---

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=compression_engine --cov-report=term-missing

# Run specific test file
python3 -m pytest tests/test_lzw.py -v

# Run only codec roundtrip tests
python3 -m pytest tests/ -k "roundtrip" -v
```

**203 tests** covering:
- All 8 codecs: basic roundtrips, edge cases (empty, single byte, all-same, all-bytes)
- CRC32 integrity verification and corruption detection
- Codec-specific features (LZ77 window sizes, LZW max_bits, Delta modes)
- Pipeline chaining with all codec combinations
- Analysis tools (entropy, histograms, compressibility)
- Benchmarking utilities
- Configuration loading/saving
- Bit I/O correctness
- Abstract base class enforcement
- Bug regression tests

---

## Known Issues (Resolved)

| # | Bug | Severity | Fix |
|---|-----|----------|-----|
| 1 | **LZ77 hardcoded min_match=3 in decompress** — Decompressor always used `min_match=3` regardless of encoder's setting, causing corruption for `LZ77Codec(min_match=4+)`. | High | Added `min_match` as an 8-bit value in the LZ77 header. |
| 2 | **Delta codec uint16/uint32 modes lose trailing bytes** — Non-aligned data lengths silently dropped trailing bytes. | High | Added `n_vals` count header; trailing bytes stored literally. |
| 3 | **Delta auto-detect false positives** — Short data (≤2 bytes) could incorrectly select uint16/uint32 modes. | Medium | Added `len(vals) >= 2` guard in `_detect_mode`. |
| 4 | **BWT empty data header too short** — Compressing empty data returned 8 bytes but decompress expected 16. | Low | Fixed empty-data path to emit all 4 header fields. |
| 5 | **RLE escape byte decoding failures** — Inconsistent escape handling caused length mismatches. | Critical | Rewrote with clean escape scheme. |
| 6 | **LZW code width transition desync** — Encoder and decoder disagreed on when to increase code width, causing `Invalid LZW code` errors. | Critical | Fixed with GIF-style synchronization: decoder bumps width when `next_code >= (1 << code_width)`, accounting for one-step lag. |
| 7 | **Arithmetic CRC32 corruption test** — Corrupting trailing padding bytes didn't trigger CRC mismatch. | Low | Changed test to corrupt core payload bytes. |

---

## Roadmap

- [ ] **Suffix array BWT** — Replace O(n log² n) sort with O(n) suffix array for large inputs
- [ ] **Hash chain LZ77** — Add hash-chain match finding for better compression ratio
- [ ] **Adaptive Huffman** — Dynamic Huffman tree updates during compression
- [ ] **Zstandard-style entropy coding** — Finite-state entropy for better speed
- [ ] **Multi-threaded pipelines** — Parallel codec stages for large data
- [ ] **Stream I/O** — Support streaming compress/decompress for large files
- [ ] **Dictionary presets** — Built-in training dictionaries for common data types
- [ ] **Compression level tuning** — Speed/ratio tradeoff knobs for each codec

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Adding new codecs (inherit from `Codec` base class)
- Writing tests (roundtrip + edge cases + CRC32 corruption)
- Code style (type hints, docstrings, 88-char line width)
- Submitting pull requests

All codecs must:
1. Inherit from `compression_engine.base.Codec`
2. Implement `compress(data: bytes) -> bytes` and `decompress(data: bytes) -> bytes`
3. Include CRC32 integrity (use `compute_crc32` / `verify_crc32` from `base.py`)
4. Have comprehensive tests in `tests/test_<codec>.py`

---

## License

[MIT License](LICENSE) — free for personal and commercial use.