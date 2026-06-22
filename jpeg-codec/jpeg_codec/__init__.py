"""jpeg-codec: A baseline JPEG encoder/decoder implemented from scratch.

This package provides a complete (baseline / sequential DCT) JPEG codec:
  - RGB <-> YCbCr colour-space conversion
  - Chroma subsampling (4:4:4, 4:2:2, 4:2:0, 4:1:1)
  - Forward / inverse 8x8 Discrete Cosine Transform (DCT)
  - Quantisation with standard JPEG luminance / chrominance tables
  - Zig-zag reordering
  - Run-length / differential encoding of DC & AC coefficients
  - Canonical Huffman coding with standard JPEG tables
  - Full JFIF file writer / reader (markers, segments, scan header)
  - Comment (COM) marker and restart marker (DRI/RST) support
  - Image quality metrics (PSNR, SSIM, MSE)
  - Configuration file support (JSON/YAML/TOML)
  - Comprehensive metadata inspection
  - Benchmarking utilities

Public API
----------
``encode``  -- encode an RGB / grayscale numpy array to raw JPEG bytes
``decode``  -- decode raw JPEG bytes back into an RGB / grayscale numpy array

The package also exposes the building blocks (dct, huffman, quantize, etc.)
for educational / experimental use.
"""

from .encoder import encode, encode_image
from .decoder import decode, decode_image
from .color import rgb_to_ycbcr, ycbcr_to_rgb
from .dct import dct2d, idct2d
from .quantize import quantize_block, dequantize_block
from .huffman import build_huffman_table, HuffmanTree
from .zigzag import ZIGZAG_ORDER, IZIGZAG_ORDER, zigzag_block, izigzag_block
from .metrics import psnr, ssim, mse, quality_report
from .config import EncodingConfig, load_config, save_config
from .exceptions import (
    JPEGError, EncodingError, DecodingError,
    InvalidMarkerError, UnsupportedFeatureError,
    TruncatedDataError, InvalidQualityError, InvalidSamplingError,
    InvalidImageError,
)
from .info import JPEGInfo, get_info

__all__ = [
    # Core encode/decode
    "encode", "encode_image",
    "decode", "decode_image",
    # Building blocks
    "rgb_to_ycbcr", "ycbcr_to_rgb",
    "dct2d", "idct2d",
    "quantize_block", "dequantize_block",
    "build_huffman_table", "HuffmanTree",
    "ZIGZAG_ORDER", "IZIGZAG_ORDER",
    "zigzag_block", "izigzag_block",
    # Metrics
    "psnr", "ssim", "mse", "quality_report",
    # Config
    "EncodingConfig", "load_config", "save_config",
    # Metadata
    "JPEGInfo", "get_info",
    # Exceptions
    "JPEGError", "EncodingError", "DecodingError",
    "InvalidMarkerError", "UnsupportedFeatureError",
    "TruncatedDataError", "InvalidQualityError",
    "InvalidSamplingError", "InvalidImageError",
]

__version__ = "2.0.0"