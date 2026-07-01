"""
Statistics and profiling for the nonogram solver.

Tracks per-line solve times, cache hit/miss ratios, propagation rounds,
and backtracking nodes. Useful for benchmarking and identifying
bottlenecks.

Usage::

    from nonogram.stats import SolverStats

    stats = SolverStats()
    solver = Solver()
    solver.solve(board)
    # stats can be plugged into custom instrumentation
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LineStats:
    """Statistics for a single line-solve operation."""
    line_type: str  # 'row' or 'col'
    index: int
    length: int
    elapsed: float = 0.0
    cells_decided: int = 0
    cache_hit: bool = False
    feasible: bool = True


@dataclass
class SolverStats:
    """Aggregate solver statistics."""
    # Propagation.
    propagation_rounds: int = 0
    lines_solved: int = 0
    lines_skipped_complete: int = 0
    cells_decided_total: int = 0
    # Backtracking.
    backtrack_nodes: int = 0
    backtrack_dead_ends: int = 0
    # Timing.
    total_time: float = 0.0
    propagation_time: float = 0.0
    backtracking_time: float = 0.0
    # Line solver cache.
    cache_hits: int = 0
    cache_misses: int = 0
    # Per-line detail (optional — only if tracking enabled).
    line_details: List[LineStats] = field(default_factory=list)

    @property
    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    @property
    def avg_line_time(self) -> float:
        if self.lines_solved == 0:
            return 0.0
        return self.propagation_time / max(self.lines_solved, 1)

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.propagation_rounds = 0
        self.lines_solved = 0
        self.lines_skipped_complete = 0
        self.cells_decided_total = 0
        self.backtrack_nodes = 0
        self.backtrack_dead_ends = 0
        self.total_time = 0.0
        self.propagation_time = 0.0
        self.backtracking_time = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.line_details.clear()

    def summary(self) -> str:
        """Return a human-readable summary."""
        return (
            f"Solver Statistics:\n"
            f"  Total time:        {self.total_time:.4f}s\n"
            f"  Propagation rounds: {self.propagation_rounds}\n"
            f"  Lines solved:      {self.lines_solved}\n"
            f"  Lines skipped:     {self.lines_skipped_complete}\n"
            f"  Cells decided:     {self.cells_decided_total}\n"
            f"  Backtrack nodes:   {self.backtrack_nodes}\n"
            f"  Dead ends:         {self.backtrack_dead_ends}\n"
            f"  Cache hit ratio:   {self.cache_hit_ratio:.2%}\n"
            f"  Avg line time:     {self.avg_line_time:.6f}s"
        )

    def to_dict(self) -> dict:
        return {
            "total_time": round(self.total_time, 6),
            "propagation_rounds": self.propagation_rounds,
            "lines_solved": self.lines_solved,
            "lines_skipped_complete": self.lines_skipped_complete,
            "cells_decided_total": self.cells_decided_total,
            "backtrack_nodes": self.backtrack_nodes,
            "backtrack_dead_ends": self.backtrack_dead_ends,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_ratio": round(self.cache_hit_ratio, 4),
            "propagation_time": round(self.propagation_time, 6),
            "backtracking_time": round(self.backtracking_time, 6),
        }


class StatsCollector:
    """Context manager for timing a section of code and recording stats.

    Usage::

        with StatsCollector(stats, "propagation"):
            solver._propagate(board)
    """

    def __init__(self, stats: SolverStats, section: str = "") -> None:
        self.stats = stats
        self.section = section
        self._start = 0.0

    def __enter__(self) -> "StatsCollector":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed = time.perf_counter() - self._start
        self.stats.total_time += elapsed
        if self.section == "propagation":
            self.stats.propagation_time += elapsed
        elif self.section == "backtracking":
            self.stats.backtracking_time += elapsed