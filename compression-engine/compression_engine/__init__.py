"""
compression-engine: A from-scratch data compression engine implementing
Huffman coding, LZ77, Burrows-Wheeler Transform, RLE, Delta encoding,
DEFLATE-like codec, LZW, Arithmetic coding, codec pipelines, and
compression analysis tools.
"""

__version__ = "3.0.0"

from .base import Codec, CompressionError, IntegrityError, FormatError
from .huffman import HuffmanCodec
from .lz77 import LZ77Codec
from .bwt import BWTCodec
from .deflate import DeflateCodec
from .rle import RLECodec
from .delta import DeltaCodec
from .lzw import LZWCodec
from .arithmetic import ArithmeticCodec
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
from .benchmark import (
    BenchmarkResult,
    BenchmarkReport,
    run_benchmark,
    benchmark_codec,
)
from .config import load_config, save_config, get_codec_config, resolve_pipeline
from .cli import main

__all__ = [
    # Base classes
    "Codec",
    "CompressionError",
    "IntegrityError",
    "FormatError",
    # Codecs
    "HuffmanCodec",
    "LZ77Codec",
    "BWTCodec",
    "DeflateCodec",
    "RLECodec",
    "DeltaCodec",
    "LZWCodec",
    "ArithmeticCodec",
    # Pipeline
    "Pipeline",
    "create_pipeline",
    "CODEC_REGISTRY",
    # Bit I/O
    "BitReader",
    "BitWriter",
    # Analysis
    "shannon_entropy",
    "frequency_distribution",
    "optimal_compression_ratio",
    "compressibility_score",
    "byte_histogram",
    "unique_byte_count",
    "redundancy",
    "analyze",
    # Benchmarking
    "BenchmarkResult",
    "BenchmarkReport",
    "run_benchmark",
    "benchmark_codec",
    # Configuration
    "load_config",
    "save_config",
    "get_codec_config",
    "resolve_pipeline",
    # CLI
    "main",
]