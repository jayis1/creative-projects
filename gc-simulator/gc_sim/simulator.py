"""High-level garbage-collection simulator.

The :class:`GCSimulator` ties together a :class:`~gc_sim.heap.Heap`, an
:class:`~gc_sim.allocators.Allocator`, a :class:`~gc_sim.collectors.Collector`
and a :class:`~gc_sim.stats.StatsTracker`, exposing a convenient API for
building allocation scenarios, running collections and inspecting results.

It also provides several ready-made *scenario* generators (linked lists,
binary trees, random graphs) that produce realistic object-graph shapes for
benchmarking different collectors.

Event tracing
-------------
Pass ``trace=True`` to record every allocation, root, link, and collection
as an :class:`~gc_sim.events.Event`.  Traces can be exported as JSON and
replayed on different collectors via :mod:`gc_sim.replay`.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from .heap import Heap, Object, ObjectRef, RootSet
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
from .stats import StatsTracker, CollectionStats
from .events import EventTracer, EventType


class GCSimulator:
    """End-to-end GC simulation driver.

    Parameters
    ----------
    heap_size : int
        Total number of cells in the simulated heap.
    collector : str
        Collector name (``"mark_sweep"``, ``"mark_compact"``, ``"copying"``,
        ``"ref_count"``, ``"generational"``).
    allocator : str
        Allocator name (``"bump"`` or ``"free_list"``).
    allocator_policy : str
        Free-list policy (``"first_fit"``, ``"best_fit"``, ``"worst_fit"``).
    trace : bool
        If ``True``, record every operation as an :class:`~gc_sim.events.Event`
        for later replay and analysis.
    **collector_kwargs
        Extra keyword arguments forwarded to the collector constructor.
    """

    def __init__(
        self,
        heap_size: int = 1024,
        collector: str = "mark_sweep",
        allocator: str = "bump",
        allocator_policy: str = "first_fit",
        *,
        trace: bool = False,
        **collector_kwargs,
    ):
        self.heap = Heap(heap_size)
        self.roots = RootSet()
        self.stats = StatsTracker()
        self.tracer: Optional[EventTracer] = EventTracer() if trace else None

        # build allocator
        if allocator == "bump":
            self.allocator: Allocator = BumpAllocator(self.heap)
        elif allocator == "free_list":
            self.allocator = FreeListAllocator(self.heap, policy=allocator_policy)
        else:
            raise ValueError(f"unknown allocator {allocator!r}")

        self.collector_name = collector
        self.collector_kwargs = collector_kwargs
        self._build_collector()
        self._alloc_count = 0

    def _build_collector(self) -> None:
        """(Re)build the collector, wiring in the current allocator where
        relevant."""
        kw = dict(self.collector_kwargs)
        if self.collector_name == "copying":
            kw.setdefault("allocator", self.allocator)
        self.collector: Collector = get_collector(
            self.collector_name, self.heap, self.roots, **kw)

    # -- allocation ----------------------------------------------------------
    def allocate(self, size: int, name: str = "") -> Object:
        """Allocate a new object of ``size`` cells.  Returns the
        :class:`Object`.  Raises :class:`~gc_sim.heap.HeapError` if the
        allocator cannot satisfy the request (out of memory)."""
        if size <= 0:
            raise ValueError("allocation size must be positive")
        obj = self.allocator.allocate(size, name=name)
        if obj is None:
            raise MemoryError(
                f"out of memory: cannot allocate {size} cells "
                f"(used={self.heap.used}/{self.heap.size})")
        self._alloc_count += 1
        self.stats.total_allocated += size
        # ref_count collector needs an initial count of 0
        if isinstance(self.collector, RefCountCollector):
            self.collector.refcounts[obj.oid] = 0
        if self.tracer is not None:
            self.tracer.record(EventType.ALLOCATE, size=size, name=name, oid=obj.oid)
        return obj

    # -- root management -----------------------------------------------------
    def add_root(self, name: str, obj: Object) -> None:
        self.roots.add(name, obj)
        if isinstance(self.collector, RefCountCollector):
            self.collector.update_count(obj, +1)
        if self.tracer is not None:
            self.tracer.record(EventType.ADD_ROOT, name=name, oid=obj.oid)

    def remove_root(self, name: str) -> None:
        obj = self.roots[name]
        self.roots.remove(name)
        if obj is not None and isinstance(self.collector, RefCountCollector):
            self.collector.update_count(obj, -1)
        if self.tracer is not None:
            self.tracer.record(EventType.REMOVE_ROOT, name=name)

    def clear_root(self, name: str) -> None:
        obj = self.roots[name]
        self.roots.clear_root(name)
        if obj is not None and isinstance(self.collector, RefCountCollector):
            self.collector.update_count(obj, -1)
        if self.tracer is not None:
            self.tracer.record(EventType.CLEAR_ROOT, name=name)

    # -- reference management ------------------------------------------------
    def link(self, src: Object, tgt: Object, name: str = "") -> ObjectRef:
        """Add a reference from ``src`` to ``tgt`` and update ref counts."""
        if not isinstance(src, Object):
            raise TypeError("src must be an Object")
        if not isinstance(tgt, Object):
            raise TypeError("tgt must be an Object")
        if not src.alive:
            raise ValueError("cannot link from a dead object")
        if not tgt.alive:
            raise ValueError("cannot link to a dead object")
        ref = src.add_ref(tgt, name=name)
        if isinstance(self.collector, RefCountCollector):
            self.collector.update_count(tgt, +1)
        if self.tracer is not None:
            self.tracer.record(
                EventType.LINK,
                src_oid=src.oid,
                tgt_oid=tgt.oid,
                name=name,
                ref_index=len(src.refs) - 1,
            )
        return ref

    def weak_link(self, src: Object, tgt: Object, name: str = "") -> ObjectRef:
        """Add a *weak* reference from ``src`` to ``tgt``.

        Weak references do not prevent the target from being collected and
        do not update reference counts.  The returned :class:`ObjectRef`
        becomes dead (``target=None``) when the target is freed.
        """
        if not isinstance(src, Object):
            raise TypeError("src must be an Object")
        if not isinstance(tgt, Object):
            raise TypeError("tgt must be an Object")
        ref = src.add_weak_ref(tgt, name=name)
        if self.tracer is not None:
            self.tracer.record(
                EventType.WEAK_LINK,
                src_oid=src.oid,
                tgt_oid=tgt.oid,
                name=name,
            )
        return ref

    def add_finalizer(self, obj: Object, fn) -> None:
        """Register a finalizer callback on ``obj``.

        ``fn(obj)`` will be called when ``obj`` is freed by the GC.
        """
        if not isinstance(obj, Object):
            raise TypeError("obj must be an Object")
        if not callable(fn):
            raise TypeError("fn must be callable")
        obj.add_finalizer(fn)
        if self.tracer is not None:
            self.tracer.record(EventType.ADD_FINALIZER, oid=obj.oid)

    def unlink(self, src: Object, ref: ObjectRef) -> None:
        """Remove ``ref`` from ``src.refs`` and decrement the target's count."""
        if ref in src.refs:
            idx = src.refs.index(ref)
            src.refs.remove(ref)
            if ref.target is not None and isinstance(self.collector, RefCountCollector):
                self.collector.update_count(ref.target, -1)
            if self.tracer is not None:
                self.tracer.record(
                    EventType.UNLINK,
                    src_oid=src.oid,
                    ref_index=idx,
                )

    # -- collection ---------------------------------------------------------
    def collect(self, **kwargs) -> CollectionStats:
        """Run one GC cycle and record stats."""
        if isinstance(self.collector, GenerationalCollector):
            stats = self.collector.collect(**kwargs)
        else:
            stats = self.collector.collect()
        # rebuild remembered set for generational after any collect
        self.stats.record(stats)
        # after a compact/copy, reset bump allocator cursor
        if isinstance(self.allocator, BumpAllocator):
            # only reset if a compacting collector ran
            if self.collector_name in ("mark_compact", "copying"):
                self.allocator.reset()
        if self.tracer is not None:
            self.tracer.record(
                EventType.COLLECT,
                cycle=stats.cycle,
                collected=stats.collected,
                bytes_freed=stats.bytes_freed,
                pause_cells=stats.pause_cells,
                force_major=kwargs.get("force_major", False),
            )
        return stats

    # -- queries ------------------------------------------------------------
    @property
    def live_objects(self) -> List[Object]:
        return self.heap.live_objects

    @property
    def used(self) -> int:
        return self.heap.used

    @property
    def free(self) -> int:
        return self.heap.free

    def fragmentation(self) -> float:
        return self.heap.fragmentation()

    def snapshot(self) -> dict:
        """Return a JSON-serialisable snapshot of the entire simulation state."""
        return {
            "heap": self.heap.snapshot(),
            "collector": self.collector_name,
            "stats": self.stats.as_dict(),
            "roots": [name for name in self.roots.labels()],
        }

    def summary(self) -> str:
        return self.stats.summary()

    # -- scenarios ----------------------------------------------------------
    def scenario_linked_list(self, n: int, obj_size: int = 8) -> Object:
        """Allocate a singly-linked list of ``n`` nodes, root the head, and
        return the head object."""
        if n <= 0:
            raise ValueError("n must be positive")
        if obj_size <= 0:
            raise ValueError("obj_size must be positive")
        if self.tracer is not None:
            self.tracer.record(
                EventType.SCENARIO_START, scenario="linked_list",
                n=n, obj_size=obj_size)
        head = self.allocate(obj_size, name="list_head")
        self.add_root("list_head", head)
        cur = head
        for i in range(1, n):
            node = self.allocate(obj_size, name=f"node_{i}")
            self.link(cur, node, name="next")
            cur = node
        if self.tracer is not None:
            self.tracer.record(EventType.SCENARIO_END, scenario="linked_list")
        return head

    def scenario_binary_tree(self, depth: int, obj_size: int = 8) -> Object:
        """Allocate a complete binary tree of the given ``depth`` (root at
        depth 0).  Returns the root object."""
        if depth < 0:
            raise ValueError("depth must be >= 0")
        if obj_size <= 0:
            raise ValueError("obj_size must be positive")
        if self.tracer is not None:
            self.tracer.record(
                EventType.SCENARIO_START, scenario="binary_tree",
                depth=depth, obj_size=obj_size)
        # build level by level
        root = self.allocate(obj_size, name="tree_root")
        self.add_root("tree_root", root)
        prev_level = [root]
        for d in range(1, depth + 1):
            cur_level: List[Object] = []
            for parent in prev_level:
                left = self.allocate(obj_size, name=f"tree_{d}_L")
                right = self.allocate(obj_size, name=f"tree_{d}_R")
                self.link(parent, left, name="left")
                self.link(parent, right, name="right")
                cur_level.append(left)
                cur_level.append(right)
            prev_level = cur_level
        if self.tracer is not None:
            self.tracer.record(EventType.SCENARIO_END, scenario="binary_tree")
        return root

    def scenario_random_graph(self, n: int, edge_prob: float = 0.1,
                               obj_size: int = 4,
                               n_roots: int = 3,
                               seed: Optional[int] = None) -> List[Object]:
        """Allocate ``n`` random objects with ``edge_prob`` probability of a
        reference between any pair, and root the first ``n_roots`` objects."""
        if n <= 0:
            raise ValueError("n must be positive")
        if not 0.0 <= edge_prob <= 1.0:
            raise ValueError("edge_prob must be in [0, 1]")
        if obj_size <= 0:
            raise ValueError("obj_size must be positive")
        if self.tracer is not None:
            self.tracer.record(
                EventType.SCENARIO_START, scenario="random_graph",
                n=n, edge_prob=edge_prob, obj_size=obj_size,
                n_roots=n_roots, seed=seed)
        rng = random.Random(seed)
        objs: List[Object] = []
        for i in range(n):
            objs.append(self.allocate(obj_size, name=f"obj_{i}"))
        for i in range(min(n_roots, n)):
            self.add_root(f"root_{i}", objs[i])
        for i in range(n):
            for j in range(n):
                if i != j and rng.random() < edge_prob:
                    self.link(objs[i], objs[j], name=f"ref_{i}_{j}")
        if self.tracer is not None:
            self.tracer.record(EventType.SCENARIO_END, scenario="random_graph")
        return objs

    def scenario_churn(self, n_short: int = 100, n_long: int = 3,
                        obj_size: int = 4) -> List[Object]:
        """Allocation churn scenario: many short-lived objects plus a few
        long-lived roots.  Models the *generational hypothesis* — most
        objects die young.

        Parameters
        ----------
        n_short : int
            Number of short-lived (unrooted) objects to allocate.
        n_long : int
            Number of long-lived rooted objects.
        obj_size : int
            Object size in cells.
        """
        if n_short < 0 or n_long < 0 or obj_size <= 0:
            raise ValueError("n_short, n_long >= 0 and obj_size > 0 required")
        if self.tracer is not None:
            self.tracer.record(
                EventType.SCENARIO_START, scenario="churn",
                n_short=n_short, n_long=n_long, obj_size=obj_size)
        long_lived: List[Object] = []
        for i in range(n_long):
            obj = self.allocate(obj_size, name=f"long_{i}")
            self.add_root(f"long_{i}", obj)
            long_lived.append(obj)
        for i in range(n_short):
            obj = self.allocate(obj_size, name=f"short_{i}")
            if i % 10 == 0 and long_lived:
                ref = self.link(long_lived[i % len(long_lived)], obj,
                                name=f"temp_{i}")
                self.unlink(long_lived[i % len(long_lived)], ref)
        if self.tracer is not None:
            self.tracer.record(EventType.SCENARIO_END, scenario="churn")
        return long_lived

    def scenario_cycle_heavy(self, n_cycles: int = 10, n_roots: int = 3,
                              obj_size: int = 4) -> List[Object]:
        """Create many cyclic structures (challenging for ref counting).

        Parameters
        ----------
        n_cycles : int
            Number of 2-node cycles to create.
        n_roots : int
            Number of cycles that get a root (rest become garbage).
        obj_size : int
            Object size in cells.
        """
        if n_cycles < 0 or n_roots < 0 or obj_size <= 0:
            raise ValueError("n_cycles, n_roots >= 0 and obj_size > 0 required")
        if self.tracer is not None:
            self.tracer.record(
                EventType.SCENARIO_START, scenario="cycle_heavy",
                n_cycles=n_cycles, n_roots=n_roots, obj_size=obj_size)
        rooted: List[Object] = []
        for i in range(n_cycles):
            a = self.allocate(obj_size, name=f"cyc_a_{i}")
            b = self.allocate(obj_size, name=f"cyc_b_{i}")
            self.link(a, b, name="next")
            self.link(b, a, name="back")
            if i < n_roots:
                self.add_root(f"cyc_root_{i}", a)
                rooted.append(a)
        if self.tracer is not None:
            self.tracer.record(EventType.SCENARIO_END, scenario="cycle_heavy")
        return rooted

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (f"GCSimulator(heap={self.heap}, collector={self.collector_name}, "
                f"allocs={self._alloc_count})")