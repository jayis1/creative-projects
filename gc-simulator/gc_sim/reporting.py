"""Pause-time analysis and reporting for GC simulations.

Analyses :class:`~gc_sim.stats.CollectionStats` records to produce
pause-time histograms, percentile breakdowns, allocation throughput
estimates, and formatted comparison reports.  These tools make it easy to
understand the *latency* characteristics of each collector — the core
trade-off in real-world GC design.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from .stats import CollectionStats, StatsTracker

if TYPE_CHECKING:
    from .simulator import GCSimulator


@dataclass
class PauseHistogram:
    """A histogram of pause-cell counts across collection cycles.

    Bins are configurable; default uses power-of-two bucket boundaries so
    that small pauses (the common case) get fine-grained resolution while
    large pauses collapse into a few buckets.
    """

    bins: List[int] = field(default_factory=lambda: [1, 4, 16, 64, 256, 1024])
    counts: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0, 0, 0])
    total: int = 0
    min_val: int = 0
    max_val: int = 0
    mean_val: float = 0.0
    median_val: float = 0.0
    p90: int = 0
    p95: int = 0
    p99: int = 0

    @classmethod
    def from_records(
        cls, records: List[CollectionStats], bins: Optional[List[int]] = None
    ) -> "PauseHistogram":
        """Build a histogram from a list of collection stats."""
        pauses = [r.pause_cells for r in records]
        if not pauses:
            return cls()

        if bins is None:
            bins = [1, 4, 16, 64, 256, 1024]

        counts = [0] * (len(bins) + 1)
        for p in pauses:
            placed = False
            for i, boundary in enumerate(bins):
                if p <= boundary:
                    counts[i] += 1
                    placed = True
                    break
            if not placed:
                counts[-1] += 1

        sorted_p = sorted(pauses)
        n = len(sorted_p)

        def percentile(pct: float) -> int:
            idx = max(0, min(n - 1, math.ceil(pct / 100 * n) - 1))
            return sorted_p[idx]

        return cls(
            bins=bins,
            counts=counts,
            total=n,
            min_val=sorted_p[0],
            max_val=sorted_p[-1],
            mean_val=round(sum(pauses) / n, 1),
            median_val=float(sorted_p[n // 2]) if n % 2 == 1 else round(
                (sorted_p[n // 2 - 1] + sorted_p[n // 2]) / 2, 1
            ),
            p90=percentile(90),
            p95=percentile(95),
            p99=percentile(99),
        )

    def render_ascii(self, width: int = 40) -> str:
        """Render the histogram as an ASCII bar chart."""
        lines: List[str] = []
        lines.append(f"Pause-time histogram ({self.total} collections)")
        lines.append(f"  min={self.min_val}  mean={self.mean_val}  "
                      f"median={self.median_val}  "
                      f"p90={self.p90}  p95={self.p95}  p99={self.p99}  "
                      f"max={self.max_val}")
        lines.append("")

        if self.total == 0:
            lines.append("  (no data)")
            return "\n".join(lines)

        max_count = max(self.counts) if self.counts else 1
        if max_count == 0:
            max_count = 1

        labels: List[str] = []
        for i, boundary in enumerate(self.bins):
            if i == 0:
                labels.append(f"  <= {boundary:>5}")
            else:
                labels.append(f"  {self.bins[i - 1] + 1:>5}-{boundary:>5}")
        labels.append(f"  > {self.bins[-1]:>5}")

        for i, (label, count) in enumerate(zip(labels, self.counts)):
            bar_len = int((count / max_count) * width) if count > 0 else 0
            bar = "█" * bar_len
            pct = (count / self.total) * 100 if self.total > 0 else 0
            lines.append(f"{label}: {bar} {count:>4} ({pct:5.1f}%)")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "bins": self.bins,
            "counts": self.counts,
            "total": self.total,
            "min": self.min_val,
            "max": self.max_val,
            "mean": self.mean_val,
            "median": self.median_val,
            "p90": self.p90,
            "p95": self.p95,
            "p99": self.p99,
        }


@dataclass
class CollectorReport:
    """Summary report for a single collector's run."""

    collector: str
    num_collections: int
    total_allocated: int
    total_freed: int
    total_collected: int
    total_pause: int
    avg_pause: float
    max_pause: int
    avg_survival: float
    final_fragmentation: float
    peak_heap_used: int
    histogram: Optional[PauseHistogram] = None

    @classmethod
    def from_simulator(cls, sim) -> "CollectorReport":
        stats = sim.stats
        hist = PauseHistogram.from_records(stats.records)
        return cls(
            collector=sim.collector_name,
            num_collections=stats.num_collections,
            total_allocated=stats.total_allocated,
            total_freed=stats.total_freed,
            total_collected=stats.total_collected,
            total_pause=stats.total_pause,
            avg_pause=round(stats.avg_pause, 1),
            max_pause=stats.max_pause,
            avg_survival=round(stats.avg_survival, 4),
            final_fragmentation=round(sim.fragmentation(), 4),
            peak_heap_used=sim.heap.high_water_mark,
            histogram=hist,
        )

    def to_dict(self) -> dict:
        d = {
            "collector": self.collector,
            "num_collections": self.num_collections,
            "total_allocated": self.total_allocated,
            "total_freed": self.total_freed,
            "total_collected": self.total_collected,
            "total_pause": self.total_pause,
            "avg_pause": self.avg_pause,
            "max_pause": self.max_pause,
            "avg_survival": self.avg_survival,
            "final_fragmentation": self.final_fragmentation,
            "peak_heap_used": self.peak_heap_used,
        }
        if self.histogram:
            d["histogram"] = self.histogram.to_dict()
        return d


