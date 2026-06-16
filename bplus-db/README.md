# B+ Tree Database Engine

A key-value database engine backed by a B+ tree, with range queries, prefix scans, ACID-like transactions, a Write-Ahead Log, bulk loading, database merge/diff, JSON/binary persistence, and a SQL-like query language — all implemented from scratch in Python.

## How It Works

### B+ Tree

The core data structure is a generic B+ tree with configurable order:

- **Internal nodes** store keys and child pointers for navigation
- **Leaf nodes** store key-value pairs and are linked in a doubly-linked list for efficient range scans
- All operations (insert, delete, search, range) are O(log n)
- Splits and merges are handled automatically during insertions and deletions
- The minimum order is 3 (at least 2 keys per internal node except root)
- **Tree validation** checks all B+ tree invariants
- **Bulk loading** builds the tree efficiently from sorted data
- **Height and leaf count** statistics are available

### Architecture

```
bplus_db/
├── bplus_tree.py    # Core B+ tree (insert, delete, search, range, bulk load, validate, stats)
├── database.py      # Database layer (CRUD, transactions, WAL, persistence, merge/diff, query execution)
├── serializer.py    # Type-aware value serialization (str, int, float, bool, None, list, dict)
├── query_parser.py  # SQL-like query tokenizer and parser
└── cli.py           # Interactive shell and command-line interface
```

## Usage

### Python API

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
results = db.prefix_scan("user:1:")  # All keys starting with "user:1:"

# Keys, values, items
db.keys()    # Sorted list of all keys
db.values()  # All values in key order
db.items()    # All (key, value) pairs

# Transactions (ACID-like)
txn = db.begin_transaction()
txn.put("x", 1)
txn.put("y", 2)
txn.commit()  # All writes applied atomically

txn = db.begin_transaction()
txn.put("z", 3)
txn.rollback()  # Discarded

# Write-Ahead Log for crash recovery
db_wal = Database(order=64, wal_path="/tmp/mydb.wal")
db_wal.put("important", "data")
db_wal.save("/tmp/mydb.json")
# After crash: Database.recover("/tmp/mydb.json", "/tmp/mydb.wal")

# Persistence
db.save("mydb.json")           # JSON format (human-readable)
db2 = Database.load("mydb.json")
db.save_binary("mydb.bin")     # Binary format (compact)
db3 = Database.load_binary("mydb.bin")

# SQL-like query language
db.execute("INSERT INTO db KEY 'hello' VALUE 'world'")
result = db.execute("SELECT * FROM db WHERE key = 'hello'")
result = db.execute("SELECT * FROM db WHERE key >= 'a' AND key <= 'z'")
result = db.execute("COUNT db")
result = db.execute("DELETE FROM db WHERE key = 'hello'")

# Database merge and diff
db1.merge(db2, conflict="theirs")  # Merge db2 into db1
diff = db1.diff(db2)                # Compare databases

# Statistics and introspection
stats = db.stats()    # {total_keys, tree_height, leaf_count, gets, puts, ...}
db.validate()         # Check all B+ tree invariants
db.tree_structure()   # Visualize tree structure

# Bulk loading (efficient for sorted data)
from bplus_db import BPlusTree
tree = BPlusTree(order=16)
tree.bulk_load([(f"k{i:04d}", i) for i in range(10000)])
```

### Command-Line Interface

```bash
# Interactive shell
bplus-db shell

# Open existing database
bplus-db shell -d mydb.json

# Execute a single query
bplus-db execute "SELECT * FROM db WHERE key >= 'a'"

# Inspect a database file
bplus-db load mydb.json

# Validate tree invariants
bplus-db validate mydb.json
```

### Interactive Shell Commands

```
bplus-db> PUT user:1 Alice
bplus-db> GET user:1
  'Alice'
bplus-db> RANGE key0000 key0010
  ('key0000', 0)
  ('key0001', 1)
  ...
bplus-db> PREFIX user:
  ('user:1', 'Alice')
bplus-db> SELECT * FROM db WHERE key >= 'a' AND key <= 'z'
bplus-db> STATS
bplus-db> TREE
bplus-db> VALIDATE
bplus-db> KEYS
bplus-db> SAVE mydb.json
bplus-db> SAVEBIN mydb.bin
bplus-db> QUIT
```

## Supported Query Language

| Query | Description |
|-------|-------------|
| `SELECT * FROM db` | List all entries |
| `SELECT * FROM db WHERE key = 'x'` | Get value for key |
| `SELECT * FROM db WHERE key > 'a'` | Keys greater than 'a' |
| `SELECT * FROM db WHERE key < 'z'` | Keys less than 'z' |
| `SELECT * FROM db WHERE key >= 'a' AND key <= 'z'` | Range query |
| `INSERT INTO db KEY 'x' VALUE 'y'` | Insert key-value pair |
| `DELETE FROM db WHERE key = 'x'` | Delete key |
| `COUNT db` | Count total keys |

## Features

- **B+ Tree** with configurable order (minimum 3), full CRUD, range queries, validation, and bulk loading
- **Type-aware serialization** preserving int, float, bool, None, str, list, dict types
- **ACID-like transactions** with commit/rollback (serialized execution)
- **Write-Ahead Log (WAL)** for crash recovery
- **Batch operations** — `put_many`, `delete_many`
- **Database merge and diff** — merge databases with conflict resolution, compare for differences
- **Keys/values/items** — iterate over all data in sorted order
- **Tree validation** — verify all B+ tree invariants
- **Dual persistence formats** — human-readable JSON and compact binary with version header
- **SQL-like query language** for ad-hoc queries
- **Thread-safe** operations with reentrant locking
- **Interactive shell** with shorthand and SQL commands
- **Comprehensive test suite** (112 tests)