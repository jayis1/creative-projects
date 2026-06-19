"""Bug-hunt tests for the GC simulator.

Each test verifies a specific bug before the fix is applied, then confirms
the fix works afterward.  Tests are named descriptively.
"""

import pytest
from gc_sim.simulator import GCSimulator
from gc_sim.heap import Heap, Object, RootSet
from gc_sim.collectors import (
    MarkSweepCollector, MarkCompactCollector, CopyingCollector,
    RefCountCollector, GenerationalCollector,
)


# ---------------------------------------------------------------------------
# Bug A: _major_collect assigns a Set[int] to stats.marked (typed as int)
#        and computes pause_cells = marked + collected, which raises
#        TypeError: unsupported operand type(s) for +: 'set' and 'int'
# ---------------------------------------------------------------------------

class TestBugMajorCollectMarkedType:
    def test_major_collect_does_not_crash(self):
        """A major collection (force_major=True) must not raise TypeError."""
        sim = GCSimulator(heap_size=256, collector="generational",
                          promote_threshold=1)
        sim.scenario_linked_list(n=5, obj_size=8)
        # Force a major collection — this used to crash with TypeError
        stats = sim.collect(force_major=True)
        assert isinstance(stats.marked, int)
        assert isinstance(stats.pause_cells, int)

    def test_major_collect_marked_is_int(self):
        sim = GCSimulator(heap_size=256, collector="generational")
        sim.scenario_linked_list(n=3, obj_size=8)
        stats = sim.collect(force_major=True)
        assert isinstance(stats.marked, int)
        assert stats.marked >= 0
        assert isinstance(stats.pause_cells, int)


# ---------------------------------------------------------------------------
# Bug B: CopyingCollector frees dead objects by directly setting alive=False
#        instead of calling heap.free_obj(), which means finalizers are NOT
#        run and weak references pointing to the dead objects are NOT cleared.
# ---------------------------------------------------------------------------

class TestBugCopyingFinalizers:
    def test_copying_runs_finalizers(self):
        """Finalizers must be called for objects collected by the copying GC."""
        sim = GCSimulator(heap_size=256, collector="copying",
                          allocator="bump")
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")  # will be unreachable
        called = []
        sim.add_finalizer(b, lambda obj: called.append(obj.oid))
        sim.add_root("a", a)
        # b is unreachable
        sim.collect()
        assert called == [b.oid], \
            "Copying collector should run finalizers on dead objects"

    def test_copying_clears_weak_refs(self):
        """Weak refs to dead objects must be cleared by the copying GC."""
        sim = GCSimulator(heap_size=256, collector="copying",
                          allocator="bump")
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")  # unreachable
        sim.add_root("a", a)
        wref = sim.weak_link(a, b, "weak_b")
        assert not wref.is_dead
        sim.collect()
        assert wref.is_dead, \
            "Copying collector should clear weak refs to dead objects"
        assert wref.target is None


# ---------------------------------------------------------------------------
# Bug C: GenerationalCollector._is_young returns True for dead objects
#        because address=-1 < young_size.  This can cause freed objects to
#        be treated as young, leading to double-free or incorrect stats.
# ---------------------------------------------------------------------------

class TestBugIsYoungForDeadObjects:
    def test_is_young_dead_object(self):
        """_is_young should return False for dead objects (address=-1)."""
        heap = Heap(256)
        roots = RootSet()
        col = GenerationalCollector(heap, roots, young_ratio=0.5)
        obj = Object(size=8)
        heap.place(obj, 4)  # in young gen
        assert col._is_young(obj)
        heap.free_obj(obj)
        # After freeing, address is -1, which is < young_size.
        # _is_young should NOT return True for a dead object.
        assert not obj.alive
        # The fix: _is_young should check obj.alive or obj.address >= 0
        assert not col._is_young(obj), \
            "_is_young should return False for dead objects"


# ---------------------------------------------------------------------------
# Bug D: MarkCompactCollector rewrite function is a no-op (dead code).
#        While not a runtime bug, it's misleading.  This test just documents
#        that compaction still works correctly despite the no-op rewrite.
# ---------------------------------------------------------------------------

class TestBugMarkCompactNoOpRewrite:
    def test_compact_preserves_references(self):
        """After compaction, object references should still be valid."""
        sim = GCSimulator(heap_size=256, collector="mark_compact")
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        c = sim.allocate(8, "c")
        sim.add_root("a", a)
        sim.link(a, b, "next")
        sim.link(b, c, "next")
        sim.collect()
        # References should still be valid after compaction
        assert a.alive and b.alive and c.alive
        # Check that refs still point to the right objects
        assert a.refs[0].target is b
        assert b.refs[0].target is c


