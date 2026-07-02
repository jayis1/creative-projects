"""
Example: Rebalancing — self-balancing B+Tree deletes.

Demonstrates that the B+Tree stays balanced after many deletions,
thanks to automatic merge/borrow rebalancing.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from btreestore import Store


def main():
    db_path = os.path.join(tempfile.gettempdir(), "example_rebalance.btree")
    wal_path = db_path + ".wal"
    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)

    with Store(db_path, page_size=512, wal_enabled=False) as store:
        # Insert 500 keys
        print("Inserting 500 keys...")
        for i in range(500):
            store.put(f"k{i:04d}", f"v{i}")
        stats = store.stats()
        print(f"  Keys: {stats['num_keys']}, Depth: {stats['tree_depth']}, "
              f"Pages: {stats['total_pages']}")

        # Delete half
        print("\nDeleting every other key (250 deletions)...")
        for i in range(0, 500, 2):
            store.delete(f"k{i:04d}")
        stats = store.stats()
        print(f"  Keys: {stats['num_keys']}, Depth: {stats['tree_depth']}, "
              f"Pages: {stats['total_pages']}")
        print(f"  Tree valid: {store.validate()}")

        # Delete the rest
        print("\nDeleting remaining keys...")
        for i in range(1, 500, 2):
            store.delete(f"k{i:04d}")
        stats = store.stats()
        print(f"  Keys: {stats['num_keys']}, Depth: {stats['tree_depth']}")
        print(f"  Tree valid: {store.validate()}")

    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)
    print("\nDone!")


if __name__ == "__main__":
    main()