# btreestore

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/ci.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 255](https://img.shields.io/badge/tests-255%20passing-brightgreen.svg)](#testing)
[![Version: 4.0.0](https://img.shields.io/badge/version-4.0.0-blue.svg)](#changelog)
[![Dependencies: 0](https://img.shields.io/badge/dependencies-0-success.svg)](#dependencies)

> A persistent B+Tree key-value store with MVCC transactions, self-balancing deletes, Write-Ahead Log crash recovery, CRC32 checksums, TTL key expiration, secondary indexes, backup/restore, streaming cursors, event subscriptions, and optional page compression — pure Python, zero external dependencies.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [Streaming Cursor](#streaming-cursor)
  - [TTL Key Expiration](#ttl-key-expiration)
  - [Secondary Indexes](#secondary-indexes)
  - [Backup & Restore](#backup--restore)
  - [Event Subscriptions](#event-subscriptions)
  - [Page Compression](#page-compression)
  - [CLI](#cli)
  - [Configuration](#configuration)
  - [Write-Ahead Log (WAL)](#write-ahead-log-wal)
  - [Compaction](#compaction)
  - [Atomic Increment](#atomic-increment)
  - [Self-Balancing Deletes](#self-balancing-deletes)
- [Architecture](#architecture)
  - [File Layout](#file-layout)
  - [Page Types](#page-types)
  - [Serialization](#serialization)
  - [B+Tree Structure](#btree-structure)
  - [Rebalancing (Merge/Borrow)](#rebalancing-mergeborrow)
  - [Transactions (MVCC)](#transactions-mvcc)
  - [CRC32 Integrity](#crc32-integrity)
  - [Write-Ahead Log](#write-ahead-log-1)
  - [Page Cache](#page-cache)
  - [Module Structure](#module-structure)
- [Examples](#examples)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [License](#license)

---

## Overview

`btreestore` is an embedded key-value database that uses a B+Tree as its core data structure. It provides ordered key storage with efficient range scans, MVCC snapshot-isolated transactions, self-balancing deletes (merge/borrow), crash recovery via a Write-Ahead Log, TTL key expiration, secondary indexes, backup/restore, streaming cursors, and event subscriptions — all implemented from scratch in pure Python with zero external dependencies.

## Key Features

- **B+Tree with linked leaves**: Internal nodes route lookups; leaf nodes are doubly-linked for efficient ordered scans.
- **Self-balancing deletes**: Automatic rebalancing via key borrowing and page merging after deletions keeps the tree dense — no more sparse pages.
- **Persistent storage**: Pages are serialized to a single file with a fixed-size header and fixed-size pages.
- **CRC32 page checksums**: Every page stores a CRC32 of its content. On read, the checksum is verified to detect corruption.
- **MVCC transactions**: Each transaction gets a snapshot view. Writes are buffered and applied atomically on commit.
- **Write-Ahead Log (WAL)**: All writes are logged before applying. On startup, the WAL is replayed to recover the last committed state.
- **Context-manager transactions**: `with store.transaction() as txn:` auto-commits on success, auto-rolls-back on exception.
- **Compare-and-swap (CAS)**: Optimistic concurrency with `txn.cas(key, expected, new)`.
- **Range and prefix scans**: Cursor-based iteration with `reverse`, `limit`, `offset`, `seek`, `filter`, `map`, and `batch`.
- **Streaming cursor**: Memory-efficient lazy iteration over large ranges — O(1 page) memory instead of O(total entries).
- **TTL key expiration**: Set time-to-live on keys with lazy expiration on read and active background sweep.
- **Secondary indexes**: Build indexes on value fields for efficient multi-field lookups.
- **Backup/restore**: Full backup to CRC32-verified archive files with restore capability.
- **Event subscriptions**: Observer pattern for monitoring put/delete/commit/compact/checkpoint/close events.
- **Page compression**: Optional zlib page-level compression to reduce file size.
- **Min/max and contains**: O(log n) lookups via leftmost/rightmost leaf traversal.
- **Atomic increment**: `txn.increment(key, amount)` for counter patterns.
- **Batch operations**: `put_many`, `delete_many`, and `bulk_load` for high-throughput ingestion.
- **Tree compaction**: Rebuild sparse trees to reclaim space from deletions.
- **Binary-safe keys and values**: All data stored as raw bytes; str convenience API handles UTF-8.
- **Free-page list**: Deleted pages are recycled via a free list.
- **Configuration**: JSON, TOML, and environment variable config support.
- **Logging**: Configurable structured logging to file or stderr.
- **CLI tool**: 23-subcommand command-line interface with JSON output format.
- **Installable**: `pip install -e .` with `btreestore` entry point.
- **Zero dependencies**: Pure Python stdlib only.

## Installation

### From source (development)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/btree-store
pip install -e .
```

### Without installation

```bash
cd creative-projects/btree-store
# The package directory must be in your Python path
export PYTHONPATH=/path/to/btree-store:$PYTHONPATH
```

### Dependencies

- **Python 3.10+**
- No external runtime dependencies (stdlib only)
- Optional: `tomli` for TOML config on Python < 3.11
- Dev: `pytest`, `pytest-cov`

## Quick Start

```python
from btreestore import Store

with Store("mydb.btree") as store:
    store.put("hello", "world")
    assert store.get("hello") == b"world"
    assert "hello" in store

    # Transaction
    with store.transaction() as txn:
        txn.put("key1", "val1")
        txn.put("key2", "val2")
    # Auto-committed

    # Scan
    for key, value in store.cursor():
        print(key, value)

    # Prefix scan
    for key, value in store.prefix("key"):
        print(key, value)

    # Stats
    print(store.stats())
```

## Usage

### Python API

```python
from btreestore import Store

# Open or create a store
with Store("mydb.btree") as store:
    # Autocommit convenience methods
    store.put("hello", "world")
    store.put("foo", "bar")
    assert store.get("hello") == b"world"
    assert "hello" in store  # __contains__

    # Min/max
    print(store.min())  # (b'foo', b'bar')
    print(store.max())  # (b'hello', b'world')

    # Compare-and-swap
    assert store.cas("hello", "world", "universe")  # update if matches
    assert not store.cas("hello", "world", "x")     # fails: expected mismatch
    assert store.cas("new_key", None, "val")        # insert-if-absent
    assert store.cas("new_key", "val", None)        # delete-if-matches

    # Atomic increment
    store.put("counter", "0")
    store.increment("counter")      # -> 1
    store.increment("counter", 5)   # -> 6

    # Context-manager transaction
    with store.transaction() as txn:
        txn.put("key1", "val1")
        txn.put("key2", "val2")
        txn.delete("foo")
    # Auto-committed here

    # Range scan with limit/offset/reverse
    for key, value in store.cursor(low="a", high="z", limit=10, offset=5):
        print(key, value)

    # Reverse scan
    for key, value in store.cursor(reverse=True, limit=5):
        print(key, value)

    # Prefix scan
    for key, value in store.prefix("key"):
        print(key, value)

    # Cursor navigation
    c = store.cursor()
    c.first()        # first entry
    c.last()         # last entry
    c.next()         # advance forward
    c.prev()         # go backward
    c.seek(b"key")   # binary search to first entry >= key
    c.seek_exact(b"key")  # exact match

    # Cursor transformations
    filtered = c.filter(lambda k, v: len(v) > 10)
    mapped = c.map(lambda k, v: (k, str(len(v)).encode()))
    batches = c.batch(100)  # split into batches of 100
    total = c.reduce(lambda acc, k, v: acc + int(v), 0)

    # Batch operations
    txn = store.begin()
    txn.put_many({"a": "1", "b": "2", "c": "3"})
    txn.delete_many(["old1", "old2"])
    store.commit(txn)

    # Bulk load (single transaction)
    pairs = [(f"item{i:04d}", f"val{i}") for i in range(1000)]
    store.bulk_load(pairs)

    # Compaction (rebuild tree after many deletions)
    store.compact()

    # Stats
    print(store.stats())

    # Validate tree invariants
    assert store.validate()
```

### Streaming Cursor

The `StreamingCursor` reads pages lazily from the B+Tree, using O(1 page) memory instead of materializing all results. Ideal for iterating over millions of entries:

```python
from btreestore import Store, StreamingCursor

with Store("bigdb.btree") as store:
    # Stream all entries — memory stays flat regardless of data size
    for key, value in StreamingCursor(store):
        process(key, value)

    # Stream with range and limit
    for key, value in StreamingCursor(store, low=b"a", high=b"z", limit=1000):
        process(key, value)

    # Reverse streaming
    for key, value in StreamingCursor(store, reverse=True, limit=10):
        print(key, value)
```

### TTL Key Expiration

Set time-to-live on keys. Expired keys are lazily removed on read or actively purged via a background sweep:

```python
from btreestore import Store, TTLManager, TTLSweeper

with Store("mydb.btree") as store:
    ttl = TTLManager(store)

    # Set keys with TTLs
    ttl.put("session:123", "data", ttl_seconds=3600)  # expires in 1 hour
    ttl.put("cache:456", "data", ttl_seconds=60)      # expires in 1 minute
    ttl.put("permanent", "data", ttl_seconds=None)     # no expiration

    # Read (lazy expiration — expired keys return None)
    ttl.get("session:123")  # -> b"data" or None if expired

    # Check remaining TTL
    ttl.ttl("session:123")  # -> 3599.8 (seconds remaining) or None

    # Make a key permanent
    ttl.persist("session:123")  # -> True (TTL removed)

    # Active sweep — delete all expired keys
    expired_count = ttl.sweep_expired()

    # Background sweeper thread
    sweeper = TTLSweeper(ttl, interval=60)  # sweep every 60s
    sweeper.start()
    # ... do work ...
    sweeper.stop()
```

### Secondary Indexes

Build secondary indexes on value fields for efficient multi-field lookups:

```python
from btreestore import Store, IndexManager

with Store("users.btree") as store:
    mgr = IndexManager(store)
    email_idx = mgr.create_index("email")
    city_idx = mgr.create_index("city")

    # Index records
    store.put("user:1", b'{"name":"Alice","email":"alice@x.com","city":"NYC"}')
    email_idx.add("alice@x.com", "user:1")
    city_idx.add("NYC", "user:1")

    # Look up by indexed field
    keys = email_idx.find("alice@x.com")  # -> [b"user:1"]
    keys = city_idx.find("NYC")           # -> [b"user:1", b"user:3", ...]

    # Find first match
    key = email_idx.find_one("alice@x.com")  # -> b"user:1"

    # Range query on index
    for value, primary_keys in email_idx.range(low="a", high="d"):
        print(value, primary_keys)

    # Remove from index
    email_idx.remove("alice@x.com", "user:1")

    # Drop index
    mgr.drop_index("email")
```

### Backup & Restore

Create full backup archives with CRC32 integrity verification:

```python
from btreestore import Store, BackupManager

with Store("mydb.btree") as store:
    bm = BackupManager(store)

    # Create backup
    n = bm.backup("backup.bak")
    print(f"Backed up {n} entries")

    # Verify backup integrity
    assert bm.verify_backup("backup.bak")

    # Backup metadata
    info = bm.backup_info("backup.bak")
    # {'version': 1, 'page_size': 4096, 'num_entries': 1000, ...}

    # Restore to a new store
    n = bm.restore("backup.bak", "restored.btree")
```

### Event Subscriptions

Monitor store operations via the observer pattern:

```python
from btreestore import Store, EventBus

with Store("mydb.btree") as store:
    bus = EventBus(store)

    @bus.on("put")
    def on_put(key, value):
        print(f"PUT: {key} = {value}")

    @bus.on("delete")
    def on_delete(key):
        print(f"DELETE: {key}")

    @bus.on("commit")
    def on_commit(txn_id):
        print(f"COMMIT: txn #{txn_id}")

    store.put("hello", "world")  # triggers on_put + on_commit
    store.delete("hello")        # triggers on_delete + on_commit

    # Unsubscribe
    bus.off("put", on_put)

    # Disable all events
    bus.disable()
```

### Page Compression

Optional zlib compression reduces file size for data with repetition:

```python
from btreestore.compression import CompressionConfig, compress_page, decompress_page

# Configure compression
config = CompressionConfig(level=6, min_size=64, max_ratio=0.9)

# Compress and decompress page content
compressed = compress_page(raw_page_data, config)
decompressed = decompress_page(compressed)
assert decompressed == raw_page_data
```

### CLI

```bash
# Create a database and insert keys
btreestore --db mydb.btree put hello world
btreestore --db mydb.btree put foo bar
btreestore --db mydb.btree put abc def

# Retrieve a key
btreestore --db mydb.btree get hello

# Compare-and-swap (use __NONE__ for absent/null)
btreestore --db mydb.btree cas hello world universe
btreestore --db mydb.btree cas new_key __NONE__ inserted

# Atomic increment
btreestore --db mydb.btree incr counter 5

# Scan all keys in order (TSV format)
btreestore --db mydb.btree scan

# Stream keys (memory-efficient for large datasets)
btreestore --db mydb.btree stream --limit 100

# Scan with JSON output
btreestore --db mydb.btree scan --format json

# Reverse scan with limit
btreestore --db mydb.btree scan --reverse --limit 5

# Range scan with offset
btreestore --db mydb.btree scan --low a --high h --offset 2 --limit 3

# Prefix scan
btreestore --db mydb.btree prefix fo

# Min/max
btreestore --db mydb.btree min
btreestore --db mydb.btree max

# Count keys
btreestore --db mydb.btree count

# Detailed store info
btreestore --db mydb.btree info
btreestore --db mydb.btree info --format json

# Database statistics (JSON)
btreestore --db mydb.btree stats --format json

# Validate tree structure
btreestore --db mydb.btree validate

# Compact the tree (reclaim space)
btreestore --db mydb.btree compact

# Checkpoint the WAL
btreestore --db mydb.btree checkpoint

# Backup and restore
btreestore --db mydb.btree backup backup.bak
btreestore --db mydb.btree backup-info backup.bak
btreestore --db mydb.btree restore backup.bak restored.btree

# Batch import/export from JSON
btreestore --db mydb.btree batch-import data.json
btreestore --db mydb.btree batch-export output.json

# Interactive REPL
btreestore --db mydb.btree interactive

# Use a config file
btreestore --config config.toml --db mydb.btree put hello world

# Disable WAL
btreestore --db mydb.btree --no-wal put hello world

# Enable fsync on every commit (durable)
btreestore --db mydb.btree --sync put hello world
```

### Configuration

Configuration can be provided via a config file (JSON or TOML), environment variables, or programmatically.

**TOML config file** (`config.toml`):

```toml
path = "mydb.btree"
page_size = 4096
branching = 32
cache_size = 512
wal_enabled = true
log_level = "INFO"
auto_checkpoint = true
checkpoint_interval = 100
sync_on_commit = false
```

**JSON config file** (`config.json`):

```json
{
  "page_size": 8192,
  "cache_size": 1024,
  "wal_enabled": false,
  "log_level": "DEBUG"
}
```

**Environment variables** (prefix `BTREESTORE_`):

```bash
export BTREESTORE_PAGE_SIZE=8192
export BTREESTORE_CACHE_SIZE=1024
export BTREESTORE_LOG_LEVEL=DEBUG
```

**Programmatic configuration**:

```python
from btreestore import Store, StoreConfig

config = StoreConfig(
    path="mydb.btree",
    page_size=8192,
    cache_size=1024,
    wal_enabled=True,
    log_level="DEBUG",
    sync_on_commit=True,
)
store = Store("mydb.btree", config=config)
```

### Write-Ahead Log (WAL)

The WAL records all write operations before applying them to the main file. On startup, the WAL is replayed to recover the last committed state.

```python
from btreestore import Store

# WAL is enabled by default
store = Store("mydb.btree")

# If the process crashes, reopening replays the WAL
store2 = Store("mydb.btree")
# All committed data is recovered automatically

# Disable WAL for maximum speed (no crash recovery)
store = Store("mydb.btree", wal_enabled=False)

# Manual checkpoint (flush + truncate WAL)
store.checkpoint()
```

### Compaction

After many deletions, the tree may become sparse. Compaction rebuilds the tree:

```python
store.compact()  # Returns number of keys compacted
```

### Atomic Increment

```python
store.put("counter", "0")
store.increment("counter")      # -> 1
store.increment("counter", 5)   # -> 6
store.increment("counter", -2)  # -> 4
```

### Self-Balancing Deletes

The B+Tree automatically rebalances after deletions by borrowing keys from siblings or merging pages when siblings are too small to share. This keeps pages dense and prevents sparse trees:

```python
with Store("mydb.btree", page_size=512) as store:
    for i in range(500):
        store.put(f"k{i:04d}", f"v{i}")

    # Delete half — tree rebalances automatically
    for i in range(0, 500, 2):
        store.delete(f"k{i:04d}")

    assert store.count() == 250
    assert store.validate()  # Tree still valid and balanced
```

You can disable rebalancing for faster deletions if you plan to compact periodically:

```python
# Direct tree access with rebalance=False
store.tree.delete(key, rebalance=False)
```

## Architecture

### File Layout

```
+------------------+
|     Header       |  36 bytes: magic, version, page_size, root_page_id,
|                  |            next_page_id, free_list_head, commit_ts
+------------------+
|     Page 0       |  page_size bytes (leaf, internal, or free) + CRC32
+------------------+
|     Page 1       |  page_size bytes + CRC32
+------------------+
|     ...          |
+------------------+
|     WAL file     |  <db_path>.wal — Write-Ahead Log
+------------------+
|     Index files  |  <db_path>.idx.<name>.btree — Secondary indexes
+------------------+
```

Each page is `page_size` bytes, with the last 4 bytes reserved for a CRC32 checksum of the preceding content.

### Page Types

- **Leaf pages** store sorted key-value pairs with `prev`/`next` pointers to sibling leaves for O(1) sequential traversal.
- **Internal pages** store separator keys and child page IDs: `child[0], key[0], child[1], ..., key[n-1], child[n]`.
- **Free pages** form a singly-linked free list for page reuse.

### Serialization

Keys and values use LEB128 varint length prefixes followed by raw bytes. Pages are zero-padded to `page_size - 4`, then a CRC32 is appended.

### B+Tree Structure

When a leaf or internal page exceeds 90% of usable capacity (page_size minus CRC), it splits at the median. The right half becomes a new node, and the median key is promoted to the parent. If the root splits, a new root is created. Internal nodes also split when they exceed twice the branching factor.

### Rebalancing (Merge/Borrow)

After a deletion, if a page falls below 25% of usable capacity, the tree rebalances:

1. **Borrow from left sibling**: Move the last key from the left sibling to the underflowing page. Update the parent's separator key.
2. **Borrow from right sibling**: Move the first key from the right sibling to the underflowing page. Update the parent's separator key.
3. **Merge with sibling**: If neither sibling has enough keys to spare, merge the underflowing page with a sibling. Remove the separator key from the parent and free the merged page.
4. **Root collapse**: If the root internal node ends up with only one child, that child becomes the new root, reducing tree height by one.

Rebalancing propagates up the tree: after merging two internal pages, the parent may also underflow and need rebalancing.

### Transactions (MVCC)

- `store.begin()` creates a read-write transaction with a snapshot timestamp.
- `store.begin(read_only=True)` creates a read-only snapshot.
- `store.transaction()` returns a context-managed transaction.
- Writes (`put`/`delete`/`cas`/`increment`) are buffered in the transaction's write set.
- `store.commit(txn)` applies writes in sorted order, bumps the commit timestamp, and flushes all dirty pages.
- `store.rollback(txn)` discards the write set.
- Cursor queries overlay the write set on the tree's current state for read-your-writes semantics.

### CRC32 Integrity

Every page write computes a CRC32 of the page content and stores it in the last 4 bytes. On read, the checksum is verified. All-zero pages (uninitialized) are exempt. A mismatch raises `IOError`.

### Write-Ahead Log

The WAL records all write operations (put/delete) before they are applied to the main B+Tree file. Each record includes a CRC32 for integrity. On startup, the WAL is replayed: operations after the last commit marker are applied to recover the committed state, then the WAL is checkpointed (truncated).

WAL record format:
```
[CRC32 (4 bytes)] [Length (4 bytes)] [Body: op_type + key + value]
```

### Page Cache

An `OrderedDict`-based LRU cache holds up to `cache_size` pages. On eviction, dirty pages are flushed to disk. On commit or close, all dirty pages and the header are flushed.

### Module Structure

```
btreestore/
├── __init__.py          # Public API exports
├── store.py             # Store class — main entry point, page I/O, WAL integration
├── tree.py              # BPlusTree — search, insert, delete, split, validate, compact
├── merge.py             # Rebalancer — merge/borrow for self-balancing deletes
├── transaction.py       # Transaction — MVCC, write set, cursor, CAS, increment
├── cursor.py            # Cursor — bidirectional iteration, seek, filter, map, batch
├── streaming_cursor.py  # StreamingCursor — lazy memory-efficient iteration
├── pages.py             # Page types, serialization, CRC32, prefix bounds
├── wal.py               # Write-Ahead Log — append, replay, checkpoint
├── ttl.py               # TTLManager — key expiration with lazy + active sweep
├── index.py             # IndexManager, Index — secondary indexes
├── backup.py            # BackupManager — backup/restore with CRC32 archives
├── events.py            # EventBus — event subscription system
├── compression.py       # Page-level zlib compression
├── config.py            # StoreConfig — JSON/TOML/env config loading
└── logging_util.py      # Logging setup
```

## Examples

The `examples/` directory contains runnable demos:

- **`basic_usage.py`** — Basic put/get, transactions, scans, CAS, increment, persistence
- **`wal_recovery.py`** — Demonstrates WAL crash recovery with simulated crash
- **`bulk_load.py`** — Bulk loading 10K entries, deletion, compaction, performance measurement
- **`rebalancing.py`** — Self-balancing deletes: insert 500 keys, delete them all, verify tree stays valid
- **`ttl_expiration.py`** — TTL key expiration with lazy deletion and active sweep
- **`backup_restore.py`** — Full backup and restore with integrity verification
- **`secondary_index.py`** — Secondary indexes for multi-field lookups
- **`config.toml`** — Example TOML configuration file

Run them with:

```bash
cd btree-store
python3 examples/basic_usage.py
python3 examples/wal_recovery.py
python3 examples/bulk_load.py
python3 examples/rebalancing.py
python3 examples/ttl_expiration.py
python3 examples/backup_restore.py
python3 examples/secondary_index.py
```

### ASCII Art Demo

```
btreestore > info
btreestore v4.0.0
  path:         /tmp/demo.btree
  file_size:    16,384 bytes
  page_size:    4096
  total_pages:  4
  num_keys:     3
  tree_depth:   1
  cached_pages: 4
  commit_ts:    9
  commit_count: 9
  wal_enabled:  true
  wal_size:     311 bytes

btreestore > scan
  foo      bar
  hello    world
  counter  5
  (3 entries)

btreestore > scan --reverse --limit 2
  hello    world
  counter  5
  (2 entries)

btreestore > stream --limit 3
  foo      bar
  hello    world
  counter  5

btreestore > backup /tmp/backup.bak
Backed up 3 entries to /tmp/backup.bak

btreestore > backup-info /tmp/backup.bak
  version: 1
  page_size: 4096
  num_entries: 3
  incremental: False
  file_size: 142
```

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ -v --cov=btreestore --cov-report=term-missing

# Run only the v4 feature tests
python3 -m pytest tests/test_v4_features.py -v

# Run only the legacy tests
python3 -m pytest tests/test_btree.py tests/test_bug_hunt.py -v
```

The test suite includes **255 tests** covering:
- Basic operations (put/get/delete/contains)
- B+Tree splitting (500+ keys, random insertion order)
- **Self-balancing deletes (merge/borrow, root collapse, interleaved ops)** ← NEW
- Persistence (close + reopen, commit_ts persistence)
- Range scans, prefix scans, reverse scans, cursor navigation
- Cursor transformations (filter, map, batch, reduce, take, skip)
- **Streaming cursor (range, reverse, limit, include_high)** ← NEW
- Transactions (commit/rollback, read-only, context manager, isolation)
- CAS (compare-and-swap: update, insert-if-absent, delete-if-matches)
- Atomic increment (positive, negative, non-integer error)
- Min/max
- Batch operations (put_many, delete_many, bulk_load)
- CRC32 integrity verification and corruption detection
- WAL crash recovery (write, simulate crash, reopen, verify)
- Compaction (after deletion, empty tree)
- **TTL key expiration (lazy, active sweep, background thread, persist)** ← NEW
- **Secondary indexes (add, remove, find, range, count, drop)** ← NEW
- **Backup/restore (roundtrip, verify, corrupt detection, binary data)** ← NEW
- **Event subscriptions (put, delete, commit, compact, off, disable)** ← NEW
- **Page compression (roundtrip, savings, config validation)** ← NEW
- **New CLI commands (info, stream, backup, restore, backup-info)** ← NEW
- Configuration (JSON, TOML, env vars, validation)
- Edge cases (empty key, binary keys, large values, oversized rejection)
- Import/export roundtrip

## Roadmap

- [ ] **True MVCC snapshots**: Store multiple versions per key for read-only snapshot isolation
- [ ] **Compression integration**: Wire page compression into the store's I/O path
- [ ] **Encryption**: Optional AES-256 page encryption
- [ ] **Network protocol**: Optional TCP server mode for remote access
- [ ] **Metrics**: Prometheus-compatible metrics export
- [ ] **Replication**: Primary-replica replication for high availability
- [x] ~~**B+Tree merge/borrow**: Rebalance after deletions to keep pages full~~ ✓ v4.0
- [x] ~~**Iterative cursor**: Streaming cursor that doesn't materialize all results~~ ✓ v4.0
- [x] ~~**Secondary indexes**: Configurable index on value patterns~~ ✓ v4.0
- [x] ~~**Compression**: Optional page-level compression (zlib/lz4)~~ ✓ v4.0 (module ready)
- [x] ~~**Backup/restore**: Snapshot to archive file and restore~~ ✓ v4.0

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and pull request process.

## Changelog

### v4.0.0 (2026-07-02) — Comprehensive Improvement

Major new features and architecture enhancements:

- **Self-balancing deletes (merge/borrow)**: B+Tree now automatically rebalances after deletions by borrowing from siblings or merging pages, with root collapse when the root has one child. Eliminates sparse pages without needing compaction.
- **TTL key expiration**: `TTLManager` with lazy expiration on read, active sweep, background sweeper thread, `ttl()`, `persist()`, `expire_at()`.
- **Streaming cursor**: `StreamingCursor` for O(1 page) memory iteration over large ranges, with forward/reverse, range bounds, and limit support.
- **Secondary indexes**: `IndexManager` and `Index` for building indexes on value fields with add/remove/find/range/count/drop operations.
- **Backup/restore**: `BackupManager` with full backup to CRC32-verified archives, verify, info, and restore to new store.
- **Event subscriptions**: `EventBus` with observer pattern for put/delete/commit/compact/checkpoint/close events, with on/off/enable/disable.
- **Page compression**: `CompressionConfig` with zlib compression, configurable level, min size, and max ratio.
- **5 new CLI subcommands**: `backup`, `restore`, `backup-info`, `stream`, `info` (total 23 subcommands).
- **4 new example scripts**: `rebalancing.py`, `ttl_expiration.py`, `backup_restore.py`, `secondary_index.py`.
- **67 new tests**: Total 255 tests covering all new features.
- **Updated CI**: Now tests all new CLI commands in smoke test.
- **Improved README**: New sections for all features, updated badges, expanded testing section.

### v3.0.0 (2026-07-02) — Comprehensive Improvement

Major restructuring and new features:

- **Package structure**: Split monolithic `btree.py` into modular `btreestore/` package (store, tree, transaction, cursor, pages, wal, config, logging)
- **Write-Ahead Log (WAL)**: Crash recovery via WAL replay with CRC32-verified records
- **Tree compaction**: Rebuild sparse trees to reclaim space from deletions
- **Atomic increment**: `txn.increment(key, amount)` for counter patterns
- **Configuration system**: JSON, TOML, and environment variable config loading with validation
- **Logging**: Configurable structured logging to file or stderr
- **Enhanced cursor**: `filter()`, `map()`, `batch()`, `reduce()`, `take()`, `skip()`, `min_key()`, `max_key()`, `as_dict()`
- **Enhanced CLI**: 18 subcommands (added `compact`, `checkpoint`, `incr`, `--format json`, `--config`, `--no-wal`, `--sync`, `--log-level`, `--log-file`)
- **Installable**: `pyproject.toml` with `btreestore` entry point
- **CI**: GitHub Actions workflow testing Python 3.10/3.11/3.12
- **Examples**: `basic_usage.py`, `wal_recovery.py`, `bulk_load.py`, `config.toml`
- **99 new tests**: Total 188 tests covering all new features
- **CONTRIBUTING.md** and **MIT LICENSE** added
- **Dramatically improved README**: Badges, TOC, architecture, roadmap, changelog

### v2.0.0 — Enhanced

- CRC32 page checksums
- CAS (compare-and-swap)
- Reverse/limit/offset cursors
- Min/max
- Batch operations (put_many, delete_many, bulk_load)
- Enhanced stats
- Expanded CLI to 15 subcommands

### v1.0.0 — Initial Release

- B+Tree with linked leaves
- MVCC transactions
- Persistence
- Range/prefix scans
- Cursor iteration

## Known Issues (Resolved)

The following bugs were identified during development and fixed:

1. **Header/page struct overflow with -1 sentinel** (Phase 1): Unsigned `I` format couldn't store `-1` used as "no page" sentinel. Fixed by using signed `i` format for all page-ID fields.

2. **File mode `r+b` on first create** (Phase 1): `_flush_header` and `_flush_page` opened with `r+b` which fails if the file doesn't exist. Fixed by checking `os.path.exists()` and using `w+b` for new files.

3. **LeafPage constructor keyword mismatch** (Phase 1): Used wrong keyword `next` (shadows builtin); constructor parameter is `next_id`. Fixed.

4. **Reverse cursor with limit returns wrong entries** (Phase 3): `cursor(reverse=True, limit=5)` applied limit before reversing. Fixed by applying offset before reverse, and limit after reverse.

5. **Empty prefix scan returns no results** (Phase 3): `prefix('')` computed `high=b'\x00'` which excluded all keys. Fixed by returning `None` for the upper bound when prefix is empty.

6. **All-0xFF prefix scan excludes longer keys** (Phase 3): `_prefix_upper_bound(b'\xff\xff')` returned `b'\xff\xff\x00'` which is less than `\xff\xff\xff`. Fixed by returning `None` (no upper bound) when all prefix bytes are `0xFF`.

7. **Oversized values crash during page serialization** (Phase 3): No early validation; deep `ValueError` in `_finalize_page`. Fixed by checking key+value size in `insert()` with clear error message.

8. **`commit_ts` not persisted on in-place updates** (Phase 3): `_dirty_header` was False when no new pages allocated. Fixed by setting `_dirty_header = True` in `commit()`.

9. **CRC corruption test false negative** (Phase 3): Test wrote `0xFF` to a byte that was already `0xFF`. Fixed the test to choose a byte value that differs from the original.

## License

MIT License — see [LICENSE](LICENSE).