# ---------------------------------------------------------------------------
# Bug E: CopyingCollector — when a root points to an object that was already
#        copied to to_space in a previous collection, the root filter
#        `r.address >= from_start` may skip it.  This test verifies that
#        multiple collections work correctly.
# ---------------------------------------------------------------------------

class TestBugCopyingMultipleCollections:
    def test_multiple_collections(self):
        """Objects must survive multiple copying collections."""
        sim = GCSimulator(heap_size=256, collector="copying",
                          allocator="bump")
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        sim.add_root("a", a)
        sim.link(a, b, "next")
        # First collection: copy a and b to to_space
        sim.collect()
        assert a.alive and b.alive
        # Second collection: copy a and b back to from_space
        sim.collect()
        assert a.alive and b.alive
        # Third collection
        sim.collect()
        assert a.alive and b.alive


# ---------------------------------------------------------------------------
# Bug F: RefCountCollector._recursive_free doesn't run finalizers
#        because it calls heap.free_obj which does run finalizers.
#        Actually, this is correct — let me verify it works.
# ---------------------------------------------------------------------------

class TestBugRefCountFinalizers:
    def test_ref_count_runs_finalizers(self):
        """Ref counting should run finalizers when objects are freed."""
        sim = GCSimulator(heap_size=256, collector="ref_count",
                          collect_cycles=False)
        a = sim.allocate(8, "a")
        called = []
        sim.add_finalizer(a, lambda obj: called.append(obj.oid))
        sim.add_root("r", a)
        sim.remove_root("r")  # refcount drops to 0, a is freed
        assert called == [a.oid]


# ---------------------------------------------------------------------------
# Bug G: GenerationalCollector — when minor collection promotes objects,
#        the promoted objects' addresses change.  Any references from
#        non-promoted young objects to promoted objects should still work
#        because we use ObjectRef (Python object identity), not addresses.
#        This test verifies that cross-generational references survive.
# ---------------------------------------------------------------------------

class TestBugGenerationalCrossGenRefs:
    def test_cross_gen_reference_survives(self):
        """A young object referencing a promoted object should still work."""
        sim = GCSimulator(heap_size=256, collector="generational",
                          promote_threshold=1)
        # a will be promoted after 1 minor collection
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        sim.add_root("a", a)
        sim.add_root("b", b)
        sim.link(b, a, "ref_to_a")
        # First minor: a gets promoted (age >= 1), b stays young
        sim.collect()
        assert a.alive
        assert b.alive
        # b's reference to a should still be valid
        assert b.refs[0].target is a
        # Second minor: b may get promoted too
        sim.collect()
        assert a.alive
        assert b.alive
        assert b.refs[0].target is a


# ---------------------------------------------------------------------------
# Bug H: CopyingCollector — the `scan_ptr` variable on line 231 is dead code
#        (unused).  Not a runtime bug, just cleanup.
# ---------------------------------------------------------------------------

class TestBugCopyingDeadCode:
    def test_copying_no_unused_scan_ptr(self):
        """Verify the CopyingCollector doesn't have a stale scan_ptr variable
        that could cause confusion."""
        import inspect
        from gc_sim.collectors import CopyingCollector
        source = inspect.getsource(CopyingCollector.collect)
        # The dead `scan_ptr = to_start` line should be removed
        lines = [l.strip() for l in source.splitlines()]
        # After fix, there should be no standalone "scan_ptr = to_start"
        # (scan_ptr_current is the one that's used)
        standalone_scan_ptr = [l for l in lines
                               if l == "scan_ptr = to_start"]
        assert len(standalone_scan_ptr) == 0, \
            "Dead code: 'scan_ptr = to_start' should be removed"


# ---------------------------------------------------------------------------
# Bug I: GenerationalCollector.collect() with force_major=True increments
#        self.cycle, but _minor_collect and _major_collect use self.cycle
#        without incrementing it.  If collect() is called with force_major,
#        then called again without, the cycle counter should still be
#        sequential.
# ---------------------------------------------------------------------------

class TestBugGenerationalCycleCounter:
    def test_cycle_counter_sequential(self):
        """Cycle counter should increment by 1 for each collect() call."""
        sim = GCSimulator(heap_size=256, collector="generational")
        sim.scenario_linked_list(n=3, obj_size=8)
        s1 = sim.collect()
        s2 = sim.collect()
        s3 = sim.collect(force_major=True)
        s4 = sim.collect()
        assert s1.cycle == 1
        assert s2.cycle == 2
        assert s3.cycle == 3
        assert s4.cycle == 4