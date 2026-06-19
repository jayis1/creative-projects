"""Garbage-collection algorithms.

This module implements five classic collectors, all operating on the same
:class:`~gc_sim.heap.Heap` / :class:`~gc_sim.heap.RootSet` abstraction:

* :class:`MarkSweepCollector`  -- trace, then free unmarked objects.
* :class:`MarkCompactCollector` -- trace, then slide live objects to the
  bottom of the heap (Lisp 2 sliding-compact).
* :class:`CopyingCollector`   -- trace by copying live objects to a
  semispace, then flip.
* :class:`RefCountCollector`   -- immediate reclamation via reference counts
  with cycle-collection support.
* :class:`GenerationalCollector` -- a young/old heap with a copying minor
  collector and a mark-sweep major collector.

Every collector returns a :class:`~gc_sim.stats.CollectionStats` describing
the work it did.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .heap import Heap, Object, RootSet
from .tracer import mark_dfs, clear_marks, reachable_set
from .stats import CollectionStats


class Collector(ABC):
    """Abstract base class for all collectors."""

    name: str = "abstract"

    def __init__(self, heap: Heap, roots: RootSet):
        self.heap = heap
        self.roots = roots
        self.cycle = 0

    @abstractmethod
    def collect(self) -> CollectionStats:
        """Run one collection cycle and return statistics."""

    def _base_stats(self) -> CollectionStats:
        self.cycle += 1
        return CollectionStats(
            cycle=self.cycle,
            collector=self.name,
            live_before=self.heap.num_live,
            heap_used_before=self.heap.used,
            fragmentation_before=self.heap.fragmentation(),
            roots_count=len(self.roots),
        )

    def _finish(self, stats: CollectionStats, marked: int,
                bytes_moved: int = 0, promoted: int = 0) -> CollectionStats:
        stats.marked = marked
        stats.live_after = self.heap.num_live
        stats.collected = stats.live_before - stats.live_after
        stats.bytes_freed = stats.heap_used_before - self.heap.used
        stats.bytes_moved = bytes_moved
        stats.promoted = promoted
        stats.fragmentation_after = self.heap.fragmentation()
        stats.heap_used_after = self.heap.used
        # pause cost: marking work + sweeping/moving work
        stats.pause_cells = marked + stats.collected + bytes_moved
        return stats


# ---------------------------------------------------------------------------
# Mark-sweep
# ---------------------------------------------------------------------------

class MarkSweepCollector(Collector):
    """Classic mark-sweep collector.

    Phase 1 -- *mark*: DFS/BFS from the roots, setting ``obj.mark`` on every
    reachable object.
    Phase 2 -- *sweep*: scan every cell; free any object whose mark bit is
    clear.

    Pros: objects do not move (no pointer rewriting needed).
    Cons: fragmentation grows over time.
    """

    name = "mark_sweep"

    def __init__(self, heap: Heap, roots: RootSet, *, mark_strategy: str = "dfs"):
        super().__init__(heap, roots)
        if mark_strategy not in ("dfs", "bfs"):
            raise ValueError(f"unknown mark strategy {mark_strategy!r}")
        self.mark_strategy = mark_strategy

    def collect(self) -> CollectionStats:
        stats = self._base_stats()
        # 1. clear all marks
        clear_marks(self.heap.live_objects)
        # 2. mark from roots
        if self.mark_strategy == "bfs":
            from .tracer import mark_bfs
            marked = mark_bfs(list(self.roots))
        else:
            marked = mark_dfs(list(self.roots))
        # 3. sweep: free any live object that was NOT marked
        for obj in list(self.heap.live_objects):
            if obj.alive and not obj.mark:
                self.heap.free_obj(obj)

        clear_marks(self.heap.live_objects)
        return self._finish(stats, len(marked))


# ---------------------------------------------------------------------------
# Mark-compact (Lisp 2 sliding compaction)
# ---------------------------------------------------------------------------

class MarkCompactCollector(Collector):
    """Mark-sweep followed by sliding compaction (Lisp 2 algorithm).

    1. Mark live objects.
    2. Compute forwarding addresses by sliding live objects toward address 0.
    3. Update references to use forwarding addresses.
    4. Move objects to their forwarding addresses.

    This eliminates fragmentation at the cost of a longer pause.
    """

    name = "mark_compact"

    def collect(self) -> CollectionStats:
        stats = self._base_stats()
        clear_marks(self.heap.live_objects)
        marked = mark_dfs(list(self.roots))

        live = [o for o in self.heap.live_objects if o.mark]
        # Sort by current address so we slide in place
        live.sort(key=lambda o: o.address)

        # 1. compute forwarding addresses
        next_addr = 0
        for o in live:
            o.forwarding = next_addr
            next_addr += o.size

        # 2. update references (roots + live objects' refs)
        def rewrite(obj: Object) -> None:
            for ref in obj.refs:
                tgt = ref.target
                if tgt is not None and tgt.alive and tgt.forwarding >= 0:
                    # the target itself stays the same Python object; only its
                    # address changes. No pointer rewriting needed because we
                    # use ObjectRef, not raw addresses.
                    pass

        for r in list(self.roots):
            rewrite(r)
        for o in live:
            rewrite(o)

        # 3. move objects.  Because objects may overlap during the slide, we
        #    first detach all live objects, then re-place them at their
        #    forwarding addresses.
        for o in live:
            # detach
            for i in range(o.address, o.address + o.size):
                if 0 <= i < self.heap.size and self.heap.cells[i] is o:
                    self.heap.cells[i] = None
        moved = 0
        for o in live:
            old = o.address
            new = o.forwarding
            for i in range(new, new + o.size):
                self.heap.cells[i] = o
            o.address = new
            o.forwarding = -1
            moved += o.size if new != old else 0

        # 4. free dead objects (sweep)
        for obj in list(self.heap.live_objects):
            if obj.alive and not obj.mark:
                self.heap.free_obj(obj)

        clear_marks(self.heap.live_objects)
        return self._finish(stats, len(marked), bytes_moved=moved)


# ---------------------------------------------------------------------------
# Copying (semispace)
# ---------------------------------------------------------------------------

class CopyingCollector(Collector):
    """Stop-the-world copying (Cheney-style) collector.

    The heap is split into two equal *semispaces*: ``from_space`` and
    ``to_space``.  Live objects are copied from ``from`` to ``to``; dead
    objects are simply abandoned.  After the copy the roles of the semispaces
    are swapped.

    Because the heap model here is a single flat array, we implement
    semispaces as the low and high halves of the heap.  ``to_space`` is the
    half not currently in use; we copy survivors there, then conceptually
    flip.  After the flip we reset the bump allocator to the new ``to_space``
    base.

    NOTE: This collector *requires* a :class:`~gc_sim.allocators.BumpAllocator`
    because the "from" side must be a compact region that can be cleared in
    one shot.
    """

    name = "copying"

    def __init__(self, heap: Heap, roots: RootSet, *, allocator=None):
        super().__init__(heap, roots)
        self.allocator = allocator
        self.semispace = 0  # 0 = lower half active, 1 = upper half active
        self.half = heap.size // 2

    def collect(self) -> CollectionStats:
        stats = self._base_stats()
        clear_marks(self.heap.live_objects)

        from_start = self.half * self.semispace
        to_start = self.half * (1 - self.semispace)

        # BFS (Cheney) copy
        # scan queue of copied objects; copy their referents
        from collections import deque
        queue: deque = deque()
        copied: dict = {}  # oid -> new address
        copied_objs: List[Object] = []

        def copy_obj(o: Object) -> int:
            if o.oid in copied:
                return copied[o.oid]
            addr = scan_ptr_current[0]
            scan_ptr_current[0] += o.size
            copied[o.oid] = addr
            copied_objs.append(o)
            queue.append(o)
            return addr

        scan_ptr_current = [to_start]

        # 1. copy roots
        for r in list(self.roots):
            if r is not None and r.alive and r.address >= from_start \
               and r.address < from_start + self.half:
                copy_obj(r)

        # 2. scan queue
        marked = 0
        while queue:
            o = queue.popleft()
            marked += 1
            for ref in o.refs:
                tgt = ref.target
                if tgt is not None and tgt.alive and tgt.oid not in copied:
                    copy_obj(tgt)

        # 3. physically move objects: detach from from_space, place in to_space
        #    First clear the to_space region entirely.
        for i in range(to_start, to_start + self.half):
            self.heap.cells[i] = None
        # detach all live objects (we'll re-place survivors)
        for o in list(self.heap.live_objects):
            if o.alive:
                for i in range(o.address, o.address + o.size):
                    if 0 <= i < self.heap.size and self.heap.cells[i] is o:
                        self.heap.cells[i] = None
        # place survivors
        bytes_moved = 0
        for o in copied_objs:
            new_addr = copied[o.oid]
            for i in range(new_addr, new_addr + o.size):
                self.heap.cells[i] = o
            bytes_moved += o.size
            o.address = new_addr
            o.mark = True

        # 4. free everything that was NOT copied (in from_space)
        # FIX: use heap.free_obj() instead of directly setting alive=False,
        # so that finalizers run and weak references are properly cleared.
        for o in list(self.heap.live_objects):
            if o.alive and o.oid not in copied:
                self.heap.free_obj(o)

        # 5. flip semispace
        self.semispace = 1 - self.semispace
        if self.allocator is not None:
            # reset bump cursor to end of live objects in the new active space
            new_active_start = self.half * self.semispace
            # cursor = scan_ptr_current[0] (end of copied objects)
            self.allocator.cursor = scan_ptr_current[0]

        clear_marks(self.heap.live_objects)
        return self._finish(stats, marked, bytes_moved=bytes_moved)


# ---------------------------------------------------------------------------
# Reference counting
# ---------------------------------------------------------------------------

class RefCountCollector(Collector):
    """Reference-counting collector with optional cycle collection.

    Maintains a per-object reference count incremented on ``add_ref`` and
    decremented on ref removal / object death.  When a count drops to zero
    the object is immediately freed.  Reference counting cannot reclaim
    *cycles* on its own, so an optional *trial deletion* / synchronous cycle
    collector (the "Deutsch-Bobrow" style) can be enabled.

    In this simulation the simulator calls :meth:`update_count` whenever the
    reference graph changes, but a full :meth:`collect` scans for cycles.
    """

    name = "ref_count"

    def __init__(self, heap: Heap, roots: RootSet, *, collect_cycles: bool = True):
        super().__init__(heap, roots)
        self.collect_cycles = collect_cycles
        self.refcounts: dict = {}

    def update_count(self, obj: Object, delta: int) -> None:
        """Increment (``delta=+1``) or decrement (``delta=-1``) a ref count."""
        self.refcounts[obj.oid] = self.refcounts.get(obj.oid, 0) + delta
        if self.refcounts[obj.oid] <= 0 and obj.alive:
            # immediate reclamation
            self._recursive_free(obj)

    def _recursive_free(self, obj: Object) -> None:
        """Free ``obj`` and recursively free any objects it was keeping alive."""
        if not obj.alive:
            return
        # decrement refs of targets
        for ref in list(obj.refs):
            tgt = ref.target
            if tgt is not None and tgt.alive:
                self.refcounts[tgt.oid] = self.refcounts.get(tgt.oid, 0) - 1
                if self.refcounts[tgt.oid] <= 0:
                    self._recursive_free(tgt)
        self.heap.free_obj(obj)
        self.refcounts.pop(obj.oid, None)

    def recompute_counts(self) -> None:
        """Recompute all refcounts from scratch (after structural changes)."""
        self.refcounts.clear()
        # each object gets +1 per incoming reference (from root or other obj)
        # roots
        for r in list(self.roots):
            if r is not None and r.alive:
                self.refcounts[r.oid] = self.refcounts.get(r.oid, 0) + 1
        for o in self.heap.live_objects:
            if not o.alive:
                continue
            for ref in o.refs:
                tgt = ref.target
                if tgt is not None and tgt.alive:
                    self.refcounts[tgt.oid] = self.refcounts.get(tgt.oid, 0) + 1

    def collect(self) -> CollectionStats:
        stats = self._base_stats()
        self.recompute_counts()
        marked = 0
        if self.collect_cycles:
            # Cycle detection: objects with refcount > 0 that are NOT reachable
            # from roots form garbage cycles.  This is a simplified version of
            # the "trial deletion" algorithm.
            reachable = reachable_set(list(self.roots))
            collected = 0
            for obj in list(self.heap.live_objects):
                if obj.alive and obj.oid not in reachable:
                    self.heap.free_obj(obj)
                    collected += 1
            marked = len(reachable)
            stats.collected = collected
        else:
            # just free zero-refcount objects
            collected = 0
            for obj in list(self.heap.live_objects):
                if obj.alive and self.refcounts.get(obj.oid, 0) <= 0:
                    self.heap.free_obj(obj)
                    collected += 1
            marked = self.heap.num_live
            stats.collected = collected
        stats.live_after = self.heap.num_live
        stats.bytes_freed = stats.heap_used_before - self.heap.used
        stats.fragmentation_after = self.heap.fragmentation()
        stats.heap_used_after = self.heap.used
        stats.pause_cells = marked + collected
        stats.marked = marked
        return stats


# ---------------------------------------------------------------------------
# Generational
# ---------------------------------------------------------------------------

class GenerationalCollector(Collector):
    """A two-generation collector.

    * **Young generation** -- serviced by a :class:`CopyingCollector` over the
      lower half of the heap.  Minor collections are frequent and cheap.
    * **Old generation** -- serviced by a :class:`MarkSweepCollector` over the
      upper half.  Major collections are rare and expensive.

    Objects that survive ``promote_threshold`` minor collections are promoted
    to the old generation.  A *remembered set* tracks old-to-young references
    so minor collections don't need to scan the entire old gen.

    For simulation simplicity the heap is split in half: young = lower half,
    old = upper half.
    """

    name = "generational"

    def __init__(self, heap: Heap, roots: RootSet, *,
                 promote_threshold: int = 2,
                 young_ratio: float = 0.5):
        super().__init__(heap, roots)
        self.promote_threshold = promote_threshold
        self.young_size = int(heap.size * young_ratio)
        self.old_size = heap.size - self.young_size
        self.minor_count = 0
        self.major_count = 0
        self.remembered_set: set = set()  # oids of old objects pointing young

    def _is_young(self, obj: Object) -> bool:
        """Return True if ``obj`` is in the young generation.

        Dead objects (address=-1) are treated as *not* young so they are
        not mistaken for young-gen objects during sweep.
        """
        return obj.alive and obj.address >= 0 and obj.address < self.young_size

    def _minor_collect(self) -> CollectionStats:
        """Copy-collect the young generation only."""
        stats = CollectionStats(
            cycle=self.cycle,
            collector=self.name + "_minor",
            live_before=self.heap.num_live,
            heap_used_before=self.heap.used,
            fragmentation_before=self.heap.fragmentation(),
            roots_count=len(self.roots),
        )
        self.minor_count += 1
        clear_marks(self.heap.live_objects)

        # Roots that point into young + remembered set entries
        young_roots = []
        for r in list(self.roots):
            if r is not None and r.alive and self._is_young(r):
                young_roots.append(r)
        # remembered set: old objects pointing into young; their references are
        # treated as additional roots for the minor collection
        for oid in list(self.remembered_set):
            obj = self._find_by_oid(oid)
            if obj is not None and obj.alive:
                for ref in obj.refs:
                    tgt = ref.target
                    if tgt is not None and tgt.alive and self._is_young(tgt):
                        young_roots.append(tgt)

        # Copy young survivors to the old gen boundary (just past young_size)
        # We do a simple compaction of young into [0, young_size) and promote
        # aged objects to [young_size, ...)
        from collections import deque
        queue: deque = deque()
        copied: dict = {}
        young_survivors: List[Object] = []
        promote_ptrs: List[Object] = []

        # BFS copy within young
        def visit(o: Object):
            if o.oid in copied or not o.alive or not self._is_young(o):
                return
            copied[o.oid] = o
            young_survivors.append(o)
            queue.append(o)

        for r in young_roots:
            visit(r)
        while queue:
            o = queue.popleft()
            for ref in o.refs:
                tgt = ref.target
                if tgt is not None and tgt.alive and self._is_young(tgt):
                    visit(tgt)

        # compact young survivors to the bottom
        # detach all young objects
        for o in list(self.heap.live_objects):
            if o.alive and self._is_young(o):
                for i in range(o.address, o.address + o.size):
                    if 0 <= i < self.young_size and self.heap.cells[i] is o:
                        self.heap.cells[i] = None
        # place survivors
        addr = 0
        promoted = 0
        bytes_moved = 0
        old_addr = self.young_size
        for o in young_survivors:
            o.age += 1
            if o.age >= self.promote_threshold and old_addr + o.size <= self.heap.size:
                # promote to old gen
                for i in range(old_addr, old_addr + o.size):
                    self.heap.cells[i] = o
                bytes_moved += o.size
                o.address = old_addr
                old_addr += o.size
                promoted += 1
            else:
                for i in range(addr, addr + o.size):
                    self.heap.cells[i] = o
                bytes_moved += o.size
                o.address = addr
                addr += o.size

        # free dead young objects
        for o in list(self.heap.live_objects):
            if o.alive and self._is_young(o) and o.oid not in copied:
                self.heap.free_obj(o)

        # rebuild remembered set
        self.remembered_set.clear()
        for o in self.heap.live_objects:
            if o.alive and not self._is_young(o):
                for ref in o.refs:
                    tgt = ref.target
                    if tgt is not None and tgt.alive and self._is_young(tgt):
                        self.remembered_set.add(o.oid)
                        break

        clear_marks(self.heap.live_objects)
        stats.marked = len(copied)
        stats.live_after = self.heap.num_live
        stats.collected = stats.live_before - self.heap.num_live
        stats.bytes_freed = stats.heap_used_before - self.heap.used
        stats.bytes_moved = bytes_moved
        stats.promoted = promoted
        stats.fragmentation_after = self.heap.fragmentation()
        stats.heap_used_after = self.heap.used
        stats.pause_cells = len(copied) + stats.collected + bytes_moved
        return stats

    def _major_collect(self) -> CollectionStats:
        """Mark-sweep the old generation."""
        stats = CollectionStats(
            cycle=self.cycle,
            collector=self.name + "_major",
            live_before=self.heap.num_live,
            heap_used_before=self.heap.used,
            fragmentation_before=self.heap.fragmentation(),
            roots_count=len(self.roots),
        )
        self.major_count += 1
        clear_marks(self.heap.live_objects)
        # mark everything reachable (minor handles young; major scans all)
        marked = mark_dfs(list(self.roots))
        # sweep only old-gen objects that are unmarked
        collected = 0
        for obj in list(self.heap.live_objects):
            if obj.alive and not self._is_young(obj) and not obj.mark:
                self.heap.free_obj(obj)
                collected += 1
        clear_marks(self.heap.live_objects)
        # FIX: mark_dfs returns a Set[int]; convert to int count for stats.
        # Previously this assigned the set directly to stats.marked and used
        # it in arithmetic (marked + collected), causing TypeError at runtime.
        stats.marked = len(marked)
        stats.live_after = self.heap.num_live
        stats.collected = collected
        stats.bytes_freed = stats.heap_used_before - self.heap.used
        stats.fragmentation_after = self.heap.fragmentation()
        stats.heap_used_after = self.heap.used
        stats.pause_cells = len(marked) + collected
        return stats

    def _find_by_oid(self, oid: int) -> Optional[Object]:
        for o in self.heap.live_objects:
            if o.oid == oid:
                return o
        return None

    def collect(self, *, force_major: bool = False) -> CollectionStats:
        """Run a collection.  By default a minor collection is performed; a
        major collection is triggered when the old generation is more than
        80% full or when ``force_major`` is set."""
        self.cycle += 1
        if force_major:
            return self._major_collect()
        # decide minor vs major
        old_used = sum(1 for i in range(self.young_size, self.heap.size)
                       if self.heap.cells[i] is not None)
        if old_used > 0.8 * self.old_size:
            return self._major_collect()
        return self._minor_collect()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_COLLECTORS = {
    "mark_sweep": MarkSweepCollector,
    "mark_compact": MarkCompactCollector,
    "copying": CopyingCollector,
    "ref_count": RefCountCollector,
    "generational": GenerationalCollector,
}


def get_collector(name: str, heap: Heap, roots: RootSet, **kwargs) -> Collector:
    """Factory: build a collector by name."""
    if name not in _COLLECTORS:
        raise ValueError(
            f"unknown collector {name!r}; choices: {list(_COLLECTORS)}")
    return _COLLECTORS[name](heap, roots, **kwargs)


def available_collectors() -> List[str]:
    """Return the list of registered collector names."""
    return list(_COLLECTORS)