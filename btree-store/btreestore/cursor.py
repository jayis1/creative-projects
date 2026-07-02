"""
Cursor: bidirectional iterator over (key, value) pairs.

Created by Transaction.cursor() or Transaction.prefix(). The cursor
materializes results at creation time for snapshot consistency; this
is simple and safe under MVCC, though memory-heavy for huge ranges.

Supports reverse iteration, limit, offset, seek, and projections.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, List, Optional, Tuple

import bisect


class Cursor:
    """Bidirectional cursor over (key, value) pairs.

    Attributes:
        pairs: The materialized list of (key, value) tuples.
        _idx: Current cursor position index.
    """

    __slots__ = ("_pairs", "_idx")

    def __init__(self, pairs: List[Tuple[bytes, bytes]]):
        self._pairs: List[Tuple[bytes, bytes]] = pairs
        self._idx: int = 0

    # --- Iteration protocol ---

    def __iter__(self) -> Iterator[Tuple[bytes, bytes]]:
        """Iterate over all (key, value) pairs."""
        return iter(self._pairs)

    def __len__(self) -> int:
        """Return the number of entries in this cursor."""
        return len(self._pairs)

    def __bool__(self) -> bool:
        """Return True if the cursor has any entries."""
        return len(self._pairs) > 0

    def __repr__(self) -> str:
        return f"Cursor({len(self._pairs)} entries, idx={self._idx})"

    # --- Positioning ---

    def first(self) -> Optional[Tuple[bytes, bytes]]:
        """Move to the first entry and return it."""
        if not self._pairs:
            return None
        self._idx = 0
        return self._pairs[0]

    def last(self) -> Optional[Tuple[bytes, bytes]]:
        """Move to the last entry and return it."""
        if not self._pairs:
            return None
        self._idx = len(self._pairs) - 1
        return self._pairs[-1]

    def next(self) -> Optional[Tuple[bytes, bytes]]:
        """Advance to the next entry (forward). Returns None if past end."""
        self._idx += 1
        if self._idx >= len(self._pairs):
            self._idx = len(self._pairs)
            return None
        return self._pairs[self._idx]

    def prev(self) -> Optional[Tuple[bytes, bytes]]:
        """Move to the previous entry (backward). Returns None if before start."""
        if self._idx <= 0:
            return None
        self._idx -= 1
        return self._pairs[self._idx]

    def seek(self, key: bytes) -> Optional[Tuple[bytes, bytes]]:
        """Seek to the first entry >= key. Returns the entry or None.

        Uses binary search for O(log n) positioning.
        """
        lo, hi = 0, len(self._pairs)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._pairs[mid][0] < key:
                lo = mid + 1
            else:
                hi = mid
        if lo >= len(self._pairs):
            return None
        self._idx = lo
        return self._pairs[lo]

    def seek_exact(self, key: bytes) -> Optional[Tuple[bytes, bytes]]:
        """Seek to the exact key. Returns the entry or None if not found."""
        result = self.seek(key)
        if result is not None and result[0] == key:
            return result
        return None

    # --- Query helpers ---

    def count(self) -> int:
        """Return the number of entries in this cursor."""
        return len(self._pairs)

    def is_empty(self) -> bool:
        """Return True if the cursor has no entries."""
        return len(self._pairs) == 0

    def keys(self) -> List[bytes]:
        """Return all keys as a list."""
        return [k for k, _ in self._pairs]

    def values(self) -> List[bytes]:
        """Return all values as a list."""
        return [v for _, v in self._pairs]

    def items(self) -> List[Tuple[bytes, bytes]]:
        """Return all (key, value) pairs as a list."""
        return list(self._pairs)

    def as_list(self) -> List[Tuple[bytes, bytes]]:
        """Alias for items()."""
        return list(self._pairs)

    def as_dict(self) -> dict:
        """Return entries as a dictionary {key: value}."""
        return {k: v for k, v in self._pairs}

    def apply(self, fn: Callable[[bytes, bytes], Any]) -> List[Any]:
        """Apply a function to each (key, value) pair and return results.

        Useful for projections: ``cursor.apply(lambda k, v: (k, len(v)))``
        """
        return [fn(k, v) for k, v in self._pairs]

    def filter(self, predicate: Callable[[bytes, bytes], bool]) -> "Cursor":
        """Return a new cursor containing only entries matching the predicate.

        Example: ``cursor.filter(lambda k, v: len(v) > 10)``
        """
        filtered = [(k, v) for k, v in self._pairs if predicate(k, v)]
        return Cursor(filtered)

    def map(self, fn: Callable[[bytes, bytes], Tuple[bytes, bytes]]) -> "Cursor":
        """Return a new cursor with a function applied to each entry.

        The function must return a (key, value) tuple.
        """
        mapped = [fn(k, v) for k, v in self._pairs]
        return Cursor(mapped)

    def take(self, n: int) -> "Cursor":
        """Return a new cursor with at most the first n entries."""
        return Cursor(self._pairs[:n])

    def skip(self, n: int) -> "Cursor":
        """Return a new cursor skipping the first n entries."""
        return Cursor(self._pairs[n:])

    def batch(self, size: int) -> List["Cursor"]:
        """Split the cursor into batches of the given size.

        Useful for paginated processing of large result sets.
        """
        if size <= 0:
            raise ValueError("batch size must be positive")
        return [
            Cursor(self._pairs[i:i + size])
            for i in range(0, len(self._pairs), size)
        ]

    def reduce(self, fn: Callable[[Any, bytes, bytes], Any], initial: Any = None) -> Any:
        """Reduce entries to a single value.

        fn(accumulator, key, value) -> new_accumulator
        """
        acc = initial
        for k, v in self._pairs:
            acc = fn(acc, k, v)
        return acc

    def min_key(self) -> Optional[bytes]:
        """Return the smallest key in the cursor, or None if empty."""
        return self._pairs[0][0] if self._pairs else None

    def max_key(self) -> Optional[bytes]:
        """Return the largest key in the cursor, or None if empty."""
        return self._pairs[-1][0] if self._pairs else None

    def sum_values(self) -> int:
        """Sum all values interpreted as integers. Raises if values aren't integer-like."""
        total = 0
        for _, v in self._pairs:
            try:
                total += int(v)
            except (ValueError, TypeError):
                raise ValueError(f"Cannot sum non-integer value: {v!r}")
        return total