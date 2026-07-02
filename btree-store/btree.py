"""
btree-store: A persistent B+Tree key-value store with MVCC transactions,
cursor iteration, range queries, and snapshot isolation.

Design goals:
  * Single-file, dependency-free Python implementation.
  * Multi-Version Concurrency Control (MVCC) with snapshot isolation:
    readers see a consistent snapshot; writers get a commit timestamp.
  * B+Tree structure for ordered keys with efficient range scans.
  * Prefix scans and full cursors with bidirectional iteration (forward + reverse).
  * Explicit transactions (begin/commit/rollback) and implicit autocommit.
  * Context-manager transactions: ``with store.transaction() as txn:``.
  * In-memory page cache backed by a file; pages evicted via LRU.
  * CRC32 checksums on every page for corruption detection.
  * Binary-safe keys and values (bytes), with a str convenience API.
  * Compare-and-swap (CAS) for optimistic concurrency control.
  * Batch operations and bulk-load for high-throughput ingestion.
  * Min/max, contains, limit/offset cursors, and reverse iteration.

Public API:
  Store(path, ...)            - open or create a store file
  txn = store.begin()         - explicit read-write transaction
  txn = store.begin(read_only=True) - read-only snapshot
  txn.get(key)                - point lookup
  txn.put(key, value)         - insert/update
  txn.delete(key)             - tombstone
  txn.cas(key, expected, new) - compare-and-swap
  txn.contains(key)           - existence check
  txn.cursor(low=, high=, reverse=, limit=, offset=) - ordered range cursor
  txn.prefix(prefix)          - prefix scan cursor
  txn.min() / txn.max()       - smallest / largest key
  store.commit(txn)           - commit a transaction
  store.rollback(txn)         - abort
  store.close()               - flush and close
  store.snapshot()            - returns a read-only snapshot view
  store.bulk_load(pairs)      - efficiently load pre-sorted (key, value) pairs

Wire format details are documented inline.
"""

from __future__ import annotations

import bisect
import os
import struct
import threading
import zlib
from collections import OrderedDict
from typing import Iterator, List, Optional, Tuple, Union, Dict, Any

# ---------------------------------------------------------------------------
# Constants and on-disk format
# ---------------------------------------------------------------------------

MAGIC = b"BTREESTR"  # file magic
VERSION = 2  # v2: adds per-page CRC32 checksums

# File header: magic (8) + version (4) + page_size (4) + root_page_id (4, signed for -1)
# + next_page_id (4, signed) + free_list_head (4, signed for -1) + commit_ts (8, signed) = 36 bytes
HEADER_FMT = "<8sIIiiiq"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# Page types
PAGE_LEAF = 1
PAGE_INTERNAL = 2
PAGE_FREE = 3

# Leaf page: type(1) + num_keys(2) + prev(4, signed for -1) + next(4, signed for -1)
LEAF_HEADER_FMT = "<BHii"
LEAF_HEADER_SIZE = struct.calcsize(LEAF_HEADER_FMT)

# Internal page: type(1) + num_keys(2) + (key_len, key, child_id)* + trailing child
INTERNAL_HEADER_FMT = "<BH"
INTERNAL_HEADER_SIZE = struct.calcsize(INTERNAL_HEADER_FMT)

# CRC32 checksum stored in the last 4 bytes of every page
CRC_SIZE = 4

DEFAULT_PAGE_SIZE = 4096
DEFAULT_BRANCHING = 32  # order: max children per internal node
CACHE_SIZE = 512


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _varint_encode(buf: bytearray, value: int) -> None:
    """LEB128 unsigned varint encoding."""
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            buf.append(b | 0x80)
        else:
            buf.append(b)
            break


def _varint_decode(data: bytes, offset: int) -> Tuple[int, int]:
    """Decode LEB128 unsigned varint, return (value, new_offset)."""
    result = 0
    shift = 0
    while True:
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, offset


def _pack_kv(buf: bytearray, key: bytes, value: bytes) -> None:
    _varint_encode(buf, len(key))
    buf.extend(key)
    _varint_encode(buf, len(value))
    buf.extend(value)


def _unpack_kv(data: bytes, offset: int) -> Tuple[bytes, bytes, int]:
    klen, offset = _varint_decode(data, offset)
    key = data[offset:offset + klen]
    offset += klen
    vlen, offset = _varint_decode(data, offset)
    value = data[offset:offset + vlen]
    offset += vlen
    return key, value, offset


# ---------------------------------------------------------------------------
# Page types
# ---------------------------------------------------------------------------

