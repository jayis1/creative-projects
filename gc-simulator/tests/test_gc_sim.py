"""Smoke tests for all collectors — verifies Phase 1 works end-to-end."""
import pytest
from gc_sim.simulator import GCSimulator
from gc_sim.heap import Heap, Object, RootSet
from gc_sim.allocators import BumpAllocator, FreeListAllocator
from gc_sim.collectors import (
    MarkSweepCollector, MarkCompactCollector, CopyingCollector,
    RefCountCollector, GenerationalCollector, available_collectors,
)
from gc_sim.tracer import mark_dfs, mark_bfs, reachable_set, detect_cycles


# ---------------------------------------------------------------------------
# Heap / allocator basics
# ---------------------------------------------------------------------------

class TestHeap:
    def test_place_and_free(self):
        h = Heap(64)
        o = Object(size=4)
        h.place(o, 0)
        assert h.used == 4
        assert o.address == 0
        h.free_obj(o)
        assert h.used == 0
        assert not o.alive

    def test_out_of_bounds(self):
        h = Heap(16)
        from gc_sim.heap import HeapError
        with pytest.raises(HeapError):
            h.place(Object(size=4), 14)  # 14+4 > 16

    def test_double_place_collision(self):
        h = Heap(16)
        from gc_sim.heap import HeapError
        h.place(Object(size=4), 0)
        with pytest.raises(HeapError):
            h.place(Object(size=4), 2)

    def test_fragmentation(self):
        h = Heap(16)
        a = Object(size=2); h.place(a, 0)
        b = Object(size=2); h.place(b, 2)
        c = Object(size=2); h.place(c, 4)
        d = Object(size=2); h.place(d, 6)
        # After freeing b and d: free blocks [2,4), [6,16) (merged: [6,8)+[8,16)).
        # total free = 2+10 = 12, largest free block = 10 (cells 6..15)
        # frag = 1 - 10/12 = 1/6
        h.free_obj(b)
        h.free_obj(d)
        assert h.fragmentation() == pytest.approx(1 - 10/12)

    def test_fragmentation_no_free(self):
        h = Heap(8)
        h.place(Object(size=8), 0)
        assert h.fragmentation() == 0.0


class TestBumpAllocator:
    def test_sequential_alloc(self):
        h = Heap(32)
        a = BumpAllocator(h)
        o1 = a.allocate(4)
        o2 = a.allocate(8)
        assert o1.address == 0
        assert o2.address == 4
        assert h.used == 12

    def test_oom(self):
        h = Heap(8)
        a = BumpAllocator(h)
        assert a.allocate(4) is not None
        assert a.allocate(4) is not None
        assert a.allocate(1) is None  # OOM

    def test_reset(self):
        h = Heap(16)
        a = BumpAllocator(h)
        a.allocate(8)
        # reset repositions cursor to end of live objects (after compaction)
        a.reset()
        # cursor should be at used=8, not 0 (object still occupies [0,8))
        assert a.cursor == 8
        # new alloc continues after existing objects
        o = a.allocate(4)
        assert o is not None
        assert o.address == 8


class TestFreeListAllocator:
    def test_reuse_freed(self):
        h = Heap(16)
        a = FreeListAllocator(h, policy="first_fit")
        o1 = a.allocate(4)
        o2 = a.allocate(4)
        h.free_obj(o1)
        o3 = a.allocate(2)  # should reuse freed space at addr 0
        assert o3.address == 0

    def test_best_fit(self):
        h = Heap(32)
        a = FreeListAllocator(h, policy="best_fit")
        o1 = a.allocate(4); o2 = a.allocate(8); o3 = a.allocate(4)
        h.free_obj(o1)  # free block [0,4)
        h.free_obj(o2)  # free block [4,12)
        # request 3 cells: best fit is [0,4) (size 4)
        o4 = a.allocate(3)
        assert o4.address == 0

    def test_worst_fit(self):
        h = Heap(32)
        a = FreeListAllocator(h, policy="worst_fit")
        o1 = a.allocate(4); o2 = a.allocate(8); o3 = a.allocate(4)
        # Layout: o1=[0,4), o2=[4,12), o3=[12,16), free=[16,32) (16 cells)
        # Free o1 and o2 -> adjacent blocks merge into [0,12) (12 cells)
        h.free_obj(o1)  # [0,4)
        h.free_obj(o2)  # [4,12) -> merges with [0,4) -> [0,12)
        # Free blocks: [0,12) size=12, [16,32) size=16
        # request 3: worst fit is [16,32) (size 16)
        o4 = a.allocate(3)
        assert o4.address == 16


