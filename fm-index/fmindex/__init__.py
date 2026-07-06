"""
FM-Index: a compressed full-text index in pure Python.

Combines the Burrows-Wheeler Transform (BWT), a wavelet tree for rank/select
queries, the LF-mapping, and a sampled suffix array to support:
  - count(pattern): number of occurrences of a pattern in the text
  - locate(pattern): the starting positions of all occurrences
  - extract(pos, length): arbitrary substring retrieval
  - search with mismatches via backtracking over the BWT

The package is organised into small, focused modules:

  :mod:`wavelet`   - balanced wavelet tree with rank/select over a bit array
  :mod:`bwt`       - Burrows-Wheeler Transform via suffix array
  :mod:`suffix_array` - O(n log^2 n) prefix-doubling suffix array construction
  :mod:`index`     - FMIndex tying everything together
  :mod:`cli`       - command-line interface
"""

from .index import FMIndex, FMIndexMatch
from .bwt import bwt_encode, bwt_decode
from .wavelet import WaveletTree, BitArray
from .wavelet_matrix import WaveletMatrix
from .suffix_array import build_suffix_array, build_suffix_array_naive
from . import serialize
from . import analysis

__all__ = [
    "FMIndex",
    "FMIndexMatch",
    "bwt_encode",
    "bwt_decode",
    "WaveletTree",
    "WaveletMatrix",
    "BitArray",
    "build_suffix_array",
    "build_suffix_array_naive",
    "serialize",
    "analysis",
]

__version__ = "1.1.0"