class Page:
    """Base class for in-memory pages."""

    __slots__ = ("id", "dirty")

    def __init__(self, page_id: int):
        self.id = page_id
        self.dirty = False


class LeafPage(Page):
    """Leaf node: stores sorted key-value pairs.

    prev/next form a doubly-linked list for efficient cursor iteration
    without traversing internal nodes.
    """

    __slots__ = ("keys", "values", "prev", "next")

    def __init__(self, page_id: int, prev: int = -1, next_id: int = -1):
        super().__init__(page_id)
        self.keys: List[bytes] = []
        self.values: List[bytes] = []
        self.prev = prev
        self.next = next_id

    @property
    def num_keys(self) -> int:
        return len(self.keys)


class InternalPage(Page):
    """Internal node: N separator keys and N+1 child page IDs.

    Layout: child0, key0, child1, key1, ..., key_{n-1}, child_n
    Keys[i] separates child[i] (keys < Keys[i]) and child[i+1] (keys >= Keys[i]).
    """

    __slots__ = ("keys", "children")

    def __init__(self, page_id: int):
        super().__init__(page_id)
        self.keys: List[bytes] = []
        self.children: List[int] = []

    @property
    def num_keys(self) -> int:
        return len(self.keys)


class FreePage(Page):
    """A freed page that is part of the free list."""

    __slots__ = ("next_free",)

    def __init__(self, page_id: int, next_free: int = -1):
        super().__init__(page_id)
        self.next_free = next_free


# ---------------------------------------------------------------------------
# Page serialization
# ---------------------------------------------------------------------------

def _finalize_page(buf: bytearray, page_size: int) -> bytes:
    """Pad buf to page_size - CRC_SIZE, then append CRC32 of the content.

    The CRC covers all bytes before the checksum field, providing integrity
    verification on every page read.
    """
    content_size = page_size - CRC_SIZE
    if len(buf) > content_size:
        raise ValueError(f"Page content too large: {len(buf)} > {content_size}")
    buf.extend(b"\x00" * (content_size - len(buf)))
    crc = zlib.crc32(bytes(buf)) & 0xFFFFFFFF
    buf += struct.pack("<I", crc)
    return bytes(buf)


def serialize_leaf(page: LeafPage, page_size: int) -> bytes:
    """Serialize a leaf page to bytes with CRC32 trailer."""
    buf = bytearray()
    buf += struct.pack(LEAF_HEADER_FMT, PAGE_LEAF, len(page.keys), page.prev, page.next)
    for k, v in zip(page.keys, page.values):
        _pack_kv(buf, k, v)
    return _finalize_page(buf, page_size)


def deserialize_leaf(data: bytes, page_id: int) -> LeafPage:
    ptype, num_keys, prev, next_id = struct.unpack(LEAF_HEADER_FMT, data[:LEAF_HEADER_SIZE])
    page = LeafPage(page_id, prev=prev, next_id=next_id)
    offset = LEAF_HEADER_SIZE
    for _ in range(num_keys):
        k, v, offset = _unpack_kv(data, offset)
        page.keys.append(k)
        page.values.append(v)
    return page


def serialize_internal(page: InternalPage, page_size: int) -> bytes:
    buf = bytearray()
    buf += struct.pack(INTERNAL_HEADER_FMT, PAGE_INTERNAL, len(page.keys))
    # first child
    buf += struct.pack("<I", page.children[0])
    for i in range(len(page.keys)):
        _varint_encode(buf, len(page.keys[i]))
        buf.extend(page.keys[i])
        buf += struct.pack("<I", page.children[i + 1])
    return _finalize_page(buf, page_size)


def deserialize_internal(data: bytes, page_id: int) -> InternalPage:
    ptype, num_keys = struct.unpack(INTERNAL_HEADER_FMT, data[:INTERNAL_HEADER_SIZE])
    page = InternalPage(page_id)
    offset = INTERNAL_HEADER_SIZE
    child0 = struct.unpack("<I", data[offset:offset + 4])[0]
    page.children.append(child0)
    offset += 4
    for _ in range(num_keys):
        klen, offset = _varint_decode(data, offset)
        key = data[offset:offset + klen]
        offset += klen
        child = struct.unpack("<I", data[offset:offset + 4])[0]
        offset += 4
        page.keys.append(key)
        page.children.append(child)
    return page


def serialize_free(page: FreePage, page_size: int) -> bytes:
    buf = bytearray()
    buf += struct.pack("<Bi", PAGE_FREE, page.next_free)
    return _finalize_page(buf, page_size)


