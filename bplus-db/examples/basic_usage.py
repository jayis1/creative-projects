#!/usr/bin/env python3
"""Example: Getting started with bplus-db.

Demonstrates basic CRUD operations, range queries, and persistence.
"""

from bplus_db import Database

# Create a database with order 32
db = Database(order=32)

# Basic CRUD
db.put("user:1", {"name": "Alice", "age": 30})
db.put("user:2", {"name": "Bob", "age": 25})
db.put("user:3", {"name": "Carol", "age": 35})

# Retrieve values
print("user:1 =", db.get("user:1"))
print("user:2 =", db.get("user:2"))

# Check existence
print("'user:1' in db:", "user:1" in db)
print("'missing' in db:", "missing" in db)

# Update a value
db.put("user:2", {"name": "Bob", "age": 26})
print("Updated user:2 =", db.get("user:2"))

# Delete
db.delete("user:3")
print("After deleting user:3:", db.get("user:3"))

# Batch operations
db.put_many({"k1": "v1", "k2": "v2", "k3": "v3"})
db.delete_many(["k2"])

# Range queries
for i in range(20):
    db.put(f"key{i:04d}", i)
results = db.range_query("key0005", "key0010")
print(f"\nRange query (key0005 to key0010): {len(results)} results")
for k, v in results[:3]:
    print(f"  {k} => {v}")

# Prefix scan
for i in range(5):
    db.put(f"product:{i}", f"Product {i}")
products = db.prefix_scan("product:")
print(f"\nProducts: {len(products)} items")

# Statistics
print("\nDatabase stats:")
stats = db.stats()
for k, v in stats.items():
    print(f"  {k}: {v}")