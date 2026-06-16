#!/usr/bin/env python3
"""Example: Configuration and advanced features.

Demonstrates DatabaseConfig, cursor-based pagination, and the query language.
"""

import tempfile
import os
from bplus_db import (
    Database, DatabaseConfig, TreeConfig, CacheConfig, WALConfig, Cursor
)

# ── Configuration ─────────────────────────────────────────────

print("=== Configuration ===\n")

# Create a database from a config
config = DatabaseConfig(
    tree=TreeConfig(order=16),
    cache=CacheConfig(enabled=True, max_size=256),
    wal=WALConfig(enabled=False),
)
db = Database(config=config)

print(f"Database: {db}")
print(f"Tree order: {db._tree.order}")
print(f"Cache enabled: {db._cache is not None}")

# Save and load config from JSON
with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    config_path = f.name
try:
    config.to_json(config_path)
    print(f"\nConfig saved to {config_path}")
    loaded_config = DatabaseConfig.from_json(config_path)
    print(f"Loaded config tree order: {loaded_config.tree.order}")
finally:
    os.unlink(config_path)

# ── Cursor-based Pagination ───────────────────────────────────

print("\n=== Cursor Pagination ===\n")

db.put_many({f"item:{i:04d}": f"Product {i}" for i in range(100)})

# Paginate through all items
cursor = db.cursor(page_size=25)
total = 0
page_num = 0
while not cursor.exhausted:
    page = cursor.fetch_page()
    page_num += 1
    total += len(page)
    print(f"  Page {page_num}: {len(page)} items (total so far: {total})")

print(f"Total items: {total}")

# Cursor with prefix scan
cursor = db.cursor(prefix="item:00", page_size=10)
page = cursor.fetch_page()
print(f"\nPrefix scan 'item:00': {len(page)} items")
for k, v in page:
    print(f"  {k} => {v}")

# ── SQL-like Query Language ───────────────────────────────────

print("\n=== Query Language ===\n")

# Clear and re-populate
for i in range(10):
    db.put(f"score:{i:02d}", i * 10)

# SELECT all
results = db.execute("SELECT * FROM db WHERE key >= 'score:03' AND key <= 'score:07'")
print(f"Range query: {len(results)} results")
for k, v in results[:3]:
    print(f"  {k} => {v}")

# COUNT
count = db.execute("COUNT db")
print(f"\nTotal keys: {count}")

# INSERT
db.execute("INSERT INTO db KEY 'greeting' VALUE 'hello world'")
print(f"After INSERT: greeting = {db.get('greeting')}")

# ── Database Merge and Diff ───────────────────────────────────

print("\n=== Merge and Diff ===\n")

db1 = Database(order=16)
db1.put("shared", "from db1")
db1.put("only1", "value1")

db2 = Database(order=16)
db2.put("shared", "from db2")
db2.put("only2", "value2")

# Diff
diff = db1.diff(db2)
print("Diff:")
for k, v in diff.items():
    print(f"  {k}: {v}")

# Merge with "ours" strategy
merged = db1.merge(db2, conflict="ours")
print(f"\nMerged {merged} keys (ours strategy)")
print(f"  shared = {db1.get('shared')} (kept ours)")

# Merge with "theirs" strategy
db1b = Database(order=16)
db1b.put("shared", "from db1b")
merged2 = db1b.merge(db2, conflict="theirs")
print(f"\nMerged {merged2} keys (theirs strategy)")
print(f"  shared = {db1b.get('shared')} (took theirs)")