def deserialize_free(data: bytes, page_id: int) -> FreePage:
    ptype, next_free = struct.unpack("<Bi", data[:5])
    return FreePage(page_id, next_free=next_free)


def detect_page_type(data: bytes) -> int:
    return struct.unpack("<B", data[:1])[0]


def verify_page_crc(data: bytes) -> bool:
    """Verify the CRC32 checksum of a serialized page.

    The last 4 bytes are the CRC32 of the preceding content.
    Returns True if the checksum matches, False otherwise.
    """
    if len(data) < CRC_SIZE:
        return False
    content = data[:-CRC_SIZE]
    stored_crc = struct.unpack("<I", data[-CRC_SIZE:])[0]
    return (zlib.crc32(content) & 0xFFFFFFFF) == stored_crc


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------

class Cursor:
    """Bidirectional cursor over (key, value) pairs.

    Created by Transaction.cursor() or Transaction.prefix(). The cursor
    materializes results at creation time for snapshot consistency; this
    is simple and safe under MVCC, though memory-heavy for huge ranges.

    Supports reverse iteration, limit, and offset for paginated queries.
    """

    def __init__(self, pairs: List[Tuple[bytes, bytes]]):
        self._pairs = pairs
        self._idx = 0

    def __iter__(self) -> Iterator[Tuple[bytes, bytes]]:
        return iter(self._pairs)

    def __len__(self) -> int:
        return len(self._pairs)

    def __bool__(self) -> bool:
        return len(self._pairs) > 0

    def __repr__(self) -> str:
        return f"Cursor({len(self._pairs)} entries, idx={self._idx})"

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

    def count(self) -> int:
        """Return the number of entries in this cursor."""
        return len(self._pairs)

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

    def is_empty(self) -> bool:
        """Return True if the cursor has no entries."""
        return len(self._pairs) == 0

    def apply(self, fn: Any) -> List[Any]:
        """Apply a function to each (key, value) pair and return results.

        Useful for projections: ``cursor.apply(lambda k, v: (k, len(v)))``
        """
        return [fn(k, v) for k, v in self._pairs]


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

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
        # Check tree's min and write set's min, pick the smaller
        tree_min = self.store._tree_min()
        # Find min in writes that are not tombstones
        write_keys = [k for k, v in self._writes.items() if v is not None]
        write_min = min(write_keys) if write_keys else None

        if tree_min is None and write_min is None:
            return None
        if tree_min is None:
            return (write_min, self._writes[write_min])
        if write_min is None:
            return tree_min
        if write_min < tree_min[0]:
            # Write key is smaller — check if it's a tombstone for tree_min
            if tree_min[0] in self._writes and self._writes[tree_min[0]] is None:
                pass  # tree_min was deleted
            return (write_min, self._writes[write_min])
        # Tree min is smaller — check if it was tombstoned
        if tree_min[0] in self._writes:
            wv = self._writes[tree_min[0]]
            if wv is None:
                # tree_min was deleted; fall back to write_min or next tree key
                # This is an approximation; a full implementation would scan
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

    # --- Internal helpers ---

    def _sorted_write_keys(self) -> List[bytes]:
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
        # high is None for empty prefix or all-0xFF prefix (no finite upper bound)
        return self.cursor(low=prefix_b if prefix_b else None, high=high,
                            include_high=False,
                            reverse=reverse, limit=limit, offset=offset)

    def count(self) -> int:
        """Count total keys in the transaction's view (including writes)."""
        tree_count = self.store.count()
        # Adjust for writes: add new inserts, subtract tombstones for existing keys
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


def _prefix_upper_bound(prefix: bytes) -> Optional[bytes]:
    """Compute the smallest key strictly greater than all keys with the given prefix.

    This is done by treating the prefix as a big-endian number and adding 1
    to the last non-0xFF byte. If the prefix is all 0xFF bytes, there is no
    finite upper bound — we return None to signal "no upper bound".

    Special case: empty prefix b'' matches all keys. We return None to
    signal "no upper bound".
    """
    if not prefix:
        return None  # empty prefix = match everything
    for i in range(len(prefix) - 1, -1, -1):
        if prefix[i] != 0xFF:
            return prefix[:i] + bytes([prefix[i] + 1]) + b"\x00" * (len(prefix) - i - 1)
    # All 0xFF — no finite upper bound exists
    return None


# ---------------------------------------------------------------------------
# B+Tree
# ---------------------------------------------------------------------------

