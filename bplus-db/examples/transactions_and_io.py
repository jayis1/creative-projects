#!/usr/bin/env python3
"""Example: Transactions, WAL recovery, and import/export.

Demonstrates ACID-like transactions, crash recovery, and data interchange.
"""

import tempfile
import os
from bplus_db import Database

# ── Transactions ─────────────────────────────────────────────

print("=== Transactions ===\n")

db = Database(order=16)

# Successful transaction
txn = db.begin_transaction()
txn.put("account:A", 1000)
txn.put("account:B", 500)
txn.commit()
print(f"After commit: A={db.get('account:A')}, B={db.get('account:B')}")

# Rolled-back transaction
txn = db.begin_transaction()
txn.put("account:A", 0)
txn.put("account:B", 0)
txn.rollback()
print(f"After rollback: A={db.get('account:A')}, B={db.get('account:B')}")

# Transaction is no longer active
print(f"Transaction active: {txn.is_active}")

# ── WAL Recovery ─────────────────────────────────────────────

print("\n=== WAL Recovery ===\n")

db2 = Database(order=16)
db2.put("persistent", "data")
db2.put("another", "value")

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    db_path = f.name
with tempfile.NamedTemporaryFile(suffix=".wal", delete=False) as f:
    wal_path = f.name

try:
    # Save a snapshot
    db2.save(db_path)
    print("Saved database snapshot")

    # Simulate crash with uncommitted WAL entries
    from bplus_db.database import WriteAheadLog
    from bplus_db.serializer import Serializer
    s = Serializer()
    wal = WriteAheadLog(wal_path)
    wal.append("PUT", "recovered_key", s.serialize_value("recovered_value"))
    wal.append("PUT", "also_recovered", s.serialize_value(42))
    print("Created WAL entries simulating crash")

    # Recover
    recovered = Database.recover(db_path, wal_path)
    print(f"Recovered: persistent={recovered.get('persistent')}")
    print(f"Recovered: recovered_key={recovered.get('recovered_key')}")
    print(f"Recovered: also_recovered={recovered.get('also_recovered')}")
finally:
    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)

# ── Import/Export ─────────────────────────────────────────────

print("\n=== Import/Export ===\n")

from bplus_db import io as db_io

db3 = Database(order=16)
db3.put("name", "Alice")
db3.put("age", 30)
db3.put("city", "NYC")

# Export to CSV
with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
    csv_path = f.name
try:
    count = db_io.export_csv(db3, csv_path)
    print(f"Exported {count} rows to CSV")

    # Import from CSV into a new database
    db4 = Database(order=16)
    imported = db_io.import_csv(db4, csv_path)
    print(f"Imported {imported} rows from CSV")
    print(f"  name={db4.get('name')}, age={db4.get('age')}, city={db4.get('city')}")
finally:
    os.unlink(csv_path)

# Export to JSONL
with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
    jsonl_path = f.name
try:
    count = db_io.export_json_lines(db3, jsonl_path)
    print(f"\nExported {count} rows to JSONL")
    with open(jsonl_path) as f:
        for line in f:
            print(f"  {line.strip()}")
finally:
    os.unlink(jsonl_path)

# Export to Pickle
with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
    pkl_path = f.name
try:
    count = db_io.export_pickle(db3, pkl_path)
    print(f"\nExported {count} entries to Pickle")
    db5 = Database(order=16)
    imported = db_io.import_pickle(db5, pkl_path)
    print(f"Imported {imported} entries from Pickle")
finally:
    os.unlink(pkl_path)