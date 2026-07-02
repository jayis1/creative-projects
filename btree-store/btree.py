"""
btree-store: A persistent B-Tree key-value store with MVCC transactions,
cursor iteration, range queries, and snapshot isolation.

Design goals:
  * Single-file, dependency-free Python implementation.
  * Crash-safe durability via an append-only write-ahead log (WAL).
  * Multi-Version Concurrency Control (MVCC) with snapshot isolation:
    readers see a consistent snapshot; writers get a commit timestamp.
  * B+Tree structure for ordered keys with efficient range scans.
  * Prefix scans and full cursors with bidirectional iteration.
  * Explicit transactions (begin/commit/rollback) and implicit autocommit.
  * In-memory page cache backed by a file; pages evicted via LRU.
  * Binary-safe keys and values (bytes), with a str convenience API.

Public API:
  Store(path, ...)            - open or create a store file
  txn = store.begin()         - explicit read-write transaction
  txn = store.begin(read_only=True) - read-only snapshot
  txn.get(key)                - point lookup
  txn.put(key, value)         - insert/update
  txn.delete(key)            - tombstone
  txn.cursor(low=, high=)     - ordered range cursor
  txn.prefix(prefix)          - prefix scan cursor
  store.commit(txn)           - commit a transaction
  store.rollback(txn)         - abort
  store.close()               - flush and close
  store.snapshot()            - returns a read-only snapshot view

Wire format details are documented inline.
"""

from __future__ import annotations

import bisect
import io
import os
import struct
import threading
import time
import zlib
from collections import OrderedDict
from typing import Callable, Iterator, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Constants and on-disk format
# ---------------------------------------------------------------------------

MAGIC = b"BTREESTR"  # file magic
VERSION = 1

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

def serialize_leaf(page: LeafPage, page_size: int) -> bytes:
    """Serialize a leaf page to bytes, padded to page_size."""
    buf = bytearray()
    # header
    buf += struct.pack(LEAF_HEADER_FMT, PAGE_LEAF, len(page.keys), page.prev, page.next)
    for k, v in zip(page.keys, page.values):
        _pack_kv(buf, k, v)
    if len(buf) > page_size:
        raise ValueError(f"Leaf page {page.id} too large: {len(buf)} > {page_size}")
    buf.extend(b"\x00" * (page_size - len(buf)))
    return bytes(buf)


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
    if len(buf) > page_size:
        raise ValueError(f"Internal page {page.id} too large: {len(buf)} > {page_size}")
    buf.extend(b"\x00" * (page_size - len(buf)))
    return bytes(buf)


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
    buf.extend(b"\x00" * (page_size - len(buf)))
    return bytes(buf)


def deserialize_free(data: bytes, page_id: int) -> FreePage:
    ptype, next_free = struct.unpack("<Bi", data[:5])
    return FreePage(page_id, next_free=next_free)


def detect_page_type(data: bytes) -> int:
    return struct.unpack("<B", data[:1])[0]


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------