def format_comparison_report(
    reports: List[CollectorReport],
    *,
    include_histogram: bool = False,
) -> str:
    """Format a detailed cross-collector comparison report as text."""
    lines: List[str] = []
    header = (
        f"{'collector':<16} {'#coll':>5} {'alloc':>7} {'freed':>6} "
        f"{'coll':>5} {'t_pause':>7} {'avg_p':>6} {'max_p':>6} "
        f"{'surv%':>6} {'frag%':>5} {'peak':>5}"
    )
    sep = "=" * len(header)
    lines.append(sep)
    lines.append("GC Collector Comparison Report")
    lines.append(sep)
    lines.append(header)
    lines.append("-" * len(header))
    for r in reports:
        lines.append(
            f"{r.collector:<16} {r.num_collections:>5} {r.total_allocated:>7} "
            f"{r.total_freed:>6} {r.total_collected:>5} {r.total_pause:>7} "
            f"{r.avg_pause:>6.1f} {r.max_pause:>6} "
            f"{r.avg_survival * 100:>5.1f}% {r.final_fragmentation * 100:>4.0f}% "
            f"{r.peak_heap_used:>5}"
        )
    lines.append(sep)
    lines.append("")

    # Winner analysis
    if reports:
        best_pause = min(reports, key=lambda r: r.avg_pause)
        best_throughput = min(reports, key=lambda r: r.total_pause)
        best_survival = max(reports, key=lambda r: r.avg_survival)
        least_frag = min(reports, key=lambda r: r.final_fragmentation)

        lines.append("Winner Analysis:")
        lines.append(f"  Lowest avg pause : {best_pause.collector} "
                      f"({best_pause.avg_pause:.1f} cells)")
        lines.append(f"  Lowest total pause: {best_throughput.collector} "
                      f"({best_throughput.total_pause} cells)")
        lines.append(f"  Highest survival  : {best_survival.collector} "
                      f"({best_survival.avg_survival:.2%})")
        lines.append(f"  Least fragmentation: {least_frag.collector} "
                      f"({least_frag.final_fragmentation:.1%})")

    if include_histogram:
        lines.append("")
        lines.append("Pause-time histograms:")
        for r in reports:
            if r.histogram and r.histogram.total > 0:
                lines.append("")
                lines.append(f"--- {r.collector} ---")
                lines.append(r.histogram.render_ascii())

    return "\n".join(lines)


def generate_report_json(reports: List[CollectorReport]) -> str:
    """Generate a JSON comparison report."""
    import json

    return json.dumps([r.to_dict() for r in reports], indent=2)


def analyse_from_sims(
    sims: Dict[str, "GCSimulator"],
) -> List[CollectorReport]:
    """Build :class:`CollectorReport` objects from a dict of simulators."""
    reports: List[CollectorReport] = []
    for cname, sim in sims.items():
        reports.append(CollectorReport.from_simulator(sim))
    return reports