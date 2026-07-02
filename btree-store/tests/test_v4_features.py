"""
Comprehensive tests for new v4.0 features.

Tests cover:
  - B+Tree rebalancing (merge/borrow) after deletions
  - TTL key expiration (lazy + active sweep)
  - Streaming cursor (memory-efficient iteration)
  - Backup and restore
  - Event subscription system
  - Secondary indexes
  - Page compression
  - New CLI commands (backup, restore, stream, info)
"""

import os
import sys
import time
import json
import struct
import tempfile
import subprocess
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from btreestore import (
    Store, StreamingCursor, TTLManager, TTLSweeper,
    BackupManager, EventBus, IndexManager, CompressionConfig,
)
from btreestore.merge import Rebalancer
from btreestore.compression import compress_page, decompress_page, CompressionConfig as CompCfg


@pytest.fixture
def store():
    path = tempfile.mktemp(suffix=".btree")
    s = Store(path)
    yield s
    s.close()
    for p in [path, path + ".wal"]:
        if os.path.exists(p):
            os.unlink(p)


@pytest.fixture
def store_small():
    """Store with small page size to force tree splitting/rebalancing."""
    path = tempfile.mktemp(suffix=".btree")
    s = Store(path, page_size=512, wal_enabled=False)
    yield s
    s.close()
    for p in [path, path + ".wal"]:
        if os.path.exists(p):
            os.unlink(p)


# =====================================================================
# Rebalancing Tests
# =====================================================================

class TestRebalancing:
    """Test B+Tree merge/borrow rebalancing after deletions."""

    def test_delete_maintains_order(self, store_small):
        """After many deletions, keys remain correctly ordered."""
        for i in range(100):
            store_small.put(f"key{i:03d}", f"val{i}")
        # Delete every other key
        for i in range(0, 100, 2):
            store_small.delete(f"key{i:03d}")
        assert store_small.count() == 50
        assert store_small.validate()
        # Verify remaining keys
        for i in range(1, 100, 2):
            assert store_small.get(f"key{i:03d}") == f"val{i}".encode()

    def test_delete_all_keys(self, store_small):
        """Deleting all keys should leave a valid (possibly empty) tree."""
        for i in range(50):
            store_small.put(f"k{i:03d}", f"v{i}")
        for i in range(50):
            assert store_small.delete(f"k{i:03d}") is True
        assert store_small.count() == 0
        assert store_small.validate()

    def test_delete_then_reinsert(self, store_small):
        """Reinserting after deletion should work correctly."""
        for i in range(30):
            store_small.put(f"k{i:03d}", f"v{i}")
        for i in range(30):
            store_small.delete(f"k{i:03d}")
        for i in range(30):
            store_small.put(f"k{i:03d}", f"v{i}_new")
        assert store_small.count() == 30
        assert store_small.validate()
        for i in range(30):
            assert store_small.get(f"k{i:03d}") == f"v{i}_new".encode()

    def test_sequential_deletion(self, store_small):
        """Delete keys in order (left to right) — tests right-sibling borrow/merge."""
        for i in range(80):
            store_small.put(f"k{i:03d}", f"v{i}")
        for i in range(80):
            store_small.delete(f"k{i:03d}")
        assert store_small.count() == 0
        assert store_small.validate()

    def test_reverse_deletion(self, store_small):
        """Delete keys in reverse order — tests left-sibling borrow/merge."""
        for i in range(80):
            store_small.put(f"k{i:03d}", f"v{i}")
        for i in range(79, -1, -1):
            store_small.delete(f"k{i:03d}")
        assert store_small.count() == 0
        assert store_small.validate()

    def test_root_collapse(self, store_small):
        """When root internal node has one child, it should collapse."""
        for i in range(500):
            store_small.put(f"k{i:04d}", f"v{i}")
        initial_depth = store_small.stats()["tree_depth"]
        assert initial_depth >= 1
        # Delete most keys to trigger root collapse
        for i in range(500):
            store_small.delete(f"k{i:04d}")
        assert store_small.count() == 0
        assert store_small.validate()

    def test_no_rebalance_option(self, store_small):
        """Delete with rebalance=False should still work (sparse tree)."""
        for i in range(50):
            store_small.put(f"k{i:03d}", f"v{i}")
        # Use tree.delete directly with rebalance=False
        for i in range(0, 50, 2):
            store_small.tree.delete(f"k{i:03d}".encode(), rebalance=False)
        store_small._flush_all()
        assert store_small.count() == 25
        assert store_small.validate()

    def test_borrow_from_sibling(self, store_small):
        """Test that borrowing from a sibling keeps tree balanced."""
        # Insert enough to create multiple leaves
        for i in range(60):
            store_small.put(f"k{i:03d}", f"v{i}")
        # Delete from one end to trigger borrow
        for i in range(55, 60):
            store_small.delete(f"k{i:03d}")
        assert store_small.count() == 55
        assert store_small.validate()
        for i in range(55):
            assert store_small.get(f"k{i:03d}") == f"v{i}".encode()

    def test_rebalance_preserves_linked_list(self, store_small):
        """After rebalancing, leaf linked-list should be intact."""
        for i in range(100):
            store_small.put(f"k{i:03d}", f"v{i}")
        for i in range(0, 100, 3):
            store_small.delete(f"k{i:03d}")
        # Full scan should work (uses linked list)
        c = store_small.cursor()
        keys = [k for k, _ in c]
        assert keys == sorted(keys)
        # 100 keys, delete every 3rd (0,3,6,...99) = 34 deleted, 66 remain
        assert len(keys) == 66

    def test_interleaved_insert_delete(self, store_small):
        """Interleave insertions and deletions."""
        for i in range(40):
            store_small.put(f"k{i:03d}", f"v{i}")
        for i in range(0, 40, 2):
            store_small.delete(f"k{i:03d}")
        for i in range(40, 60):
            store_small.put(f"k{i:03d}", f"v{i}")
        for i in range(1, 40, 2):
            store_small.delete(f"k{i:03d}")
        assert store_small.validate()
        # Should have keys 40-59
        for i in range(40, 60):
            assert store_small.get(f"k{i:03d}") == f"v{i}".encode()

    def test_compact_after_rebalance(self, store_small):
        """Compaction should still work after rebalancing deletions."""
        for i in range(100):
            store_small.put(f"k{i:03d}", f"v{i}")
        for i in range(0, 100, 2):
            store_small.delete(f"k{i:03d}")
        n = store_small.compact()
        assert n == 50
        assert store_small.validate()
        assert store_small.count() == 50


