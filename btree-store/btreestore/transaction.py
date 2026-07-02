"""
Transaction: snapshot-isolated read/write transaction for btreestore.

Reads resolve against the B+Tree at the transaction's snapshot timestamp.
Writes are buffered in a write set and applied atomically on commit.

Can be used as a context manager:

    with store.transaction() as txn:
        txn.put('k', 'v')
        # auto-commits on success, auto-rolls-back on exception
"""

from __future__ import annotations

import bisect
from collections import OrderedDict
from typing import Dict, Iterator, List, Optional, Tuple, Union, Any, Callable

from .cursor import Cursor
from .pages import _prefix_upper_bound
from .logging_util import get_logger

logger = get_logger()


class Transaction:
    """A snapshot-isolated read/write transaction.

    Reads resolve against the B+Tree at the transaction's snapshot timestamp.
    Writes are buffered in a write set and applied atomically on commit.

    Can be used as a context manager:

        with store.transaction() as txn:
            txn.put('k', 'v')
            # auto-commits on success, auto-rolls-back on exception
    """

    def __init__(self, store: "Store", txn_id: int, read_ts: int,
                 read_only: bool = False):
        self.store = store
        self.txn_id = txn_id
        self.read_ts = read_ts
        self.read_only = read_only
        self._writes: OrderedDict[bytes, Optional[bytes]] = OrderedDict()
        self._write_keys_sorted: Optional[List[bytes]] = None
        self._aborted = False
        self._committed = False

    # --- Context manager protocol ---

    def __enter__(self) -> "Transaction":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if not self._committed and not self._aborted:
            if exc_type is not None:
                self.store.rollback(self)
            else:
                self.store.commit(self)
        return False  # don't suppress exceptions

    def __repr__(self) -> str:
        state = "committed" if self._committed else \
                "aborted" if self._aborted else "active"
        return f"Transaction(id={self.txn_id}, ts={self.read_ts}, {state})"

    # --- Type coercion ---

    def _coerce_key(self, key: Union[str, bytes]) -> bytes:
        if isinstance(key, str):
            return key.encode("utf-8")
        if isinstance(key, bytes):
            return key
        raise TypeError(f"key must be str or bytes, got {type(key).__name__}")

    def _coerce_value(self, value: Union[str, bytes, None]) -> Optional[bytes]:
        if value is None:
            return None
        if isinstance(value, str):
            return value.encode("utf-8")
        if isinstance(value, bytes):
            return value
        raise TypeError(f"value must be str, bytes, or None, got {type(value).__name__}")

    # --- Read operations ---

    def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        """Get the value for key, or None if not present."""
        bkey = self._coerce_key(key)
        if bkey in self._writes:
            return self._writes[bkey]
        return self.store._tree_get(bkey)

    def contains(self, key: Union[str, bytes]) -> bool:
        """Check if key exists in the store (including uncommitted writes)."""
        return self.get(key) is not None

    def __contains__(self, key: Union[str, bytes]) -> bool:
        return self.contains(key)

    def min(self) -> Optional[Tuple[bytes, bytes]]:
        """Return the (key, value) with the smallest key, or None if empty."""
        tree_min = self.store._tree_min()
        write_keys = [k for k, v in self._writes.items() if v is not None]
        write_min = min(write_keys) if write_keys else None

        if tree_min is None and write_min is None:
            return None
        if tree_min is None:
            return (write_min, self._writes[write_min])
        if write_min is None:
            return tree_min
        if write_min < tree_min[0]:
            if tree_min[0] in self._writes and self._writes[tree_min[0]] is None:
                pass
            return (write_min, self._writes[write_min])
        if tree_min[0] in self._writes:
            wv = self._writes[tree_min[0]]
            if wv is None:
                return (write_min, self._writes[write_min]) if write_min else None
            return (tree_min[0], wv)
        return tree_min

    def max(self) -> Optional[Tuple[bytes, bytes]]:
        """Return the (key, value) with the largest key, or None if empty."""
        tree_max = self.store._tree_max()
        write_keys = [k for k, v in self._writes.items() if v is not None]
        write_max = max(write_keys) if write_keys else None

        if tree_max is None and write_max is None:
            return None
        if tree_max is None:
            return (write_max, self._writes[write_max])
        if write_max is None:
            return tree_max
        if write_max > tree_max[0]:
            return (write_max, self._writes[write_max])
        if tree_max[0] in self._writes:
            wv = self._writes[tree_max[0]]
            if wv is None:
                return (write_max, self._writes[write_max]) if write_max else None
            return (tree_max[0], wv)
        return tree_max

    # --- Write operations ---

    def _check_writable(self) -> None:
        """Check that the transaction is writable and active."""
        if self.read_only:
            raise PermissionError("Transaction is read-only")
        if self._aborted:
            raise RuntimeError("Transaction has been aborted")
        if self._committed:
            raise RuntimeError("Transaction has already been committed")

    def put(self, key: Union[str, bytes], value: Union[str, bytes]) -> None:
        """Insert or update a key-value pair."""
        self._check_writable()
        bkey = self._coerce_key(key)
        bval = self._coerce_value(value)
        if bval is None:
            raise ValueError("put() value cannot be None; use delete()")
        if not bkey:
            raise ValueError("key cannot be empty (b'')")
        self._writes[bkey] = bval
        self._write_keys_sorted = None

    def delete(self, key: Union[str, bytes]) -> bool:
        """Delete a key. Returns True if the key existed."""
        self._check_writable()
        bkey = self._coerce_key(key)
        existed = self.get(bkey) is not None
        self._writes[bkey] = None
        self._write_keys_sorted = None
        return existed

    def cas(self, key: Union[str, bytes], expected: Union[str, bytes, None],
            new_value: Union[str, bytes, None]) -> bool:
        """Compare-and-swap: atomically set key to new_value if the current
        value matches expected.

        - If expected is None, the key must not exist (insert-if-absent).
        - If new_value is None, the key is deleted (delete-if-matches).
        - Returns True if the swap succeeded, False otherwise.
        """
        self._check_writable()
        bkey = self._coerce_key(key)
        expected_b = self._coerce_value(expected)
        current = self.get(bkey)
        if current != expected_b:
            return False
        if new_value is None:
            self._writes[bkey] = None
        else:
            self._writes[bkey] = self._coerce_value(new_value)
        self._write_keys_sorted = None
        return True

    def put_many(self, pairs: Dict[Union[str, bytes], Union[str, bytes]]) -> None:
        """Insert or update multiple key-value pairs efficiently."""
        self._check_writable()
        for k, v in pairs.items():
            self.put(k, v)

    def delete_many(self, keys: List[Union[str, bytes]]) -> int:
        """Delete multiple keys. Returns the number of keys that existed."""
        self._check_writable()
        count = 0
        for k in keys:
            if self.delete(k):
                count += 1
        return count

    def increment(self, key: Union[str, bytes], amount: int = 1) -> int:
        """Atomically increment a numeric value.

        The current value is interpreted as a UTF-8 string of an integer.
        If the key doesn't exist, it's treated as 0.
        Returns the new value.
        """
        self._check_writable()
        bkey = self._coerce_key(key)
        current = self.get(bkey)
        if current is None:
            current_val = 0
        else:
            try:
                current_val = int(current.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise ValueError(f"Cannot increment non-integer value: {current!r}")
        new_val = current_val + amount
        self._writes[bkey] = str(new_val).encode("utf-8")
        self._write_keys_sorted = None
        return new_val

    # --- Internal helpers ---

    def _sorted_write_keys(self) -> List[bytes]:
        """Return write keys in sorted order (cached)."""
        if self._write_keys_sorted is None:
            self._write_keys_sorted = sorted(self._writes.keys())
        return self._write_keys_sorted

    # --- Cursor operations ---

    def cursor(self, low: Union[str, bytes, None] = None,
               high: Union[str, bytes, None] = None,
               include_high: bool = False,
               reverse: bool = False,
               limit: Optional[int] = None,
               offset: int = 0) -> Cursor:
        """Create a cursor over the transaction's view.

        Parameters:
            low: lower bound key (inclusive), or None for unbounded
            high: upper bound key (exclusive unless include_high=True)
            include_high: if True, high is inclusive
            reverse: if True, return results in descending key order
            limit: maximum number of entries to return (applied AFTER reverse)
            offset: number of entries to skip (default 0, applied BEFORE reverse)
        """
        low_b = self._coerce_key(low) if low is not None else None
        high_b = self._coerce_key(high) if high is not None else None
        pairs: List[Tuple[bytes, bytes]] = []
        # Collect from tree
        for k, v in self.store._tree_scan(low_b, high_b, include_high):
            # Overlay writes
            if k in self._writes:
                wv = self._writes[k]
                if wv is not None:
                    pairs.append((k, wv))
            else:
                pairs.append((k, v))
        # Collect from writes not in tree range (new inserts not yet committed)
        for wk in self._sorted_write_keys():
            wv = self._writes[wk]
            if wv is None:
                continue  # tombstone
            if low_b is not None and wk < low_b:
                continue
            if high_b is not None:
                if include_high:
                    if wk > high_b:
                        continue
                else:
                    if wk >= high_b:
                        continue
            idx = bisect.bisect_left([p[0] for p in pairs], wk)
            if idx < len(pairs) and pairs[idx][0] == wk:
                continue  # already present (and already overlaid above)
            pairs.append((wk, wv))
        pairs.sort(key=lambda x: x[0])
        # Apply offset BEFORE reverse so it skips from the start
        if offset > 0:
            pairs = pairs[offset:]
        # Apply reverse BEFORE limit so limit takes from the correct end
        if reverse:
            pairs = pairs[::-1]
        # Apply limit AFTER reverse so it takes the first N of the reversed list
        if limit is not None and limit >= 0:
            pairs = pairs[:limit]
        return Cursor(pairs)

    def prefix(self, prefix: Union[str, bytes],
               reverse: bool = False,
               limit: Optional[int] = None,
               offset: int = 0) -> Cursor:
        """Scan all keys with the given byte-level prefix.

        An empty prefix matches all keys.
        """
        prefix_b = self._coerce_key(prefix)
        high = _prefix_upper_bound(prefix_b)
        return self.cursor(low=prefix_b if prefix_b else None, high=high,
                            include_high=False,
                            reverse=reverse, limit=limit, offset=offset)

    def count(self) -> int:
        """Count total keys in the transaction's view (including writes)."""
        tree_count = self.store.count()
        delta = 0
        for k, v in self._writes.items():
            if v is None:
                # Tombstone: if key exists in tree, -1
                if self.store._tree_get(k) is not None:
                    delta -= 1
            else:
                # Insert/update: if key doesn't exist in tree, +1
                if self.store._tree_get(k) is None:
                    delta += 1
        return max(0, tree_count + delta)

    def is_empty(self) -> bool:
        """Return True if the transaction sees no keys."""
        return self.count() == 0

    # --- Export/import ---

    def export_dict(self) -> Dict[str, str]:
        """Export all entries as a {key_str: value_str} dictionary.

        Binary data that cannot be decoded as UTF-8 is hex-encoded.
        """
        result: Dict[str, str] = {}
        for k, v in self.cursor():
            try:
                ks = k.decode("utf-8")
            except UnicodeDecodeError:
                ks = k.hex()
            try:
                vs = v.decode("utf-8")
            except UnicodeDecodeError:
                vs = v.hex()
            result[ks] = vs
        return result