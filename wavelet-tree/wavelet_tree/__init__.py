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
    interval_symbols,
)
from .serialization import save, load

__version__ = "1.0.0"

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
    "interval_symbols",
    "save",
    "load",
]