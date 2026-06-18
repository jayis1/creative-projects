"""Top-K heavy-hitter tracking via the Space-Saving algorithm.

Space-Saving maintains exact top-k for frequent items and approximate
counts for all items, using O(k) memory.  Based on Metwally et al. (2005).
"""
from .hashing import fnv1a_64


class TopK:
    """Space-Saving heavy-hitter tracker.

    Parameters
    ----------
    k : int
        Number of top elements to track.
    """

    def __init__(self, k: int = 100):
        if k <= 0:
            raise ValueError("k must be positive")
        self.k = k
        self._counts: dict = {}  # item -> estimated count
        self._capacity = k

    def add(self, item, count: int = 1) -> None:
        """Add an item (with optional count increment)."""
        if count <= 0:
            return
        if item in self._counts:
            self._counts[item] += count
        elif len(self._counts) < self._capacity:
            self._counts[item] = count
        else:
            # Replace the item with minimum count
            min_item = min(self._counts, key=self._counts.get)
            min_count = self._counts[min_item]
            del self._counts[min_item]
            self._counts[item] = min_count + count

    def topk(self, n: int | None = None) -> list[tuple]:
        """Return top-n (item, count) pairs sorted by count descending."""
        if n is None:
            n = self.k
        return sorted(self._counts.items(), key=lambda x: -x[1])[:n]

    def query(self, item) -> int | None:
        """Return estimated count for item, or None if not tracked."""
        return self._counts.get(item)

    def __contains__(self, item) -> bool:
        return item in self._counts

    def __len__(self) -> int:
        return len(self._counts)

    @property
    def total_seen(self) -> int:
        """Total number of add() calls (approximate)."""
        return sum(self._counts.values())