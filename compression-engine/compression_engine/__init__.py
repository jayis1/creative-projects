"""
compression-engine: A from-scratch data compression engine implementing
Huffman coding, LZ77, Burrows-Wheeler Transform, RLE, Delta encoding,
DEFLATE-like codec, codec pipelines, and compression analysis tools.
"""

__version__ = "2.0.0"

from .huffman import HuffmanCodec
from .lz77 import LZ77Codec
from .bwt import BWTCodec
from .deflate import DeflateCodec
from .rle import RLECodec
from .delta import DeltaCodec
from .pipeline import Pipeline, create_pipeline, CODEC_REGISTRY
from .bitio import BitReader, BitWriter
from .analysis import (
    shannon_entropy,
    frequency_distribution,
    optimal_compression_ratio,
    compressibility_score,
    byte_histogram,
    unique_byte_count,
    redundancy,
    analyze,
)
from .cli import main

__all__ = [
    "HuffmanCodec",
    "LZ77Codec",
    "BWTCodec",
    "DeflateCodec",
    "RLECodec",
    "DeltaCodec",
    "Pipeline",
    "create_pipeline",
    "CODEC_REGISTRY",
    "BitReader",
    "BitWriter",
    "shannon_entropy",
    "frequency_distribution",
    "optimal_compression_ratio",
    "compressibility_score",
    "byte_histogram",
    "unique_byte_count",
    "redundancy",
    "analyze",
    "main",
]