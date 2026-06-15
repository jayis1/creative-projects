# Compression Engine

A from-scratch data compression engine implementing multiple algorithms with codec pipelines, analysis tools, and CRC32 integrity verification.

## Overview

This project implements six compression codecs from scratch (no external compression libraries), plus a pipeline system for chaining codecs, and analysis tools for measuring data compressibility.

### Codecs

| Codec | Description | Best For |
|-------|-------------|----------|
| **Huffman** | Canonical Huffman coding with optimal prefix codes | General-purpose, data with skewed byte distributions |
| **LZ77** | Sliding-window dictionary compression | Text with repeated patterns, moderate compression |
| **BWT** | Burrows-Wheeler Transform + Move-to-Front + RLE | Data with context-dependent patterns, similar to bzip2 |
| **DEFLATE** | LZ77 tokenization + static Huffman coding | General-purpose, balanced speed/ratio (like zlib) |
| **RLE** | Run-Length Encoding | Data with long runs of identical bytes |
| **Delta** | Delta encoding with zigzag varint | Time-series, sorted sequences, audio waveforms |

### Codec Pipelines

Chain multiple codecs together for better compression. For example:
- `rle+huffman` — RLE pre-processing followed by Huffman coding
- `rle+lz77` — RLE before LZ77 sliding window
- `delta+huffman` — Delta encoding then Huffman (great for numeric sequences)
- `delta+deflate` — Delta then DEFLATE (best overall for time-series)
- `rle+deflate` — RLE then DEFLATE (best for data with long runs)

### Analysis Tools

- **Shannon entropy**: Measure information content in bits/symbol
- **Optimal compression ratio**: Theoretical best possible compression
- **Compressibility score**: 0 (random) to 1 (fully compressible)
- **Byte histogram**: Frequency distribution of byte values
- **Redundancy**: Fraction of data that is redundant

## Architecture

### Core Components

- `bitio.py` — Bit-level I/O (MSB-first) with `BitWriter` and `BitReader`
- `huffman.py` — Canonical Huffman coding with EOF symbol and CRC32
- `lz77.py` — LZ77 sliding-window with configurable window size and CRC32
- `bwt.py` — BWT + Move-to-Front + RLE pipeline with CRC32
- `deflate.py` — DEFLATE-like codec (LZ77 + static Huffman) with CRC32
- `rle.py` — Run-Length Encoding with 0xFF escape sequences and CRC32
- `delta.py` — Delta encoding (byte/uint16/uint32 modes, zigzag varints) with CRC32
- `pipeline.py` — Codec chaining framework with serializable format
- `analysis.py` — Compression analysis and entropy calculations
- `cli.py` — Command-line interface with compress/decompress/benchmark/analyze

### Data Format (with CRC32 Integrity)

Every codec stores a header before the compressed payload:

| Field | Size | Description |
|-------|------|-------------|
| Original Length | 4 bytes | Little-endian, original data size |
| CRC32 | 4 bytes | Checksum of original data |

On decompression, the CRC32 is verified. Any data corruption raises `ValueError`.

### RLE Escape Scheme

- Non-0xFF bytes emitted literally for singles and pairs
- Runs of 3+ identical bytes: `0xFF, byte, count` where count = run_length - 2
- Single 0xFF byte: `0xFF, 0xFF, 0x00` (escape + value + zero count)
- Run of 3+ 0xFF bytes: `0xFF, 0xFF, count` (escape + value + count)

### Delta Encoding

- Mode 0 (byte): Byte-level deltas with wrapping `& 0xFF`
- Mode 1 (uint16): 16-bit little-endian value deltas
- Mode 2 (uint32): 32-bit little-endian value deltas
- Auto-detect: Automatically selects the best mode based on data characteristics
- Deltas encoded as zigzag + variable-length integers for compactness

## Usage

### Command-Line

```bash
# Compress with default codec (deflate)
python3 -m compression_engine compress input.txt -o output.bin

# Compress with specific codec
python3 -m compression_engine compress input.txt -c huffman -o output.bin

# Compress with pipeline
python3 -m compression_engine compress input.txt -p rle+huffman -o output.bin

# Decompress
python3 -m compression_engine decompress output.bin -c deflate -o restored.txt

# Decompress with pipeline (codecs applied in reverse)
python3 -m compression_engine decompress output.bin -p delta+huffman -o restored.txt

# Benchmark all codecs on input
python3 -m compression_engine benchmark input.txt

# Analyze compressibility
python3 -m compression_engine analyze input.txt
```

### Python API

```python
from compression_engine import (
    HuffmanCodec, LZ77Codec, BWTCodec, DeflateCodec,
    RLECodec, DeltaCodec, Pipeline, create_pipeline,
    analyze, shannon_entropy
)

# Simple compression
codec = DeflateCodec()
compressed = codec.compress(b"hello world " * 100)
original = codec.decompress(compressed)
assert original == b"hello world " * 100

# Pipeline compression
pipe = create_pipeline("rle+huffman")
compressed = pipe.compress(data)
original = pipe.decompress(compressed)

# Analysis
result = analyze(data)
print(f"Entropy: {result['entropy_bits']:.2f} bits/symbol")
print(f"Compressibility: {result['compressibility']:.1%}")
print(f"Optimal ratio: {result['optimal_ratio']:.1%}")
```

## Testing

```bash
python3 -m pytest tests/ -v
```

104 tests covering all codecs, pipeline, analysis, bit I/O, CRC32 integrity, and edge cases.

## Implementation Notes

- All algorithms implemented from scratch in Python
- Bit I/O is MSB-first for multi-bit writes (`write_bits`), matching Huffman coding conventions
- DEFLATE uses static Huffman tables per the RFC 1951 specification
- BWT uses lexicographic sorting with O(n log² n) Python sort
- CRC32 uses `zlib.crc32` for reliable checksum computation
- Pipeline format stores codec names for reconstruction during decompression

## Known Issues (Resolved)

| # | Bug | Severity | Fix |
|---|-----|----------|-----|
| 1 | **LZ77 hardcoded min_match=3 in decompress** — The decompressor always used `min_match=3` regardless of the encoder's actual `min_match` setting, causing corrupted output for `LZ77Codec(min_match=4+)`. | High | Added `min_match` as an 8-bit value in the LZ77 header (after offset/length bit widths), read during decompression. |
| 2 | **Delta codec uint16/uint32 modes lose trailing bytes** — When data length wasn't a multiple of the element size (e.g., 5 bytes with uint16 mode), trailing bytes were silently dropped during compression and decompression. | High | Added a `n_vals` count (2-byte LE) to the delta payload header; trailing bytes are now stored literally after the delta stream. |
| 3 | **Delta auto-detect false positives** — The `_detect_mode` method could incorrectly select uint16/uint32 modes for very short data (e.g., 2 bytes) because `all(...)` on an empty delta list returns True. | Medium | Added `len(vals) >= 2` guard before computing deltas in auto-detect. |
| 4 | **BWT empty data header too short** — Compressing empty data returned only 8 bytes (length+CRC32), but decompress expected 16 bytes (4 fields). | Low | Fixed empty-data path to emit all 4 header fields (16 bytes). |
| 5 | **RLE escape byte decoding failures** — The original RLE codec had inconsistent escape handling; 0xFF bytes in data and run markers were confused, causing length mismatches on nearly all non-trivial inputs. | Critical | Rewrote RLE codec with clean escape scheme: runs of 3+ encoded as `0xFF, byte, count`; single 0xFF as `0xFF, 0xFF, 0x00`; literals for singles/pairs of non-0xFF bytes. |