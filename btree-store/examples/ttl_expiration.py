"""
Example: TTL key expiration.

Demonstrates TTL-based key expiration with lazy deletion and active sweep.
"""

import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from btreestore import Store, TTLManager


def main():
    db_path = os.path.join(tempfile.gettempdir(), "example_ttl.btree")
    wal_path = db_path + ".wal"
    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)

    with Store(db_path) as store:
        ttl = TTLManager(store)

        # Set keys with different TTLs
        print("Setting keys with TTLs...")
        ttl.put("session:1", "active", ttl_seconds=0.1)   # expires in 0.1s
        ttl.put("session:2", "active", ttl_seconds=2.0)   # expires in 2s
        ttl.put("permanent", "data", ttl_seconds=None)     # no expiration

        print(f"  session:1 TTL remaining: {ttl.ttl('session:1'):.2f}s")
        print(f"  session:2 TTL remaining: {ttl.ttl('session:2'):.2f}s")
        print(f"  permanent TTL: {ttl.ttl('permanent')}")

        # All keys accessible immediately
        print(f"\nAll keys accessible:")
        print(f"  session:1 -> {ttl.get('session:1')!r}")
        print(f"  session:2 -> {ttl.get('session:2')!r}")
        print(f"  permanent -> {ttl.get('permanent')!r}")

        # Wait for session:1 to expire
        print("\nWaiting 0.15s for session:1 to expire...")
        time.sleep(0.15)
        print(f"  session:1 -> {ttl.get('session:1')!r}  (expired!)")
        print(f"  session:2 -> {ttl.get('session:2')!r}  (still active)")

        # Active sweep
        print(f"\nKeys with TTLs: {ttl.count()}")
        print("Waiting 2s then sweeping...")
        time.sleep(2.0)
        expired = ttl.sweep_expired()
        print(f"  Swept {expired} expired keys")
        print(f"  permanent -> {ttl.get('permanent')!r}  (still active)")

    for p in [db_path, wal_path]:
        if os.path.exists(p):
            os.unlink(p)
    print("\nDone!")


if __name__ == "__main__":
    main()