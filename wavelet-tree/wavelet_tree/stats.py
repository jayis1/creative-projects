"""Statistics and benchmarking for wavelet tree structures.

Provides:
    - space_stats(wt): estimate space usage (bits and bytes)
    - tree_stats(wt): structural metrics (depth, node count, etc.)
    - benchmark(structures, sequence, ...): time operations across structures
    - benchmark_report(...): human-readable benchmark report
"""

from __future__ import annotations

import sys
import time
import math
from typing import Any
from dataclasses import dataclass, field

from .base import WaveletBase
from .bitvector import BitVector, BlockedBitVector
from .rrr_bitvector import RRRBitVector


@dataclass
class SpaceStats:
    """Space usage statistics for a wavelet structure."""
    sequence_length: int
    alphabet_size: int
    total_bits: int
    total_bytes: int
    overhead_bits: int
    bits_per_symbol: float
    entropy_bits: float  # n * H0
    h0: float  # zeroth-order empirical entropy

    def __repr__(self) -> str:
        return (
            f"SpaceStats(n={self.sequence_length}, σ={self.alphabet_size}, "
            f"total={self.total_bits} bits ({self.total_bytes} bytes), "
            f"{self.bits_per_symbol:.2f} bits/symbol, "
            f"H₀={self.h0:.4f}, n·H₀={self.entropy_bits:.0f} bits)"
        )


def _zeroth_order_entropy(sequence: list) -> float:
    """Compute the zeroth-order empirical entropy H₀ of a sequence."""
    from collections import Counter
    n = len(sequence)
    if n == 0:
        return 0.0
    counts = Counter(sequence)
    h = 0.0
    for c in counts.values():
        p = c / n
        if p > 0:
            h -= p * math.log2(p)
    return h


def _object_size_bits(obj: Any) -> int:
    """Estimate the memory size of an object in bits using sys.getsizeof."""
    total = 0
    seen: set[int] = set()

    def _measure(o: Any) -> int:
        nonlocal total
        oid = id(o)
        if oid in seen:
            return 0
        seen.add(oid)
        size = sys.getsizeof(o)
        total += size
        # Recurse into common containers
        if isinstance(o, (list, tuple)):
            for item in o:
                _measure(item)
        elif isinstance(o, dict):
            for k, v in o.items():
                _measure(k)
                _measure(v)
        elif isinstance(o, (BitVector, BlockedBitVector, RRRBitVector)):
            # These have _bits array.array which getsizeof covers
            if hasattr(o, "_bits"):
                _measure(o._bits)
            if hasattr(o, "_prefix"):
                _measure(o._prefix)
            if hasattr(o, "_block_popcount"):
                _measure(o._block_popcount)
            if hasattr(o, "_superblock_cumulative"):
                _measure(o._superblock_cumulative)
        return total

    return _measure(obj) * 8  # bytes to bits


def space_stats(wt: WaveletBase) -> SpaceStats:
    """Compute space usage statistics for a wavelet structure.

    Args:
        wt: A wavelet tree/matrix instance.

    Returns:
        A SpaceStats dataclass with detailed space metrics.
    """
    n = len(wt)
    sigma = len(wt.alphabet)
    seq = wt.to_list() if n > 0 else []
    h0 = _zeroth_order_entropy(seq)

    total_bits = _object_size_bits(wt)
    total_bytes = (total_bits + 7) // 8
    # Theoretical minimum: n * H0 bits for the bitvectors
    entropy_bits = n * h0
    overhead_bits = max(0, total_bits - int(entropy_bits))
    bits_per_symbol = total_bits / n if n > 0 else 0.0

    return SpaceStats(
        sequence_length=n,
        alphabet_size=sigma,
        total_bits=total_bits,
        total_bytes=total_bytes,
        overhead_bits=overhead_bits,
        bits_per_symbol=bits_per_symbol,
        entropy_bits=entropy_bits,
        h0=h0,
    )


