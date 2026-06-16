"""LRU read cache for the B+ Tree Database.

Provides a configurable least-recently-used cache layer that sits in front of
the B+ tree for read-heavy workloads.  The cache is **not** write-through —
mutations (put, delete) invalidate the affected cache entries so that
subsequent reads re-fetch from the tree.

Thread-safety is provided by the same RLock that guards the Database.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    """Simple LRU cache backed by an ``OrderedDict``.

    Args:
        max_size: Maximum number of entries.  When ``max_size`` is ``None`` or
            ``<= 0`` the cache is effectively disabled and every
            ``get`` returns the sentinel ``_CACHE_MISS``.
    """

    _CACHE_MISS = object()  # Sentinel: key not in cache

    def __init__(self, max_size: Optional[int] = 256):
        if max_size is not None and max_size <= 0:
            max_size = None  # Disable
        self._max_size = max_size
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._hits = 0
        self._misses = 0

    # ── public API ────────────────────────────────────────────────

    def get(self, key: str) -> Any:
        """Return cached value or ``_CACHE_MISS`` if not found."""
        if self._max_size is None:
            return self._CACHE_MISS
        try:
            value = self._data.pop(key)
            self._data[key] = value  # Move to end (most-recently-used)
            self._hits += 1
            return value
        except KeyError:
            self._misses += 1
            return self._CACHE_MISS

    def put(self, key: str, value: Any) -> None:
        """Insert or update a cached entry."""
        if self._max_size is None:
            return
        if key in self._data:
            self._data.pop(key)
        elif len(self._data) >= self._max_size:
            self._data.popitem(last=False)  # Evict least-recently-used
        self._data[key] = value

    def invalidate(self, key: str) -> None:
        """Remove *key* from the cache (no error if absent)."""
        self._data.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        self._data.clear()
        self._hits = 0
        self._misses = 0

    # ── introspection ─────────────────────────────────────────────

    @property
    def max_size(self) -> Optional[int]:
        return self._max_size

    @property
    def size(self) -> int:
        return len(self._data)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "cache_size": len(self._data),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total else 0.0,
        }