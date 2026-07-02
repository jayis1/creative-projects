# btreestore

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/ci.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 188](https://img.shields.io/badge/tests-188%20passing-brightgreen.svg)](#testing)
[![Version: 3.0.0](https://img.shields.io/badge/version-3.0.0-blue.svg)](#changelog)

> A persistent B+Tree key-value store with MVCC transactions, Write-Ahead Log crash recovery, CRC32 checksums, and cursor-based iteration — pure Python, zero external dependencies.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Configuration](#configuration)
  - [Write-Ahead Log (WAL)](#write-ahead-log-wal)
  - [Compaction](#compaction)
  - [Atomic Increment](#atomic-increment)
- [Architecture](#architecture)
  - [File Layout](#file-layout)
  - [Page Types](#page-types)
  - [Serialization](#serialization)
  - [B+Tree Structure](#btree-structure)
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

`btreestore` is an embedded key-value database that uses a B+Tree as its core data structure. It provides ordered key storage with efficient range scans, MVCC snapshot-isolated transactions, and crash recovery via a Write-Ahead Log — all implemented from scratch in pure Python with zero external dependencies.

## Key Features

- **B+Tree with linked leaves**: Internal nodes route lookups; leaf nodes are doubly-linked for efficient ordered scans.
- **Persistent storage**: Pages are serialized to a single file with a fixed-size header and fixed-size pages.
- **CRC32 page checksums**: Every page stores a CRC32 of its content. On read, the checksum is verified to detect corruption.
- **MVCC transactions**: Each transaction gets a snapshot view. Writes are buffered and applied atomically on commit.
- **Write-Ahead Log (WAL)**: All writes are logged before applying. On startup, the WAL is replayed to recover the last committed state.
- **Context-manager transactions**: `with store.transaction() as txn:` auto-commits on success, auto-rolls-back on exception.
- **Compare-and-swap (CAS)**: Optimistic concurrency with `txn.cas(key, expected, new)`.
- **Range and prefix scans**: Cursor-based iteration with `reverse`, `limit`, `offset`, `seek`, `filter`, `map`, and `batch`.
- **Min/max and contains**: O(log n) lookups via leftmost/rightmost leaf traversal.
- **Atomic increment**: `txn.increment(key, amount)` for counter patterns.
- **Batch operations**: `put_many`, `delete_many`, and `bulk_load` for high-throughput ingestion.
- **Tree compaction**: Rebuild sparse trees to reclaim space from deletions.
- **Binary-safe keys and values**: All data stored as raw bytes; str convenience API handles UTF-8.
- **Free-page list**: Deleted pages are recycled via a free list.
- **Configuration**: JSON, TOML, and environment variable config support.
- **Logging**: Configurable structured logging to file or stderr.
- **CLI tool**: 18-subcommand command-line interface with JSON output format.
- **Installable**: `pip install -e .` with `btreestore` entry point.

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
    store.increment("counter", 5)    # -> 6

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
    # {'file_size': ..., 'page_size': 4096, 'total_pages': ...,
    #  'tree_depth': 2, 'num_keys': 1005, 'wal_enabled': True, ...}

    # Validate tree invariants
    assert store.validate()
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

# Delete a key
btreestore --db mydb.btree del foo

# Count keys
btreestore --db mydb.btree count

# Database statistics (JSON)
btreestore --db mydb.btree stats --format json

# Validate tree structure
btreestore --db mydb.btree validate

# Compact the tree (reclaim space)
btreestore --db mydb.btree compact

# Checkpoint the WAL
btreestore --db mydb.btree checkpoint

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

After many deletions, the tree may become sparse (pages with few keys). Compaction rebuilds the tree:

```python
store.compact()  # Returns number of keys compacted
```

### Atomic Increment

```python
store.put("counter", "0")
store.increment("counter")     # -> 1
store.increment("counter", 5)  # -> 6
store.increment("counter", -2)  # -> 4
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
├── __init__.py       # Public API exports
├── store.py          # Store class — main entry point, page I/O, WAL integration
├── tree.py           # BPlusTree — search, insert, delete, split, validate, compact
├── transaction.py    # Transaction — MVCC, write set, cursor, CAS, increment
├── cursor.py         # Cursor — bidirectional iteration, seek, filter, map, batch
├── pages.py          # Page types, serialization, CRC32, prefix bounds
├── wal.py            # Write-Ahead Log — append, replay, checkpoint
├── config.py         # StoreConfig — JSON/TOML/env config loading
└── logging_util.py   # Logging setup
```

## Examples

The `examples/` directory contains runnable demos:

- **`basic_usage.py`** — Basic put/get, transactions, scans, CAS, increment, persistence
- **`wal_recovery.py`** — Demonstrates WAL crash recovery with simulated crash
- **`bulk_load.py`** — Bulk loading 10K entries, deletion, compaction, performance measurement
- **`config.toml`** — Example TOML configuration file

Run them with:

```bash
cd btree-store
python3 examples/basic_usage.py
python3 examples/wal_recovery.py
python3 examples/bulk_load.py
```

### ASCII Art Demo

```
btreestore > stats
  file_size: 4132
  page_size: 4096
  total_pages: 1
  num_keys: 3
  tree_depth: 0
  wal_enabled: true
  wal_size: 311

btreestore > scan
  foo      bar
  hello    world
  counter  5
  (3 entries)

btreestore > scan --reverse --limit 2
  hello    world
  counter  5
  (2 entries)
```

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ -v --cov=btreestore --cov-report=term-missing

# Run only the new package tests
python3 -m pytest tests/test_btreestore.py -v

# Run only the legacy tests
python3 -m pytest tests/test_btree.py tests/test_bug_hunt.py -v
```

The test suite includes **188 tests** covering:
- Basic operations (put/get/delete/contains)
- B+Tree splitting (500+ keys, random insertion order)
- Persistence (close + reopen, commit_ts persistence)
- Range scans, prefix scans, reverse scans, cursor navigation
- Cursor transformations (filter, map, batch, reduce, take, skip)
- Transactions (commit/rollback, read-only, context manager, isolation)
- CAS (compare-and-swap: update, insert-if-absent, delete-if-matches)
- Atomic increment (positive, negative, non-integer error)
- Min/max
- Batch operations (put_many, delete_many, bulk_load)
- CRC32 integrity verification and corruption detection
- WAL crash recovery (write, simulate crash, reopen, verify)
- Compaction (after deletion, empty tree)
- Configuration (JSON, TOML, env vars, validation)
- Edge cases (empty key, binary keys, large values, oversized rejection)
- Import/export roundtrip

## Roadmap

- [ ] **B+Tree merge/borrow**: Rebalance after deletions to keep pages full
- [ ] **True MVCC snapshots**: Store multiple versions per key for read-only snapshot isolation
- [ ] **Secondary indexes**: Configurable index on value patterns
- [ ] **Iterative cursor**: Streaming cursor that doesn't materialize all results (memory-efficient for large ranges)
- [ ] **Compression**: Optional page-level compression (zlib/lz4)
- [ ] **Encryption**: Optional AES-256 page encryption
- [ ] **Network protocol**: Optional TCP server mode for remote access
- [ ] **Backup/restore**: Snapshot to archive file and restore
- [ ] **Metrics**: Prometheus-compatible metrics export
- [ ] **Replication**: Primary-replica replication for high availability

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and pull request process.

## Changelog

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