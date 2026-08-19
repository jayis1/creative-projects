"""
wavelet_tree: A succinct data structure library implementing Wavelet Trees
and Wavelet Matrices for sequence analysis with rank/select/access operations.

Pure Python, no external dependencies.
"""

from .bitvector import BitVector, BlockedBitVector
from .rrr_bitvector import RRRBitVector
from .base import WaveletBase
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
    range_report,
    range_report_all,
    range_top_k,
    range_bottom_k,
)
from .serialization import save, load
from .config import Config
from .fm_index import FMIndex, backward_search, compute_bwt, compute_c_array
from .stats import (
    space_stats,
    tree_stats,
    benchmark,
    benchmark_report,
    SpaceStats,
    TreeStats,
    BenchmarkResult,
)

__version__ = "3.0.0"

__all__ = [
    # Base class
    "WaveletBase",
    # BitVectors
    "BitVector",
    "BlockedBitVector",
    "RRRBitVector",
    # Structures
    "WaveletTree",
    "WaveletMatrix",
    "HuffmanWaveletTree",
    "HuffmanWaveletMatrix",
    "build_huffman_code",
    # Queries
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
    "range_report",
    "range_report_all",
    "range_top_k",
    "range_bottom_k",
    # Serialization
    "save",
    "load",
    # Config
    "Config",
    # FM-Index
    "FMIndex",
    "backward_search",
    "compute_bwt",
    "compute_c_array",
    # Stats
    "space_stats",
    "tree_stats",
    "benchmark",
    "benchmark_report",
    "SpaceStats",
    "TreeStats",
    "BenchmarkResult",
]