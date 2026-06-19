"""High-level garbage-collection simulator.

The :class:`GCSimulator` ties together a :class:`~gc_sim.heap.Heap`, an
:class:`~gc_sim.allocators.Allocator`, a :class:`~gc_sim.collectors.Collector`
and a :class:`~gc_sim.stats.StatsTracker`, exposing a convenient API for
building allocation scenarios, running collections and inspecting results.

It also provides several ready-made *scenario* generators (linked lists,
binary trees, random graphs) that produce realistic object-graph shapes for
benchmarking different collectors.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

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
    **collector_kwargs
        Extra keyword arguments forwarded to the collector constructor.
    """

    def __init__(
        self,
        heap_size: int = 1024,
        collector: str = "mark_sweep",
        allocator: str = "bump",
        allocator_policy: str = "first_fit",
        **collector_kwargs,
    ):
        self.heap = Heap(heap_size)
        self.roots = RootSet()
        self.stats = StatsTracker()

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
        return obj

    # -- root management -----------------------------------------------------
    def add_root(self, name: str, obj: Object) -> None:
        self.roots.add(name, obj)
        if isinstance(self.collector, RefCountCollector):
            self.collector.update_count(obj, +1)

    def remove_root(self, name: str) -> None:
        obj = self.roots[name]
        self.roots.remove(name)
        if obj is not None and isinstance(self.collector, RefCountCollector):
            self.collector.update_count(obj, -1)

    def clear_root(self, name: str) -> None:
        obj = self.roots[name]
        self.roots.clear_root(name)
        if obj is not None and isinstance(self.collector, RefCountCollector):
            self.collector.update_count(obj, -1)

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
        return src.add_weak_ref(tgt, name=name)

    def add_finalizer(self, obj: Object, fn) -> None:
        """Register a finalizer callback on ``obj``.

        ``fn(obj)`` will be called when ``obj`` is freed by the GC.
        """
        if not isinstance(obj, Object):
            raise TypeError("obj must be an Object")
        if not callable(fn):
            raise TypeError("fn must be callable")
        obj.add_finalizer(fn)

    def unlink(self, src: Object, ref: ObjectRef) -> None:
        """Remove ``ref`` from ``src.refs`` and decrement the target's count."""
        if ref in src.refs:
            src.refs.remove(ref)
            if ref.target is not None and isinstance(self.collector, RefCountCollector):
                self.collector.update_count(ref.target, -1)

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
        head = self.allocate(obj_size, name="list_head")
        self.add_root("list_head", head)
        cur = head
        for i in range(1, n):
            node = self.allocate(obj_size, name=f"node_{i}")
            self.link(cur, node, name="next")
            cur = node
        return head

    def scenario_binary_tree(self, depth: int, obj_size: int = 8) -> Object:
        """Allocate a complete binary tree of the given ``depth`` (root at
        depth 0).  Returns the root object."""
        if depth < 0:
            raise ValueError("depth must be >= 0")
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
        return root

    def scenario_random_graph(self, n: int, edge_prob: float = 0.1,
                               obj_size: int = 4,
                               n_roots: int = 3,
                               seed: Optional[int] = None) -> List[Object]:
        """Allocate ``n`` random objects with ``edge_prob`` probability of a
        reference between any pair, and root the first ``n_roots`` objects."""
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
        return objs

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (f"GCSimulator(heap={self.heap}, collector={self.collector_name}, "
                f"allocs={self._alloc_count})")