# btree-store

A persistent B+Tree key-value store with MVCC snapshot-isolated transactions, ordered range scans, prefix queries, cursor-based iteration with reverse/limit/offset, compare-and-swap, and per-page CRC32 checksums — all implemented from scratch in pure Python with zero external dependencies.

## Overview

`btree-store` is a single-file embedded key-value database that uses a B+Tree as its core data structure. It provides:

- **B+Tree with linked leaves**: internal nodes route lookups; leaf nodes are doubly-linked for efficient ordered scans without climbing the tree.
- **Persistent storage**: pages are serialized to a single file with a fixed-size header and fixed-size pages. An LRU cache keeps hot pages in memory and evicts dirty pages to disk.
- **CRC32 page checksums**: every page stores a CRC32 of its content in the last 4 bytes. On read, the checksum is verified to detect file corruption.
- **MVCC transactions**: each transaction gets a snapshot view. Writes are buffered in a write set and applied atomically on commit. Readers never block writers.
- **Context-manager transactions**: `with store.transaction() as txn:` auto-commits on success and auto-rolls-back on exception.
- **Compare-and-swap (CAS)**: optimistic concurrency with `txn.cas(key, expected, new)` — insert-if-absent, update-if-matches, delete-if-matches.
- **Range and prefix scans**: cursor-based iteration with optional lower/upper bounds, `include_high`, `reverse`, `limit`, and `offset` for pagination.
- **Min/max and contains**: O(log n) min/max lookups via leftmost/rightmost leaf traversal.
- **Batch operations**: `put_many`, `delete_many`, and `bulk_load` for high-throughput ingestion.
- **Binary-safe keys and values**: all data is stored as raw bytes; a str convenience API handles UTF-8 encoding.
- **Free-page list**: deleted pages are recycled via a free list to avoid unbounded file growth.
- **Tree validation**: structural invariant checker for testing and debugging (key ordering, parent-child consistency, range bounds).
- **Enhanced statistics**: file size, page counts (leaf/internal/free), tree depth, commit timestamp, transaction counter.
- **CLI tool**: 15-subcommand command-line interface for put/get/del/cas/scan/prefix/count/min/max/stats/validate/batch-import/batch-export/interactive.

## How It Works

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
```

Each page is `page_size` bytes, with the last 4 bytes reserved for a CRC32 checksum of the preceding content.

### Page Types

- **Leaf pages** store sorted key-value pairs with `prev`/`next` pointers to sibling leaves for O(1) sequential traversal.
- **Internal pages** store separator keys and child page IDs: `child[0], key[0], child[1], ..., key[n-1], child[n]`.
- **Free pages** form a singly-linked free list for page reuse.

### Serialization

Keys and values use LEB128 varint length prefixes followed by raw bytes. Pages are zero-padded to `page_size - 4`, then a CRC32 is appended.

### Splitting

When a leaf or internal page exceeds 90% of usable capacity (page_size minus CRC), it splits at the median. The right half becomes a new node, and the median key is promoted to the parent. If the root splits, a new root is created. Internal nodes also split when they exceed twice the branching factor.

### Transactions

- `store.begin()` creates a read-write transaction with a snapshot timestamp.
- `store.begin(read_only=True)` creates a read-only snapshot.
- `store.transaction()` returns a context-managed transaction.
- Writes (`put`/`delete`/`cas`) are buffered in the transaction's write set.
- `store.commit(txn)` applies writes in sorted order, bumps the commit timestamp, and flushes all dirty pages.
- `store.rollback(txn)` discards the write set.
- Cursor queries overlay the write set on the tree's current state for read-your-writes semantics.
- `txn.count()` computes the logical count by adjusting the tree count for inserts and tombstones.

### CRC32 Integrity

Every page write computes a CRC32 of the page content and stores it in the last 4 bytes. On read, the checksum is verified. All-zero pages (uninitialized) are exempt. A mismatch raises `IOError`.

### Page Cache

An `OrderedDict`-based LRU cache holds up to `cache_size` pages. On eviction, dirty pages are flushed to disk. On commit or close, all dirty pages and the header are flushed.

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
    assert "hello" in store  # __contains__

    # Min/max
    print(store.min())  # (b'foo', b'bar')
    print(store.max())  # (b'hello', b'world')

    # Compare-and-swap
    assert store.cas("hello", "world", "universe")  # update if matches
    assert not store.cas("hello", "world", "x")     # fails: expected mismatch
    assert store.cas("new_key", None, "val")        # insert-if-absent
    assert store.cas("new_key", "val", None)        # delete-if-matches

    # Context-manager transaction (auto-commit/rollback)
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

    # Batch operations
    txn = store.begin()
    txn.put_many({"a": "1", "b": "2", "c": "3"})
    txn.delete_many(["old1", "old2"])
    store.commit(txn)

    # Bulk load (single transaction)
    pairs = [(f"item{i:04d}", f"val{i}") for i in range(1000)]
    store.bulk_load(pairs)

    # Stats with tree depth
    print(store.stats())
    # {'file_size': ..., 'page_size': 4096, 'total_pages': ...,
    #  'tree_depth': 2, 'num_keys': 1005, ...}

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

# Compare-and-swap (use __NONE__ for absent/null)
python3 cli.py --db mydb.btree cas hello world universe
python3 cli.py --db mydb.btree cas new_key __NONE__ inserted

# Scan all keys in order
python3 cli.py --db mydb.btree scan

# Reverse scan with limit
python3 cli.py --db mydb.btree scan --reverse --limit 5

# Range scan with offset
python3 cli.py --db mydb.btree scan --low a --high h --offset 2 --limit 3

# Prefix scan
python3 cli.py --db mydb.btree prefix fo

# Min/max
python3 cli.py --db mydb.btree min
python3 cli.py --db mydb.btree max

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
| `page_size` | 4096 | Size of each page in bytes (includes 4-byte CRC) |
| `branching` | 32 | Target max children per internal node |
| `cache_size` | 512 | Max pages kept in LRU cache |

## Files

- `btree.py` — Core implementation: pages, serialization with CRC32, B+Tree, transactions, store
- `cli.py` — Command-line interface with 15 subcommands
- `tests/test_btree.py` — Comprehensive test suite

## Known Issues (Resolved)

See the "Known Issues (Resolved)" section below for bugs found and fixed during development.

## Known Issues (Resolved)

1. **Header/page struct overflow with -1 sentinel**: Unsigned `I` format couldn't store `-1` used as "no page" sentinel for `root_page_id`, `free_list_head`, `prev`, `next`. Fixed by using signed `i` format for all page-ID fields.

2. **File mode `r+b` on first create**: `_flush_header` and `_flush_page` opened with `r+b` which fails if the file doesn't exist yet. Fixed by checking `os.path.exists()` and using `w+b` for new files.

3. **LeafPage constructor keyword**: `LeafPage(new_id, next=leaf.next)` used wrong keyword `next` (shadows builtin); constructor parameter is `next_id`. Fixed to `next_id=leaf.next`.