@dataclass
class TreeStats:
    """Structural metrics for a wavelet tree/matrix."""
    structure_type: str
    sequence_length: int
    alphabet_size: int
    num_levels: int
    num_bitvectors: int
    total_bitvector_length: int
    avg_bits_per_level: float
    max_tree_depth: int = 0
    num_internal_nodes: int = 0
    num_leaves: int = 0

    def __repr__(self) -> str:
        lines = [
            f"TreeStats({self.structure_type}):",
            f"  n={self.sequence_length}, σ={self.alphabet_size}",
            f"  levels={self.num_levels}, bitvectors={self.num_bitvectors}",
            f"  total_bv_length={self.total_bitvector_length}",
            f"  avg_bits/level={self.avg_bits_per_level:.1f}",
        ]
        if self.max_tree_depth > 0:
            lines.append(f"  tree_depth={self.max_tree_depth}")
            lines.append(f"  internal_nodes={self.num_internal_nodes}")
            lines.append(f"  leaves={self.num_leaves}")
        return "\n".join(lines)


def tree_stats(wt: WaveletBase) -> TreeStats:
    """Compute structural metrics for a wavelet structure.

    Args:
        wt: A wavelet tree/matrix instance.

    Returns:
        A TreeStats dataclass with structural metrics.
    """
    n = len(wt)
    sigma = len(wt.alphabet)
    type_name = type(wt).__name__

    # For matrix-based structures
    if hasattr(wt, "_level_bits"):
        num_levels = len(wt._level_bits)
        num_bv = num_levels
        total_bv_len = sum(len(bv) for bv in wt._level_bits)
        avg = total_bv_len / num_levels if num_levels > 0 else 0.0

        return TreeStats(
            structure_type=type_name,
            sequence_length=n,
            alphabet_size=sigma,
            num_levels=num_levels,
            num_bitvectors=num_bv,
            total_bitvector_length=total_bv_len,
            avg_bits_per_level=avg,
        )

    # For tree-based structures
    if hasattr(wt, "_root") and wt._root is not None:
        max_depth = 0
        num_internal = 0
        num_leaves = 0
        total_bv_len = 0
        num_bv = 0

        def _traverse(node, depth):
            nonlocal max_depth, num_internal, num_leaves, total_bv_len, num_bv
            max_depth = max(max_depth, depth)
            if node is None:
                return
            has_bits = hasattr(node, "bits") and node.bits is not None
            if has_bits:
                num_internal += 1
                num_bv += 1
                total_bv_len += len(node.bits)
                _traverse(getattr(node, "left", None), depth + 1)
                _traverse(getattr(node, "right", None), depth + 1)
            else:
                num_leaves += 1

        _traverse(wt._root, 0)

        avg = total_bv_len / num_bv if num_bv > 0 else 0.0

        return TreeStats(
            structure_type=type_name,
            sequence_length=n,
            alphabet_size=sigma,
            num_levels=max_depth,
            num_bitvectors=num_bv,
            total_bitvector_length=total_bv_len,
            avg_bits_per_level=avg,
            max_tree_depth=max_depth,
            num_internal_nodes=num_internal,
            num_leaves=num_leaves,
        )

    # Fallback
    return TreeStats(
        structure_type=type_name,
        sequence_length=n,
        alphabet_size=sigma,
        num_levels=0,
        num_bitvectors=0,
        total_bitvector_length=0,
        avg_bits_per_level=0.0,
    )


@dataclass
class BenchmarkResult:
    """Results of benchmarking a single structure on a single operation."""
    structure: str
    operation: str
    build_time: float
    query_time: float
    num_queries: int
    avg_query_time_us: float

    def __repr__(self) -> str:
        return (
            f"  {self.structure:<25} {self.operation:<15} "
            f"build={self.build_time*1000:8.2f}ms  "
            f"query={self.avg_query_time_us:8.3f}µs  "
            f"({self.num_queries} queries)"
        )


