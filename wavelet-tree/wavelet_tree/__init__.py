"""
wavelet_tree: A succinct data structure library implementing Wavelet Trees
and Wavelet Matrices for sequence analysis with rank/select/access operations.

Pure Python, no external dependencies.
"""

from .bitvector import BitVector, BlockedBitVector
from .wavelet_tree import WaveletTree
from .wavelet_matrix import WaveletMatrix
from .huffman import HuffmanWaveletTree, HuffmanWaveletMatrix, build_huffman_code
from .queries import (
    range_quantile,
    range_count,
    range_next_value,
    range_prev_value,
    range_min,
    range_max,
    interval_symbols,
    range_intersection,
    prefix_search,
    count_distinct,
)
from .serialization import save, load
from .config import Config

__version__ = "2.0.0"

__all__ = [
    "BitVector",
    "BlockedBitVector",
    "WaveletTree",
    "WaveletMatrix",
    "HuffmanWaveletTree",
    "HuffmanWaveletMatrix",
    "build_huffman_code",
    "range_quantile",
    "range_count",
    "range_next_value",
    "range_prev_value",
    "range_min",
    "range_max",
    "interval_symbols",
    "range_intersection",
    "prefix_search",
    "count_distinct",
    "save",
    "load",
    "Config",
]