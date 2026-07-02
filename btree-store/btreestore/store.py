"""
Store: persistent B+Tree key-value store with MVCC transactions.

File layout:
  [Header (HEADER_SIZE bytes)]
  [Page 0] [Page 1] ... [Page N]
Pages are page_size bytes each, starting at offset HEADER_SIZE.
Page IDs are 0-indexed.
"""

from __future__ import annotations

import os
import struct
import threading
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from .pages import (
    Page, LeafPage, InternalPage, FreePage,
    MAGIC, VERSION, HEADER_FMT, HEADER_SIZE,
    PAGE_LEAF, PAGE_INTERNAL, PAGE_FREE, CRC_SIZE,
    DEFAULT_PAGE_SIZE, DEFAULT_BRANCHING, DEFAULT_CACHE_SIZE,
    detect_page_type, deserialize_leaf, deserialize_internal, deserialize_free,
    serialize_leaf, serialize_internal, serialize_free, verify_page_crc,
)
from .tree import BPlusTree
from .transaction import Transaction
from .cursor import Cursor
from .config import StoreConfig
from .logging_util import get_logger, setup_logging
from .wal import WAL

logger = get_logger()


class Store:
    """A persistent B+Tree key-value store with MVCC transactions.

    File layout:
      [Header (HEADER_SIZE bytes)]
      [Page 0] [Page 1] ... [Page N]
    Pages are page_size bytes each, starting at offset HEADER_SIZE.
    Page IDs are 0-indexed.
    """

    def __init__(
        self,
        path: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        branching: int = DEFAULT_BRANCHING,
        cache_size: int = DEFAULT_CACHE_SIZE,
        *,
        config: Optional[StoreConfig] = None,
        wal_enabled: bool = True,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        sync_on_commit: bool = False,
    ):
        """Open or create a store.

        Args:
            path: Path to the database file.
            page_size: Size of each page in bytes (includes 4-byte CRC).
            branching: Target max children per internal node.
            cache_size: Max pages kept in LRU cache.
            config: Optional StoreConfig object. If provided, overrides
                    individual parameters.
            wal_enabled: Whether to enable the Write-Ahead Log.
            log_level: Logging level string.
            log_file: Optional path to log file.
            sync_on_commit: Whether to fsync on each commit.
        """
        if config is not None:
            self.path = config.path or path
            self.page_size = config.page_size
            self.branching = config.branching
            self.cache_size = config.cache_size
            wal_enabled = config.wal_enabled
            log_level = config.log_level
            log_file = config.log_file
            self.sync_on_commit = config.sync_on_commit
        else:
            self.path = path
            self.page_size = page_size
            self.branching = branching
            self.cache_size = cache_size
            self.sync_on_commit = sync_on_commit

        # Setup logging
        setup_logging(log_level, log_file)

        self._cache: OrderedDict[int, Page] = OrderedDict()
        self._lock = threading.RLock()
        self._next_page_id = 0
        self._free_list_head = -1
        self._commit_ts = 0
        self._next_txn_id = 1
        self.header: Dict[str, Any] = {}
        self.tree: Optional[BPlusTree] = None
        self._closed = False
        self._dirty_header = False
        self._wal: Optional[WAL] = None
        self._commit_count = 0
        self._wal_enabled = wal_enabled

        if os.path.exists(self.path) and os.path.getsize(self.path) >= HEADER_SIZE:
            self._open()
        else:
            self._create()

        # Setup WAL and replay if needed
        if self._wal_enabled:
            wal_path = self.path + ".wal"
            self._wal = WAL(wal_path)
            # Check if WAL has data to replay
            wal_ops = self._wal.replay()
            if wal_ops:
                logger.info(f"Replaying {len(wal_ops)} WAL operations")
                for op_type, key, value in wal_ops:
                    if op_type == 1:  # OP_PUT
                        self.tree.insert(key, value)  # type: ignore
                    elif op_type == 2:  # OP_DELETE
                        self.tree.delete(key)  # type: ignore
                self._flush_all()
                self._wal.checkpoint()

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
        logger.info(f"Created new store: {self.path}")

    def _open(self) -> None:
        """Open existing store file."""
        with open(self.path, "rb") as f:
            data = f.read(HEADER_SIZE)
        magic, version, page_size, root_id, next_page_id, free_list_head, commit_ts = \
            struct.unpack(HEADER_FMT, data)
        if magic != MAGIC:
            raise ValueError(f"Bad magic: {magic!r}")
        if version != VERSION:
            # Try to handle v2 (previous version)
            if version == 2:
                logger.warning(
                    f"Store file version {version} (expected {VERSION}). "
                    "Upgrading in-memory — no on-disk migration needed for data."
                )
            else:
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
        logger.info(f"Opened store: {self.path} (commit_ts={commit_ts})")

    def _flush_header(self) -> None:
        """Write header to disk."""
        header_data = struct.pack(
            HEADER_FMT, MAGIC, VERSION, self.page_size,
            self.header["root_page_id"], self._next_page_id,
            self._free_list_head, self._commit_ts,
        )
        mode = "r+b" if os.path.exists(self.path) else "w+b"
        with open(self.path, mode) as f:
            f.seek(0)
            f.write(header_data)
            if self.sync_on_commit:
                f.flush()
                os.fsync(f.fileno())
        self._dirty_header = False

    # --- Page allocation and I/O ---

    def _alloc_page(self) -> int:
        """Allocate a page, reusing free list if available."""
        if self._free_list_head != -1:
            page_id = self._free_list_head
            free_page = self._read_page(page_id)
            assert isinstance(free_page, FreePage)
            self._free_list_head = free_page.next_free
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
        """Add a page to the cache, evicting LRU pages if needed."""
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
            if self.sync_on_commit:
                f.flush()
                os.fsync(f.fileno())
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

            # Write to WAL if enabled
            if self._wal is not None:
                for key in txn._sorted_write_keys():
                    val = txn._writes[key]
                    if val is None:
                        self._wal.append_delete(key)
                    else:
                        self._wal.append_put(key, val)
                self._wal.append_commit()

            # Apply writes in sorted order for better locality
            for key in txn._sorted_write_keys():
                val = txn._writes[key]
                if val is None:
                    self.tree.delete(key)  # type: ignore
                else:
                    self.tree.insert(key, val)  # type: ignore
            self._commit_ts += 1
            self.header["commit_ts"] = self._commit_ts
            self._dirty_header = True
            self._flush_all()
            txn._committed = True
            self._commit_count += 1

            # Auto-checkpoint WAL
            if self._wal is not None and self._commit_count % 100 == 0:
                self._wal.checkpoint()
                logger.debug(f"WAL auto-checkpoint at commit #{self._commit_count}")

    def rollback(self, txn: Transaction) -> None:
        """Abort a transaction: discard buffered writes."""
        txn._writes.clear()
        txn._aborted = True

    # --- Convenience methods (autocommit) ---

    def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        """Get the value for a key (autocommit read)."""
        txn = self.begin(read_only=True)
        try:
            return txn.get(key)
        finally:
            txn._committed = True

    def put(self, key: Union[str, bytes], value: Union[str, bytes]) -> None:
        """Insert or update a key-value pair (autocommit)."""
        txn = self.begin()
        try:
            txn.put(key, value)
            self.commit(txn)
        except Exception:
            self.rollback(txn)
            raise

    def delete(self, key: Union[str, bytes]) -> bool:
        """Delete a key (autocommit). Returns True if the key existed."""
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
        """Create a cursor (autocommit read)."""
        txn = self.begin(read_only=True)
        return txn.cursor(low, high, include_high, reverse, limit, offset)

    def prefix(self, prefix: Union[str, bytes],
               reverse: bool = False,
               limit: Optional[int] = None,
               offset: int = 0) -> Cursor:
        """Scan keys with a prefix (autocommit read)."""
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

    def increment(self, key: Union[str, bytes], amount: int = 1) -> int:
        """Autocommit atomic increment."""
        txn = self.begin()
        try:
            result = txn.increment(key, amount)
            self.commit(txn)
            return result
        except Exception:
            self.rollback(txn)
            raise

    def count(self) -> int:
        """Count total keys in the store."""
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

    def compact(self) -> int:
        """Compact the tree by rebuilding it with all existing keys.

        This eliminates sparse pages from deletions and rebuilds the tree
        structure. Returns the number of keys compacted.
        """
        if self.tree is None:
            return 0
        with self._lock:
            result = self.tree.compact()
            self._flush_all()
            if self._wal is not None:
                self._wal.checkpoint()
            return result

    def checkpoint(self) -> None:
        """Checkpoint the WAL: flush all dirty pages and truncate the WAL."""
        with self._lock:
            self._flush_all()
            if self._wal is not None:
                self._wal.checkpoint()
            logger.info("Checkpoint complete")

    def close(self) -> None:
        """Flush and close the store."""
        with self._lock:
            if self._closed:
                return
            self._flush_all()
            if self._wal is not None:
                self._wal.checkpoint()
                self._wal.close()
            self._cache.clear()
            self._closed = True
            logger.info(f"Closed store: {self.path}")

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
        tree_depth = self.tree.depth() if self.tree else 0
        wal_size = 0
        if self._wal is not None and os.path.exists(self.path + ".wal"):
            wal_size = os.path.getsize(self.path + ".wal")
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
            "wal_enabled": self._wal is not None,
            "wal_size": wal_size,
            "commit_count": self._commit_count,
        }