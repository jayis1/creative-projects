# jpeg-codec

A from-scratch implementation of the baseline (sequential DCT) JPEG codec.

This project implements the complete JPEG pipeline — encoding and decoding —
without using any image-processing libraries.  Only NumPy is used for array
operations; all JPEG-specific logic (DCT, quantization, Huffman coding,
bit-level I/O, JFIF file format) is implemented from first principles.

## Features

- **Full baseline JPEG encode/decode** — produces standard JFIF `.jpg` files
  that can be decoded by any JPEG reader (e.g., Pillow/libjpeg, web browsers)
- **RGB and grayscale** support
- **Chroma subsampling**: 4:4:4, 4:2:2, 4:2:0, 4:1:1
- **Quality control**: 1–100 (libjpeg-compatible scaling)
- **Standard JPEG Huffman and quantization tables** (Annex K)
- **Canonical Huffman coding** with proper byte-stuffing (0xFF → 0xFF 0x00)
- **8×8 Type-II DCT** via separable matrix multiplication
- **Zig-zag scan ordering** for run-length encoding efficiency
- **Differential DC coding** (diff from previous block)
- **Run-length + magnitude-category AC coding** with ZRL and End-of-Block
- **Command-line tool** for encoding, decoding, round-trip testing, and
  JPEG structure inspection

## How It Works

### Encoding Pipeline

1. **Color transform**: RGB → YCbCr (ITU-R BT.601)
2. **Chroma subsampling**: Cb/Cr channels downsampled by averaging
3. **Block splitting**: Each channel split into 8×8 blocks
4. **Level shift**: Pixel values shifted from [0,255] to [-128,127]
5. **Forward DCT**: 2D Type-II DCT of each block (separable: C·block·Cᵀ)
6. **Quantization**: DCT coefficients divided by quality-scaled quant table
7. **Zig-zag scan**: Coefficients reordered in zig-zag order
8. **Entropy coding**:
   - DC: differential from previous block → (SIZE, VALUE) Huffman coding
   - AC: run-length of zeros + (RUN, SIZE, VALUE) Huffman coding
   - Special symbols: End-of-Block (0x00), ZRL (0xF0 for 16 zeros)
9. **Bit packing**: MSB-first with JPEG byte-stuffing
10. **JFIF file writing**: SOI, APP0, DQT, SOF0, DHT, SOS, entropy data, EOI

### Decoding Pipeline

The reverse: parse markers → read quantization/Huffman tables → entropy
decode → dequantize → inverse DCT → level unshift → upsample chroma →
YCbCr → RGB.

### Architecture

```
jpeg_codec/
├── __init__.py       # Public API
├── color.py          # RGB ↔ YCbCr, level shift
├── dct.py            # Forward/inverse 8×8 DCT-II
├── quantize.py       # Quantization tables and scaling
├── zigzag.py         # Zig-zag scan order
├── huffman.py        # Huffman tables, magnitude-category coding
├── entropy.py        # DC/AC coefficient entropy coding
├── bitio.py          # Bit-level reader/writer with byte-stuffing
├── subsample.py      # Chroma up/downsampling
├── encoder.py        # Full JPEG encoder
├── decoder.py        # Full JPEG decoder
└── cli.py            # Command-line interface
```

## Usage

### Python API

```python
from jpeg_codec import encode, decode
import numpy as np

# Create or load an image (H×W×3 uint8)
image = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)

# Encode to JPEG bytes
jpeg_bytes = encode(image, quality=90, sampling="4:2:0")

# Decode back to numpy array
reconstructed = decode(jpeg_bytes)
```

### Command Line

```bash
# Encode an image to JPEG
python -m jpeg_codec.cli encode input.png output.jpg --quality 80 --sampling 4:2:0

# Decode a JPEG to an image
python -m jpeg_codec.cli decode input.jpg output.png

# Round-trip test (reports PSNR and compression ratio)
python -m jpeg_codec.cli roundtrip input.png --quality 90 --sampling 4:2:0

# Inspect JPEG marker structure
python -m jpeg_codec.cli info input.jpg
```

### Quality and Subsampling

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

## Compatibility

The encoder produces standard JFIF JPEG files that are decodable by:
- Pillow / libjpeg
- Web browsers
- Image viewers
- Any standard JPEG decoder

The decoder can read JPEG files produced by:
- This codec
- Pillow / libjpeg
- Most baseline JPEG encoders

## Requirements

- Python 3.8+
- NumPy
- Pillow (optional, for CLI image I/O with PNG/JPEG files)