"""Database layer built on top of B+ Tree with persistence, transactions, and a query interface.

Features:
    - Put / get / delete operations
    - Range queries and prefix scans
    - ACID-like transactions (serialized)
    - Write-Ahead Log (WAL) for crash recovery
    - Batch operations (put_many, delete_many)
    - LRU read cache (optional)
    - Key-level TTL / expiration
    - Configurable via DatabaseConfig
    - Structured logging
    - JSON and binary persistence
    - Import/export (CSV, JSONL, Pickle)
    - SQL-like query language
    - Statistics and introspection
    - Database merging and diffing
    - Cursor-based pagination
"""

from __future__ import annotations

import json
import logging
import os
import time
import threading
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from .bplus_tree import BPlusTree
from .cache import LRUCache
from .config import DatabaseConfig, TreeConfig, CacheConfig, WALConfig
from .cursor import Cursor
from .serializer import Serializer
from .ttl import TTLManager
from .query_parser import QueryParser, QueryAST

logger = logging.getLogger("bplus_db")


class Transaction:
    """A transaction that buffers writes until commit.

    Transactions provide ACID-like guarantees:
    - Atomicity: All operations are applied or none are
    - Consistency: The tree is always in a valid state
    - Isolation: Transactions are serialized via the database lock
    - Durability: Committed data can be persisted to disk
    """

    def __init__(self, db: "Database", txn_id: int):
        self.db = db
        self.txn_id = txn_id
        self._buffer: List[Tuple[str, str, Any]] = []  # (op, key, value)
        self._committed = False
        self._rolled_back = False

    def put(self, key: str, value: Any) -> None:
        """Queue an insert operation."""
        if self._committed or self._rolled_back:
            raise RuntimeError("Transaction already finalized")
        self._buffer.append(("put", key, value))

    def delete(self, key: str) -> None:
        """Queue a delete operation."""
        if self._committed or self._rolled_back:
            raise RuntimeError("Transaction already finalized")
        self._buffer.append(("delete", key, None))

    def commit(self) -> None:
        """Commit all buffered operations to the database."""
        if self._committed:
            raise RuntimeError("Transaction already committed")
        if self._rolled_back:
            raise RuntimeError("Transaction already rolled back")
        logger.debug("Transaction %d committing %d operations", self.txn_id, len(self._buffer))
        self.db._apply_transaction(self._buffer)
        self._committed = True

    def rollback(self) -> None:
        """Discard all buffered operations."""
        if self._committed:
            raise RuntimeError("Transaction already committed")
        if self._rolled_back:
            raise RuntimeError("Transaction already rolled back")
        logger.debug("Transaction %d rolled back", self.txn_id)
        self._buffer.clear()
        self._rolled_back = True

    @property
    def is_active(self) -> bool:
        """Check if this transaction is still active (not committed or rolled back)."""
        return not self._committed and not self._rolled_back


class WriteAheadLog:
    """Simple write-ahead log for crash recovery.

    The WAL records all write operations (puts and deletes) before they are
    applied to the tree. On recovery, the WAL is replayed to restore consistency.
    """

    OP_PUT = "PUT"
    OP_DELETE = "DEL"

    def __init__(self, path: str = None):
        self.path = path
        self._entries: List[Tuple[str, str, Any]] = []
        self._enabled = path is not None
        self._lock = threading.Lock()

    def append(self, op: str, key: str, value: Any = None) -> None:
        """Append an operation to the WAL."""
        with self._lock:
            self._entries.append((op, key, value))
            if self._enabled and self.path:
                self._flush_entry(op, key, value)

    def _flush_entry(self, op: str, key: str, value: Any) -> None:
        """Write a single entry to the WAL file."""
        entry = {"op": op, "key": key}
        if value is not None:
            entry["value"] = value
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def replay(self) -> List[Tuple[str, str, Any]]:
        """Read and return all entries from the WAL file."""
        if not self._enabled or not self.path:
            return list(self._entries)

        entries = []
        try:
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        op = entry["op"]
                        key = entry["key"]
                        value = entry.get("value")
                        entries.append((op, key, value))
        except FileNotFoundError:
            pass
        return entries

    def clear(self) -> None:
        """Clear the WAL (after successful checkpoint)."""
        with self._lock:
            self._entries.clear()
            if self._enabled and self.path:
                try:
                    os.remove(self.path)
                except FileNotFoundError:
                    pass


