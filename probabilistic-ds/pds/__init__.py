"""
Probabilistic Data Structures Toolkit
=====================================

A collection of memory-efficient probabilistic data structures implemented
from scratch in pure Python.

Structures:
    BloomFilter      – approximate set membership (no false negatives)
    CountingBloomFilter  – deletable Bloom filter variant
    CuckooFilter     – approximate set membership with deletion & better space
    CountMinSketch   – approximate frequency estimation
    HyperLogLog      – approximate cardinality estimation
    TopK             – heavy-hitters tracking (Space-Saving algorithm)
    TDigest          – approximate streaming quantiles
    SkipList         – probabilistic ordered map (support structure)

Each structure trades exactness for dramatic memory savings and/or speed.
"""
from .bloom import BloomFilter, CountingBloomFilter
from .cuckoo import CuckooFilter
from .countmin import CountMinSketch
from .hll import HyperLogLog
from .topk import TopK
from .tdigest import TDigest
from .skiplist import SkipList

__version__ = "1.0.0"
__all__ = [
    "BloomFilter",
    "CountingBloomFilter",
    "CuckooFilter",
    "CountMinSketch",
    "HyperLogLog",
    "TopK",
    "TDigest",
    "SkipList",
]