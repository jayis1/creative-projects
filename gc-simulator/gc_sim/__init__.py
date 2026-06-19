"""Heap & garbage collector simulator.

A from-scratch, pure-Python toolkit for modelling memory allocation and
automatic memory management.  It simulates a tiny, fixed-size "machine heap"
populated with objects that can reference each other, and provides several
classic garbage-collection algorithms that run over that heap, exposing
detailed statistics, traces and visualisations so that the trade-offs between
collectors can be studied empirically.

Public surface
---------------
The package is organised into the following sub-modules:

* :mod:`gc_sim.heap`   -- :class:`Heap`, :class:`Object` and the object graph.
* :gc_sim.allocators`  -- bump, free-list and coalescing allocators.
* :gc_sim.collectors`  -- mark-sweep, mark-compact, copying, generational and
  reference-counting collectors.
* :gc_sim.tracer`      -- graph traversal utilities (DFS/BFS marking, roots).
* :gc_sim.stats`       -- collection statistics & reporting.
* :gc_sim.simulator`   -- high-level :class:`GCSimulator` driver tying it all
  together.
* :gc_sim.visualizer`  -- ASCII visualisations of the heap layout.
* :gc_sim.config`      -- configuration loading (JSON/YAML/TOML).
* :gc_sim.cli`         -- command-line interface.

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

__version__ = "1.0.0"
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
]