class Database:
    """A key-value database backed by a B+ tree with persistence and querying.

    Features:
        - Put / get / delete operations
        - Range queries (inclusive bounds)
        - Prefix scans
        - ACID-like transactions (serialized)
        - Write-Ahead Log for crash recovery
        - LRU read cache (optional, configurable)
        - Key-level TTL / expiration
        - Batch operations
        - JSON and binary persistence
        - Import/export (CSV, JSONL, Pickle)
        - SQL-like query language
        - Statistics and introspection
        - Database merging and diffing
        - Cursor-based pagination
        - Structured logging
    """

    MAGIC = b"BPDB"
    FORMAT_VERSION = 2

    def __init__(self, order: int = 64, wal_path: str = None, config: DatabaseConfig = None):
        """Initialize a B+ tree database.

        Args:
            order: The B+ tree order (branching factor). Default 64.
                Ignored if *config* is provided.
            wal_path: Optional path for the write-ahead log file.
                Ignored if *config* is provided.
            config: Optional :class:`DatabaseConfig` for full configuration.
                When provided, *order* and *wal_path* are taken from the config.
        """
        if config is not None:
            self._config = config
            order = config.tree.order
            wal_path = config.wal.path if config.wal.enabled else None
        else:
            self._config = DatabaseConfig(
                tree=TreeConfig(order=order),
                wal=WALConfig(path=wal_path, enabled=wal_path is not None),
            )

        self._tree = BPlusTree(order=order)
        self._serializer = Serializer()
        self._lock = threading.RLock()
        self._path: Optional[str] = self._config.persistence.json_path
        self._txn_counter = 0
        self._wal = WriteAheadLog(wal_path)

        # LRU read cache
        cache_cfg = self._config.cache
        if cache_cfg.enabled:
            self._cache: Optional[LRUCache] = LRUCache(max_size=cache_cfg.max_size)
        else:
            self._cache = None

        # TTL manager
        self._ttl = TTLManager()

        # Auto-save counter
        self._write_count = 0

        # Setup logging
        log_cfg = self._config.logging
        _handler = logging.StreamHandler()
        _handler.setFormatter(logging.Formatter(log_cfg.format))
        logger.addHandler(_handler)
        logger.setLevel(getattr(logging, log_cfg.level.upper(), logging.WARNING))

        self._stats = {
            "gets": 0,
            "puts": 0,
            "deletes": 0,
            "ranges": 0,
            "transactions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "ttl_evictions": 0,
            "start_time": time.time(),
        }

    # ── Core CRUD ──────────────────────────────────────────────

    def put(self, key: str, value: Any, ttl: float = None) -> None:
        """Insert or update a key-value pair.

        Args:
            key: The key to store.
            value: The value to store.
            ttl: Optional time-to-live in seconds.  After *ttl* seconds
                the key is considered expired and will be removed on the next
                read or explicit cleanup.
        """
        with self._lock:
            serialized = self._serializer.serialize_value(value)
            self._tree.insert(key, serialized)
            self._wal.append(WriteAheadLog.OP_PUT, key, serialized)
            self._stats["puts"] += 1

            # Invalidate cache entry (stale data)
            if self._cache is not None:
                self._cache.invalidate(key)

            # Set TTL if requested
            if ttl is not None:
                self._ttl.set_ttl(key, ttl)

            self._maybe_auto_save()
            logger.debug("PUT %s", key)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key, returning default if not found.

        Note: If the stored value is None, this returns None (not the default).
        The default is only returned when the key doesn't exist.

        If the key has expired (TTL), it is lazily deleted and *default*
        is returned.
        """
        with self._lock:
            # Check TTL first
            if self._ttl.is_expired(key):
                self._evict_expired_key(key)
                return default

            self._stats["gets"] += 1

            # Check cache
            if self._cache is not None:
                cached = self._cache.get(key)
                if cached is not LRUCache._CACHE_MISS:
                    self._stats["cache_hits"] += 1
                    return self._serializer.deserialize_value(cached)
                self._stats["cache_misses"] += 1

            result = self._tree.search(key)
            if result is BPlusTree._NOT_FOUND:
                return default

            # Populate cache
            if self._cache is not None:
                self._cache.put(key, result)

            return self._serializer.deserialize_value(result)

    def delete(self, key: str) -> bool:
        """Delete a key-value pair. Returns True if key existed."""
        with self._lock:
            # Remove TTL if present
            self._ttl.remove_ttl(key)

            self._stats["deletes"] += 1
            result = self._tree.delete(key)
            if result:
                self._wal.append(WriteAheadLog.OP_DELETE, key)

                # Invalidate cache
                if self._cache is not None:
                    self._cache.invalidate(key)

            self._maybe_auto_save()
            logger.debug("DELETE %s (existed=%s)", key, result)
            return result

    def contains(self, key: str) -> bool:
        """Check if a key exists in the database (and has not expired)."""
        with self._lock:
            if self._ttl.is_expired(key):
                self._evict_expired_key(key)
                return False
            return key in self._tree

    # ── Batch Operations ────────────────────────────────────────

    def put_many(self, items: Dict[str, Any]) -> int:
        """Insert multiple key-value pairs at once.

        Args:
            items: Dictionary of key-value pairs to insert.

        Returns:
            Number of pairs inserted.
        """
        with self._lock:
            count = 0
            for key, value in items.items():
                serialized = self._serializer.serialize_value(value)
                self._tree.insert(key, serialized)
                self._wal.append(WriteAheadLog.OP_PUT, key, serialized)
                if self._cache is not None:
                    self._cache.invalidate(key)
                count += 1
            self._stats["puts"] += count
            self._maybe_auto_save()
            return count

    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys at once.

        Args:
            keys: List of keys to delete.

        Returns:
            Number of keys actually deleted.
        """
        with self._lock:
            count = 0
            for key in keys:
                self._ttl.remove_ttl(key)
                if self._tree.delete(key):
                    self._wal.append(WriteAheadLog.OP_DELETE, key)
                    if self._cache is not None:
                        self._cache.invalidate(key)
                    count += 1
            self._stats["deletes"] += count
            self._maybe_auto_save()
            return count

    # ── Range & Prefix Queries ──────────────────────────────────

    def range_query(self, start_key: str = None, end_key: str = None) -> List[Tuple[str, Any]]:
        """Return all key-value pairs in [start_key, end_key]."""
        with self._lock:
            self._stats["ranges"] += 1
            results = []
            for key, val in self._tree.range_query(start_key, end_key):
                # Skip expired keys
                if self._ttl.is_expired(key):
                    continue
                results.append((key, self._serializer.deserialize_value(val)))
            # Eagerly evict any expired keys encountered
            self._cleanup_expired_in_results(results)
            return results

    def prefix_scan(self, prefix: str) -> List[Tuple[str, Any]]:
        """Return all key-value pairs where the key starts with prefix."""
        with self._lock:
            self._stats["ranges"] += 1
            results = []
            for key, val in self._tree.range_query(prefix):
                if not key.startswith(prefix):
                    break
                if self._ttl.is_expired(key):
                    continue
                results.append((key, self._serializer.deserialize_value(val)))
            return results

    def keys(self) -> List[str]:
        """Return all keys in sorted order (excluding expired)."""
        with self._lock:
            self._cleanup_all_expired()
            return [k for k, v in self._tree.range_query()]

    def values(self) -> List[Any]:
        """Return all values in key order (excluding expired)."""
        with self._lock:
            self._cleanup_all_expired()
            return [self._serializer.deserialize_value(v) for k, v in self._tree.range_query()]

    def items(self) -> List[Tuple[str, Any]]:
        """Return all (key, value) pairs in sorted order (excluding expired)."""
        with self._lock:
            self._cleanup_all_expired()
            return [(k, self._serializer.deserialize_value(v)) for k, v in self._tree.range_query()]

    # ── Cursor / Pagination ─────────────────────────────────────

    def cursor(self, start_key: str = None, end_key: str = None,
               prefix: str = None, page_size: int = 100) -> Cursor:
        """Create a cursor for paginating through results.

        Args:
            start_key: Inclusive lower bound (or None).
            end_key: Inclusive upper bound (or None).
            prefix: If set, do a prefix scan instead of range query.
            page_size: Number of entries per page.
        """
        return Cursor(self, start_key=start_key, end_key=end_key,
                       prefix=prefix, page_size=page_size)

    # ── TTL ──────────────────────────────────────────────────────

    def set_ttl(self, key: str, ttl_seconds: float) -> None:
        """Set a time-to-live on an existing key.

        After *ttl_seconds*, the key is considered expired and will be
        lazily removed on read.
        """
        with self._lock:
            if key not in self._tree:
                raise KeyError(f"Key {key!r} not found")
            self._ttl.set_ttl(key, ttl_seconds)
            logger.debug("TTL set: %s expires in %.1fs", key, ttl_seconds)

    def get_ttl(self, key: str) -> Optional[float]:
        """Return remaining TTL in seconds, or None if no TTL is set."""
        with self._lock:
            return self._ttl.get_remaining_ttl(key)

    def cleanup_expired(self) -> int:
        """Eagerly remove all expired keys.

        Returns:
            Number of keys evicted.
        """
        with self._lock:
            expired = self._ttl.cleanup()
            count = 0
            for key in expired:
                if self._tree.delete(key):
                    if self._cache is not None:
                        self._cache.invalidate(key)
                    count += 1
            if count:
                self._stats["ttl_evictions"] += count
                logger.info("Cleaned up %d expired keys", count)
            return count

    # ── Cache ────────────────────────────────────────────────────

    def cache_stats(self) -> Optional[Dict[str, Any]]:
        """Return cache statistics, or None if caching is disabled."""
        if self._cache is None:
            return None
        return self._cache.stats()

    def clear_cache(self) -> None:
        """Clear the read cache."""
        if self._cache is not None:
            self._cache.clear()

    # ── Transactions ────────────────────────────────────────────

    def begin_transaction(self) -> Transaction:
        """Start a new transaction."""
        with self._lock:
            self._txn_counter += 1
            self._stats["transactions"] += 1
            return Transaction(self, self._txn_counter)

    def _apply_transaction(self, buffer: List[Tuple[str, str, Any]]) -> None:
        """Apply a committed transaction's buffer to the tree."""
        with self._lock:
            for op, key, value in buffer:
                if op == "put":
                    serialized = self._serializer.serialize_value(value)
                    self._tree.insert(key, serialized)
                    self._wal.append(WriteAheadLog.OP_PUT, key, serialized)
                    self._stats["puts"] += 1
                    if self._cache is not None:
                        self._cache.invalidate(key)
                elif op == "delete":
                    self._tree.delete(key)
                    self._wal.append(WriteAheadLog.OP_DELETE, key)
                    self._stats["deletes"] += 1
                    if self._cache is not None:
                        self._cache.invalidate(key)
            self._maybe_auto_save()

    # ── Persistence ─────────────────────────────────────────────

    def save(self, path: str = None) -> None:
        """Save the database to disk as JSON.

        Uses atomic write (write to temp file, then rename) to prevent corruption.
        """
        path = path or self._path
        if path is None:
            raise ValueError("No path specified. Call save(path=...) or open(path=...).")
        with self._lock:
            data = {
                "version": self.FORMAT_VERSION,
                "order": self._tree.order,
                "entries": [(k, v) for k, v in self._tree.range_query()],
                "stats": {k: v for k, v in self._stats.items() if k != "start_time"},
                "ttl": self._ttl.to_dict(),
            }
            # Use atomic write
            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, path)
            self._path = path
            # Clear WAL after successful save (checkpoint)
            self._wal.clear()
            logger.info("Database saved to %s (%d keys)", path, len(self._tree))

    @classmethod
    def load(cls, path: str) -> "Database":
        """Load a database from a JSON file on disk."""
        with open(path, "r") as f:
            data = json.load(f)

        db = cls(order=data["order"])
        for key, val in data["entries"]:
            db._tree.insert(key, val)  # Values already serialized in JSON
        db._path = path
        if "stats" in data:
            for k, v in data["stats"].items():
                if k in db._stats:
                    db._stats[k] = v
        # Restore TTL data if present
        if "ttl" in data:
            db._ttl = TTLManager.from_dict(data["ttl"])
        logger.info("Database loaded from %s (%d keys)", path, len(db._tree))
        return db

    def save_binary(self, path: str = None) -> None:
        """Save in a compact binary format."""
        path = path or self._path
        if path is None:
            raise ValueError("No path specified.")
        with self._lock:
            entries = [(k, v) for k, v in self._tree.range_query()]
            tmp_path = path + ".tmp"
            with open(tmp_path, "wb") as f:
                # Header
                f.write(self.MAGIC)
                f.write(self._tree.order.to_bytes(4, "big"))
                f.write(self.FORMAT_VERSION.to_bytes(4, "big"))
                f.write(len(entries).to_bytes(8, "big"))
                # Entries: key_len(2) + key + val_len(4) + val
                for key, val in entries:
                    key_bytes = key.encode("utf-8")
                    val_bytes = val.encode("utf-8") if isinstance(val, str) else json.dumps(val).encode("utf-8")
                    f.write(len(key_bytes).to_bytes(2, "big"))
                    f.write(key_bytes)
                    f.write(len(val_bytes).to_bytes(4, "big"))
                    f.write(val_bytes)
            os.replace(tmp_path, path)
            self._wal.clear()
            logger.info("Database saved (binary) to %s (%d keys)", path, len(self._tree))

    @classmethod
    def load_binary(cls, path: str) -> "Database":
        """Load from binary format."""
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != cls.MAGIC:
                raise ValueError("Invalid file format: bad magic bytes")
            order = int.from_bytes(f.read(4), "big")
            version = int.from_bytes(f.read(4), "big")
            if version > cls.FORMAT_VERSION:
                raise ValueError(f"Unsupported format version: {version}")
            count = int.from_bytes(f.read(8), "big")

            db = cls(order=order)
            for _ in range(count):
                key_len = int.from_bytes(f.read(2), "big")
                key = f.read(key_len).decode("utf-8")
                val_len = int.from_bytes(f.read(4), "big")
                val = f.read(val_len).decode("utf-8")
                db._tree.insert(key, val)
            db._path = path
            logger.info("Database loaded (binary) from %s (%d keys)", path, len(db._tree))
            return db

    # ── WAL Recovery ────────────────────────────────────────────

    @classmethod
    def recover(cls, db_path: str, wal_path: str) -> "Database":
        """Recover a database by loading the snapshot and replaying the WAL.

        Args:
            db_path: Path to the database snapshot (JSON format).
            wal_path: Path to the write-ahead log.

        Returns:
            Recovered database.
        """
        db = cls.load(db_path)
        wal = WriteAheadLog(wal_path)
        for op, key, value in wal.replay():
            if op == WriteAheadLog.OP_PUT:
                db._tree.insert(key, value)
            elif op == WriteAheadLog.OP_DELETE:
                db._tree.delete(key)
        logger.info("Database recovered from %s + WAL %s (%d keys)", db_path, wal_path, len(db._tree))
        return db

    # ── Query Language ───────────────────────────────────────────

    def execute(self, query: str) -> Any:
        """Execute a SQL-like query string.

        Supported queries:
            SELECT * FROM db
            SELECT * FROM db WHERE key = 'x'
            SELECT * FROM db WHERE key > 'a'
            SELECT * FROM db WHERE key < 'z'
            SELECT * FROM db WHERE key >= 'a' AND key <= 'z'
            INSERT INTO db KEY 'x' VALUE 'y'
            DELETE FROM db WHERE key = 'x'
            COUNT db
        """
        parser = QueryParser(query)
        ast = parser.parse()
        return self._execute_ast(ast)

    def _execute_ast(self, ast: QueryAST) -> Any:
        """Execute a parsed query AST."""
        if ast.command == "select":
            if ast.conditions:
                start = None
                end = None
                equals_key = None
                for cond in ast.conditions:
                    if cond["op"] == "=":
                        equals_key = cond["value"]
                    elif cond["op"] == ">":
                        start = cond["value"]
                    elif cond["op"] == ">=":
                        start = cond["value"]
                    elif cond["op"] == "<":
                        end = cond["value"]
                    elif cond["op"] == "<=":
                        end = cond["value"]
                if equals_key is not None:
                    return self.get(equals_key)
                return self.range_query(start, end)
            return self.range_query()

        elif ast.command == "insert":
            self.put(ast.key, ast.value)
            return True

        elif ast.command == "delete":
            return self.delete(ast.key)

        elif ast.command == "count":
            return len(self._tree)

        else:
            raise ValueError(f"Unknown command: {ast.command}")

    # ── Merge & Diff ────────────────────────────────────────────

    def merge(self, other: "Database", conflict: str = "ours") -> int:
        """Merge another database into this one.

        Args:
            other: The database to merge from.
            conflict: Strategy for key conflicts: 'ours' (keep existing),
                       'theirs' (overwrite with other), 'error' (raise exception).

        Returns:
            Number of keys merged.
        """
        if conflict not in ("ours", "theirs", "error"):
            raise ValueError("conflict must be 'ours', 'theirs', or 'error'")

        merged = 0
        with self._lock:
            for key, val in other._tree.range_query():
                existing = self._tree.search(key)
                if existing is BPlusTree._NOT_FOUND:
                    self._tree.insert(key, val)
                    if self._cache is not None:
                        self._cache.invalidate(key)
                    merged += 1
                elif conflict == "theirs":
                    self._tree.insert(key, val)
                    if self._cache is not None:
                        self._cache.invalidate(key)
                    merged += 1
                elif conflict == "error":
                    raise KeyError(f"Key conflict: {key!r}")
                # 'ours': keep existing, no action needed
        logger.info("Merged %d keys from other database (conflict=%s)", merged, conflict)
        return merged

    def diff(self, other: "Database") -> Dict[str, List]:
        """Compare two databases and return the differences.

        Returns:
            Dict with keys:
                'only_in_self': keys only in this database
                'only_in_other': keys only in the other database
                'changed': keys present in both but with different values
                'unchanged': keys present in both with same values
        """
        result = {
            "only_in_self": [],
            "only_in_other": [],
            "changed": [],
            "unchanged": [],
        }

        self_keys = set(k for k, v in self._tree.range_query())
        other_keys = set(k for k, v in other._tree.range_query())

        for key in self_keys - other_keys:
            result["only_in_self"].append(key)
        for key in other_keys - self_keys:
            result["only_in_other"].append(key)
        for key in self_keys & other_keys:
            self_val = self._tree.search(key)
            other_val = other._tree.search(key)
            if self_val != other_val:
                result["changed"].append(key)
            else:
                result["unchanged"].append(key)

        # Sort for deterministic output
        for k in result:
            result[k].sort()

        return result

    # ── Introspection ────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return database statistics."""
        with self._lock:
            uptime = time.time() - self._stats["start_time"]
            tree_stats = self._tree.stats()
            result = {
                "total_keys": len(self._tree),
                "tree_order": self._tree.order,
                "tree_height": tree_stats["height"],
                "leaf_count": tree_stats["leaf_count"],
                "gets": self._stats["gets"],
                "puts": self._stats["puts"],
                "deletes": self._stats["deletes"],
                "range_queries": self._stats["ranges"],
                "transactions": self._stats["transactions"],
                "ttl_evictions": self._stats["ttl_evictions"],
                "uptime_seconds": round(uptime, 2),
            }
            if self._cache is not None:
                result["cache"] = self._cache.stats()
            return result

    def tree_structure(self) -> str:
        """Return a string representation of the B+ tree structure."""
        return self._tree.print_tree()

    def validate(self) -> List[str]:
        """Validate the B+ tree invariants. Returns list of violations."""
        return self._tree.validate()

    # ── Private helpers ──────────────────────────────────────────

    def _evict_expired_key(self, key: str) -> None:
        """Remove a single expired key from the tree and cache."""
        self._tree.delete(key)
        self._ttl.remove_ttl(key)
        if self._cache is not None:
            self._cache.invalidate(key)
        self._stats["ttl_evictions"] += 1
        self._stats["deletes"] += 1
        logger.debug("Expired key evicted: %s", key)

    def _cleanup_expired_in_results(self, results: List[Tuple[str, Any]]) -> None:
        """Remove any expired keys that were found in a range scan."""
        # This is a no-op now because we already skip expired in range_query,
        # but kept as a hook for future optimization.
        pass

    def _cleanup_all_expired(self) -> None:
        """Eagerly remove all expired keys."""
        self.cleanup_expired()

    def _maybe_auto_save(self) -> None:
        """Auto-save to disk if configured."""
        cfg = self._config.persistence
        if not cfg.auto_save and cfg.auto_save_interval <= 0:
            return
        self._write_count += 1
        if cfg.auto_save:
            # Save on every write (expensive!)
            if self._path:
                self.save()
        elif cfg.auto_save_interval > 0 and self._write_count % cfg.auto_save_interval == 0:
            if self._path:
                self.save()

    # ── Dunder methods ──────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._tree)

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def __repr__(self) -> str:
        return f"Database(keys={len(self._tree)}, order={self._tree.order})"