"""Key-level TTL (time-to-live) support for the B+ Tree Database.

Each key can optionally carry an expiration timestamp.  Expired entries are
lazily removed on read (or eagerly via ``Database.cleanup_expired()``).
"""

from __future__ import annotations

import time
from typing import Optional, Set


class TTLManager:
    """Track per-key expiration timestamps.

    This is deliberately lightweight — it stores a mapping from key to
    expiration time (Unix epoch seconds).  The manager does **not** start any
    background threads; expired entries are pruned on access or on explicit
    calls to ``cleanup()``.
    """

    def __init__(self):
        self._expirations: dict[str, float] = {}  # key -> epoch_seconds

    # ── public API ────────────────────────────────────────────────

    def set_ttl(self, key: str, ttl_seconds: float) -> None:
        """Schedule *key* for expiration *ttl_seconds* from now.

        Args:
            key: The database key.
            ttl_seconds: Number of seconds until the key expires.  Must be > 0.
        """
        if ttl_seconds <= 0:
            raise ValueError("TTL must be positive")
        self._expirations[key] = time.time() + ttl_seconds

    def set_expiry(self, key: str, expiry_time: float) -> None:
        """Set an absolute expiration epoch for *key*.

        Args:
            key: The database key.
            expiry_time: Unix epoch seconds when the key expires.
        """
        self._expirations[key] = expiry_time

    def remove_ttl(self, key: str) -> None:
        """Remove any TTL associated with *key* (key becomes permanent)."""
        self._expirations.pop(key, None)

    def is_expired(self, key: str) -> bool:
        """Return ``True`` if *key* has expired."""
        expiry = self._expirations.get(key)
        if expiry is None:
            return False
        return time.time() >= expiry

    def get_remaining_ttl(self, key: str) -> Optional[float]:
        """Return the remaining TTL in seconds, or ``None`` if no TTL set.

        Returns 0.0 if the key has already expired.
        """
        expiry = self._expirations.get(key)
        if expiry is None:
            return None
        remaining = expiry - time.time()
        return max(0.0, remaining)

    def get_expiry_time(self, key: str) -> Optional[float]:
        """Return the absolute expiration epoch, or ``None`` if no TTL."""
        return self._expirations.get(key)

    def cleanup(self) -> Set[str]:
        """Remove all expired entries from the TTL registry.

        Returns:
            The set of keys that were expired (callers should delete these
            from the main store as well).
        """
        now = time.time()
        expired = {k for k, exp in self._expirations.items() if now >= exp}
        for k in expired:
            del self._expirations[k]
        return expired

    def all_ttl_keys(self) -> Set[str]:
        """Return all keys that have a TTL set (expired or not)."""
        return set(self._expirations.keys())

    def to_dict(self) -> dict:
        """Serialize state to a plain dict for persistence."""
        return dict(self._expirations)

    @classmethod
    def from_dict(cls, data: dict) -> "TTLManager":
        """Restore state from a dict produced by ``to_dict()``."""
        mgr = cls()
        mgr._expirations = {str(k): float(v) for k, v in data.items()}
        return mgr