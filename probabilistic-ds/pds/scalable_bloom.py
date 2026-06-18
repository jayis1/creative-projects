"""Scalable Bloom Filter — dynamically growing Bloom filter.

A ScalableBloomFilter starts with an initial capacity and adds
exponentially growing slices when the current slice fills up,
maintaining a compounded false-positive rate across all slices.
"""
import math
from .bloom import BloomFilter
from .hashing import double_hash


class ScalableBloomFilter:
    """A Bloom filter that grows as needed.

    When the current slice reaches capacity, a new slice is allocated
    with ``growth * previous_capacity`` capacity and a tightened error
    rate so the compounded FPR stays below the target.

    Parameters
    ----------
    initial_capacity : int
        Capacity of the first slice.
    error_rate : float
        Target compounded false-positive rate.
    growth : float
        Capacity growth factor per new slice (default 2.0).
    tighten : float
        Error-rate tightening factor per slice (default 0.9).
    """

    def __init__(self, initial_capacity: int = 1000, error_rate: float = 0.01,
                 growth: float = 2.0, tighten: float = 0.9):
        if initial_capacity <= 0:
            raise ValueError("initial_capacity must be positive")
        if not (0 < error_rate < 1):
            raise ValueError("error_rate must be in (0, 1)")
        if growth < 1:
            raise ValueError("growth must be >= 1")

        self.initial_capacity = initial_capacity
        self.target_error = error_rate
        self.growth = growth
        self.tighten = tighten
        self._slices: list[BloomFilter] = []
        self._slice_error = error_rate * (1 - tighten)  # p0 for first slice
        self._add_slice()

    def _add_slice(self) -> None:
        if not self._slices:
            cap = self.initial_capacity
            err = self._slice_error
        else:
            prev = self._slices[-1]
            cap = max(1, int(prev.capacity * self.growth))
            err = prev.error_rate * self.tighten
        self._slices.append(BloomFilter(cap, err))

    def add(self, item) -> None:
        """Add an item, allocating a new slice if the current one is full."""
        current = self._slices[-1]
        if current.count >= current.capacity:
            self._add_slice()
            current = self._slices[-1]
        current.add(item)

    def __contains__(self, item) -> bool:
        return any(item in s for s in self._slices)

    def __len__(self) -> int:
        return sum(s.count for s in self._slices)

    @property
    def num_slices(self) -> int:
        return len(self._slices)

    @property
    def total_bits(self) -> int:
        return sum(s.num_bits for s in self._slices)

    @property
    def compounded_fpr(self) -> float:
        """Compounded false-positive rate across all slices."""
        return 1 - math.prod(1 - s.estimated_false_positive_rate for s in self._slices)