# B+ Tree Database Engine

A key-value database engine backed by a B+ tree, with range queries, prefix scans, ACID-like transactions, JSON/binary persistence, and a SQL-like query language — all implemented from scratch in Python.

## How It Works

### B+ Tree

The core data structure is a generic B+ tree with configurable order:

- **Internal nodes** store keys and child pointers for navigation
- **Leaf nodes** store key-value pairs and are linked in a doubly-linked list for efficient range scans
- All operations (insert, delete, search, range) are O(log n)
- Splits and merges are handled automatically during insertions and deletions
- The minimum order is 3 (at least 2 keys per internal node except root)

### Architecture

```
bplus_db/
├── bplus_tree.py    # Core B+ tree implementation (insert, delete, search, range)
├── database.py      # Database layer (CRUD, transactions, persistence, query execution)
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

# Range queries
for i in range(100):
    db.put(f"key{i:04d}", i)
results = db.range_query("key0020", "key0050")  # 31 results

# Prefix scans
db.put("user:1:name", "Alice")
db.put("user:1:age", 30)
db.put("user:2:name", "Bob")
results = db.prefix_scan("user:1:")  # [("user:1:age", 30), ("user:1:name", "Alice")]

# Transactions
txn = db.begin_transaction()
txn.put("x", 1)
txn.put("y", 2)
txn.commit()  # All writes applied atomically

# Persistence
db.save("mydb.json")
db2 = Database.load("mydb.json")
db.save_binary("mydb.bin")
db3 = Database.load_binary("mydb.bin")

# SQL-like query language
db.execute("INSERT INTO db KEY 'hello' VALUE 'world'")
result = db.execute("SELECT * FROM db WHERE key = 'hello'")
result = db.execute("SELECT * FROM db WHERE key >= 'a' AND key <= 'z'")
result = db.execute("COUNT db")
result = db.execute("DELETE FROM db WHERE key = 'hello'")

# Statistics
stats = db.stats()
# {'total_keys': 100, 'tree_order': 64, 'gets': 5, ...}

# Tree visualization
print(db.tree_structure())
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
bplus-db> SAVE mydb.json
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

- **B+ Tree** with configurable order (minimum 3), supports insert, delete, search, range queries
- **Type-aware serialization** preserving int, float, bool, None, str, list, dict types
- **ACID-like transactions** with commit/rollback (serialized execution)
- **Dual persistence formats**: human-readable JSON and compact binary
- **SQL-like query language** for ad-hoc queries
- **Thread-safe** operations with reentrant locking
- **Interactive shell** with shorthand and SQL commands
- **Tree visualization** for debugging and introspection
- **Comprehensive test suite** (70 tests)