"""Database layer built on top of B+ Tree with persistence, transactions, and a query interface."""

from __future__ import annotations

import json
import os
import time
import threading
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .bplus_tree import BPlusTree
from .serializer import Serializer
from .query_parser import QueryParser, QueryAST


class Transaction:
    """A simple transaction that buffers writes until commit."""

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
        self.db._apply_transaction(self._buffer)
        self._committed = True

    def rollback(self) -> None:
        """Discard all buffered operations."""
        if self._committed:
            raise RuntimeError("Transaction already committed")
        if self._rolled_back:
            raise RuntimeError("Transaction already rolled back")
        self._buffer.clear()
        self._rolled_back = True


class Database:
    """A key-value database backed by a B+ tree with persistence and querying.

    Features:
        - Put / get / delete operations
        - Range queries (inclusive bounds)
        - Prefix scans
        - ACID-like transactions (serialized)
        - JSON-based persistence to disk
        - Simple SQL-like query language
        - Statistics and introspection
    """

    MAGIC = b"BPDB"
    FORMAT_VERSION = 1

    def __init__(self, order: int = 64):
        self._tree = BPlusTree(order=order)
        self._serializer = Serializer()
        self._lock = threading.RLock()
        self._path: Optional[str] = None
        self._txn_counter = 0
        self._stats = {
            "gets": 0,
            "puts": 0,
            "deletes": 0,
            "ranges": 0,
            "transactions": 0,
            "start_time": time.time(),
        }

    # ── Core CRUD ──────────────────────────────────────────────

    def put(self, key: str, value: Any) -> None:
        """Insert or update a key-value pair."""
        with self._lock:
            serialized = self._serializer.serialize_value(value)
            self._tree.insert(key, serialized)
            self._stats["puts"] += 1

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key, returning default if not found."""
        with self._lock:
            self._stats["gets"] += 1
            result = self._tree.search(key)
            if result is None:
                return default
            return self._serializer.deserialize_value(result)

    def delete(self, key: str) -> bool:
        """Delete a key-value pair. Returns True if key existed."""
        with self._lock:
            self._stats["deletes"] += 1
            return self._tree.delete(key)

    def contains(self, key: str) -> bool:
        """Check if a key exists in the database."""
        with self._lock:
            return key in self._tree

    # ── Range & Prefix Queries ──────────────────────────────────

    def range_query(self, start_key: str = None, end_key: str = None) -> List[Tuple[str, Any]]:
        """Return all key-value pairs in [start_key, end_key]."""
        with self._lock:
            self._stats["ranges"] += 1
            results = []
            for key, val in self._tree.range_query(start_key, end_key):
                results.append((key, self._serializer.deserialize_value(val)))
            return results

    def prefix_scan(self, prefix: str) -> List[Tuple[str, Any]]:
        """Return all key-value pairs where the key starts with prefix."""
        with self._lock:
            self._stats["ranges"] += 1
            results = []
            for key, val in self._tree.range_query(prefix):
                if not key.startswith(prefix):
                    break
                results.append((key, self._serializer.deserialize_value(val)))
            return results

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
                    self._stats["puts"] += 1
                elif op == "delete":
                    self._tree.delete(key)
                    self._stats["deletes"] += 1

    # ── Persistence ─────────────────────────────────────────────

    def save(self, path: str = None) -> None:
        """Save the database to disk as JSON."""
        path = path or self._path
        if path is None:
            raise ValueError("No path specified. Call save(path=...) or open(path=...).")
        with self._lock:
            data = {
                "version": self.FORMAT_VERSION,
                "order": self._tree.order,
                "entries": [(k, v) for k, v in self._tree.range_query()],
                "stats": self._stats,
            }
            # Use atomic write
            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, path)
            self._path = path

    @classmethod
    def load(cls, path: str) -> "Database":
        """Load a database from a JSON file on disk."""
        with open(path, "r") as f:
            data = json.load(f)

        db = cls(order=data["order"])
        for key, val in data["entries"]:
            db._tree.insert(key, val)  # Values already serialized in JSON
        db._path = path
        db._stats = data.get("stats", db._stats)
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

    @classmethod
    def load_binary(cls, path: str) -> "Database":
        """Load from binary format."""
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic != cls.MAGIC:
                raise ValueError("Invalid file format")
            order = int.from_bytes(f.read(4), "big")
            count = int.from_bytes(f.read(8), "big")

            db = cls(order=order)
            for _ in range(count):
                key_len = int.from_bytes(f.read(2), "big")
                key = f.read(key_len).decode("utf-8")
                val_len = int.from_bytes(f.read(4), "big")
                val = f.read(val_len).decode("utf-8")
                db._tree.insert(key, val)
            db._path = path
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
                for cond in ast.conditions:
                    if cond["op"] == "=":
                        return self.get(cond["value"])
                    elif cond["op"] == ">":
                        start = cond["value"]
                    elif cond["op"] == ">=":
                        start = cond["value"]
                    elif cond["op"] == "<":
                        end = cond["value"]
                    elif cond["op"] == "<=":
                        end = cond["value"]
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

    # ── Introspection ────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return database statistics."""
        with self._lock:
            uptime = time.time() - self._stats["start_time"]
            return {
                "total_keys": len(self._tree),
                "tree_order": self._tree.order,
                "gets": self._stats["gets"],
                "puts": self._stats["puts"],
                "deletes": self._stats["deletes"],
                "range_queries": self._stats["ranges"],
                "transactions": self._stats["transactions"],
                "uptime_seconds": round(uptime, 2),
            }

    def tree_structure(self) -> str:
        """Return a string representation of the B+ tree structure."""
        return self._tree.print_tree()

    def __len__(self) -> int:
        return len(self._tree)

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def __repr__(self) -> str:
        return f"Database(keys={len(self._tree)}, order={self._tree.order})"