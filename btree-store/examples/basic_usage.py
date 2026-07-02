"""
Example: Basic usage of btreestore.

Demonstrates creating a store, putting/getting keys, transactions,
cursor iteration, and prefix scans.
"""

import os
import sys
import tempfile

# Add parent directory to path so we can import btreestore
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from btreestore import Store


def main():
    db_path = os.path.join(tempfile.gettempdir(), "example_basic.btree")
    
    # Clean up if exists
    if os.path.exists(db_path):
        os.unlink(db_path)
    wal_path = db_path + ".wal"
    if os.path.exists(wal_path):
        os.unlink(wal_path)

    # Open a store (context manager auto-closes)
    with Store(db_path) as store:
        # Basic put/get
        store.put("hello", "world")
        store.put("foo", "bar")
        store.put("abc", "def")
        
        print(f"hello -> {store.get('hello')!r}")
        print(f"foo -> {store.get('foo')!r}")
        print(f"missing -> {store.get('missing')!r}")
        
        # Min/max
        print(f"\nMin: {store.min()!r}")
        print(f"Max: {store.max()!r}")
        
        # Contains check
        print(f"\n'hello' in store: {'hello' in store}")
        print(f"'missing' in store: {'missing' in store}")
        
        # Compare-and-swap
        assert store.cas("hello", "world", "universe")
        print(f"\nAfter CAS: hello -> {store.get('hello')!r}")
        
        assert store.cas("new_key", None, "inserted")
        print(f"new_key -> {store.get('new_key')!r}")
        
        # Context-manager transaction
        with store.transaction() as txn:
            txn.put("key1", "val1")
            txn.put("key2", "val2")
            txn.delete("foo")
        # Auto-committed here
        
        # Scan all keys
        print("\nAll keys (forward):")
        for k, v in store.cursor():
            print(f"  {k.decode():10s} -> {v.decode()}")
        
        # Reverse scan with limit
        print("\nLast 2 keys (reverse):")
        for k, v in store.cursor(reverse=True, limit=2):
            print(f"  {k.decode():10s} -> {v.decode()}")
        
        # Prefix scan
        print("\nKeys with prefix 'key':")
        for k, v in store.prefix("key"):
            print(f"  {k.decode():10s} -> {v.decode()}")
        
        # Range scan
        print("\nKeys in [a, h):")
        for k, v in store.cursor(low="a", high="h"):
            print(f"  {k.decode():10s} -> {v.decode()}")
        
        # Atomic increment
        store.put("counter", "0")
        store.increment("counter")
        store.increment("counter", 5)
        print(f"\nCounter: {store.get('counter')!r}")
        
        # Stats
        print(f"\nStats:")
        for k, v in store.stats().items():
            print(f"  {k}: {v}")
        
        # Validate
        print(f"\nTree valid: {store.validate()}")
    
    # Reopen to test persistence
    print("\n--- Reopening store ---")
    with Store(db_path) as store:
        print(f"hello -> {store.get('hello')!r}")
        print(f"key1 -> {store.get('key1')!r}")
        print(f"counter -> {store.get('counter')!r}")
        print(f"Total keys: {store.count()}")
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    if os.path.exists(wal_path):
        os.unlink(wal_path)
    
    print("\nDone!")


if __name__ == "__main__":
    main()