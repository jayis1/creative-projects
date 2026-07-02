"""
TTL (Time-to-Live) key expiration for btreestore.

Provides automatic expiration of keys based on a TTL value. Expired keys
are lazily removed on read or actively purged via a background sweep.

Expiration metadata is stored in a separate in-memory index keyed by
expiry timestamp. On each read, the TTL manager checks if the key has
expired and transparently removes it if so.

Usage:
    from btreestore import Store
    from btreestore.ttl import TTLManager

    with Store("mydb.btree") as store:
        ttl = TTLManager(store)
        ttl.put("session:123", "data", ttl_seconds=3600)  # expires in 1 hour
        ttl.put("perm", "data", ttl_seconds=None)          # no expiration

        # Lazy: expired keys return None on read
        ttl.get("session:123")

        # Active: sweep expired keys
        expired = ttl.sweep_expired()
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Optional, Tuple, List, Union
from .logging_util import get_logger

logger = get_logger()


class TTLManager:
    """Manages TTL-based key expiration for a Store.

    Maintains an in-memory expiry index. Expired keys are detected on
    read (lazy expiration) and can be actively purged with sweep_expired().

    The expiry index is not persisted to disk; on restart, all TTLs are
    lost and keys become permanent. For persistence, use the store's
    own key-value pairs to encode expiry metadata.
    """

    def __init__(self, store):
        """Initialize the TTL manager.

        Args:
            store: A btreestore.Store instance.
        """
        self.store = store
        self._lock = threading.RLock()
        # key (bytes) -> expiry timestamp (float, unix epoch)
        self._expiry: Dict[bytes, float] = {}
        # For efficient sweep: sorted list of (expiry_ts, key)
        # We maintain a simple dict and scan on sweep for simplicity.
        # For large-scale TTL, a min-heap would be better.

    def put(self, key: Union[str, bytes], value: Union[str, bytes],
            ttl_seconds: Optional[float] = None) -> None:
        """Insert a key with an optional TTL.

        Args:
            key: The key to insert.
            value: The value to store.
            ttl_seconds: Time-to-live in seconds. None means no expiration.
        """
        self.store.put(key, value)
        if ttl_seconds is not None:
            bkey = self._coerce_key(key)
            expiry = time.time() + ttl_seconds
            with self._lock:
                self._expiry[bkey] = expiry
            logger.debug(f"TTL set: {bkey!r} expires at {expiry:.3f}")
        else:
            # Ensure no stale TTL
            bkey = self._coerce_key(key)
            with self._lock:
                self._expiry.pop(bkey, None)

    def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        """Get a value, returning None if expired or missing.

        If the key has expired, it is lazily deleted from the store.
        """
        bkey = self._coerce_key(key)
        with self._lock:
            if bkey in self._expiry:
                if time.time() >= self._expiry[bkey]:
                    # Expired — delete and return None
                    del self._expiry[bkey]
                    self.store.delete(bkey)
                    logger.debug(f"TTL expired (lazy): {bkey!r}")
                    return None
        return self.store.get(bkey)

    def ttl(self, key: Union[str, bytes]) -> Optional[float]:
        """Return the remaining TTL in seconds, or None if no TTL set.

        Returns 0.0 if the key has expired but not yet been swept.
        """
        bkey = self._coerce_key(key)
        with self._lock:
            if bkey not in self._expiry:
                return None
            remaining = self._expiry[bkey] - time.time()
            return max(0.0, remaining)

    def expire_at(self, key: Union[str, bytes], expiry_timestamp: float) -> None:
        """Set an absolute expiry timestamp for an existing key."""
        bkey = self._coerce_key(key)
        with self._lock:
            self._expiry[bkey] = expiry_timestamp

    def persist(self, key: Union[str, bytes]) -> bool:
        """Remove the TTL from a key, making it permanent.

        Returns True if the key had a TTL, False otherwise.
        """
        bkey = self._coerce_key(key)
        with self._lock:
            if bkey in self._expiry:
                del self._expiry[bkey]
                return True
            return False

    def sweep_expired(self, max_keys: int = 10000) -> int:
        """Actively delete all expired keys from the store.

        Args:
            max_keys: Maximum number of keys to check per sweep.

        Returns:
            Number of keys deleted.
        """
        now = time.time()
        expired_keys: List[bytes] = []
        with self._lock:
            for bkey, expiry in self._expiry.items():
                if now >= expiry:
                    expired_keys.append(bkey)
                if len(expired_keys) >= max_keys:
                    break

        deleted = 0
        for bkey in expired_keys:
            try:
                with self._lock:
                    del self._expiry[bkey]
                self.store.delete(bkey)
                deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete expired key {bkey!r}: {e}")

        if deleted:
            logger.info(f"TTL sweep: deleted {deleted} expired keys")
        return deleted

    def expired_keys(self) -> List[bytes]:
        """Return a list of keys that have expired but not yet been removed."""
        now = time.time()
        with self._lock:
            return [k for k, exp in self._expiry.items() if now >= exp]

    def all_ttls(self) -> Dict[bytes, float]:
        """Return a copy of the expiry index {key: expiry_timestamp}."""
        with self._lock:
            return dict(self._expiry)

    def count(self) -> int:
        """Return the number of keys with TTLs set."""
        with self._lock:
            return len(self._expiry)

    def _coerce_key(self, key: Union[str, bytes]) -> bytes:
        if isinstance(key, str):
            return key.encode("utf-8")
        if isinstance(key, bytes):
            return key
        raise TypeError(f"key must be str or bytes, got {type(key).__name__}")


class TTLSweeper:
    """Background thread that periodically sweeps expired keys.

    Usage:
        sweeper = TTLSweeper(ttl_manager, interval=60)
        sweeper.start()
        # ... do work ...
        sweeper.stop()
    """

    def __init__(self, ttl_manager: TTLManager, interval: float = 60.0):
        self.ttl_manager = ttl_manager
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the background sweeper thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="ttl-sweeper"
        )
        self._thread.start()
        logger.info(f"TTL sweeper started (interval={self.interval}s)")

    def stop(self) -> None:
        """Stop the background sweeper thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 5)
            self._thread = None
        logger.info("TTL sweeper stopped")

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval):
            try:
                self.ttl_manager.sweep_expired()
            except Exception as e:
                logger.warning(f"TTL sweeper error: {e}")