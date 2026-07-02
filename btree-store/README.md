# btree-store

A persistent B+Tree key-value store with MVCC snapshot-isolated transactions, ordered range scans, prefix queries, and cursor-based iteration — all implemented from scratch in pure Python with zero external dependencies.

## Overview

`btree-store` is a single-file embedded key-value database that uses a B+Tree as its core data structure. It provides:

- **B+Tree with linked leaves**: internal nodes route lookups; leaf nodes are doubly-linked for efficient ordered scans without climbing the tree.
- **Persistent storage**: pages are serialized to a single file with a fixed-size header and fixed-size pages. An LRU cache keeps hot pages in memory and evicts dirty pages to disk.
- **MVCC transactions**: each transaction gets a snapshot view. Writes are buffered in a write set and applied atomically on commit. Readers never block writers.
- **Range and prefix scans**: cursor-based iteration with optional lower/upper bounds. Prefix scans efficiently find all keys sharing a byte-level prefix.
- **Binary-safe keys and values**: all data is stored as raw bytes; a str convenience API handles UTF-8 encoding.
- **Free-page list**: deleted pages are recycled via a free list to avoid unbounded file growth.
- **Tree validation**: structural invariant checker for testing and debugging.
- **CLI tool**: full-featured command-line interface for put/get/delete/scan/prefix/count/stats/validate/batch-import/batch-export/interactive.

## How It Works

### File Layout

```
+------------------+
|     Header       |  36 bytes: magic, version, page_size, root_page_id,
|                  |            next_page_id, free_list_head, commit_ts
+------------------+
|     Page 0       |  page_size bytes (leaf, internal, or free)
+------------------+
|     Page 1       |  page_size bytes
+------------------+
|     ...          |
+------------------+
```

### Page Types

- **Leaf pages** store sorted key-value pairs with `prev`/`next` pointers to sibling leaves for O(1) sequential traversal.
- **Internal pages** store separator keys and child page IDs in a classic B+Tree layout: `child[0], key[0], child[1], key[1], ..., key[n-1], child[n]`.
- **Free pages** form a singly-linked free list for page reuse.

### Serialization

Keys and values use LEB128 varint length prefixes followed by raw bytes, enabling compact storage of variable-length binary data. Pages are zero-padded to `page_size`.

### Splitting

When a leaf page exceeds 90% of `page_size`, it splits at the median key. The right half becomes a new leaf, and the median key is promoted to the parent internal node. If the root splits, a new root internal node is created. Internal nodes split similarly when they exceed 90% of `page_size` or twice the branching factor.

### Transactions

- `store.begin()` creates a read-write transaction with a snapshot timestamp.
- `store.begin(read_only=True)` creates a read-only snapshot.
- Writes (`put`/`delete`) are buffered in the transaction's write set.
- `store.commit(txn)` applies writes in sorted order, bumps the commit timestamp, and flushes all dirty pages.
- `store.rollback(txn)` discards the write set.
- Cursor queries overlay the write set on the tree's current state for read-your-writes semantics.

### Page Cache

An `OrderedDict`-based LRU cache holds up to `cache_size` pages. On eviction, dirty pages are flushed to disk. On commit, all dirty pages and the header are flushed.

## Usage

### Python API

```python
from btree import Store

# Open or create a store
with Store("mydb.btree") as store:
    # Autocommit convenience methods
    store.put("hello", "world")
    store.put("foo", "bar")
    assert store.get("hello") == b"world"

    # Explicit transaction
    txn = store.begin()
    txn.put("key1", "val1")
    txn.put("key2", "val2")
    txn.delete("foo")
    store.commit(txn)

    # Range scan (inclusive low, exclusive high)
    for key, value in store.cursor(low="a", high="z"):
        print(key, value)

    # Prefix scan
    for key, value in store.prefix("key"):
        print(key, value)

    # Stats
    print(store.stats())
    # {'file_size': ..., 'page_size': 4096, 'total_pages': ..., 'num_keys': ...}

    # Validate tree invariants
    assert store.validate()
```

### CLI

```bash
# Create a database and insert keys
python3 cli.py --db mydb.btree put hello world
python3 cli.py --db mydb.btree put foo bar
python3 cli.py --db mydb.btree put abc def

# Retrieve a key
python3 cli.py --db mydb.btree get hello
# Output: world

# Scan all keys in order
python3 cli.py --db mydb.btree scan
# Output:
#   abc     def
#   foo     bar
#   hello   world

# Range scan with bounds
python3 cli.py --db mydb.btree scan --low a --high h

# Prefix scan
python3 cli.py --db mydb.btree prefix fo

# Delete a key
python3 cli.py --db mydb.btree del foo

# Count keys
python3 cli.py --db mydb.btree count

# Database statistics
python3 cli.py --db mydb.btree stats

# Validate tree structure
python3 cli.py --db mydb.btree validate

# Batch import/export from JSON
python3 cli.py --db mydb.btree batch-import data.json
python3 cli.py --db mydb.btree batch-export output.json

# Interactive REPL
python3 cli.py --db mydb.btree interactive
```

### JSON Import/Export Format

```json
{
  "key1": "value1",
  "key2": "value2",
  "key3": "value3"
}
```

Binary keys/values that cannot be decoded as UTF-8 are exported as hex strings.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `page_size` | 4096 | Size of each page in bytes |
| `branching` | 32 | Target max children per internal node |
| `cache_size` | 512 | Max pages kept in LRU cache |

## Files

- `btree.py` — Core implementation: pages, serialization, B+Tree, transactions, store
- `cli.py` — Command-line interface with 11 subcommands
- `tests/test_btree.py` — Comprehensive test suite