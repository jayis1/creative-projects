"""Probabilistic Data Structures Toolkit
=====================================

A collection of memory-efficient probabilistic data structures implemented
from scratch in pure Python.

Structures:
    BloomFilter      – approximate set membership (no false negatives)
    CountingBloomFilter  – deletable Bloom filter variant
    ScalableBloomFilter  – auto-growing Bloom filter
    BlockedBloomFilter   – cache-friendly Bloom filter variant
    CuckooFilter     – approximate set membership with deletion & better space
    CountMinSketch   – approximate frequency estimation
    ConservativeCountMinSketch  – CMS with reduced overestimation
    HyperLogLog      – approximate cardinality estimation
    KMV              – K-Minimum Values cardinality estimator
    MinHash          – approximate Jaccard set similarity
    LSHIndex         – locality-sensitive hashing for near-duplicate detection
    TopK             – heavy-hitters tracking (Space-Saving algorithm)
    TDigest          – approximate streaming quantiles
    SkipList         – probabilistic ordered map (support structure)
    ReservoirSampler – uniform random stream sampling
    WeightedReservoirSampler – weighted stream sampling

Each structure trades exactness for dramatic memory savings and/or speed.
"""
from .bloom import BloomFilter, CountingBloomFilter
from .blocked_bloom import BlockedBloomFilter
from .cuckoo import CuckooFilter
from .countmin import CountMinSketch
from .hll import HyperLogLog
from .kmv import KMV
from .minhash import MinHash, LSHIndex
from .sampling import ReservoirSampler, WeightedReservoirSampler
from .topk import TopK
from .tdigest import TDigest
from .skiplist import SkipList
from .scalable_bloom import ScalableBloomFilter
from .conservative_cms import ConservativeCountMinSketch
from .serialization import serialize, deserialize
from .benchmark import run_all_benchmarks
from .config import (
    load_config, build_from_config, build_from_file,
    list_structures, get_param_spec, save_config, ConfigError,
)
from .logging_utils import get_logger, set_level as set_log_level, disable as disable_logging

__version__ = "3.0.0"
__all__ = [
    "BloomFilter",
    "CountingBloomFilter",
    "BlockedBloomFilter",
    "CuckooFilter",
    "CountMinSketch",
    "ConservativeCountMinSketch",
    "HyperLogLog",
    "KMV",
    "MinHash",
    "LSHIndex",
    "ReservoirSampler",
    "WeightedReservoirSampler",
    "TopK",
    "TDigest",
    "SkipList",
    "ScalableBloomFilter",
    "serialize",
    "deserialize",
    "run_all_benchmarks",
    "load_config",
    "build_from_config",
    "build_from_file",
    "list_structures",
    "get_param_spec",
    "save_config",
    "ConfigError",
    "get_logger",
    "set_log_level",
    "disable_logging",
]