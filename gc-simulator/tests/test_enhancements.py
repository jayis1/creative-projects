"""Tests for event tracing, replay, reporting and new simulator features."""

import json
import os
import tempfile
import pytest
from gc_sim.simulator import GCSimulator
from gc_sim.events import EventTracer, Event, EventType
from gc_sim.replay import TraceReplayer, replay_from_file, load_trace
from gc_sim.reporting import (
    PauseHistogram,
    CollectorReport,
    format_comparison_report,
    generate_report_json,
    analyse_from_sims,
)
from gc_sim.stats import CollectionStats, StatsTracker
from gc_sim.collectors import available_collectors
from gc_sim.heap import Heap, Object


# ===========================================================================
# Event tracing
# ===========================================================================

class TestEventTracer:
    def test_tracer_not_enabled_by_default(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        assert sim.tracer is None

    def test_tracer_enabled_with_flag(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        assert sim.tracer is not None
        assert isinstance(sim.tracer, EventTracer)

    def test_allocate_event_recorded(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        obj = sim.allocate(8, "test_obj")
        events = sim.tracer.events
        assert len(events) == 1
        assert events[0].event_type == EventType.ALLOCATE.value
        assert events[0].data["size"] == 8
        assert events[0].data["name"] == "test_obj"
        assert events[0].data["oid"] == obj.oid

    def test_add_root_event_recorded(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        obj = sim.allocate(8, "a")
        sim.add_root("r", obj)
        events = sim.tracer.events
        assert len(events) == 2
        assert events[1].event_type == EventType.ADD_ROOT.value
        assert events[1].data["name"] == "r"
        assert events[1].data["oid"] == obj.oid

    def test_link_event_recorded(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        sim.add_root("ra", a)
        sim.link(a, b, "next")
        link_events = sim.tracer.filter(EventType.LINK.value)
        assert len(link_events) == 1
        assert link_events[0].data["src_oid"] == a.oid
        assert link_events[0].data["tgt_oid"] == b.oid
        assert link_events[0].data["name"] == "next"

    def test_collect_event_recorded(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=5, obj_size=8)
        sim.collect()
        collect_events = sim.tracer.filter(EventType.COLLECT.value)
        assert len(collect_events) == 1
        assert collect_events[0].data["collected"] == 0

    def test_scenario_events_recorded(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=3, obj_size=8)
        start_events = sim.tracer.filter(EventType.SCENARIO_START.value)
        end_events = sim.tracer.filter(EventType.SCENARIO_END.value)
        assert len(start_events) == 1
        assert len(end_events) == 1
        assert start_events[0].data["scenario"] == "linked_list"

    def test_export_json(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=3, obj_size=8)
        sim.collect()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            sim.tracer.export_json(path)
            with open(path) as f:
                data = json.load(f)
            assert isinstance(data, list)
            assert len(data) > 0
            assert all("seq" in e and "event_type" in e for e in data)
        finally:
            os.unlink(path)

    def test_event_counts(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=3, obj_size=8)
        sim.collect()
        counts = sim.tracer.counts()
        assert counts.get(EventType.ALLOCATE.value, 0) == 3
        assert counts.get(EventType.COLLECT.value, 0) == 1

    def test_tracer_clear(self):
        tracer = EventTracer()
        tracer.record(EventType.ALLOCATE, size=8)
        assert len(tracer) == 1
        tracer.clear()
        assert len(tracer) == 0

    def test_tracer_disable_enable(self):
        tracer = EventTracer()
        tracer.disable()
        tracer.record(EventType.NOTE, msg="test")
        assert len(tracer) == 0
        tracer.enable()
        tracer.record(EventType.NOTE, msg="test2")
        assert len(tracer) == 1

    def test_event_from_dict_roundtrip(self):
        ev = Event(seq=5, timestamp=1.0, event_type="allocate",
                   data={"size": 8, "oid": 1})
        d = ev.to_dict()
        ev2 = Event.from_dict(d)
        assert ev2.seq == 5
        assert ev2.event_type == "allocate"
        assert ev2.data["size"] == 8

    def test_from_json_loads_tracer(self):
        """EventTracer.from_json should load events from a file."""
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=3, obj_size=8)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(sim.tracer.export(), f)
            path = f.name
        try:
            tracer = EventTracer.from_json(path)
            assert len(tracer) == len(sim.tracer)
            assert tracer.events[0].event_type == EventType.SCENARIO_START.value
        finally:
            os.unlink(path)


# ===========================================================================
# Replay
# ===========================================================================

class TestReplay:
    def test_replay_same_collector(self):
        """Replaying a trace on the same collector should produce the same
        number of allocations and similar results."""
        sim = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=10, obj_size=8)
        sim.collect()

        replayer = TraceReplayer(sim.tracer, collector="mark_sweep",
                                 heap_size=512)
        replayed = replayer.replay()
        assert replayed._alloc_count == sim._alloc_count

    def test_replay_different_collector(self):
        """Replaying on a different collector should work."""
        sim = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
        sim.scenario_binary_tree(depth=2, obj_size=8)
        sim.collect()

        replayer = TraceReplayer(sim.tracer, collector="copying",
                                 heap_size=512)
        replayed = replayer.replay()
        assert replayed._alloc_count == sim._alloc_count

    def test_replay_random_graph(self):
        """Replaying a random graph trace on a different collector."""
        sim = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
        sim.scenario_random_graph(n=20, edge_prob=0.1, n_roots=3, seed=42)
        sim.collect()

        replayer = TraceReplayer(sim.tracer, collector="generational",
                                 heap_size=512)
        replayed = replayer.replay()
        assert replayed._alloc_count == 20

    def test_replay_no_collections(self):
        """Replaying without collections should skip collection events."""
        sim = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=5, obj_size=8)
        sim.collect()
        sim.clear_root("list_head")
        sim.collect()

        replayer = TraceReplayer(sim.tracer, collector="mark_sweep",
                                 heap_size=512)
        replayed = replayer.replay(run_collections=False)
        # Should have the same allocations but no collections
        assert replayed._alloc_count == sim._alloc_count
        assert replayed.stats.num_collections == 0

    def test_replay_all_collectors(self):
        """Replay on all collectors should produce a dict of sims."""
        sim = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=5, obj_size=8)

        replayer = TraceReplayer(sim.tracer, collector="mark_sweep",
                                 heap_size=512)
        results = replayer.replay_all_collectors()
        assert len(results) == len(available_collectors())
        for cname, s in results.items():
            assert s._alloc_count == 5

    def test_replay_from_file(self):
        """Load a trace file and replay it."""
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=5, obj_size=8)
        sim.collect()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(sim.tracer.export(), f)
            path = f.name
        try:
            replayed = replay_from_file(path, collector="mark_sweep",
                                        heap_size=256)
            assert replayed._alloc_count == 5
        finally:
            os.unlink(path)

    def test_replay_from_event_list(self):
        """TraceReplayer should accept a list of event dicts."""
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=3, obj_size=8)
        events = sim.tracer.export()
        replayer = TraceReplayer(events, collector="mark_sweep", heap_size=256)
        replayed = replayer.replay()
        assert replayed._alloc_count == 3

    def test_replay_trace_type_error(self):
        """TraceReplayer should reject invalid trace types."""
        with pytest.raises(TypeError):
            TraceReplayer("not a trace")


