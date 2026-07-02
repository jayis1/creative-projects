"""
Example: Bulk loading and compaction.

Demonstrates loading large datasets and compacting sparse trees.
"""

import os
import sys
import time
import tempfile

# Add parent directory to path so we can import btreestore
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from btreestore import Store


def main():
    db_path = os.path.join(tempfile.gettempdir(), "example_bulk.btree")
    wal_path = db_path + ".wal"
    
    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)

    with Store(db_path) as store:
        # Bulk load 10,000 entries
        print("Bulk loading 10,000 entries...")
        pairs = [(f"key{i:05d}", f"value{i}") for i in range(10000)]
        start = time.time()
        store.bulk_load(pairs)
        elapsed = time.time() - start
        print(f"  Loaded in {elapsed:.2f}s ({10000/elapsed:.0f} ops/s)")
        
        # Stats before compaction
        stats = store.stats()
        print(f"\nBefore compaction:")
        print(f"  Keys: {stats['num_keys']}")
        print(f"  File size: {stats['file_size']:,} bytes")
        print(f"  Tree depth: {stats['tree_depth']}")
        
        # Delete half the keys to create sparse pages
        print("\nDeleting even-numbered keys...")
        for i in range(0, 10000, 2):
            store.delete(f"key{i:05d}")
        print(f"  Keys after deletion: {store.count()}")
        
        stats = store.stats()
        print(f"  File size: {stats['file_size']:,} bytes")
        
        # Compact to reclaim space
        print("\nCompacting tree...")
        start = time.time()
        n = store.compact()
        elapsed = time.time() - start
        print(f"  Compacted {n} keys in {elapsed:.2f}s")
        
        stats = store.stats()
        print(f"\nAfter compaction:")
        print(f"  Keys: {stats['num_keys']}")
        print(f"  File size: {stats['file_size']:,} bytes")
        print(f"  Tree depth: {stats['tree_depth']}")
        print(f"  Valid: {store.validate()}")
        
        # Verify data integrity
        print("\nVerifying data integrity...")
        ok = True
        for i in range(1, 10000, 2):
            val = store.get(f"key{i:05d}")
            if val != f"value{i}".encode():
                print(f"  MISMATCH at key{i:05d}: {val!r}")
                ok = False
                break
        if ok:
            print("  All values verified!")
    
    # Cleanup
    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)
    
    print("\nDone!")


if __name__ == "__main__":
    main()