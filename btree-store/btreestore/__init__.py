"""
btreestore: A persistent B+Tree key-value store with MVCC transactions.

A dependency-free embedded key-value database featuring:
  - B+Tree with linked leaves for efficient ordered scans
  - Self-balancing deletes with merge/borrow rebalancing
  - MVCC snapshot-isolated transactions
  - CRC32 per-page checksums for integrity
  - Compare-and-swap (CAS) for optimistic concurrency
  - Range, prefix, and cursor-based iteration
  - Streaming cursor for memory-efficient large-range scans
  - Batch operations and bulk loading
  - Write-Ahead Log (WAL) for crash recovery
  - TTL key expiration with lazy and active sweep
  - Secondary indexes for multi-field lookups
  - Backup/restore with CRC32-verified archives
  - Event subscription system
  - Optional page-level compression
  - Configuration file support (JSON/TOML)
  - Structured logging

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
from btreestore.streaming_cursor import StreamingCursor
from btreestore.ttl import TTLManager, TTLSweeper
from btreestore.backup import BackupManager
from btreestore.events import EventBus
from btreestore.index import IndexManager, Index
from btreestore.compression import CompressionConfig
from btreestore.merge import Rebalancer

__version__ = "4.0.0"
__author__ = "Creative Projects"
__license__ = "MIT"

__all__ = [
    "Store",
    "Transaction",
    "Cursor",
    "StreamingCursor",
    "StoreConfig",
    "WAL",
    "TTLManager",
    "TTLSweeper",
    "BackupManager",
    "EventBus",
    "IndexManager",
    "Index",
    "CompressionConfig",
    "Rebalancer",
    "__version__",
]