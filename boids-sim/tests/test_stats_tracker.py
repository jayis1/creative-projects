"""Tests for the StatsTracker."""

import pytest
from boids.stats_tracker import StatsTracker


class TestStatsTrackerBasic:
    def test_empty_tracker(self):
        tracker = StatsTracker()
        assert len(tracker) == 0

    def test_record(self):
        tracker = StatsTracker()
        tracker.record(1, {"alignment": 0.5, "avg_speed": 3.0})
        assert len(tracker) == 1

    def test_record_multiple(self):
        tracker = StatsTracker()
        for i in range(10):
            tracker.record(i, {"alignment": 0.01 * i, "avg_speed": 2.0 + 0.1 * i})
        assert len(tracker) == 10

    def test_invalid_max_history(self):
        with pytest.raises(ValueError):
            StatsTracker(max_history=-1)


class TestStatsTrackerQueries:
    def test_column(self):
        tracker = StatsTracker()
        for i in range(5):
            tracker.record(i, {"alignment": 0.1 * i})
        col = tracker.column("alignment")
        assert len(col) == 5
        assert col[0] == 0.0
        assert abs(col[1] - 0.1) < 1e-10
        assert abs(col[2] - 0.2) < 1e-10
        assert abs(col[3] - 0.3) < 1e-10
        assert abs(col[4] - 0.4) < 1e-10

    def test_column_missing_key(self):
        tracker = StatsTracker()
        tracker.record(1, {"alignment": 0.5})
        tracker.record(2, {"avg_speed": 3.0})
        col = tracker.column("alignment")
        assert col == [0.5]  # only one entry has alignment

    def test_average(self):
        tracker = StatsTracker()
        tracker.record(1, {"val": 10})
        tracker.record(2, {"val": 20})
        tracker.record(3, {"val": 30})
        assert tracker.average("val") == 20.0

    def test_average_empty(self):
        tracker = StatsTracker()
        assert tracker.average("val") is None

    def test_min_max(self):
        tracker = StatsTracker()
        for v in [3, 1, 4, 1, 5, 9, 2, 6]:
            tracker.record(0, {"val": v})
        assert tracker.min_val("val") == 1
        assert tracker.max_val("val") == 9

    def test_min_max_empty(self):
        tracker = StatsTracker()
        assert tracker.min_val("val") is None
        assert tracker.max_val("val") is None

    def test_history(self):
        tracker = StatsTracker()
        tracker.record(1, {"val": 10})
        tracker.record(2, {"val": 20})
        hist = tracker.history()
        assert len(hist) == 2
        assert hist[0]["val"] == 10

    def test_ticks(self):
        tracker = StatsTracker()
        tracker.record(5, {"val": 1})
        tracker.record(10, {"val": 2})
        assert tracker.ticks() == [5, 10]


class TestStatsTrackerAnalysis:
    def test_trend_increasing(self):
        tracker = StatsTracker()
        for i in range(10):
            tracker.record(i, {"val": float(i)})
        trend = tracker.trend("val", window=10)
        assert trend > 0  # increasing

    def test_trend_decreasing(self):
        tracker = StatsTracker()
        for i in range(10):
            tracker.record(i, {"val": float(10 - i)})
        trend = tracker.trend("val", window=10)
        assert trend < 0  # decreasing

    def test_trend_empty(self):
        tracker = StatsTracker()
        assert tracker.trend("val") is None

    def test_trend_single_point(self):
        tracker = StatsTracker()
        tracker.record(1, {"val": 5.0})
        assert tracker.trend("val") is None

    def test_convergence_tick_found(self):
        tracker = StatsTracker()
        # 5 below, then 20 above threshold
        for i in range(5):
            tracker.record(i, {"alignment": 0.1})
        for i in range(5, 25):
            tracker.record(i, {"alignment": 0.9})
        conv = tracker.convergence_tick("alignment", threshold=0.8, window=10)
        assert conv is not None
        assert conv == 5

    def test_convergence_tick_never(self):
        tracker = StatsTracker()
        for i in range(20):
            tracker.record(i, {"alignment": 0.1})
        conv = tracker.convergence_tick("alignment", threshold=0.8, window=5)
        assert conv is None

    def test_summary(self):
        tracker = StatsTracker()
        for i in range(10):
            tracker.record(i, {"alignment": 0.1 * i, "avg_speed": 2.0, "spread": 50.0})
        s = tracker.summary()
        assert "alignment" in s
        assert "avg_speed" in s
        assert "spread" in s
        assert "mean" in s["alignment"]


class TestStatsTrackerRollingWindow:
    def test_max_history_evicts_old(self):
        tracker = StatsTracker(max_history=3)
        tracker.record(1, {"val": 10})
        tracker.record(2, {"val": 20})
        tracker.record(3, {"val": 30})
        tracker.record(4, {"val": 40})
        assert len(tracker) == 3
        vals = tracker.column("val")
        assert vals == [20, 30, 40]  # first entry evicted