# ===========================================================================
# Reporting
# ===========================================================================

class TestPauseHistogram:
    def test_empty_histogram(self):
        hist = PauseHistogram.from_records([])
        assert hist.total == 0
        assert "no data" in hist.render_ascii()

    def test_single_record(self):
        stats = CollectionStats(cycle=1, collector="test", live_before=10,
                                pause_cells=5)
        hist = PauseHistogram.from_records([stats])
        assert hist.total == 1
        assert hist.min_val == 5
        assert hist.max_val == 5
        assert hist.mean_val == 5.0

    def test_multiple_records(self):
        records = []
        for i in range(1, 11):
            records.append(CollectionStats(
                cycle=i, collector="test", live_before=10,
                pause_cells=i * 10))
        hist = PauseHistogram.from_records(records)
        assert hist.total == 10
        assert hist.min_val == 10
        assert hist.max_val == 100
        assert hist.mean_val == 55.0

    def test_percentiles(self):
        records = []
        for i in range(1, 101):
            records.append(CollectionStats(
                cycle=i, collector="test", live_before=10,
                pause_cells=i))
        hist = PauseHistogram.from_records(records)
        assert hist.p90 >= 90
        assert hist.p95 >= 95
        assert hist.p99 >= 99

    def test_render_ascii_not_empty(self):
        records = [
            CollectionStats(cycle=1, collector="test", live_before=10,
                            pause_cells=5),
            CollectionStats(cycle=2, collector="test", live_before=10,
                            pause_cells=20),
        ]
        hist = PauseHistogram.from_records(records)
        text = hist.render_ascii()
        assert "Pause-time histogram" in text
        assert "2 collections" in text

    def test_custom_bins(self):
        records = [
            CollectionStats(cycle=1, collector="test", live_before=10,
                            pause_cells=3),
        ]
        hist = PauseHistogram.from_records(records, bins=[2, 5, 10])
        assert hist.bins == [2, 5, 10]
        # 3 falls in the 2-5 bucket
        assert hist.counts[1] == 1

    def test_to_dict(self):
        records = [
            CollectionStats(cycle=1, collector="test", live_before=10,
                            pause_cells=5),
        ]
        hist = PauseHistogram.from_records(records)
        d = hist.to_dict()
        assert "bins" in d
        assert "counts" in d
        assert "total" in d
        assert d["total"] == 1


