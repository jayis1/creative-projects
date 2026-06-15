# Compression Engine

A from-scratch data compression engine implementing four classic compression algorithms with bit-level I/O, canonical Huffman coding, and a CLI interface.

## Algorithms

| Codec | Description |
|-------|-------------|
| **Huffman** | Canonical Huffman coding with frequency analysis and serialized code tables |
| **LZ77** | Sliding-window dictionary compression with configurable window/min-match parameters |
| **BWT** | Burrows-Wheeler Transform + Move-to-Front encoding + Run-Length Encoding |
| **DEFLATE** | DEFLATE-like codec combining LZ77 tokenization with static Huffman coding (length/distance tables) |

## How It Works

### Huffman Coding
1. Build a frequency table of all byte values (0-255) plus an EOF symbol (256)
2. Construct a Huffman tree using a min-heap priority queue
3. Derive bit lengths, then build canonical Huffman codes (shorter codes for more frequent symbols)
4. Serialize: write original length, code-length table, then the bitstream

### LZ77
1. Maintain a sliding window over previously-seen data
2. For each position, search backward in the window for the longest match
3. Emit either a literal byte (flag=0) or a (offset, length) pair (flag=1)
4. Offset and length are encoded with variable bit widths based on window size

### BWT (Burrows-Wheeler Transform)
1. Compute the BWT by sorting all cyclic rotations of the input
2. The transform output is the last column of the sorted rotation matrix
3. Apply Move-to-Front (MTF) encoding to convert BWT's clustered symbols to small integers
4. Apply Run-Length Encoding (RLE) to compress runs in the MTF output
5. Inverse uses the LF-mapping technique for exact reconstruction

### DEFLATE-like
1. LZ77 pass produces literal/length/distance tokens
2. Lengths mapped to DEFLATE-compatible codes (257-285) with extra bits
3. Distances mapped to DEFLATE-compatible codes (0-29) with extra bits
4. Static Huffman coding: fixed code lengths (8/9 bits for literals, 7/8 for lengths, 5 for distances)
5. Block format with BFINAL/BTYPE headers

## Usage

### Command Line

```bash
# Compress a file with DEFLATE
python3 -m compression_engine compress input.txt -o output.def -c deflate -v

# Decompress
python3 -m compression_engine decompress output.def -o restored.txt -c deflate -v

# Benchmark all codecs
python3 -m compression_engine benchmark input.txt

# Use different codecs
python3 -m compression_engine compress data.bin -c huffman -v
python3 -m compression_engine compress data.bin -c lz77 -v
python3 -m compression_engine compress data.bin -c bwt -v
```

### Python API

```python
from compression_engine import HuffmanCodec, LZ77Codec, BWTCodec, DeflateCodec

# Huffman
codec = HuffmanCodec()
compressed = codec.compress(b"hello world")
decompressed = codec.decompress(compressed)
assert decompressed == b"hello world"

# LZ77 with custom window
codec = LZ77Codec(window_size=8192, min_match=3, max_match=258)
compressed = codec.compress(b"repeat repeat repeat")
decompressed = codec.decompress(compressed)

# BWT
codec = BWTCodec()
compressed = codec.compress(b"banana")
decompressed = codec.decompress(compressed)

# DEFLATE
codec = DeflateCodec(window_size=32768)
compressed = codec.compress(b"some data to compress")
decompressed = codec.decompress(compressed)
```

## Architecture

```
compression_engine/
├── __init__.py        # Package exports
├── __main__.py        # python -m entry point
├── bitio.py           # BitReader / BitWriter (bit-level I/O)
├── huffman.py         # Canonical Huffman codec
├── lz77.py            # LZ77 sliding-window codec
├── bwt.py             # BWT + MTF + RLE codec
├── deflate.py         # DEFLATE-like codec (LZ77 + Huffman)
└── cli.py             # CLI: compress, decompress, benchmark
```

## Testing

```bash
pytest tests/ -v
```

## Limitations

- Huffman codec limited to 65535 bytes (2-byte length header)
- BWT uses O(n²) rotation sort — practical for inputs up to ~100KB
- DEFLATE implements static Huffman only (no dynamic Huffman blocks)
- No stored (uncompressed) block type in DEFLATE