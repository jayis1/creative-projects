"""Time-series statistics tracking for the boids simulation.

Records simulation statistics at each step and provides query/analysis
methods for understanding how the flock's behavior evolves over time.

Usage::

    tracker = StatsTracker(max_history=1000)
    sim = BoidSimulation(cfg)
    for _ in range(500):
        sim.step()
        tracker.record(sim.tick, sim.stats())
    # Analyze
    history = tracker.history()
    avg_align = tracker.average("alignment")
    trend = tracker.trend("alignment", window=50)
"""

from __future__ import annotations

import math
from collections import deque
from typing import Optional


class StatsTracker:
    """Records time-series statistics from the simulation.

    Keeps a rolling window of stats dicts for analysis. Useful for plotting
    alignment over time, detecting oscillations, or finding the step at which
    the flock converged.

    Args:
        max_history: Maximum number of stat snapshots to retain. Older
            entries are discarded (FIFO). Use 0 for unlimited (memory warning
            for very long runs).
    """

    def __init__(self, max_history: int = 1000):
        if max_history < 0:
            raise ValueError(f"max_history must be non-negative, got {max_history}")
        self._max = max_history if max_history > 0 else None
        self._data: deque[dict] = deque(
            maxlen=self._max if self._max is not None else None
        )
        self._ticks: deque[int] = deque(
            maxlen=self._max if self._max is not None else None
        )

    def record(self, tick: int, stats: dict) -> None:
        """Record a stats snapshot at the given *tick*."""
        self._ticks.append(tick)
        self._data.append(dict(stats))

    def __len__(self) -> int:
        return len(self._data)

    def history(self) -> list[dict]:
        """Return all recorded stats as a list of dicts."""
        return list(self._data)

    def ticks(self) -> list[int]:
        """Return all recorded tick numbers."""
        return list(self._ticks)

    def column(self, key: str) -> list[float]:
        """Extract a single stats key across all recorded snapshots.

        Missing keys are skipped (not included in the result).
        """
        result = []
        for entry in self._data:
            if key in entry:
                result.append(entry[key])
        return result

    def average(self, key: str) -> Optional[float]:
        """Return the mean of *key* across all recorded snapshots.

        Returns None if no snapshots contain the key.
        """
        values = self.column(key)
        if not values:
            return None
        return sum(values) / len(values)

    def min_val(self, key: str) -> Optional[float]:
        """Return the minimum value of *key* across all snapshots."""
        values = self.column(key)
        if not values:
            return None
        return min(values)

    def max_val(self, key: str) -> Optional[float]:
        """Return the maximum value of *key* across all snapshots."""
        values = self.column(key)
        if not values:
            return None
        return max(values)

    def trend(self, key: str, window: int = 10) -> Optional[float]:
        """Compute the recent trend (last *window* values) of *key*.

        Returns the slope of a simple linear regression on the last *window*
        data points. Positive = increasing, negative = decreasing.

        Returns None if fewer than 2 points are available.
        """
        values = self.column(key)
        if len(values) < 2:
            return None
        window = min(window, len(values))
        recent = values[-window:]
        n = len(recent)
        if n < 2:
            return None
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = sum(recent) / n
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, recent))
        denominator = sum((x - x_mean) ** 2 for x in xs)
        if abs(denominator) < 1e-12:
            return 0.0
        return numerator / denominator

    def convergence_tick(self, key: str, threshold: float = 0.8, window: int = 20) -> Optional[int]:
        """Find the tick at which *key* first stays above *threshold*.

        Returns the tick number of the first window-length consecutive run
        where *key* >= threshold, or None if convergence never happened.
        """
        values = self.column(key)
        ticks = list(self._ticks)
        consecutive = 0
        for i, val in enumerate(values):
            if isinstance(val, (int, float)) and val >= threshold:
                consecutive += 1
                if consecutive >= window:
                    start_idx = i - window + 1
                    return ticks[start_idx]
            else:
                consecutive = 0
        return None

    def to_dict(self) -> dict:
        """Serialize the tracker state to a dict."""
        return {
            "max_history": self._max,
            "ticks": list(self._ticks),
            "data": list(self._data),
        }

    def summary(self) -> dict:
        """Return a summary of key statistics across all recorded data."""
        result = {}
        for key in ("alignment", "avg_speed", "spread"):
            avg = self.average(key)
            mn = self.min_val(key)
            mx = self.max_val(key)
            if avg is not None:
                result[key] = {
                    "mean": round(avg, 4),
                    "min": round(mn, 4) if mn is not None else None,
                    "max": round(mx, 4) if mx is not None else None,
                }
        return result