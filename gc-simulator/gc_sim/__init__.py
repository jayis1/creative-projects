"""Heap & garbage-collector simulator.

A from-scratch, pure-Python toolkit for modelling memory allocation and
automatic memory management.  It simulates a tiny, fixed-size "machine heap"
populated with objects that can reference each other, and provides several
classic garbage-collection algorithms that run over that heap, exposing
detailed statistics, traces and visualisations so that the trade-offs between
collectors can be studied empirically.

Public surface
---------------
The package is organised into the following sub-modules:

* :mod:`gc_sim.heap`        -- :class:`Heap`, :class:`Object` and the object graph.
* :mod:`gc_sim.allocators`  -- bump, free-list and coalescing allocators.
* :mod:`gc_sim.collectors`  -- mark-sweep, mark-compact, copying, generational and
  reference-counting collectors.
* :mod:`gc_sim.tracer`      -- graph traversal utilities (DFS/BFS marking, roots).
* :mod:`gc_sim.stats`       -- collection statistics & reporting.
* :mod:`gc_sim.simulator`   -- high-level :class:`GCSimulator` driver tying it all
  together.
* :mod:`gc_sim.visualizer`  -- ASCII visualisations of the heap layout.
* :mod:`gc_sim.benchmark`   -- cross-collector benchmarking harness.
* :mod:`gc_sim.config`      -- configuration loading (JSON/YAML/TOML).
* :mod:`gc_sim.logging_utils` -- structured logging.
* :mod:`gc_sim.events`      -- event-sourcing trace recording.
* :mod:`gc_sim.replay`      -- replay recorded traces on any collector.
* :mod:`gc_sim.reporting`   -- pause-time analysis, histograms, reports.
* :mod:`gc_sim.cli`         -- command-line interface.

Example
-------
>>> from gc_sim.simulator import GCSimulator
>>> sim = GCSimulator(heap_size=256, collector="mark_sweep")
>>> a = sim.allocate(16, name="root_a")
>>> b = sim.allocate(24, name="child_b")
>>> sim.add_root("global", a)
>>> a.add_ref(b)
>>> sim.collect()
>>> sim.stats.live_objects
2
"""

from .heap import Heap, Object, ObjectRef, HeapError
from .allocators import BumpAllocator, FreeListAllocator, Allocator
from .collectors import (
    Collector,
    MarkSweepCollector,
    MarkCompactCollector,
    CopyingCollector,
    RefCountCollector,
    GenerationalCollector,
    get_collector,
)
from .simulator import GCSimulator
from .stats import CollectionStats, StatsTracker
from .benchmark import (
    BenchmarkResult,
    run_benchmark,
    benchmark_all,
    format_benchmark_table,
)
from .events import EventTracer, Event, EventType
from .replay import TraceReplayer, replay_from_file, load_trace
from .reporting import (
    PauseHistogram,
    CollectorReport,
    format_comparison_report,
    generate_report_json,
    analyse_from_sims,
)

__version__ = "2.0.0"
__all__ = [
    "Heap",
    "Object",
    "ObjectRef",
    "HeapError",
    "Allocator",
    "BumpAllocator",
    "FreeListAllocator",
    "Collector",
    "MarkSweepCollector",
    "MarkCompactCollector",
    "CopyingCollector",
    "RefCountCollector",
    "GenerationalCollector",
    "get_collector",
    "GCSimulator",
    "CollectionStats",
    "StatsTracker",
    "BenchmarkResult",
    "run_benchmark",
    "benchmark_all",
    "format_benchmark_table",
    "EventTracer",
    "Event",
    "EventType",
    "TraceReplayer",
    "replay_from_file",
    "load_trace",
    "PauseHistogram",
    "CollectorReport",
    "format_comparison_report",
    "generate_report_json",
    "analyse_from_sims",
]