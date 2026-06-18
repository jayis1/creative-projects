"""K-Minimum Values (KMV): approximate cardinality estimation.

KMV (also called KVM or bottom-k) is a simple, elegant cardinality estimator:
keep the k smallest distinct hash values seen; the cardinality estimate is
(k - 1) / (max_stored_hash / hash_space).

It's the predecessor to HyperLogLog and is simpler to understand, though
slightly less memory-efficient.  KMV is mergeable (union via merging the k
smallest from both sketches).

Memory: O(k) integers (typically k = 1024 to 4096).
Error: ≈ 1/√(k-2).
"""
from __future__ import annotations

import math
from typing import Iterable

from .hashing import fnv1a_64


class KMV:
    """K-Minimum Values cardinality estimator.

    Parameters
    ----------
    k : int
        Number of minimum hash values to retain.  Higher → lower error.
        Standard error ≈ 1/√(k - 2).  Default 1024.

    Examples
    --------
    >>> kmv = KMV(k=512)
    >>> for i in range(10000): kmv.add(str(i))
    >>> abs(kmv.estimate() - 10000) / 10000 < 0.1
    True
    """

    MAX_HASH = (1 << 64) - 1

    def __init__(self, k: int = 1024):
        if k < 10:
            raise ValueError("k must be >= 10")
        self.k = k
        self._values: set[int] = set()
        self._max_in_set: int = 0  # current max of the k smallest
        self._has_max = False

    @staticmethod
    def _serialize(item) -> bytes:
        if isinstance(item, bytes):
            return item
        if isinstance(item, str):
            return item.encode("utf-8")
        return repr(item).encode("utf-8")

    def add(self, item) -> None:
        """Add an item."""
        data = self._serialize(item)
        # Use MD5 for uniform distribution (FNV-1a doesn't cover the full
        # 64-bit hash space uniformly for short inputs, biasing the estimate)
        from .hashing import md5_128
        h = md5_128(data) & self.MAX_HASH  # use lower 64 bits
        if h in self._values:
            return
        if len(self._values) < self.k:
            self._values.add(h)
            if not self._has_max or h > self._max_in_set:
                self._max_in_set = h
                self._has_max = True
        elif h < self._max_in_set:
            # Replace the max
            self._values.discard(self._max_in_set)
            self._values.add(h)
            self._max_in_set = max(self._values)

    def add_batch(self, items: Iterable) -> None:
        """Add multiple items."""
        for item in items:
            self.add(item)

    def estimate(self) -> float:
        """Estimate the number of distinct elements seen."""
        if len(self._values) < self.k:
            # Not yet full — exact count
            return float(len(self._values))
        if self._max_in_set == 0:
            return float("inf")
        # E[n] = (k - 1) / (max / hash_space)
        return (self.k - 1) / (self._max_in_set / self.MAX_HASH)

    def merge(self, other: "KMV") -> None:
        """Merge another KMV (set union)."""
        if self.k != other.k:
            raise ValueError("Cannot merge KMVs with different k")
        combined = self._values | other._values
        if len(combined) <= self.k:
            self._values = combined
        else:
            # Keep the k smallest
            sorted_vals = sorted(combined)
            self._values = set(sorted_vals[:self.k])
        if self._values:
            self._max_in_set = max(self._values)
            self._has_max = True

    @property
    def relative_error(self) -> float:
        """Theoretical standard error."""
        if self.k <= 2:
            return float("inf")
        return 1.0 / math.sqrt(self.k - 2)

    def __len__(self) -> int:
        """Number of stored hash values."""
        return len(self._values)

    def to_dict(self) -> dict:
        """Serialize to a dict."""
        return {"k": self.k, "values": list(self._values)}

    @classmethod
    def from_dict(cls, d: dict) -> "KMV":
        """Deserialize from a dict."""
        kmv = cls(k=d["k"])
        kmv._values = set(d["values"])
        if kmv._values:
            kmv._max_in_set = max(kmv._values)
            kmv._has_max = True
        return kmv