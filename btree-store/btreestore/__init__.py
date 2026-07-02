"""
btreestore: A persistent B+Tree key-value store with MVCC transactions.

A dependency-free embedded key-value database featuring:
  - B+Tree with linked leaves for efficient ordered scans
  - MVCC snapshot-isolated transactions
  - CRC32 per-page checksums for integrity
  - Compare-and-swap (CAS) for optimistic concurrency
  - Range, prefix, and cursor-based iteration
  - Batch operations and bulk loading
  - Write-Ahead Log (WAL) for crash recovery
  - Configuration file support (JSON/TOML)
  - Structured logging
  - Plugin architecture for custom extensions

Usage:
    from btreestore import Store

    with Store("mydb.btree") as store:
        store.put("hello", "world")
        assert store.get("hello") == b"world"
"""

from btreestore.store import Store
from btreestore.transaction import Transaction
from btreestore.cursor import Cursor
from btreestore.config import StoreConfig
from btreestore.wal import WAL

__version__ = "3.0.0"
__author__ = "Creative Projects"
__license__ = "MIT"

__all__ = [
    "Store",
    "Transaction",
    "Cursor",
    "StoreConfig",
    "WAL",
    "__version__",
]