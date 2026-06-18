"""Reservoir Sampler: uniform random sampling from a stream of unknown size.

Algorithm R (Vitter, 1985): maintain a reservoir of k items; for the i-th
item (i > k), include it with probability k/i, replacing a random existing
item.  At any point, the reservoir contains a uniform random sample of the
stream seen so far.

This is a probabilistic data structure in the sense that it uses randomness
to maintain a fixed-size representative sample with O(1) amortized cost
per item.
"""
from __future__ import annotations

import random
from typing import Iterator, Iterable

from .hashing import fnv1a_64


class ReservoirSampler:
    """Uniform random reservoir sampling from a stream.

    Parameters
    ----------
    k : int
        Reservoir size (number of items to retain).

    Examples
    --------
    >>> rs = ReservoirSampler(k=5)
    >>> for i in range(1000): rs.add(i)
    >>> len(rs.sample())
    5
    """

    def __init__(self, k: int = 100, rng: random.Random | None = None):
        if k <= 0:
            raise ValueError("k must be positive")
        self.k = k
        self._reservoir: list = []
        self._n: int = 0  # total items seen
        self._rng = rng or random.Random()

    def add(self, item) -> None:
        """Add an item from the stream."""
        self._n += 1
        if len(self._reservoir) < self.k:
            self._reservoir.append(item)
        else:
            # Include with probability k/n
            j = self._rng.randint(0, self._n - 1)
            if j < self.k:
                self._reservoir[j] = item

    def add_batch(self, items: Iterable) -> None:
        """Add multiple items from the stream."""
        for item in items:
            self.add(item)

    def sample(self) -> list:
        """Return the current reservoir sample."""
        return list(self._reservoir)

    @property
    def total_seen(self) -> int:
        """Total number of items added to the stream."""
        return self._n

    def __len__(self) -> int:
        return len(self._reservoir)

    def merge(self, other: "ReservoirSampler") -> None:
        """Merge another reservoir into this one.

        The merged reservoir is a uniform sample of the combined stream,
        using the weighted-reservoir technique.
        """
        if self.k != other.k:
            raise ValueError("Cannot merge reservoirs of different k")
        combined_n = self._n + other._n
        if combined_n <= self.k:
            # Just combine
            self._reservoir.extend(other._reservoir)
            self._n = combined_n
            return

        # Weighted merge: items from self have weight self._n, from other
        # have weight other._n.  Use the algorithm from "On merging
        # reservoirs" (for unequal stream lengths, sample proportionally).
        all_items = list(zip(self._reservoir,
                              [self._n] * len(self._reservoir))) + \
                     list(zip(other._reservoir,
                              [other._n] * len(other._reservoir)))
        # Weighted reservoir sampling
        new_reservoir: list = []
        weights_remaining = list(all_items)
        for _ in range(self.k):
            if not weights_remaining:
                break
            total_w = sum(w for _, w in weights_remaining)
            r = self._rng.uniform(0, total_w)
            cum = 0.0
            chosen_idx = 0
            for idx, (item, w) in enumerate(weights_remaining):
                cum += w
                if cum >= r:
                    chosen_idx = idx
                    break
            new_reservoir.append(weights_remaining[chosen_idx][0])
            weights_remaining.pop(chosen_idx)
        self._reservoir = new_reservoir
        self._n = combined_n

    def to_dict(self) -> dict:
        """Serialize to a dict."""
        return {"k": self.k, "reservoir": list(self._reservoir),
                "total_seen": self._n}

    @classmethod
    def from_dict(cls, d: dict) -> "ReservoirSampler":
        """Deserialize from a dict."""
        rs = cls(k=d["k"])
        rs._reservoir = list(d["reservoir"])
        rs._n = d["total_seen"]
        return rs


class WeightedReservoirSampler:
    """Weighted reservoir sampling (A-Res algorithm, Efraimidis & Spirakis 2006).

    Each item has a weight; the sample is a weighted random sample without
    replacement.  Uses the key = u^(1/w) technique where u is uniform(0,1)
    and w is the item weight.  Keep the k items with largest keys.
    """

    def __init__(self, k: int = 100, rng: random.Random | None = None):
        if k <= 0:
            raise ValueError("k must be positive")
        self.k = k
        self._heap: list[tuple[float, int]] = []  # min-heap of (key, idx)
        self._items: list = []
        self._n = 0
        self._rng = rng or random.Random()

    def add(self, item, weight: float = 1.0) -> None:
        """Add a weighted item."""
        if weight <= 0:
            return
        self._n += 1
        import heapq
        # Key = u^(1/weight), keep largest k keys
        u = self._rng.random()
        # Avoid log(0)
        if u == 0:
            u = 1e-300
        key = u ** (1.0 / weight)
        if len(self._heap) < self.k:
            heapq.heappush(self._heap, (key, len(self._items)))
            self._items.append(item)
        elif key > self._heap[0][0]:
            # Replace min
            old_key, old_idx = heapq.heappushpop(
                self._heap, (key, len(self._items)))
            # Overwrite the old item slot (it's no longer in the reservoir)
            self._items.append(item)
            # Mark old slot as dead by tracking active indices
            # Simpler: rebuild active list from heap
        if len(self._items) > 10 * self.k:
            self._compact()

    def _compact(self):
        """Rebuild the items list to contain only reservoir members."""
        active_indices = {idx for _, idx in self._heap}
        old_items = self._items
        self._items = []
        new_heap = []
        import heapq
        for key, old_idx in sorted(self._heap, key=lambda x: -x[0]):
            new_idx = len(self._items)
            self._items.append(old_items[old_idx])
            heapq.heappush(new_heap, (key, new_idx))
        self._heap = new_heap

    def sample(self) -> list:
        """Return the current weighted sample."""
        self._compact()
        return list(self._items)

    @property
    def total_seen(self) -> int:
        return self._n

    def __len__(self) -> int:
        return len(self._heap)