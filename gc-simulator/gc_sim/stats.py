"""Collection-statistics tracking and reporting.

A :class:`StatsTracker` accumulates per-collection :class:`CollectionStats`
records and exposes summary aggregates (totals, averages, pause-time
distribution).  Collectors call :meth:`record` once per collection; the
:class:`~gc_sim.simulator.GCSimulator` exposes the tracker so callers can
inspect the GC's behaviour programmatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import List, Optional


@dataclass
class CollectionStats:
    """Statistics for a single GC cycle."""

    cycle: int
    collector: str
    live_before: int
    live_after: int = 0
    collected: int = 0
    promoted: int = 0          # objects moved to old gen (generational only)
    bytes_freed: int = 0
    bytes_moved: int = 0       # cells relocated (compact / copy)
    pause_cells: int = 0       # simulated pause cost (proportional to work)
    fragmentation_before: float = 0.0
    fragmentation_after: float = 0.0
    heap_used_before: int = 0
    heap_used_after: int = 0
    roots_count: int = 0
    marked: int = 0            # number of objects marked live
    elapsed_cycles: int = 0    # minor + major cycles combined, for gen GC

    @property
    def survival_ratio(self) -> float:
        """Fraction of pre-collection objects that survived."""
        if self.live_before == 0:
            return 0.0
        return self.live_after / self.live_before

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (f"CollectionStats(cycle={self.cycle}, collector={self.collector}, "
                f"collected={self.collected}, freed={self.bytes_freed}B, "
                f"pause={self.pause_cells})")


@dataclass
class StatsTracker:
    """Accumulates :class:`CollectionStats` over a run."""

    records: List[CollectionStats] = field(default_factory=list)
    total_allocated: int = 0
    total_freed: int = 0
    total_collected: int = 0

    def record(self, stats: CollectionStats) -> None:
        self.records.append(stats)
        self.total_freed += stats.bytes_freed
        self.total_collected += stats.collected

    @property
    def num_collections(self) -> int:
        return len(self.records)

    @property
    def avg_pause(self) -> float:
        if not self.records:
            return 0.0
        return mean(r.pause_cells for r in self.records)

    @property
    def max_pause(self) -> int:
        if not self.records:
            return 0
        return max(r.pause_cells for r in self.records)

    @property
    def total_pause(self) -> int:
        return sum(r.pause_cells for r in self.records)

    @property
    def avg_survival(self) -> float:
        if not self.records:
            return 0.0
        return mean(r.survival_ratio for r in self.records)

    def summary(self) -> str:
        """Return a human-readable multi-line summary string."""
        if not self.records:
            return "No collections performed."
        lines = [
            f"GC Statistics ({self.num_collections} collections)",
            f"  Total allocated : {self.total_allocated} cells",
            f"  Total freed     : {self.total_freed} cells",
            f"  Total collected : {self.total_collected} objects",
            f"  Avg pause       : {self.avg_pause:.1f} cells",
            f"  Max pause       : {self.max_pause} cells",
            f"  Total pause     : {self.total_pause} cells",
            f"  Avg survival    : {self.avg_survival:.2%}",
        ]
        return "\n".join(lines)

    def as_dict(self) -> dict:
        """Return a JSON-serialisable summary."""
        return {
            "num_collections": self.num_collections,
            "total_allocated": self.total_allocated,
            "total_freed": self.total_freed,
            "total_collected": self.total_collected,
            "avg_pause": self.avg_pause,
            "max_pause": self.max_pause,
            "total_pause": self.total_pause,
            "avg_survival": self.avg_survival,
            "records": [
                {
                    "cycle": r.cycle,
                    "collector": r.collector,
                    "live_before": r.live_before,
                    "live_after": r.live_after,
                    "collected": r.collected,
                    "promoted": r.promoted,
                    "bytes_freed": r.bytes_freed,
                    "bytes_moved": r.bytes_moved,
                    "pause_cells": r.pause_cells,
                    "fragmentation_before": r.fragmentation_before,
                    "fragmentation_after": r.fragmentation_after,
                    "heap_used_before": r.heap_used_before,
                    "heap_used_after": r.heap_used_after,
                    "roots_count": r.roots_count,
                    "marked": r.marked,
                }
                for r in self.records
            ],
        }