# =====================================================================
# TTL Expiration Tests
# =====================================================================

class TestTTL:
    """Test TTL key expiration."""

    def test_ttl_put_get(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=100)
        assert ttl.get("key1") == b"val1"

    def test_ttl_expiration(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=0.01)
        time.sleep(0.02)
        assert ttl.get("key1") is None  # expired

    def test_ttl_no_expiration(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=None)
        time.sleep(0.01)
        assert ttl.get("key1") == b"val1"

    def test_ttl_remaining(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=100)
        remaining = ttl.ttl("key1")
        assert remaining is not None
        assert 90 < remaining <= 100

    def test_ttl_remaining_no_ttl(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1")
        assert ttl.ttl("key1") is None

    def test_ttl_persist(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=100)
        assert ttl.persist("key1") is True
        assert ttl.ttl("key1") is None
        # Key should still exist
        assert store.get("key1") == b"val1"

    def test_ttl_persist_no_ttl(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1")
        assert ttl.persist("key1") is False

    def test_ttl_sweep(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=0.01)
        ttl.put("key2", "val2", ttl_seconds=0.01)
        ttl.put("key3", "val3", ttl_seconds=100)
        time.sleep(0.02)
        expired = ttl.sweep_expired()
        assert expired == 2
        assert store.get("key3") == b"val3"

    def test_ttl_expired_keys(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=0.01)
        ttl.put("key2", "val2", ttl_seconds=100)
        time.sleep(0.02)
        expired = ttl.expired_keys()
        assert b"key1" in expired
        assert b"key2" not in expired

    def test_ttl_count(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=100)
        ttl.put("key2", "val2", ttl_seconds=100)
        ttl.put("key3", "val3")  # no TTL
        assert ttl.count() == 2

    def test_ttl_expire_at(self, store):
        ttl = TTLManager(store)
        store.put("key1", "val1")
        ttl.expire_at("key1", time.time() - 1)  # already expired
        assert ttl.get("key1") is None

    def test_ttl_all_ttls(self, store):
        ttl = TTLManager(store)
        ttl.put("key1", "val1", ttl_seconds=100)
        all_ttls = ttl.all_ttls()
        assert b"key1" in all_ttls

    def test_ttl_sweeper_thread(self, store):
        """Test the background sweeper thread."""
        ttl = TTLManager(store)
        sweeper = TTLSweeper(ttl, interval=0.05)
        ttl.put("key1", "val1", ttl_seconds=0.01)
        sweeper.start()
        time.sleep(0.15)
        sweeper.stop()
        assert store.get("key1") is None  # swept


# =====================================================================
# Streaming Cursor Tests
# =====================================================================

class TestStreamingCursor:
    """Test memory-efficient streaming cursor."""

    def test_stream_all(self, store):
        for i in range(50):
            store.put(f"k{i:03d}", f"v{i}")
        results = list(StreamingCursor(store))
        assert len(results) == 50
        keys = [k for k, _ in results]
        assert keys == sorted(keys)

    def test_stream_range(self, store):
        for i in range(50):
            store.put(f"k{i:03d}", f"v{i}")
        results = list(StreamingCursor(store, low=b"k010", high=b"k020"))
        assert len(results) == 10
        assert results[0][0] == b"k010"
        assert results[-1][0] == b"k019"

    def test_stream_reverse(self, store):
        for i in range(50):
            store.put(f"k{i:03d}", f"v{i}")
        results = list(StreamingCursor(store, reverse=True))
        keys = [k for k, _ in results]
        assert keys == sorted(keys, reverse=True)

    def test_stream_limit(self, store):
        for i in range(50):
            store.put(f"k{i:03d}", f"v{i}")
        results = list(StreamingCursor(store, limit=10))
        assert len(results) == 10

    def test_stream_reverse_limit(self, store):
        for i in range(50):
            store.put(f"k{i:03d}", f"v{i}")
        results = list(StreamingCursor(store, reverse=True, limit=5))
        assert len(results) == 5
        assert results[0][0] == b"k049"

    def test_stream_empty_store(self, store):
        results = list(StreamingCursor(store))
        assert results == []

    def test_stream_include_high(self, store):
        for i in range(20):
            store.put(f"k{i:03d}", f"v{i}")
        results = list(StreamingCursor(
            store, low=b"k005", high=b"k010", include_high=True
        ))
        assert len(results) == 6
        assert results[-1][0] == b"k010"

    def test_stream_matches_regular_cursor(self, store):
        """Streaming cursor should return same results as regular cursor."""
        for i in range(100):
            store.put(f"k{i:03d}", f"v{i}")
        regular = list(store.cursor())
        streamed = list(StreamingCursor(store))
        assert regular == streamed


# =====================================================================
# Backup/Restore Tests
# =====================================================================

class TestBackupRestore:
    """Test backup and restore functionality."""

    def test_backup_restore_roundtrip(self, store):
        for i in range(100):
            store.put(f"k{i:03d}", f"v{i}")
        bm = BackupManager(store)
        backup_path = tempfile.mktemp(suffix=".bak")
        dest_path = tempfile.mktemp(suffix=".btree")
        try:
            n = bm.backup(backup_path)
            assert n == 100
            assert os.path.exists(backup_path)

            n2 = bm.restore(backup_path, dest_path)
            assert n2 == 100

            # Verify restored data
            s2 = Store(dest_path, wal_enabled=False)
            try:
                for i in range(100):
                    assert s2.get(f"k{i:03d}") == f"v{i}".encode()
                assert s2.count() == 100
            finally:
                s2.close()
        finally:
            for p in [backup_path, dest_path, dest_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_backup_verify(self, store):
        store.put("key", "value")
        bm = BackupManager(store)
        backup_path = tempfile.mktemp(suffix=".bak")
        try:
            bm.backup(backup_path)
            assert bm.verify_backup(backup_path) is True
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)

    def test_backup_verify_corrupt(self, store):
        store.put("key", "value")
        bm = BackupManager(store)
        backup_path = tempfile.mktemp(suffix=".bak")
        try:
            bm.backup(backup_path)
            # Corrupt the file
            with open(backup_path, "r+b") as f:
                f.seek(10)
                f.write(b"\xFF\xFF\xFF\xFF")
            assert bm.verify_backup(backup_path) is False
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)

    def test_backup_info(self, store):
        for i in range(50):
            store.put(f"k{i:03d}", f"v{i}")
        bm = BackupManager(store)
        backup_path = tempfile.mktemp(suffix=".bak")
        try:
            bm.backup(backup_path)
            info = bm.backup_info(backup_path)
            assert info["num_entries"] == 50
            assert info["page_size"] == store.page_size
            assert info["incremental"] is False
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)

    def test_backup_empty_store(self, store):
        bm = BackupManager(store)
        backup_path = tempfile.mktemp(suffix=".bak")
        dest_path = tempfile.mktemp(suffix=".btree")
        try:
            n = bm.backup(backup_path)
            assert n == 0
            n2 = bm.restore(backup_path, dest_path)
            assert n2 == 0
        finally:
            for p in [backup_path, dest_path, dest_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_backup_binary_data(self, store):
        store.put(b"\x00\x01\x02", b"\xFF\xFE\xFD")
        bm = BackupManager(store)
        backup_path = tempfile.mktemp(suffix=".bak")
        dest_path = tempfile.mktemp(suffix=".btree")
        try:
            bm.backup(backup_path)
            bm.restore(backup_path, dest_path)
            s2 = Store(dest_path, wal_enabled=False)
            try:
                assert s2.get(b"\x00\x01\x02") == b"\xFF\xFE\xFD"
            finally:
                s2.close()
        finally:
            for p in [backup_path, dest_path, dest_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)


# =====================================================================
# Event System Tests
# =====================================================================

class TestEventBus:
    """Test event subscription system."""

    def test_put_event(self, store):
        bus = EventBus(store)
        events = []
        @bus.on("put")
        def handler(key, value):
            events.append(("put", key, value))
        store.put("key", "value")
        assert len(events) == 1
        assert events[0] == ("put", b"key", b"value")

    def test_delete_event(self, store):
        bus = EventBus(store)
        events = []
        store.put("key", "value")
        @bus.on("delete")
        def handler(key):
            events.append(("delete", key))
        store.delete("key")
        assert len(events) == 1
        assert events[0] == ("delete", b"key")

    def test_commit_event(self, store):
        bus = EventBus(store)
        events = []
        @bus.on("commit")
        def handler(txn_id):
            events.append(txn_id)
        with store.transaction() as txn:
            txn.put("key", "val")
        assert len(events) == 1

    def test_compact_event(self, store):
        bus = EventBus(store)
        events = []
        @bus.on("compact")
        def handler(keys_compacted):
            events.append(keys_compacted)
        store.put("key", "val")
        store.compact()
        assert len(events) == 1
        assert events[0] == 1

    def test_off(self, store):
        bus = EventBus(store)
        events = []
        def handler(key, value):
            events.append(key)
        bus.on("put", handler)
        store.put("k1", "v1")
        assert len(events) == 1
        bus.off("put", handler)
        store.put("k2", "v2")
        assert len(events) == 1  # no new event

    def test_disable_enable(self, store):
        bus = EventBus(store)
        events = []
        @bus.on("put")
        def handler(key, value):
            events.append(key)
        bus.disable()
        store.put("k1", "v1")
        assert len(events) == 0
        bus.enable()
        store.put("k2", "v2")
        assert len(events) == 1

    def test_handler_count(self, store):
        bus = EventBus(store)
        @bus.on("put")
        def h1(key, value):
            pass
        @bus.on("put")
        def h2(key, value):
            pass
        @bus.on("delete")
        def h3(key):
            pass
        assert bus.handler_count("put") == 2
        assert bus.handler_count("delete") == 1
        assert bus.handler_count() == 3

    def test_handler_exception_isolated(self, store):
        """One handler's exception shouldn't affect others."""
        bus = EventBus(store)
        events = []
        @bus.on("put")
        def bad_handler(key, value):
            raise ValueError("oops")
        @bus.on("put")
        def good_handler(key, value):
            events.append(key)
        store.put("key", "val")
        assert len(events) == 1  # good handler still called


# =====================================================================
# Secondary Index Tests
# =====================================================================

class TestSecondaryIndex:
    """Test secondary indexes."""

    def test_index_add_find(self, store):
        mgr = IndexManager(store)
        idx = mgr.create_index("email")
        try:
            idx.add("alice@x.com", "user:1")
            idx.add("bob@x.com", "user:2")
            keys = idx.find("alice@x.com")
            assert keys == [b"user:1"]
        finally:
            mgr.close_all()
            # Clean up index files
            idx_path = idx.path
            for p in [idx_path, idx_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_index_multiple_keys(self, store):
        mgr = IndexManager(store)
        idx = mgr.create_index("category")
        try:
            idx.add("fruit", "apple")
            idx.add("fruit", "banana")
            idx.add("fruit", "cherry")
            idx.add("veg", "carrot")
            keys = idx.find("fruit")
            assert set(keys) == {b"apple", b"banana", b"cherry"}
            assert len(idx.find("veg")) == 1
        finally:
            mgr.close_all()
            idx_path = idx.path
            for p in [idx_path, idx_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_index_remove(self, store):
        mgr = IndexManager(store)
        idx = mgr.create_index("tag")
        try:
            idx.add("python", "doc1")
            idx.add("python", "doc2")
            assert idx.remove("python", "doc1") is True
            keys = idx.find("python")
            assert keys == [b"doc2"]
            assert idx.remove("python", "doc1") is False
        finally:
            mgr.close_all()
            idx_path = idx.path
            for p in [idx_path, idx_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_index_find_one(self, store):
        mgr = IndexManager(store)
        idx = mgr.create_index("name")
        try:
            idx.add("alice", "user:1")
            assert idx.find_one("alice") == b"user:1"
            assert idx.find_one("bob") is None
        finally:
            mgr.close_all()
            idx_path = idx.path
            for p in [idx_path, idx_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_index_count(self, store):
        mgr = IndexManager(store)
        idx = mgr.create_index("field")
        try:
            idx.add("a", "1")
            idx.add("b", "2")
            idx.add("c", "3")
            assert idx.count() == 3
        finally:
            mgr.close_all()
            idx_path = idx.path
            for p in [idx_path, idx_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_index_range(self, store):
        mgr = IndexManager(store)
        idx = mgr.create_index("score")
        try:
            idx.add("100", "doc1")
            idx.add("200", "doc2")
            idx.add("300", "doc3")
            results = list(idx.range(low="100", high="300"))
            assert len(results) == 2  # [100, 200) — 300 is exclusive
        finally:
            mgr.close_all()
            idx_path = idx.path
            for p in [idx_path, idx_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_drop_index(self, store):
        mgr = IndexManager(store)
        idx = mgr.create_index("temp")
        idx_path = idx.path
        idx.add("x", "y")
        assert mgr.drop_index("temp") is True
        assert not os.path.exists(idx_path)
        assert mgr.drop_index("nonexistent") is False

    def test_index_names(self, store):
        mgr = IndexManager(store)
        mgr.create_index("a")
        mgr.create_index("b")
        names = mgr.index_names()
        assert "a" in names
        assert "b" in names
        mgr.close_all()
        # Cleanup
        for name in names:
            idx = mgr._indexes.get(name)
            if idx:
                for p in [idx.path, idx.path + ".wal"]:
                    if os.path.exists(p):
                        os.unlink(p)


# =====================================================================
# Compression Tests
# =====================================================================

class TestCompression:
    """Test page-level compression."""

    def test_compress_decompress_roundtrip(self):
        data = b"Hello World! " * 100
        config = CompCfg(level=6)
        compressed = compress_page(data, config)
        decompressed = decompress_page(compressed)
        assert decompressed == data

    def test_compression_saves_space(self):
        data = b"AAAAAAAAAA" * 1000
        config = CompCfg(level=6)
        compressed = compress_page(data, config)
        assert len(compressed) < len(data)

    def test_no_compression_for_small_data(self):
        data = b"tiny"
        config = CompCfg(min_size=64)
        compressed = compress_page(data, config)
        # Should be uncompressed (flag byte + data)
        assert compressed[0] == 0x00
        assert decompress_page(compressed) == data

    def test_compression_level_0(self):
        data = b"test" * 100
        config = CompCfg(level=0)
        compressed = compress_page(data, config)
        assert compressed[0] == 0x00  # uncompressed flag

    def test_compression_ratio(self):
        from btreestore.compression import compression_ratio
        assert compression_ratio(100, 50) == 0.5
        assert compression_ratio(100, 100) == 1.0
        assert compression_ratio(0, 0) == 1.0

    def test_compression_config_validation(self):
        with pytest.raises(ValueError):
            CompCfg(level=-1)
        with pytest.raises(ValueError):
            CompCfg(level=10)
        with pytest.raises(ValueError):
            CompCfg(max_ratio=0)
        with pytest.raises(ValueError):
            CompCfg(max_ratio=1.5)

    def test_decompress_unknown_flag(self):
        """Unknown flag should return data as-is (backward compat)."""
        data = b"\x99raw data without flag"
        result = decompress_page(data)
        assert result == data


# =====================================================================
# CLI Tests
# =====================================================================

class TestNewCLI:
    """Test new CLI subcommands."""

    def _run_cli(self, db_path, *args):
        """Run the CLI with the given arguments."""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "btreestore_cli.py"
        )
        cmd = [sys.executable, cli_path, "--db", db_path] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result

    def test_cli_info(self):
        path = tempfile.mktemp(suffix=".btree")
        try:
            r = self._run_cli(path, "put", "key", "value")
            assert r.returncode == 0
            r = self._run_cli(path, "info")
            assert r.returncode == 0
            assert "btreestore" in r.stdout
            assert "num_keys" in r.stdout
        finally:
            for p in [path, path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_cli_info_json(self):
        path = tempfile.mktemp(suffix=".btree")
        try:
            self._run_cli(path, "put", "key", "value")
            r = self._run_cli(path, "info", "--format", "json")
            assert r.returncode == 0
            data = json.loads(r.stdout)
            assert data["num_keys"] == 1
        finally:
            for p in [path, path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_cli_stream(self):
        path = tempfile.mktemp(suffix=".btree")
        try:
            self._run_cli(path, "put", "a", "1")
            self._run_cli(path, "put", "b", "2")
            self._run_cli(path, "put", "c", "3")
            r = self._run_cli(path, "stream")
            assert r.returncode == 0
            lines = r.stdout.strip().split("\n")
            assert len(lines) == 3
        finally:
            for p in [path, path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_cli_stream_limit(self):
        path = tempfile.mktemp(suffix=".btree")
        try:
            for i in range(10):
                self._run_cli(path, "put", f"k{i:02d}", f"v{i}")
            r = self._run_cli(path, "stream", "--limit", "3")
            assert r.returncode == 0
            lines = r.stdout.strip().split("\n")
            assert len(lines) == 3
        finally:
            for p in [path, path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_cli_backup_restore(self):
        path = tempfile.mktemp(suffix=".btree")
        backup_path = tempfile.mktemp(suffix=".bak")
        dest_path = tempfile.mktemp(suffix=".btree")
        try:
            self._run_cli(path, "put", "key", "value")
            r = self._run_cli(path, "backup", backup_path)
            assert r.returncode == 0
            assert os.path.exists(backup_path)

            r = self._run_cli(path, "restore", backup_path, dest_path)
            assert r.returncode == 0

            # Verify restored data
            r = self._run_cli(dest_path, "get", "key")
            assert r.returncode == 0
            assert "value" in r.stdout
        finally:
            for p in [path, path + ".wal", backup_path, dest_path, dest_path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_cli_backup_info(self):
        path = tempfile.mktemp(suffix=".btree")
        backup_path = tempfile.mktemp(suffix=".bak")
        try:
            self._run_cli(path, "put", "key", "value")
            self._run_cli(path, "backup", backup_path)
            r = self._run_cli(path, "backup-info", backup_path)
            assert r.returncode == 0
            assert "num_entries" in r.stdout
        finally:
            for p in [path, path + ".wal", backup_path]:
                if os.path.exists(p):
                    os.unlink(p)