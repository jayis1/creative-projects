"""
Example: Backup and restore.

Demonstrates creating a backup archive and restoring it.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from btreestore import Store, BackupManager


def main():
    db_path = os.path.join(tempfile.gettempdir(), "example_backup.btree")
    wal_path = db_path + ".wal"
    backup_path = os.path.join(tempfile.gettempdir(), "example_backup.bak")
    dest_path = os.path.join(tempfile.gettempdir(), "example_restored.btree")
    for p in [db_path, wal_path, backup_path, dest_path, dest_path + ".wal"]:
        if os.path.exists(p):
            os.unlink(p)

    # Create and populate the original store
    print("Creating store with 500 entries...")
    with Store(db_path) as store:
        for i in range(500):
            store.put(f"key{i:04d}", f"value{i}")
        print(f"  Keys: {store.count()}")

        # Create backup
        bm = BackupManager(store)
        print(f"\nCreating backup: {backup_path}")
        n = bm.backup(backup_path)
        print(f"  Backed up {n} entries")

        # Show backup info
        info = bm.backup_info(backup_path)
        print(f"  Backup info: {info}")

        # Verify backup
        valid = bm.verify_backup(backup_path)
        print(f"  Backup valid: {valid}")

    # Restore to a new store
    print(f"\nRestoring to: {dest_path}")
    with Store(db_path) as store:
        bm = BackupManager(store)
        n = bm.restore(backup_path, dest_path)
        print(f"  Restored {n} entries")

    # Verify restored data
    print("\nVerifying restored data...")
    with Store(dest_path, wal_enabled=False) as restored:
        assert restored.count() == 500
        for i in [0, 100, 250, 499]:
            val = restored.get(f"key{i:04d}")
            print(f"  key{i:04d} -> {val!r}")
            assert val == f"value{i}".encode()
        print("  All values verified!")

    # Cleanup
    for p in [db_path, wal_path, backup_path, dest_path, dest_path + ".wal"]:
        if os.path.exists(p):
            os.unlink(p)
    print("\nDone!")


if __name__ == "__main__":
    main()