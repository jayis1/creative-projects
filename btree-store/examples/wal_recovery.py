"""
Example: Using the Write-Ahead Log (WAL) for crash recovery.

Demonstrates WAL replay after a simulated crash.
"""

import os
import sys
import tempfile

# Add parent directory to path so we can import btreestore
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from btreestore import Store


def main():
    db_path = os.path.join(tempfile.gettempdir(), "example_wal.btree")
    wal_path = db_path + ".wal"
    
    # Clean up
    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)

    # Phase 1: Write data and close normally
    print("Phase 1: Writing data...")
    with Store(db_path, wal_enabled=True) as store:
        for i in range(100):
            store.put(f"key{i:03d}", f"value{i}")
        print(f"  Wrote {store.count()} keys")
        print(f"  WAL size: {os.path.getsize(wal_path)} bytes")
    
    # Phase 2: Write more data, simulate crash (don't close properly)
    print("\nPhase 2: Simulating crash after writes...")
    store = Store(db_path, wal_enabled=True)
    for i in range(100, 150):
        store.put(f"key{i:03d}", f"value{i}")
    print(f"  Wrote 50 more keys (total should be 150 after recovery)")
    print(f"  WAL size: {os.path.getsize(wal_path)} bytes")
    # Simulate crash: close WAL but don't checkpoint
    store._flush_all()
    if store._wal:
        store._wal._fd.flush()
        store._wal.close()
        store._wal = None
    store._cache.clear()
    store._closed = True
    # DON'T call store.close() — that would checkpoint the WAL
    
    # Phase 3: Reopen — WAL should replay
    print("\nPhase 3: Reopening store (WAL replay)...")
    with Store(db_path, wal_enabled=True) as store:
        count = store.count()
        print(f"  Keys after recovery: {count}")
        assert count == 150, f"Expected 150 keys, got {count}"
        
        # Verify some keys
        for i in [0, 50, 99, 100, 149]:
            val = store.get(f"key{i:03d}")
            print(f"  key{i:03d} -> {val!r}")
        
        print(f"\n  WAL size after checkpoint: {os.path.getsize(wal_path)} bytes")
        print("  Recovery successful!")
    
    # Cleanup
    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)
    
    print("\nDone!")


if __name__ == "__main__":
    main()