class TestCollectorReport:
    def test_from_simulator(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        sim.scenario_linked_list(n=5, obj_size=8)
        sim.collect()
        report = CollectorReport.from_simulator(sim)
        assert report.collector == "mark_sweep"
        assert report.num_collections == 1
        assert report.histogram is not None
        assert report.histogram.total == 1

    def test_to_dict(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        sim.scenario_linked_list(n=3, obj_size=8)
        sim.collect()
        report = CollectorReport.from_simulator(sim)
        d = report.to_dict()
        assert d["collector"] == "mark_sweep"
        assert "histogram" in d


class TestComparisonReport:
    def test_format_comparison_report(self):
        sims = {}
        for cname in ["mark_sweep", "ref_count"]:
            sim = GCSimulator(heap_size=256, collector=cname)
            sim.scenario_linked_list(n=5, obj_size=8)
            sim.collect()
            sims[cname] = sim
        reports = analyse_from_sims(sims)
        text = format_comparison_report(reports)
        assert "GC Collector Comparison Report" in text
        assert "mark_sweep" in text
        assert "ref_count" in text
        assert "Winner Analysis" in text

    def test_comparison_with_histogram(self):
        sims = {}
        for cname in ["mark_sweep", "copying"]:
            sim = GCSimulator(heap_size=256, collector=cname)
            sim.scenario_linked_list(n=5, obj_size=8)
            sim.collect()
            sims[cname] = sim
        reports = analyse_from_sims(sims)
        text = format_comparison_report(reports, include_histogram=True)
        assert "histogram" in text.lower()

    def test_generate_report_json(self):
        sims = {}
        for cname in ["mark_sweep"]:
            sim = GCSimulator(heap_size=256, collector=cname)
            sim.scenario_linked_list(n=3, obj_size=8)
            sim.collect()
            sims[cname] = sim
        reports = analyse_from_sims(sims)
        j = generate_report_json(reports)
        data = json.loads(j)
        assert len(data) == 1
        assert data[0]["collector"] == "mark_sweep"


# ===========================================================================
# New scenarios
# ===========================================================================

class TestChurnScenario:
    def test_churn_creates_objects(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep")
        long_lived = sim.scenario_churn(n_short=50, n_long=3, obj_size=4)
        assert len(long_lived) == 3
        assert sim.heap.num_live > 0

    def test_churn_collects_short_lived(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep")
        sim.scenario_churn(n_short=50, n_long=3, obj_size=4)
        sim.collect()
        # Only long-lived (3) survive because short-lived are unrooted
        assert sim.heap.num_live == 3

    def test_churn_invalid_args(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep")
        with pytest.raises(ValueError):
            sim.scenario_churn(n_short=-1)
        with pytest.raises(ValueError):
            sim.scenario_churn(obj_size=0)


class TestCycleHeavyScenario:
    def test_cycle_heavy_creates_cycles(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep")
        rooted = sim.scenario_cycle_heavy(n_cycles=5, n_roots=2, obj_size=4)
        assert len(rooted) == 2
        # 5 cycles × 2 objects = 10 objects
        assert sim.heap.num_live == 10

    def test_cycle_heavy_collection(self):
        sim = GCSimulator(heap_size=512, collector="ref_count",
                          collect_cycles=True)
        sim.scenario_cycle_heavy(n_cycles=5, n_roots=2, obj_size=4)
        sim.collect()
        # Only 2 rooted cycles survive (4 objects)
        assert sim.heap.num_live <= 4

    def test_cycle_heavy_invalid_args(self):
        sim = GCSimulator(heap_size=512, collector="mark_sweep")
        with pytest.raises(ValueError):
            sim.scenario_cycle_heavy(n_cycles=-1)
        with pytest.raises(ValueError):
            sim.scenario_cycle_heavy(obj_size=0)


# ===========================================================================
# Simulator input validation
# ===========================================================================

class TestInputValidation:
    def test_allocate_zero_size(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        with pytest.raises(ValueError):
            sim.allocate(0)

    def test_allocate_negative_size(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        with pytest.raises(ValueError):
            sim.allocate(-5)

    def test_scenario_linked_list_zero(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        with pytest.raises(ValueError):
            sim.scenario_linked_list(n=0)

    def test_scenario_binary_tree_negative_depth(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        with pytest.raises(ValueError):
            sim.scenario_binary_tree(depth=-1)

    def test_scenario_random_graph_invalid_edge_prob(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        with pytest.raises(ValueError):
            sim.scenario_random_graph(n=10, edge_prob=1.5)
        with pytest.raises(ValueError):
            sim.scenario_random_graph(n=10, edge_prob=-0.1)

    def test_link_dead_object(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        a = sim.allocate(8, "a")
        b = sim.allocate(8, "b")
        sim.heap.free_obj(b)
        with pytest.raises(ValueError):
            sim.link(a, b)

    def test_link_non_object(self):
        sim = GCSimulator(heap_size=256, collector="mark_sweep")
        with pytest.raises(TypeError):
            sim.link("not_obj", sim.allocate(8))

    def test_unknown_collector(self):
        with pytest.raises(ValueError):
            GCSimulator(heap_size=256, collector="nonexistent")

    def test_unknown_allocator(self):
        with pytest.raises(ValueError):
            GCSimulator(heap_size=256, collector="mark_sweep",
                        allocator="nonexistent")


# ===========================================================================
# CLI new subcommands
# ===========================================================================

class TestCLINew:
    def test_trace(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["trace", "--heap-size", "256",
                        "--scenario", "linked_list",
                        "--scenario-params", '{"n": 5, "obj_size": 8}'])
        assert ret == 0
        out = buf.getvalue()
        assert '"event_type"' in out or "allocate" in out

    def test_trace_to_file(self):
        from gc_sim.cli import main
        import io, contextlib
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ret = main(["trace", "--heap-size", "256",
                            "--scenario", "linked_list",
                            "--scenario-params", '{"n": 3, "obj_size": 8}',
                            "--output", path, "--summary"])
            assert ret == 0
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert len(data) > 0
            assert "Event counts" in buf.getvalue()
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_replay(self):
        from gc_sim.cli import main
        import io, contextlib
        # First create a trace
        sim = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim.scenario_linked_list(n=5, obj_size=8)
        sim.collect()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(sim.tracer.export(), f)
            path = f.name
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ret = main(["replay", path, "--collector", "copying",
                            "--heap-size", "256"])
            assert ret == 0
            assert "Replayed" in buf.getvalue()
        finally:
            os.unlink(path)

    def test_report(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["report", "--heap-size", "256",
                        "--collectors", "mark_sweep", "ref_count",
                        "--scenario", "linked_list",
                        "--scenario-params", '{"n": 5, "obj_size": 8}',
                        "--num-collections", "3"])
        assert ret == 0
        assert "Comparison Report" in buf.getvalue()

    def test_histogram(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["histogram", "--heap-size", "1024",
                        "--collector", "mark_sweep",
                        "--scenario", "churn",
                        "--num-collections", "3"])
        assert ret == 0
        assert "Pause-time histogram" in buf.getvalue()

    def test_histogram_json(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["histogram", "--heap-size", "1024",
                        "--collector", "mark_sweep",
                        "--scenario", "churn",
                        "--num-collections", "2", "--json"])
        assert ret == 0
        data = json.loads(buf.getvalue())
        assert "total" in data

    def test_compare_json_output(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["compare", "--heap-size", "256",
                        "--collectors", "mark_sweep",
                        "--scenario", "linked_list",
                        "--scenario-params", '{"n": 5, "obj_size": 8}',
                        "--json"])
        assert ret == 0
        data = json.loads(buf.getvalue())
        assert isinstance(data, list)
        assert any(d["collector"] == "mark_sweep" for d in data)

    def test_report_json(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["report", "--heap-size", "256",
                        "--collectors", "mark_sweep",
                        "--scenario", "linked_list",
                        "--scenario-params", '{"n": 5, "obj_size": 8}',
                        "--json"])
        assert ret == 0
        data = json.loads(buf.getvalue())
        assert len(data) >= 1

    def test_list_shows_scenarios(self):
        from gc_sim.cli import main
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main(["list"])
        assert ret == 0
        assert "churn" in buf.getvalue()
        assert "cycle_heavy" in buf.getvalue()


# ===========================================================================
# Cross-collector determinism
# ===========================================================================

class TestCrossCollectorDeterminism:
    def test_same_trace_same_allocations(self):
        """Replaying the same trace on different collectors should produce
        the same number of allocations."""
        sim = GCSimulator(heap_size=512, collector="mark_sweep", trace=True)
        sim.scenario_random_graph(n=30, edge_prob=0.1, n_roots=5, seed=42)
        sim.collect()

        counts = {}
        for cname in available_collectors():
            replayer = TraceReplayer(sim.tracer, collector=cname,
                                     heap_size=512)
            s = replayer.replay()
            counts[cname] = s._alloc_count
        # All should have the same allocation count
        assert len(set(counts.values())) == 1, f"Counts differ: {counts}"

    def test_trace_reproducible(self):
        """Running the same scenario with the same seed should produce
        identical traces."""
        sim1 = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim1.scenario_random_graph(n=10, edge_prob=0.2, n_roots=3, seed=99)
        sim1.collect()

        sim2 = GCSimulator(heap_size=256, collector="mark_sweep", trace=True)
        sim2.scenario_random_graph(n=10, edge_prob=0.2, n_roots=3, seed=99)
        sim2.collect()

        e1 = sim1.tracer.export()
        e2 = sim2.tracer.export()
        assert len(e1) == len(e2)
        # Same allocation sizes
        allocs1 = [e["data"]["size"] for e in e1
                    if e["event_type"] == "allocate"]
        allocs2 = [e["data"]["size"] for e in e2
                    if e["event_type"] == "allocate"]
        assert allocs1 == allocs2