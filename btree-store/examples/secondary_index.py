"""
Example: Secondary indexes.

Demonstrates creating secondary indexes for efficient multi-field lookups.
"""

import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from btreestore import Store, IndexManager


def main():
    db_path = os.path.join(tempfile.gettempdir(), "example_index.btree")
    wal_path = db_path + ".wal"
    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)

    with Store(db_path) as store:
        mgr = IndexManager(store)

        # Create indexes
        email_idx = mgr.create_index("email")
        city_idx = mgr.create_index("city")

        # Insert user records and index them
        users = [
            ("user:1", {"name": "Alice", "email": "alice@x.com", "city": "NYC"}),
            ("user:2", {"name": "Bob", "email": "bob@x.com", "city": "LA"}),
            ("user:3", {"name": "Carol", "email": "carol@x.com", "city": "NYC"}),
            ("user:4", {"name": "Dave", "email": "dave@x.com", "city": "SF"}),
            ("user:5", {"name": "Eve", "email": "eve@x.com", "city": "NYC"}),
        ]

        print("Inserting users and building indexes...")
        for pk, data in users:
            store.put(pk, json.dumps(data).encode())
            email_idx.add(data["email"], pk)
            city_idx.add(data["city"], pk)

        # Look up by email
        print(f"\nLookup by email 'alice@x.com':")
        keys = email_idx.find("alice@x.com")
        for k in keys:
            val = store.get(k)
            print(f"  {k.decode()}: {json.loads(val)}")

        # Look up by city (multiple results)
        print(f"\nLookup by city 'NYC':")
        keys = city_idx.find("NYC")
        for k in keys:
            val = store.get(k)
            print(f"  {k.decode()}: {json.loads(val)}")

        # Find one by email
        print(f"\nFind one by email 'bob@x.com':")
        key = email_idx.find_one("bob@x.com")
        print(f"  {key.decode()}")

        # Index stats
        print(f"\nIndex stats:")
        print(f"  email index: {email_idx.count()} distinct values")
        print(f"  city index: {city_idx.count()} distinct values")

        # Range query on email index
        print(f"\nRange query on emails [a, d):")
        for value, pks in email_idx.range(low="a", high="d"):
            print(f"  {value.decode()}: {len(pks)} key(s)")

        # Cleanup index files
        for idx_path in [email_idx.path, city_idx.path]:
            for p in [idx_path, idx_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)
    print("\nDone!")


if __name__ == "__main__":
    main()