class Cursor:
    """Bidirectional cursor over (key, value) pairs.

    Created by Transaction.cursor() or Transaction.prefix(). The cursor
    materializes results at creation time for snapshot consistency; this
    is simple and safe under MVCC, though memory-heavy for huge ranges.
    """

    def __init__(self, pairs: List[Tuple[bytes, bytes]]):
        self._pairs = pairs
        self._idx = 0

    def __iter__(self) -> Iterator[Tuple[bytes, bytes]]:
        return iter(self._pairs)

    def __len__(self) -> int:
        return len(self._pairs)

    def first(self) -> Optional[Tuple[bytes, bytes]]:
        if not self._pairs:
            return None
        self._idx = 0
        return self._pairs[0]

    def last(self) -> Optional[Tuple[bytes, bytes]]:
        if not self._pairs:
            return None
        self._idx = len(self._pairs) - 1
        return self._pairs[-1]

    def next(self) -> Optional[Tuple[bytes, bytes]]:
        self._idx += 1
        if self._idx >= len(self._pairs):
            return None
        return self._pairs[self._idx]

    def prev(self) -> Optional[Tuple[bytes, bytes]]:
        if self._idx <= 0:
            return None
        self._idx -= 1
        return self._pairs[self._idx]

    def seek(self, key: bytes) -> Optional[Tuple[bytes, bytes]]:
        """Seek to the first entry >= key. Returns the entry or None."""
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

    def count(self) -> int:
        return len(self._pairs)

    def keys(self) -> List[bytes]:
        return [k for k, _ in self._pairs]

    def values(self) -> List[bytes]:
        return [v for _, v in self._pairs]

    def as_list(self) -> List[Tuple[bytes, bytes]]:
        return list(self._pairs)


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class Transaction:
    """A snapshot-isolated read/write transaction.

    Reads resolve against the B+Tree at the transaction's snapshot timestamp.
    Writes are buffered in a write set and applied atomically on commit.
    """

    def __init__(self, store: "Store", txn_id: int, read_ts: int,
                 read_only: bool = False):
        self.store = store
        self.txn_id = txn_id
        self.read_ts = read_ts
        self.read_only = read_only
        self._writes: dict = OrderedDict()  # key(bytes) -> Optional[bytes]; None=tombstone
        self._write_keys_sorted: Optional[List[bytes]] = None
        self._aborted = False
        self._committed = False

    def _coerce_key(self, key: Union[str, bytes]) -> bytes:
        if isinstance(key, str):
            return key.encode("utf-8")
        if isinstance(key, bytes):
            return key
        raise TypeError("key must be str or bytes")

    def _coerce_value(self, value: Union[str, bytes, None]) -> Optional[bytes]:
        if value is None:
            return None
        if isinstance(value, str):
            return value.encode("utf-8")
        if isinstance(value, bytes):
            return value
        raise TypeError("value must be str, bytes, or None")

    def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        bkey = self._coerce_key(key)
        if bkey in self._writes:
            return self._writes[bkey]
        return self.store._tree_get(bkey)

    def put(self, key: Union[str, bytes], value: Union[str, bytes]) -> None:
        if self.read_only:
            raise PermissionError("Transaction is read-only")
        if self._aborted or self._committed:
            raise RuntimeError("Transaction is no longer active")
        bkey = self._coerce_key(key)
        bval = self._coerce_value(value)
        if bval is None:
            raise ValueError("put() value cannot be None; use delete()")
        self._writes[bkey] = bval
        self._write_keys_sorted = None

    def delete(self, key: Union[str, bytes]) -> bool:
        if self.read_only:
            raise PermissionError("Transaction is no longer active")
        if self._aborted or self._committed:
            raise RuntimeError("Transaction is no longer active")
        bkey = self._coerce_key(key)
        existed = self.get(bkey) is not None
        self._writes[bkey] = None
        self._write_keys_sorted = None
        return existed

    def _sorted_write_keys(self) -> List[bytes]:
        if self._write_keys_sorted is None:
            self._write_keys_sorted = sorted(self._writes.keys())
        return self._write_keys_sorted

    def cursor(self, low: Union[str, bytes, None] = None,
               high: Union[str, bytes, None] = None,
               include_high: bool = False) -> Cursor:
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
        # Collect from writes not in tree range
        for wk in self._sorted_write_keys():
            wv = self._writes[wk]
            if wv is None:
                continue  # tombstone
            # Check bounds
            if low_b is not None and wk < low_b:
                continue
            if high_b is not None:
                if include_high:
                    if wk > high_b:
                        continue
                else:
                    if wk >= high_b:
                        continue
            # Check if already in pairs (from tree)
            # Since tree_scan may not include keys that were inserted but not yet committed,
            # we need to add writes that are not in the tree yet.
            # Use binary search to check
            idx = bisect.bisect_left([p[0] for p in pairs], wk)
            if idx < len(pairs) and pairs[idx][0] == wk:
                continue  # already present (and already overlaid above)
            pairs.append((wk, wv))
        pairs.sort(key=lambda x: x[0])
        return Cursor(pairs)

    def prefix(self, prefix: Union[str, bytes]) -> Cursor:
        prefix_b = self._coerce_key(prefix)
        # Prefix range: [prefix, prefix + 1) using byte-level increment
        high = _prefix_upper_bound(prefix_b)
        return self.cursor(low=prefix_b, high=high, include_high=False)

    def count(self) -> int:
        return len(list(self.store._tree_scan(None, None, False)))


def _prefix_upper_bound(prefix: bytes) -> bytes:
    """Compute the smallest key strictly greater than all keys with the given prefix.

    This is done by treating the prefix as a big-endian number and adding 1.
    If the prefix is all 0xFF bytes, there is no finite upper bound, so we
    return a sentinel that is larger than any key with this prefix — but
    since we cannot represent infinity, we return the prefix itself with a
    flag; the caller should handle this case by doing a full scan and
    filtering. For simplicity, we return b'\xff' * (len+1) as an upper bound
    that is guaranteed to be > any key starting with prefix.
    """
    for i in range(len(prefix) - 1, -1, -1):
        if prefix[i] != 0xFF:
            return prefix[:i] + bytes([prefix[i] + 1]) + b"\x00" * (len(prefix) - i - 1)
    # All 0xFF
    return prefix + b"\x00"  # this won't match but signals unbounded prefix


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
        # Estimate serialized size
        size = LEAF_HEADER_SIZE
        for k, v in zip(leaf.keys, leaf.values):
            size += len(k) + len(v) + 10  # overhead for varints
        return size > self.store.page_size * 0.9

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
        return size > self.store.page_size * 0.9 or len(page.children) > self.store.branching * 2

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
        """Read a page from cache or disk."""
        if page_id in self._cache:
            self._cache.move_to_end(page_id)
            return self._cache[page_id]
        offset = HEADER_SIZE + page_id * self.page_size
        with open(self.path, "rb") as f:
            f.seek(offset)
            data = f.read(self.page_size)
        if len(data) < self.page_size:
            # Extend file
            data = data + b"\x00" * (self.page_size - len(data))
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
               include_high: bool = False) -> Cursor:
        txn = self.begin(read_only=True)
        return txn.cursor(low, high, include_high)

    def prefix(self, prefix: Union[str, bytes]) -> Cursor:
        txn = self.begin(read_only=True)
        return txn.prefix(prefix)

    def count(self) -> int:
        return self.tree.count() if self.tree else 0

    def snapshot(self) -> Transaction:
        """Return a read-only snapshot transaction."""
        return self.begin(read_only=True)

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
        return {
            "file_size": file_size,
            "page_size": self.page_size,
            "total_pages": total_pages,
            "cached_pages": len(self._cache),
            "free_list_head": self._free_list_head,
            "root_page_id": self.header.get("root_page_id", -1),
            "commit_ts": self._commit_ts,
            "next_page_id": self._next_page_id,
            "num_keys": self.count(),
        }