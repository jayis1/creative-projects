# 🔖 bplus-db

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 110](https://img.shields.io/badge/tests-110%20passing-brightgreen.svg)]()

A **high-performance key-value database engine** backed by a B+ tree — with range queries, prefix scans, TTL expiration, LRU read cache, ACID-like transactions, a Write-Ahead Log, bulk loading, database merge/diff, CSV/JSONL/Pickle import/export, and a SQL-like query language — all implemented from scratch in pure Python.

## ✨ Features

| Category | Features |
|----------|----------|
| **Core** | Configurable B+ tree (order ≥ 3), full CRUD, O(log n) operations |
| **Queries** | Range queries, prefix scans, cursor-based pagination |
| **TTL** | Per-key time-to-live with lazy eviction and eager cleanup |
| **Cache** | Optional LRU read-through cache with hit/miss statistics |
| **Transactions** | ACID-like commit/rollback with serialized execution |
| **Durability** | Write-Ahead Log (WAL) for crash recovery |
| **Persistence** | Human-readable JSON and compact binary formats |
| **Import/Export** | CSV, JSON Lines, Python Pickle |
| **Query Language** | SQL-like SELECT/INSERT/DELETE/COUNT |
| **Introspection** | Tree validation, stats, structure visualization |
| **Merge & Diff** | Merge databases with conflict resolution; compare differences |
| **Config** | JSON/TOML config files for all settings |
| **CLI** | Interactive shell and one-shot command execution |
| **Thread-safe** | Reentrant locking for concurrent access |

## 📦 Installation

```bash
# Clone and install in development mode
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/bplus-db
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 🚀 Quick Start

```python
from bplus_db import Database

db = Database(order=64)

# Basic CRUD
db.put("user:1", {"name": "Alice", "age": 30})
db.put("user:2", {"name": "Bob", "age": 25})
value = db.get("user:1")      # {"name": "Alice", "age": 30}
db.delete("user:2")
print("user:1" in db)         # True

# Batch operations
db.put_many({"k1": "v1", "k2": "v2", "k3": "v3"})
db.delete_many(["k1", "k3"])

# Range queries
for i in range(100):
    db.put(f"key{i:04d}", i)
results = db.range_query("key0020", "key0050")  # 31 results

# Prefix scans
results = db.prefix_scan("user:")

# TTL — keys expire automatically
db.put("session:abc", {"token": "..."}, ttl=3600)  # expires in 1 hour
remaining = db.get_ttl("session:abc")               # ~3600 seconds
db.cleanup_expired()                                 # eagerly remove expired

# LRU cache for read-heavy workloads
from bplus_db import DatabaseConfig, CacheConfig, TreeConfig
config = DatabaseConfig(
    tree=TreeConfig(order=64),
    cache=CacheConfig(enabled=True, max_size=256),
)
db_cached = Database(config=config)
db_cached.put("hot_key", "value")
_ = db_cached.get("hot_key")  # cache hit on second access
print(db_cached.cache_stats())  # {'cache_size': 1, 'hits': 1, 'misses': 1, ...}
```

## 📖 Architecture

```
bplus_db/
├── __init__.py       # Package exports & version
├── bplus_tree.py     # Core B+ tree (insert, delete, search, range, bulk load, validate)
├── database.py       # Database layer (CRUD, TTL, cache, transactions, WAL, merge/diff)
├── serializer.py     # Type-aware value serialization (str, int, float, bool, None, list, dict)
├── query_parser.py   # SQL-like query tokenizer and parser
├── cache.py          # LRU read-through cache with statistics
├── config.py         # Configuration management (dataclasses + JSON/TOML)
├── cursor.py         # Cursor-based pagination
├── ttl.py            # Key-level TTL/expiration manager
├── io.py             # Import/export (CSV, JSONL, Pickle)
└── cli.py            # Interactive shell and command-line interface
```

### Data Flow

```
                   ┌──────────┐
  Client ─────────►│ Database │◄──── Config (JSON/TOML)
                   └────┬─────┘
                        │
              ┌─────────┼──────────┐
              ▼         ▼          ▼
         ┌────────┐ ┌──────┐ ┌────────┐
         │LRUCache│ │ TTL  │ │  WAL   │
         └────┬───┘ └──┬───┘ └────┬───┘
              │        │         │
              ▼        ▼         ▼
         ┌─────────────────────────────┐
         │        B+ Tree Core        │
         └─────────────┬──────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
        ┌──────────┐    ┌──────────┐
        │ Serializer│    │Persistence│
        └──────────┘    │ JSON/Bin  │
                        └──────────┘
```

## 📚 API Reference

### Database Operations

| Method | Description |
|--------|-------------|
| `db.put(key, value, ttl=None)` | Insert or update a key-value pair |
| `db.get(key, default=None)` | Retrieve value, with optional default |
| `db.delete(key)` | Delete a key, returns `True` if found |
| `db.contains(key)` | Check if key exists (skips expired) |
| `db.put_many(items)` | Batch insert |
| `db.delete_many(keys)` | Batch delete |
| `db.range_query(start, end)` | Range scan `[start, end]` |
| `db.prefix_scan(prefix)` | All keys starting with prefix |
| `db.keys()` | Sorted list of all keys |
| `db.values()` | All values in key order |
| `db.items()` | All (key, value) pairs |

### TTL (Time-To-Live)

| Method | Description |
|--------|-------------|
| `db.put(key, value, ttl=60.0)` | Store with expiration in seconds |
| `db.set_ttl(key, seconds)` | Set TTL on existing key |
| `db.get_ttl(key)` | Get remaining TTL, or `None` |
| `db.cleanup_expired()` | Eagerly remove all expired keys |

### Transactions & WAL

| Method | Description |
|--------|-------------|
| `db.begin_transaction()` | Start a transaction |
| `txn.put(key, value)` | Queue insert |
| `txn.delete(key)` | Queue delete |
| `txn.commit()` | Apply all operations |
| `txn.rollback()` | Discard all operations |
| `Database.recover(db_path, wal_path)` | Recover from snapshot + WAL |

### Persistence & Import/Export

| Method | Description |
|--------|-------------|
| `db.save(path)` | Save as JSON (atomic write) |
| `Database.load(path)` | Load from JSON |
| `db.save_binary(path)` | Save in compact binary |
| `Database.load_binary(path)` | Load from binary |
| `io.export_csv(db, path)` | Export to CSV |
| `io.import_csv(db, path)` | Import from CSV |
| `io.export_json_lines(db, path)` | Export as JSONL |
| `io.import_json_lines(db, path)` | Import from JSONL |
| `io.export_pickle(db, path)` | Export as Python pickle |
| `io.import_pickle(db, path)` | Import from pickle |

### Configuration

```python
from bplus_db import DatabaseConfig, TreeConfig, CacheConfig

config = DatabaseConfig(
    tree=TreeConfig(order=64),
    cache=CacheConfig(enabled=True, max_size=256),
    wal=WALConfig(enabled=True, path="/tmp/mydb.wal"),
)
db = Database(config=config)
```

Config can be loaded from JSON or TOML files:

```python
config = DatabaseConfig.from_json("config.json")
# or
config = DatabaseConfig.from_toml("config.toml")  # Python 3.11+
```

### Cursor Pagination

```python
cursor = db.cursor(prefix="user:", page_size=50)
while not cursor.exhausted:
    page = cursor.fetch_page()
    for key, value in page:
        process(key, value)

# Or iterate directly
for key, value in db.cursor(start_key="a", end_key="z", page_size=100):
    print(key, value)
```

### Merge & Diff

```python
db1.merge(db2, conflict="theirs")  # Overwrite conflicts with db2's values
db1.merge(db2, conflict="ours")    # Keep our values on conflicts
db1.merge(db2, conflict="error")   # Raise on conflicts

diff = db1.diff(db2)
# {'only_in_self': [...], 'only_in_other': [...], 'changed': [...], 'unchanged': [...]}
```

## 💻 CLI Usage

```bash
# Interactive shell
bplus-db shell

# Open existing database
bplus-db shell -d mydb.json

# With LRU cache
bplus-db shell --cache 256

# Execute a single query
bplus-db execute "SELECT * FROM db WHERE key >= 'a'"

# Inspect a database file
bplus-db load mydb.json

# Validate tree invariants
bplus-db validate mydb.json

# Export to CSV/JSONL/Pickle
bplus-db export mydb.json output.csv
bplus-db export mydb.json data.jsonl
bplus-db export mydb.json backup.pkl

# Import from CSV/JSONL/Pickle
bplus-db import mydb.json input.csv
```

### Interactive Shell

```
bplus-db> PUT user:1 {"name": "Alice"}
OK
bplus-db> GET user:1
  {'name': 'Alice'}
bplus-db> RANGE key0000 key0010
  ('key0000', 0)
  ('key0001', 1)
  ...
bplus-db> PREFIX user:
  ('user:1', "{'name': 'Alice'}")
bplus-db> TTL user:1 3600
TTL set: 'user:1' expires in 3600.0s
bplus-db> STATS
  total_keys: 150
  tree_height: 3
  cache: {'cache_size': 12, 'hits': 45, ...}
bplus-db> VALIDATE
Tree is valid. No violations found.
bplus-db> SAVE mydb.json
Saved.
bplus-db> QUIT
Bye!
```

### SQL-like Query Language

| Query | Description |
|-------|-------------|
| `SELECT * FROM db` | List all entries |
| `SELECT * FROM db WHERE key = 'x'` | Get value for key |
| `SELECT * FROM db WHERE key > 'a'` | Keys greater than 'a' |
| `SELECT * FROM db WHERE key >= 'a' AND key <= 'z'` | Range query |
| `INSERT INTO db KEY 'x' VALUE 'y'` | Insert key-value pair |
| `DELETE FROM db WHERE key = 'x'` | Delete key |
| `COUNT db` | Count total keys |

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=bplus_db --cov-report=term-missing

# Run specific test class
pytest tests/test_bplus_db.py::TestLRUCache -v
pytest tests/test_bplus_db.py::TestDatabaseTTL -v
```

**110 tests** covering:
- B+ tree operations (insert, delete, range queries, bulk load, validation)
- LRU cache (eviction, hit/miss tracking, invalidation)
- Database core (CRUD, transactions, persistence, merge/diff)
- TTL (lazy eviction, cleanup, serialization)
- Config (JSON/TOML loading, defaults)
- Cursor pagination
- Import/Export (CSV, JSONL, Pickle)
- Query parser
- Concurrency (thread safety)

## 📝 Changelog

### v3.0.0 — Comprehensive Improvement

- **LRU Read Cache**: Optional read-through cache with configurable size, hit/miss statistics, and automatic invalidation on writes
- **Key TTL**: Per-key time-to-live with lazy eviction on read and eager `cleanup_expired()`
- **Cursor Pagination**: Page through large result sets efficiently
- **Configuration System**: `DatabaseConfig` dataclass with JSON/TOML file loading
- **Structured Logging**: Integrated `logging` module with configurable level and format
- **Import/Export**: CSV, JSON Lines, and Python Pickle formats
- **Enhanced CLI**: TTL commands, cache stats, cursor pagination, import/export, config file support
- **Expanded Test Suite**: 110 tests (was 118, consolidated + new)
- **Architecture**: Modular package structure (cache.py, config.py, cursor.py, ttl.py, io.py)
- **Type Hints**: Full type annotations on all new modules
- **GitHub Actions CI**: Multi-Python-version CI pipeline
- **LICENSE**: MIT license
- **CONTRIBUTING.md**: Contribution guidelines
- **Examples**: 3 runnable example scripts

### v2.0.0 — Bug Hunt & Hardening

- Fixed bulk_load underflow for certain order/size combinations
- Fixed `search()` None ambiguity with `_NOT_FOUND` sentinel
- Fixed `Database.get()` for stored None values
- Fixed `merge()` None conflict
- Removed dead `key_func` parameter
- Fixed internal node separator key indexing
- Fixed bulk load internal node construction
- Fixed query parser regex inline flag

### v1.0.0 — Initial Release

- B+ tree with configurable order
- Database layer with CRUD, range queries, prefix scans
- Type-aware serializer
- SQL-like query language
- WAL for crash recovery
- ACID-like transactions
- JSON and binary persistence
- Interactive shell

## 🛣️ Roadmap

- [ ] **Snapshot isolation** — Multiple concurrent readers with consistent views
- [ ] **Secondary indexes** — Index on value fields for fast lookups
- [ ] **Async I/O** — Non-blocking persistence operations
- [ ] **Compression** — Snappy/zstd compression for persistence
- [ ] **Network server** — TCP/HTTP API for remote access
- [ ] **Python async API** — `async/await` interface
- [ ] **Mmap storage** — Memory-mapped file backend for large datasets
- [ ] **LSM mode** — Log-structured merge-tree as alternative backend
- [ ] **Replication** — Primary/replica sync protocol

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and pull request guidelines.