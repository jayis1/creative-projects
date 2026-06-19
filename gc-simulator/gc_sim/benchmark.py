"""Benchmarking harness for comparing GC algorithms.

Runs a scenario across multiple collectors and produces a detailed
comparison table showing pause times, survival ratios, fragmentation and
throughput.  Useful for understanding the trade-offs between collectors.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .simulator import GCSimulator
from .stats import StatsTracker
from .collectors import available_collectors


@dataclass
class BenchmarkResult:
    """Result of benchmarking a single collector."""
    collector: str
    stats: StatsTracker
    wall_time_ms: float
    allocations: int
    peak_heap_used: int
    final_fragmentation: float
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "collector": self.collector,
            "wall_time_ms": self.wall_time_ms,
            "allocations": self.allocations,
            "peak_heap_used": self.peak_heap_used,
            "final_fragmentation": self.final_fragmentation,
            "num_collections": self.stats.num_collections,
            "total_pause": self.stats.total_pause,
            "avg_pause": self.stats.avg_pause,
            "max_pause": self.stats.max_pause,
            "avg_survival": self.stats.avg_survival,
            "total_freed": self.stats.total_freed,
            "error": self.error,
        }


def run_benchmark(
    collector: str,
    heap_size: int,
    scenario_fn: Callable[[GCSimulator], None],
    num_collections: int = 5,
    allocator: str = "bump",
    allocator_policy: str = "first_fit",
    **collector_kwargs,
) -> BenchmarkResult:
    """Benchmark a single collector.

    Parameters
    ----------
    collector : str
        Collector name.
    heap_size : int
        Heap size in cells.
    scenario_fn : callable
        Function ``(sim) -> None`` that allocates objects on the simulator.
    num_collections : int
        Number of collection cycles to run after the scenario.
    """
    import time
    sim = GCSimulator(
        heap_size=heap_size,
        collector=collector,
        allocator=allocator,
        allocator_policy=allocator_policy,
        **collector_kwargs,
    )
    start = time.perf_counter()
    error = None
    try:
        scenario_fn(sim)
        peak = sim.heap.high_water_mark
        for _ in range(num_collections):
            sim.collect()
        peak = max(peak, sim.heap.high_water_mark)
    except Exception as e:
        error = str(e)
        peak = sim.heap.high_water_mark
    elapsed = (time.perf_counter() - start) * 1000
    return BenchmarkResult(
        collector=collector,
        stats=sim.stats,
        wall_time_ms=elapsed,
        allocations=sim._alloc_count,
        peak_heap_used=peak,
        final_fragmentation=sim.fragmentation(),
        error=error,
    )


def benchmark_all(
    heap_size: int,
    scenario_fn: Callable[[GCSimulator], None],
    num_collections: int = 5,
    collectors: Optional[List[str]] = None,
    allocator: str = "bump",
    allocator_policy: str = "first_fit",
) -> List[BenchmarkResult]:
    """Benchmark all (or a subset of) collectors on the same scenario.

    Returns a list of :class:`BenchmarkResult`.
    """
    if collectors is None:
        collectors = available_collectors()
    results: List[BenchmarkResult] = []
    for cname in collectors:
        result = run_benchmark(
            cname, heap_size, scenario_fn, num_collections,
            allocator=allocator, allocator_policy=allocator_policy,
        )
        results.append(result)
    return results


def format_benchmark_table(results: List[BenchmarkResult]) -> str:
    """Format benchmark results as an ASCII table."""
    header = (
        f"{'collector':<16} {'wall_ms':>8} {'#allocs':>7} {'#coll':>5} "
        f"{'total_p':>7} {'avg_p':>6} {'max_p':>6} {'avg_surv':>8} "
        f"{'freed':>6} {'frag':>5} {'peak':>5}"
    )
    sep = "=" * len(header)
    lines = [sep, header, sep]
    for r in results:
        if r.error:
            line = f"{r.collector:<16} ERROR: {r.error}"
        else:
            line = (
                f"{r.collector:<16} {r.wall_time_ms:>8.1f} {r.allocations:>7} "
                f"{r.stats.num_collections:>5} {r.stats.total_pause:>7} "
                f"{r.stats.avg_pause:>6.1f} {r.stats.max_pause:>6} "
                f"{r.stats.avg_survival:>7.1%} {r.stats.total_freed:>6} "
                f"{r.final_fragmentation:>4.0%} {r.peak_heap_used:>5}"
            )
        lines.append(line)
    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Predefined benchmark scenarios
# ---------------------------------------------------------------------------

def scenario_churn(sim: GCSimulator) -> None:
    """Allocation churn: allocate many short-lived objects, keep a few roots.

    This is the classic generational hypothesis scenario — most objects die
    young.
    """
    # Keep 3 long-lived objects rooted
    long_lived = [sim.allocate(16, f"long_{i}") for i in range(3)]
    for i, obj in enumerate(long_lived):
        sim.add_root(f"long_{i}", obj)
    # Allocate 100 short-lived objects, unrooted
    for i in range(100):
        obj = sim.allocate(4, f"short_{i}")
        # link some to long-lived so they're temporarily reachable
        if i % 10 == 0 and long_lived:
            sim.link(long_lived[i % len(long_lived)], obj, f"temp_{i}")
            sim.unlink(long_lived[i % len(long_lived)],
                       long_lived[i % len(long_lived)].refs[-1])


def scenario_growing_tree(sim: GCSimulator) -> None:
    """Build a tree, collect, then grow it further."""
    sim.scenario_binary_tree(depth=3, obj_size=4)
    sim.collect()
    sim.scenario_binary_tree(depth=2, obj_size=4)


def scenario_cycle_heavy(sim: GCSimulator) -> None:
    """Create many cyclic structures (challenging for ref counting)."""
    for i in range(10):
        a = sim.allocate(4, f"cyc_a_{i}")
        b = sim.allocate(4, f"cyc_b_{i}")
        sim.link(a, b, "next")
        sim.link(b, a, "back")  # cycle
        if i < 3:
            sim.add_root(f"cyc_root_{i}", a)