"""
FM-Index: a compressed full-text index in pure Python.

Combines the Burrows-Wheeler Transform (BWT), a wavelet tree (or wavelet
matrix) for rank/select queries, the LF-mapping, and a sampled suffix
array to support:

  - count(pattern): number of occurrences of a pattern in the text
  - locate(pattern): the starting positions of all occurrences
  - extract(pos, length): arbitrary substring retrieval
  - search with mismatches via backtracking over the BWT

The package is organised into small, focused modules:

  :mod:`wavelet`        — balanced wavelet tree with rank/select over a bit array
  :mod:`wavelet_matrix` — level-ordered wavelet matrix (alternative backend)
  :mod:`bwt`            — Burrows-Wheeler Transform via suffix array
  :mod:`suffix_array`   — O(n log^2 n) prefix-doubling suffix array construction
  :mod:`index`          — FMIndex tying everything together
  :mod:`searchers`      — high-level search utilities (regex, MUMs, repeats)
  :mod:`rle`            — run-length encoding for BWT compression
  :mod:`serialize`      — JSON + binary serialization
  :mod:`analysis`       — match clustering & coverage analysis
  :mod:`text_stats`     — information-theoretic text statistics
  :mod:`visualize`      — ASCII visualizations of index internals
  :mod:`config`         — YAML/JSON/TOML configuration
  :mod:`logging_utils`  — logging setup and timing helpers
  :mod:`errors`         — exception hierarchy
  :mod:`cli`            — command-line interface
"""

from .index import FMIndex, FMIndexMatch
from .bwt import bwt_encode, bwt_decode
from .wavelet import WaveletTree, BitArray
from .wavelet_matrix import WaveletMatrix
from .suffix_array import build_suffix_array, build_suffix_array_naive
from . import serialize
from . import analysis
from . import searchers
from . import rle
from . import text_stats
from . import visualize
from . import config
from . import logging_utils
from . import errors

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
    "searchers",
    "rle",
    "text_stats",
    "visualize",
    "config",
    "logging_utils",
    "errors",
]

__version__ = "2.0.0"