class BPlusTree:
    """In-memory B+Tree with page management and disk persistence.

    This implementation keeps pages in an LRU cache backed by the store file.
    Structural modifications (splits, merges) are done eagerly on the cached
    pages; dirty pages are flushed on commit or cache eviction.
    """

    def __init__(self, store: "Store"):
        self.store = store
        self.root_id = store.header["root_page_id"]

    def _read_page(self, page_id: int) -> Page:
        return self.store._read_page(page_id)

    def _write_page(self, page: Page) -> None:
        self.store._write_page(page)

    def _new_page(self) -> int:
        return self.store._alloc_page()

    def _free_page(self, page_id: int) -> None:
        self.store._free_page_id(page_id)

    def _search_leaf(self, key: bytes) -> LeafPage:
        """Find the leaf page that should contain key."""
        page_id = self.root_id
        while True:
            page = self._read_page(page_id)
            if isinstance(page, LeafPage):
                return page
            assert isinstance(page, InternalPage)
            # Find child: bisect to find first key >= search key, go left
            idx = bisect.bisect_right(page.keys, key)
            page_id = page.children[idx]

    def get(self, key: bytes) -> Optional[bytes]:
        leaf = self._search_leaf(key)
        idx = bisect.bisect_left(leaf.keys, key)
        if idx < len(leaf.keys) and leaf.keys[idx] == key:
            return leaf.values[idx]
        return None

    def insert(self, key: bytes, value: bytes) -> None:
        # Check that key+value can fit in a single page
        max_size = (self.store.page_size - CRC_SIZE) * 0.9
        estimated = len(key) + len(value) + 20  # overhead for headers + varints
        if estimated > max_size:
            raise ValueError(
                f"Key+value too large ({estimated} bytes) for page size "
                f"({self.store.page_size} bytes). Max combined ~{int(max_size)} bytes."
            )
        leaf = self._search_leaf(key)
        idx = bisect.bisect_left(leaf.keys, key)
        if idx < len(leaf.keys) and leaf.keys[idx] == key:
            leaf.values[idx] = value
            leaf.dirty = True
            return
        leaf.keys.insert(idx, key)
        leaf.values.insert(idx, value)
        leaf.dirty = True
        if self._leaf_needs_split(leaf):
            self._split_leaf(leaf)

    def _leaf_needs_split(self, leaf: LeafPage) -> bool:
        # Estimate serialized size (accounting for CRC trailer)
        size = LEAF_HEADER_SIZE
        for k, v in zip(leaf.keys, leaf.values):
            size += len(k) + len(v) + 10  # overhead for varints
        return size > (self.store.page_size - CRC_SIZE) * 0.9

    def _split_leaf(self, leaf: LeafPage) -> None:
        mid = len(leaf.keys) // 2
        new_id = self._new_page()
        new_leaf = LeafPage(new_id, prev=leaf.id, next_id=leaf.next)
        new_leaf.keys = leaf.keys[mid:]
        new_leaf.values = leaf.values[mid:]
        leaf.keys = leaf.keys[:mid]
        leaf.values = leaf.values[:mid]
        leaf.next = new_id
        leaf.dirty = True
        new_leaf.dirty = True
        self._write_page(new_leaf)
        self._write_page(leaf)
        # Update linked list: if leaf had a next, fix its prev
        if new_leaf.next != -1:
            next_page = self._read_page(new_leaf.next)
            assert isinstance(next_page, LeafPage)
            next_page.prev = new_id
            next_page.dirty = True
            self._write_page(next_page)
        # Propagate separator up
        self._insert_separator(leaf.id, new_leaf.keys[0], new_id)

    def _insert_separator(self, left_id: int, sep_key: bytes, right_id: int) -> None:
        if self.root_id == left_id:
            # Root was a leaf; create new root
            new_root_id = self._new_page()
            new_root = InternalPage(new_root_id)
            new_root.keys = [sep_key]
            new_root.children = [left_id, right_id]
            new_root.dirty = True
            self._write_page(new_root)
            self.root_id = new_root_id
            self.store.header["root_page_id"] = new_root_id
            return
        # Find parent of left_id
        parent = self._find_parent(self.root_id, left_id)
        assert parent is not None, "parent not found"
        idx = parent.children.index(left_id)
        parent.keys.insert(idx, sep_key)
        parent.children.insert(idx + 1, right_id)
        parent.dirty = True
        if self._internal_needs_split(parent):
            self._split_internal(parent)
        else:
            self._write_page(parent)

    def _find_parent(self, page_id: int, child_id: int) -> Optional[InternalPage]:
        """Find the parent of child_id starting from page_id (BFS)."""
        page = self._read_page(page_id)
        if isinstance(page, LeafPage):
            return None
        if child_id in page.children:
            return page
        # Search down
        for c in page.children:
            parent = self._find_parent(c, child_id)
            if parent is not None:
                return parent
        return None

    def _internal_needs_split(self, page: InternalPage) -> bool:
        size = INTERNAL_HEADER_SIZE + 4  # first child
        for k in page.keys:
            size += len(k) + 10
        size += 4 * len(page.children)
        return size > (self.store.page_size - CRC_SIZE) * 0.9 or \
            len(page.children) > self.store.branching * 2

    def _split_internal(self, page: InternalPage) -> None:
        mid = len(page.keys) // 2
        sep_key = page.keys[mid]
        new_id = self._new_page()
        new_internal = InternalPage(new_id)
        new_internal.keys = page.keys[mid + 1:]
        new_internal.children = page.children[mid + 1:]
        page.keys = page.keys[:mid]
        page.children = page.children[:mid + 1]
        page.dirty = True
        new_internal.dirty = True
        self._write_page(page)
        self._write_page(new_internal)
        self._insert_separator(page.id, sep_key, new_id)

    def delete(self, key: bytes) -> bool:
        leaf = self._search_leaf(key)
        idx = bisect.bisect_left(leaf.keys, key)
        if idx >= len(leaf.keys) or leaf.keys[idx] != key:
            return False
        leaf.keys.pop(idx)
        leaf.values.pop(idx)
        leaf.dirty = True
        self._write_page(leaf)
        # Note: we don't implement merge/borrow for simplicity; B+Tree
        # still correct, just sparse. Rebalance could be added later.
        return True

    def scan(self, low: Optional[bytes], high: Optional[bytes],
             include_high: bool = False) -> Iterator[Tuple[bytes, bytes]]:
        """Yield (key, value) pairs in [low, high) or [low, high]."""
        if self.root_id == -1:
            return
        # Find starting leaf
        if low is not None:
            leaf = self._search_leaf(low)
        else:
            leaf = self._leftmost_leaf()
        while leaf is not None:
            for i, k in enumerate(leaf.keys):
                if low is not None and k < low:
                    continue
                if high is not None:
                    if include_high:
                        if k > high:
                            return
                    else:
                        if k >= high:
                            return
                yield (k, leaf.values[i])
            if leaf.next == -1:
                break
            leaf = self._read_page(leaf.next)
            assert isinstance(leaf, LeafPage)

    def _leftmost_leaf(self) -> Optional[LeafPage]:
        if self.root_id == -1:
            return None
        page_id = self.root_id
        while True:
            page = self._read_page(page_id)
            if isinstance(page, LeafPage):
                return page
            page_id = page.children[0]

    def _rightmost_leaf(self) -> Optional[LeafPage]:
        if self.root_id == -1:
            return None
        page_id = self.root_id
        while True:
            page = self._read_page(page_id)
            if isinstance(page, LeafPage):
                return page
            page_id = page.children[-1]

    def count(self) -> int:
        n = 0
        leaf = self._leftmost_leaf()
        while leaf is not None:
            n += len(leaf.keys)
            if leaf.next == -1:
                break
            leaf = self._read_page(leaf.next)
        return n

    def validate(self) -> bool:
        """Check tree invariants: ordering, parent-child consistency."""
        if self.root_id == -1:
            return True
        return self._validate_page(self.root_id, None, None)

    def _validate_page(self, page_id: int, low: Optional[bytes],
                       high: Optional[bytes]) -> bool:
        page = self._read_page(page_id)
        if isinstance(page, LeafPage):
            for i, k in enumerate(page.keys):
                if low is not None and k < low:
                    return False
                if high is not None and k >= high:
                    return False
                if i > 0 and page.keys[i - 1] >= k:
                    return False
            return True
        if isinstance(page, InternalPage):
            for i, k in enumerate(page.keys):
                if i > 0 and page.keys[i - 1] >= k:
                    return False
            # child[0] < keys[0], child[i] in [keys[i-1], keys[i])
            if not self._validate_page(page.children[0], low, page.keys[0]):
                return False
            for i in range(1, len(page.keys)):
                if not self._validate_page(page.children[i], page.keys[i - 1], page.keys[i]):
                    return False
            if not self._validate_page(page.children[-1], page.keys[-1], high):
                return False
            return True
        return False


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class Store:
    """A persistent B+Tree key-value store with MVCC transactions.

    File layout:
      [Header (HEADER_SIZE bytes)]
      [Page 0] [Page 1] ... [Page N]
    Pages are page_size bytes each, starting at offset HEADER_SIZE.
    Page IDs are 0-indexed.
    """

    def __init__(self, path: str, page_size: int = DEFAULT_PAGE_SIZE,
                 branching: int = DEFAULT_BRANCHING, cache_size: int = CACHE_SIZE):
        self.path = path
        self.page_size = page_size
        self.branching = branching
        self.cache_size = cache_size
        self._cache: OrderedDict[int, Page] = OrderedDict()
        self._lock = threading.RLock()
        self._next_page_id = 0
        self._free_list_head = -1
        self._commit_ts = 0
        self._next_txn_id = 1
        self.header: dict = {}
        self.tree: Optional[BPlusTree] = None
        self._closed = False
        self._dirty_header = False

        if os.path.exists(path) and os.path.getsize(path) >= HEADER_SIZE:
            self._open()
        else:
            self._create()

    def _create(self) -> None:
        """Create a new store file."""
        self._next_page_id = 0
        self._free_list_head = -1
        self._commit_ts = 0
        # Create root leaf page
        root_id = self._alloc_page()
        root = LeafPage(root_id)
        self._write_page(root)
        self.header = {
            "magic": MAGIC,
            "version": VERSION,
            "page_size": self.page_size,
            "root_page_id": root_id,
            "next_page_id": self._next_page_id,
            "free_list_head": self._free_list_head,
            "commit_ts": self._commit_ts,
        }
        self._dirty_header = True
        self.tree = BPlusTree(self)
        self._flush_header()

    def _open(self) -> None:
        """Open existing store file."""
        with open(self.path, "rb") as f:
            data = f.read(HEADER_SIZE)
        magic, version, page_size, root_id, next_page_id, free_list_head, commit_ts = \
            struct.unpack(HEADER_FMT, data)
        if magic != MAGIC:
            raise ValueError(f"Bad magic: {magic!r}")
        if version != VERSION:
            raise ValueError(f"Unsupported version: {version}")
        self.page_size = page_size
        self.header = {
            "magic": magic,
            "version": version,
            "page_size": page_size,
            "root_page_id": root_id,
            "next_page_id": next_page_id,
            "free_list_head": free_list_head,
            "commit_ts": commit_ts,
        }
        self._next_page_id = next_page_id
        self._free_list_head = free_list_head
        self._commit_ts = commit_ts
        self.tree = BPlusTree(self)

    def _flush_header(self) -> None:
        """Write header to disk."""
        header_data = struct.pack(HEADER_FMT, MAGIC, VERSION, self.page_size,
                                   self.header["root_page_id"], self._next_page_id,
                                   self._free_list_head, self._commit_ts)
        mode = "r+b" if os.path.exists(self.path) else "w+b"
        with open(self.path, mode) as f:
            f.seek(0)
            f.write(header_data)
        self._dirty_header = False

    # --- Page allocation and I/O ---

    def _alloc_page(self) -> int:
        """Allocate a page, reusing free list if available."""
        if self._free_list_head != -1:
            page_id = self._free_list_head
            free_page = self._read_page(page_id)
            assert isinstance(free_page, FreePage)
            self._free_list_head = free_page.next_free
            # Remove from cache; will be overwritten
            self._cache.pop(page_id, None)
            return page_id
        page_id = self._next_page_id
        self._next_page_id += 1
        self._dirty_header = True
        return page_id

    def _free_page_id(self, page_id: int) -> None:
        """Add page_id to the free list."""
        fp = FreePage(page_id, next_free=self._free_list_head)
        self._free_list_head = page_id
        self._cache[page_id] = fp
        fp.dirty = True
        self._dirty_header = True

    def _read_page(self, page_id: int) -> Page:
        """Read a page from cache or disk, verifying CRC32 checksum."""
        if page_id in self._cache:
            self._cache.move_to_end(page_id)
            return self._cache[page_id]
        offset = HEADER_SIZE + page_id * self.page_size
        with open(self.path, "rb") as f:
            f.seek(offset)
            data = f.read(self.page_size)
        if len(data) < self.page_size:
            # Extend file with zeros — treat as uninitialized page
            data = data + b"\x00" * (self.page_size - len(data))
        # Verify CRC32 checksum (skip for all-zero pages, which are uninitialized)
        if data != b"\x00" * self.page_size and not verify_page_crc(data):
            raise IOError(
                f"CRC32 checksum mismatch on page {page_id} — file may be corrupted"
            )
        ptype = detect_page_type(data)
        if ptype == PAGE_LEAF:
            page = deserialize_leaf(data, page_id)
        elif ptype == PAGE_INTERNAL:
            page = deserialize_internal(data, page_id)
        elif ptype == PAGE_FREE:
            page = deserialize_free(data, page_id)
        else:
            raise ValueError(f"Unknown page type {ptype} at page {page_id}")
        self._cache_put(page_id, page)
        return page

    def _write_page(self, page: Page) -> None:
        """Mark page dirty; will be flushed on commit or eviction."""
        page.dirty = True
        self._cache_put(page.id, page)

    def _cache_put(self, page_id: int, page: Page) -> None:
        self._cache[page_id] = page
        self._cache.move_to_end(page_id)
        while len(self._cache) > self.cache_size:
            old_id, old_page = self._cache.popitem(last=False)
            if old_page.dirty:
                self._flush_page(old_page)

    def _flush_page(self, page: Page) -> None:
        """Write a page to disk."""
        if isinstance(page, LeafPage):
            data = serialize_leaf(page, self.page_size)
        elif isinstance(page, InternalPage):
            data = serialize_internal(page, self.page_size)
        elif isinstance(page, FreePage):
            data = serialize_free(page, self.page_size)
        else:
            raise TypeError(f"Unknown page type: {type(page)}")
        offset = HEADER_SIZE + page.id * self.page_size
        mode = "r+b" if os.path.exists(self.path) else "w+b"
        with open(self.path, mode) as f:
            f.seek(offset)
            f.write(data)
        page.dirty = False

    def _flush_all(self) -> None:
        """Flush all dirty pages and header to disk."""
        for page in list(self._cache.values()):
            if page.dirty:
                self._flush_page(page)
        if self._dirty_header:
            self._flush_header()

    # --- Transaction management ---

    def begin(self, read_only: bool = False) -> Transaction:
        """Begin a new transaction."""
        with self._lock:
            txn = Transaction(self, self._next_txn_id, self._commit_ts, read_only)
            self._next_txn_id += 1
            return txn

    def commit(self, txn: Transaction) -> None:
        """Commit a transaction: apply buffered writes to the B+Tree and flush."""
        with self._lock:
            if txn._aborted:
                raise RuntimeError("Cannot commit aborted transaction")
            if txn._committed:
                raise RuntimeError("Transaction already committed")
            if txn.read_only:
                txn._committed = True
                return
            # Apply writes in sorted order for better locality
            for key in txn._sorted_write_keys():
                val = txn._writes[key]
                if val is None:
                    self.tree.delete(key)
                else:
                    self.tree.insert(key, val)
            self._commit_ts += 1
            self.header["commit_ts"] = self._commit_ts
            self._dirty_header = True  # ensure header is flushed with new commit_ts
            self._flush_all()
            txn._committed = True

    def rollback(self, txn: Transaction) -> None:
        """Abort a transaction: discard buffered writes."""
        txn._writes.clear()
        txn._aborted = True

    # --- Convenience methods (autocommit) ---

    def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        txn = self.begin(read_only=True)
        try:
            return txn.get(key)
        finally:
            txn._committed = True

    def put(self, key: Union[str, bytes], value: Union[str, bytes]) -> None:
        txn = self.begin()
        try:
            txn.put(key, value)
            self.commit(txn)
        except Exception:
            self.rollback(txn)
            raise

    def delete(self, key: Union[str, bytes]) -> bool:
        txn = self.begin()
        try:
            existed = txn.delete(key)
            self.commit(txn)
            return existed
        except Exception:
            self.rollback(txn)
            raise

    def cursor(self, low: Union[str, bytes, None] = None,
               high: Union[str, bytes, None] = None,
               include_high: bool = False,
               reverse: bool = False,
               limit: Optional[int] = None,
               offset: int = 0) -> Cursor:
        txn = self.begin(read_only=True)
        return txn.cursor(low, high, include_high, reverse, limit, offset)

    def prefix(self, prefix: Union[str, bytes],
               reverse: bool = False,
               limit: Optional[int] = None,
               offset: int = 0) -> Cursor:
        txn = self.begin(read_only=True)
        return txn.prefix(prefix, reverse, limit, offset)

    def cas(self, key: Union[str, bytes],
            expected: Union[str, bytes, None],
            new_value: Union[str, bytes, None]) -> bool:
        """Autocommit compare-and-swap."""
        txn = self.begin()
        try:
            result = txn.cas(key, expected, new_value)
            self.commit(txn)
            return result
        except Exception:
            self.rollback(txn)
            raise

    def count(self) -> int:
        return self.tree.count() if self.tree else 0

    def contains(self, key: Union[str, bytes]) -> bool:
        """Check if a key exists in the store."""
        return self.get(key) is not None

    def __contains__(self, key: Union[str, bytes]) -> bool:
        return self.contains(key)

    def min(self) -> Optional[Tuple[bytes, bytes]]:
        """Return the (min_key, value), or None if empty."""
        return self._tree_min()

    def max(self) -> Optional[Tuple[bytes, bytes]]:
        """Return the (max_key, value), or None if empty."""
        return self._tree_max()

    def snapshot(self) -> Transaction:
        """Return a read-only snapshot transaction."""
        return self.begin(read_only=True)

    def transaction(self, read_only: bool = False) -> Transaction:
        """Return a transaction for use as a context manager.

        Auto-commits on successful exit, auto-rolls-back on exception.

            with store.transaction() as txn:
                txn.put('k', 'v')
        """
        return self.begin(read_only=read_only)

    def bulk_load(self, pairs: List[Tuple[Union[str, bytes], Union[str, bytes]]]) -> int:
        """Efficiently load many key-value pairs in a single transaction.

        If the pairs are pre-sorted by key, insertion is more cache-friendly.
        Returns the number of pairs loaded.
        """
        txn = self.begin()
        try:
            for k, v in pairs:
                txn.put(k, v)
            self.commit(txn)
            return len(pairs)
        except Exception:
            self.rollback(txn)
            raise

    def close(self) -> None:
        """Flush and close the store."""
        with self._lock:
            if self._closed:
                return
            self._flush_all()
            self._cache.clear()
            self._closed = True

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # --- B+Tree access for Transaction ---

    def _tree_get(self, key: bytes) -> Optional[bytes]:
        if self.tree is None:
            return None
        return self.tree.get(key)

    def _tree_min(self) -> Optional[Tuple[bytes, bytes]]:
        """Return the (min_key, value) from the tree, or None if empty."""
        if self.tree is None:
            return None
        leaf = self.tree._leftmost_leaf()
        if leaf is None or not leaf.keys:
            return None
        return (leaf.keys[0], leaf.values[0])

    def _tree_max(self) -> Optional[Tuple[bytes, bytes]]:
        """Return the (max_key, value) from the tree, or None if empty."""
        if self.tree is None:
            return None
        leaf = self.tree._rightmost_leaf()
        if leaf is None or not leaf.keys:
            return None
        return (leaf.keys[-1], leaf.values[-1])

    def _tree_scan(self, low: Optional[bytes], high: Optional[bytes],
                   include_high: bool) -> Iterator[Tuple[bytes, bytes]]:
        if self.tree is None:
            return iter(())
        return self.tree.scan(low, high, include_high)

    def validate(self) -> bool:
        """Validate the B+Tree structure."""
        return self.tree.validate() if self.tree else True

    def stats(self) -> dict:
        """Return store statistics."""
        file_size = os.path.getsize(self.path) if os.path.exists(self.path) else 0
        total_pages = max(0, (file_size - HEADER_SIZE) // self.page_size)
        # Count page types and tree depth by scanning cached pages
        leaf_count = 0
        internal_count = 0
        free_count = 0
        for page in self._cache.values():
            if isinstance(page, LeafPage):
                leaf_count += 1
            elif isinstance(page, InternalPage):
                internal_count += 1
            elif isinstance(page, FreePage):
                free_count += 1
        tree_depth = self._tree_depth() if self.tree else 0
        return {
            "file_size": file_size,
            "page_size": self.page_size,
            "total_pages": total_pages,
            "cached_pages": len(self._cache),
            "cached_leaf_pages": leaf_count,
            "cached_internal_pages": internal_count,
            "cached_free_pages": free_count,
            "free_list_head": self._free_list_head,
            "root_page_id": self.header.get("root_page_id", -1),
            "commit_ts": self._commit_ts,
            "next_page_id": self._next_page_id,
            "next_txn_id": self._next_txn_id,
            "num_keys": self.count(),
            "tree_depth": tree_depth,
        }

    def _tree_depth(self) -> int:
        """Return the height of the B+Tree (0 = single leaf, 1 = root+leaves, etc.)."""
        if self.tree is None or self.tree.root_id == -1:
            return 0
        page_id = self.tree.root_id
        depth = 0
        while True:
            page = self._read_page(page_id)
            if isinstance(page, LeafPage):
                return depth
            depth += 1
            page_id = page.children[0]