"""LRU encode cache for the BPE tokenizer.

Caching the result of ``encode(text)`` gives a large speed-up on
repetitive inputs (very common in real corpora).  The cache is bounded
by an LRU policy and is thread-safe via a lock.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import List

__all__ = ["EncodeCache"]


class EncodeCache:
    """Thread-safe LRU cache mapping text → token-id list."""

    def __init__(self, capacity: int = 8192):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._capacity = capacity
        self._data: "OrderedDict[str, list[int]]" = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> list[int] | None:
        with self._lock:
            if key in self._data:
                self._hits += 1
                self._data.move_to_end(key)
                return list(self._data[key])
            self._misses += 1
            return None

    def put(self, key: str, value: list[int]) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = list(value)
            self._data.move_to_end(key)
            while len(self._data) > self._capacity:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "size": len(self._data),
                "capacity": self._capacity,
                "hits": self._hits,
                "misses": self._misses,
            }

    @property
    def capacity(self) -> int:
        return self._capacity

    def resize(self, new_capacity: int) -> None:
        if new_capacity < 1:
            raise ValueError("new_capacity must be >= 1")
        with self._lock:
            self._capacity = new_capacity
            while len(self._data) > new_capacity:
                self._data.popitem(last=False)