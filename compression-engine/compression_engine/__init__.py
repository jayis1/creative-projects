"""
compression-engine: A from-scratch data compression engine implementing
Huffman coding, LZ77, Burrows-Wheeler Transform, and a DEFLATE-like codec
with bit-level I/O, adaptive coding, and a CLI interface.
"""

__version__ = "1.0.0"

from .huffman import HuffmanCodec
from .lz77 import LZ77Codec
from .bwt import BWTCodec
from .deflate import DeflateCodec
from .bitio import BitReader, BitWriter
from .cli import main

__all__ = [
    "HuffmanCodec",
    "LZ77Codec",
    "BWTCodec",
    "DeflateCodec",
    "BitReader",
    "BitWriter",
    "main",
]