# ---------------------------------------------------------------------------
# Tracer
# ---------------------------------------------------------------------------

class TestTracer:
    def test_dfs_marking(self):
        h = Heap(64)
        roots = RootSet()
        a = Object(size=4); h.place(a, 0)
        b = Object(size=4); h.place(b, 4)
        c = Object(size=4); h.place(c, 8)
        d = Object(size=4); h.place(d, 12)  # unreachable
        roots.add("a", a)
        a.add_ref(b)
        b.add_ref(c)
        marked = mark_dfs(list(roots))
        assert a.mark and b.mark and c.mark
        assert not d.mark
        assert len(marked) == 3

    def test_bfs_marking(self):
        h = Heap(64)
        roots = RootSet()
        a = Object(size=4); h.place(a, 0)
        b = Object(size=4); h.place(b, 4)
        roots.add("a", a)
        a.add_ref(b)
        marked = mark_bfs(list(roots))
        assert a.mark and b.mark
        assert len(marked) == 2

    def test_reachable_set(self):
        h = Heap(64)
        roots = RootSet()
        a = Object(size=4); h.place(a, 0)
        b = Object(size=4); h.place(b, 4)
        c = Object(size=4); h.place(c, 8)
        roots.add("a", a)
        a.add_ref(b)
        # c is unreachable
        r = reachable_set(list(roots))
        assert a.oid in r and b.oid in r
        assert c.oid not in r

    def test_cycle_detection(self):
        h = Heap(64)
        roots = RootSet()
        a = Object(size=4); h.place(a, 0)
        b = Object(size=4); h.place(b, 4)
        roots.add("a", a)
        a.add_ref(b)
        b.add_ref(a)  # cycle a <-> b
        cycles = detect_cycles(list(roots))
        assert len(cycles) >= 1


# ---------------------------------------------------------------------------
# Collectors via GCSimulator
# ---------------------------------------------------------------------------

@pytest.fixture
def linked_list_sim():
    """Common fixture: 10-node linked list."""
    def _make(collector="mark_sweep", **kw):
        sim = GCSimulator(heap_size=256, collector=collector, **kw)
        sim.scenario_linked_list(n=10, obj_size=8)
        return sim
    return _make