def benchmark(
    sequence: list | str,
    structures: list[str] | None = None,
    num_rank_queries: int = 1000,
    num_access_queries: int = 1000,
    num_select_queries: int = 1000,
    use_blocked: bool = True,
) -> list[BenchmarkResult]:
    """Benchmark wavelet tree structures on a sequence.

    Times build, access, rank, and select operations for each structure.

    Args:
        sequence: The sequence to benchmark on.
        structures: List of structure names to benchmark. Default: all four.
        num_rank_queries: Number of rank queries to time.
        num_access_queries: Number of access queries to time.
        num_select_queries: Number of select queries to time.
        use_blocked: Whether to use BlockedBitVector.

    Returns:
        A list of BenchmarkResult objects.
    """
    import random

    from .wavelet_tree import WaveletTree
    from .wavelet_matrix import WaveletMatrix
    from .huffman import HuffmanWaveletTree, HuffmanWaveletMatrix

    if isinstance(sequence, str):
        seq = list(sequence)
    else:
        seq = list(sequence)

    struct_map = {
        "tree": ("WaveletTree", WaveletTree),
        "matrix": ("WaveletMatrix", WaveletMatrix),
        "huffman-tree": ("HuffmanWaveletTree", HuffmanWaveletTree),
        "huffman-matrix": ("HuffmanWaveletMatrix", HuffmanWaveletMatrix),
    }

    if structures is None:
        structures = list(struct_map.keys())

    results: list[BenchmarkResult] = []
    alphabet = sorted(set(seq)) if seq else []
    n = len(seq)

    for struct_key in structures:
        if struct_key not in struct_map:
            continue
        name, cls = struct_map[struct_key]

        # Build
        t0 = time.perf_counter()
        wt = cls(seq, use_blocked=use_blocked)
        build_time = time.perf_counter() - t0

        # Access
        if n > 0:
            access_indices = [random.randint(0, n - 1) for _ in range(num_access_queries)]
            t0 = time.perf_counter()
            for i in access_indices:
                wt.access(i)
            access_time = time.perf_counter() - t0
            results.append(BenchmarkResult(
                structure=name,
                operation="access",
                build_time=build_time,
                query_time=access_time,
                num_queries=num_access_queries,
                avg_query_time_us=access_time / num_access_queries * 1e6,
            ))

        # Rank
        if alphabet and n > 0:
            rank_syms = [random.choice(alphabet) for _ in range(num_rank_queries)]
            rank_indices = [random.randint(0, n) for _ in range(num_rank_queries)]
            t0 = time.perf_counter()
            for c, i in zip(rank_syms, rank_indices):
                wt.rank(c, i)
            rank_time = time.perf_counter() - t0
            results.append(BenchmarkResult(
                structure=name,
                operation="rank",
                build_time=build_time,
                query_time=rank_time,
                num_queries=num_rank_queries,
                avg_query_time_us=rank_time / num_rank_queries * 1e6,
            ))

        # Select
        if alphabet and n > 0:
            select_syms = [random.choice(alphabet) for _ in range(num_select_queries)]
            t0 = time.perf_counter()
            for c in select_syms:
                total = wt.rank(c, n)
                if total > 0:
                    wt.select(c, random.randint(0, total - 1))
            select_time = time.perf_counter() - t0
            results.append(BenchmarkResult(
                structure=name,
                operation="select",
                build_time=build_time,
                query_time=select_time,
                num_queries=num_select_queries,
                avg_query_time_us=select_time / num_select_queries * 1e6,
            ))

    return results


def benchmark_report(results: list[BenchmarkResult]) -> str:
    """Generate a human-readable benchmark report.

    Args:
        results: A list of BenchmarkResult objects.

    Returns:
        A formatted string report.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("Wavelet Tree Benchmark Report")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"{'Structure':<25} {'Operation':<15} {'Build':>10} {'Avg Query':>12}")
    lines.append("-" * 70)
    for r in results:
        lines.append(
            f"{r.structure:<25} {r.operation:<15} "
            f"{r.build_time*1000:>8.2f}ms "
            f"{r.avg_query_time_us:>10.3f}µs"
        )
    lines.append("=" * 70)
    return "\n".join(lines)