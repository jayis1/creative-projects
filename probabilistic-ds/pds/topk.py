"""Top-K heavy-hitter tracking via the Space-Saving algorithm.

Space-Saving maintains exact top-k for frequent items and approximate
counts for all items, using O(k) memory.  Based on Metwally et al. (2005).

Uses a min-heap for O(log k) replacement instead of O(k) linear scan.
"""
import heapq
from .hashing import fnv1a_64


class TopK:
    """Space-Saving heavy-hitter tracker.

    Parameters
    ----------
    k : int
        Number of top elements to track.

    Examples
    --------
    >>> tk = TopK(k=3)
    >>> for _ in range(10): tk.add("a")
    >>> for _ in range(5): tk.add("b")
    >>> tk.topk()[0]
    ('a', 10)
    """

    def __init__(self, k: int = 100):
        if k <= 0:
            raise ValueError("k must be positive")
        self.k = k
        self._counts: dict = {}  # item -> estimated count
        # Min-heap of (count, item) for fast eviction; lazily rebuilt
        self._heap_dirty = True
        self._heap: list = []
        self._capacity = k

    def add(self, item, count: int = 1) -> None:
        """Add an item (with optional count increment)."""
        if count <= 0:
            return
        if item in self._counts:
            self._counts[item] += count
            self._heap_dirty = True
        elif len(self._counts) < self._capacity:
            self._counts[item] = count
            self._heap_dirty = True
        else:
            # Replace the item with minimum count
            self._rebuild_heap()
            min_count, min_item = heapq.heappop(self._heap)
            del self._counts[min_item]
            self._counts[item] = min_count + count
            heapq.heappush(self._heap, (min_count + count, item))

    def _rebuild_heap(self) -> None:
        """Rebuild the min-heap from the counts dict."""
        if not self._heap_dirty:
            return
        self._heap = [(c, i) for i, c in self._counts.items()]
        heapq.heapify(self._heap)
        self._heap_dirty = False

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

    def merge(self, other: "TopK") -> None:
        """Merge another TopK into this one by summing counts."""
        for item, count in other._counts.items():
            if item in self._counts:
                self._counts[item] += count
            elif len(self._counts) < self._capacity:
                self._counts[item] = count
            else:
                # Replace min
                self._rebuild_heap()
                min_count, min_item = heapq.heappop(self._heap)
                del self._counts[min_item]
                self._counts[item] = min_count + count
                heapq.heappush(self._heap, (min_count + count, item))
            self._heap_dirty = True