class TestMarkSweep:
    def test_collects_unreachable(self, linked_list_sim):
        sim = linked_list_sim("mark_sweep")
        # unroot the list — all nodes become unreachable
        sim.clear_root("list_head")
        stats = sim.collect()
        assert stats.collected == 10
        assert sim.heap.num_live == 0

    def test_keeps_reachable(self, linked_list_sim):
        sim = linked_list_sim("mark_sweep")
        stats = sim.collect()
        assert stats.collected == 0
        assert sim.heap.num_live == 10

    def test_partial_collection(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        c = sim.allocate(8, "c")
        sim.add_root("a", a)
        sim.link(a, b, "next")
        # c is unreachable
        stats = sim.collect()
        assert stats.collected == 1
        assert sim.heap.num_live == 2


class TestMarkCompact:
    def test_compaction_eliminates_fragmentation(self):
        sim = GCSimulator(heap_size=256, collector="mark_compact")
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        c = sim.allocate(8, "c")
        d = sim.allocate(8, "d")
        sim.add_root("a", a)
        sim.add_root("c", c)
        # b and d are unreachable
        frag_before = sim.fragmentation()
        stats = sim.collect()
        assert stats.collected == 2
        assert sim.heap.num_live == 2
        # after compaction fragmentation should be 0 (objects packed to bottom)
        assert sim.fragmentation() == 0.0

    def test_addresses_compacted(self):
        sim = GCSimulator(heap_size=256, collector="mark_compact")
        a = sim.allocate(16, "a")
        b = sim.allocate(16, "b")
        sim.add_root("b", b)
        # a is unreachable, b should slide to address 0
        sim.collect()
        assert b.address == 0


class TestCopying:
    def test_copies_survivors(self):
        sim = GCSimulator(heap_size=256, collector="copying",
                          allocator="bump")
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        c = sim.allocate(8, "c")
        sim.add_root("a", a)
        sim.link(a, b, "next")
        # c is unreachable
        stats = sim.collect()
        assert stats.collected >= 1
        assert sim.heap.num_live == 2

    def test_semispace_flip(self):
        sim = GCSimulator(heap_size=128, collector="copying",
                          allocator="bump")
        a = sim.allocate(8, "a")
        sim.add_root("a", a)
        sim.collect()
        # after first collect, a should be in the to_space (upper half)
        assert a.alive
        assert a.address >= 64  # upper half


class TestRefCount:
    def test_immediate_free_on_zero(self):
        sim = GCSimulator(heap_size=256, collector="ref_count",
                          collect_cycles=False)
        a = sim.allocate(8, "a")
        sim.add_root("r", a)
        assert sim.collector.refcounts[a.oid] == 1
        sim.remove_root("r")
        assert sim.collector.refcounts.get(a.oid, 0) == 0
        assert not a.alive

    def test_cycle_collection(self):
        sim = GCSimulator(heap_size=256, collector="ref_count",
                          collect_cycles=True)
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        sim.add_root("root_a", a)
        sim.link(a, b)
        sim.link(b, a)  # cycle
        # remove root: a and b form an unreachable cycle
        sim.remove_root("root_a")
        stats = sim.collect()
        assert sim.heap.num_live == 0


class TestGenerational:
    def test_minor_collects_young(self):
        sim = GCSimulator(heap_size=256, collector="generational",
                          promote_threshold=1)
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        sim.add_root("a", a)
        sim.link(a, b, "next")
        # b is reachable from a (both young)
        stats = sim.collect()
        # both survive minor collection
        assert a.alive
        assert b.alive

    def test_promotion(self):
        sim = GCSimulator(heap_size=256, collector="generational",
                          promote_threshold=1)
        a = sim.allocate(8, "a")
        sim.add_root("a", a)
        # after one minor collect with promote_threshold=1, a should be promoted
        sim.collect()
        assert a.age >= 1
        # a should now be in old gen (address >= young_size)
        young_size = sim.collector.young_size
        assert a.address >= young_size


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class TestScenarios:
    def test_linked_list(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep")
        head = sim.scenario_linked_list(n=5, obj_size=8)
        assert sim.heap.num_live == 5
        sim.collect()
        assert sim.heap.num_live == 5  # all reachable from root

    def test_binary_tree(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep")
        root = sim.scenario_binary_tree(depth=2, obj_size=8)
        # 1 + 2 + 4 = 7 nodes
        assert sim.heap.num_live == 7
        sim.collect()
        assert sim.heap.num_live == 7

    def test_random_graph(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep")
        objs = sim.scenario_random_graph(n=20, edge_prob=0.1, n_roots=3,
                                          seed=42)
        assert sim.heap.num_live == 20
        sim.collect()
        # at least the root objects survive
        assert sim.heap.num_live >= 3


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_recorded(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        sim.scenario_linked_list(n=5, obj_size=8)
        sim.collect()
        assert sim.stats.num_collections == 1
        assert sim.stats.records[0].live_before == 5

    def test_summary(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        sim.scenario_linked_list(n=3, obj_size=8)
        sim.collect()
        s = sim.summary()
        assert "GC Statistics" in s


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_list(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["list"])
        assert ret == 0
        assert "mark_sweep" in buf.getvalue()

    def test_run(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["run", "--collector", "mark_sweep",
                        "--scenario", "linked_list",
                        "--scenario-params", '{"n": 5, "obj_size": 8}'])
        assert ret == 0
        assert "GC Statistics" in buf.getvalue()

    def test_compare(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["compare", "--heap-size", "256",
                        "--collectors", "mark_sweep", "ref_count",
                        "--scenario", "linked_list",
                        "--scenario-params", '{"n": 5, "obj_size": 8}'])
        assert ret == 0
        assert "mark_sweep" in buf.getvalue()