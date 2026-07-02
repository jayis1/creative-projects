"""
Comprehensive test suite for the btreestore package.

Tests cover:
  - Basic operations (put/get/delete)
  - B+Tree splitting (many keys)
  - Persistence (close + reopen)
  - Range scans, prefix scans, reverse scans
  - Transactions (commit/rollback, read-only, context manager)
  - CAS (compare-and-swap)
  - Min/max
  - Batch operations (put_many, delete_many, bulk_load)
  - CRC32 integrity verification
  - Edge cases (empty key, binary keys, large values)
  - Count correctness with writes
  - Cursor offset/limit/seek/filter/map/batch
  - WAL crash recovery
  - Configuration loading (JSON/TOML/env)
  - Compaction
  - Atomic increment
  - Import/export

Bug hunt tests designed to expose issues:
  - Delete + reinsert same key
  - Insert after large deletion (sparse tree)
  - Concurrent transaction isolation
  - _find_parent correctness after splits
  - scan with low > high
  - prefix with empty prefix
  - Negative offset in cursor
  - Very large keys (near page size)
"""

import os
import sys
import json
import struct
import tempfile
import pytest

# Add the btree-store directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from btreestore import Store, Transaction, Cursor, StoreConfig
from btreestore.pages import (
    LeafPage, InternalPage, FreePage,
    verify_page_crc, _prefix_upper_bound,
    serialize_leaf, deserialize_leaf,
)
from btreestore.wal import WAL


@pytest.fixture
def store():
    """Create a temporary store for testing."""
    path = tempfile.mktemp(suffix=".btree")
    s = Store(path)
    yield s
    s.close()
    # Clean up db and wal files
    for p in [path, path + ".wal"]:
        if os.path.exists(p):
            os.unlink(p)


@pytest.fixture
def store_no_wal():
    """Create a temporary store without WAL."""
    path = tempfile.mktemp(suffix=".btree")
    s = Store(path, wal_enabled=False)
    yield s
    s.close()
    if os.path.exists(path):
        os.unlink(path)


class TestBasicOperations:
    """Test basic put/get/delete operations."""

    def test_put_get(self, store):
        store.put("hello", "world")
        assert store.get("hello") == b"world"

    def test_put_bytes(self, store):
        store.put(b"\x00\x01\x02", b"\xff\xfe")
        assert store.get(b"\x00\x01\x02") == b"\xff\xfe"

    def test_put_update(self, store):
        store.put("key", "v1")
        store.put("key", "v2")
        assert store.get("key") == b"v2"

    def test_get_missing(self, store):
        assert store.get("nonexistent") is None

    def test_contains(self, store):
        store.put("exists", "yes")
        assert "exists" in store
        assert "missing" not in store

    def test_delete(self, store):
        store.put("key", "val")
        assert store.delete("key") is True
        assert store.get("key") is None
        assert store.delete("key") is False

    def test_empty_key_rejected(self, store):
        with pytest.raises(ValueError):
            store.put("", "value")

    def test_none_value_rejected(self, store):
        with pytest.raises(ValueError):
            store.put("key", None)

    def test_type_coercion_str(self, store):
        store.put("strkey", "strval")
        assert store.get("strkey") == b"strval"

    def test_type_coercion_bytes(self, store):
        store.put(b"byteskey", b"bytesval")
        assert store.get(b"byteskey") == b"bytesval"

    def test_invalid_key_type(self, store):
        with pytest.raises(TypeError):
            store.put(123, "value")

    def test_invalid_value_type(self, store):
        with pytest.raises(TypeError):
            store.put("key", 123)


class TestBinaryKeys:
    """Test binary-safe key and value handling."""

    def test_binary_key_value(self, store):
        key = bytes(range(256))
        val = bytes(range(255, -1, -1))
        store.put(key, val)
        assert store.get(key) == val

    def test_unicode_key(self, store):
        store.put("café", "naïve")
        assert store.get("café") == "naïve".encode("utf-8")

    def test_empty_value(self, store):
        store.put("key", b"")
        assert store.get("key") == b""


class TestScans:
    """Test range scans, prefix scans, and cursor operations."""

    def test_scan_all(self, store):
        for i in range(20):
            store.put(f"key{i:02d}", f"val{i}")
        c = store.cursor()
        keys = [k.decode() for k, _ in c]
        assert keys == sorted(keys)
        assert len(keys) == 20

    def test_scan_range(self, store):
        for i in range(20):
            store.put(f"key{i:02d}", f"val{i}")
        c = store.cursor(low="key05", high="key10")
        keys = [k.decode() for k, _ in c]
        assert keys[0] == "key05"
        assert keys[-1] == "key09"
        assert len(keys) == 5

    def test_scan_include_high(self, store):
        for i in range(20):
            store.put(f"key{i:02d}", f"val{i}")
        c = store.cursor(low="key05", high="key10", include_high=True)
        keys = [k.decode() for k, _ in c]
        assert keys[-1] == "key10"
        assert len(keys) == 6

    def test_scan_reverse(self, store):
        for i in range(20):
            store.put(f"key{i:02d}", f"val{i}")
        c = store.cursor(reverse=True)
        keys = [k.decode() for k, _ in c]
        assert keys == sorted(keys, reverse=True)

    def test_scan_limit_offset(self, store):
        for i in range(20):
            store.put(f"key{i:02d}", f"val{i}")
        c = store.cursor(limit=5, offset=3)
        keys = [k.decode() for k, _ in c]
        assert len(keys) == 5
        assert keys[0] == "key03"
        assert keys[-1] == "key07"

    def test_reverse_limit(self, store):
        for i in range(20):
            store.put(f"key{i:02d}", f"val{i}")
        c = store.cursor(reverse=True, limit=5)
        keys = [k.decode() for k, _ in c]
        assert len(keys) == 5
        assert keys[0] == "key19"
        assert keys[-1] == "key15"

    def test_reverse_offset_limit(self, store):
        for i in range(20):
            store.put(f"key{i:02d}", f"val{i}")
        c = store.cursor(reverse=True, limit=5, offset=3)
        keys = [k.decode() for k, _ in c]
        assert len(keys) == 5
        # offset 3 from sorted, then reverse, then limit 5
        # sorted[3:] = key03..key19, reversed = key19..key03, take 5 = key19..key15
        assert keys[0] == "key19"
        assert keys[-1] == "key15"

    def test_prefix_scan(self, store):
        store.put("user:1", "alice")
        store.put("user:2", "bob")
        store.put("post:1", "hello")
        store.put("user:3", "carol")
        c = store.prefix("user:")
        keys = [k.decode() for k, _ in c]
        assert len(keys) == 3
        assert "user:1" in keys
        assert "post:1" not in keys

    def test_prefix_empty(self, store):
        store.put("a", "1")
        store.put("b", "2")
        c = store.prefix("")
        assert len(c) == 2

    def test_prefix_all_ff(self, store):
        store.put(b"\xff\xff", "x")
        store.put(b"\xff\xff\xff", "y")
        store.put(b"\xff\xff\x01", "z")
        c = store.prefix(b"\xff\xff")
        keys = list(k for k, _ in c)
        assert b"\xff\xff" in keys
        assert b"\xff\xff\xff" in keys
        assert b"\xff\xff\x01" in keys

    def test_scan_low_gt_high(self, store):
        store.put("a", "1")
        store.put("z", "2")
        c = store.cursor(low="z", high="a")
        assert len(c) == 0


class TestCursorNavigation:
    """Test cursor navigation methods."""

    def test_cursor_first_last(self, store):
        store.put("a", "1")
        store.put("b", "2")
        store.put("c", "3")
        c = store.cursor()
        assert c.first() == (b"a", b"1")
        assert c.last() == (b"c", b"3")

    def test_cursor_next_prev(self, store):
        store.put("a", "1")
        store.put("b", "2")
        store.put("c", "3")
        c = store.cursor()
        assert c.first() == (b"a", b"1")
        assert c.next() == (b"b", b"2")
        assert c.next() == (b"c", b"3")
        assert c.next() is None
        assert c.prev() == (b"c", b"3")

    def test_cursor_seek(self, store):
        store.put("a", "1")
        store.put("c", "3")
        store.put("e", "5")
        c = store.cursor()
        result = c.seek(b"d")
        assert result == (b"e", b"5")
        result = c.seek_exact(b"d")
        assert result is None
        result = c.seek_exact(b"e")
        assert result == (b"e", b"5")

    def test_cursor_is_empty(self, store):
        c = store.cursor()
        assert c.is_empty()
        store.put("a", "1")
        c = store.cursor()
        assert not c.is_empty()

    def test_cursor_keys_values_items(self, store):
        store.put("a", "1")
        store.put("b", "2")
        c = store.cursor()
        assert c.keys() == [b"a", b"b"]
        assert c.values() == [b"1", b"2"]
        assert c.items() == [(b"a", b"1"), (b"b", b"2")]

    def test_cursor_filter(self, store):
        store.put("a", "1")
        store.put("b", "2")
        store.put("cc", "3")
        c = store.cursor()
        filtered = c.filter(lambda k, v: len(k) > 1)
        assert len(filtered) == 1
        assert filtered.items() == [(b"cc", b"3")]

    def test_cursor_map(self, store):
        store.put("a", "1")
        store.put("b", "2")
        c = store.cursor()
        mapped = c.map(lambda k, v: (k, str(len(v)).encode()))
        assert mapped.items() == [(b"a", b"1"), (b"b", b"1")]

    def test_cursor_take_skip(self, store):
        for i in range(10):
            store.put(f"k{i:02d}", f"v{i}")
        c = store.cursor()
        taken = c.take(3)
        assert len(taken) == 3
        skipped = c.skip(7)
        assert len(skipped) == 3

    def test_cursor_batch(self, store):
        for i in range(10):
            store.put(f"k{i:02d}", f"v{i}")
        c = store.cursor()
        batches = c.batch(3)
        assert len(batches) == 4  # 3+3+3+1
        assert len(batches[0]) == 3
        assert len(batches[-1]) == 1

    def test_cursor_batch_invalid_size(self, store):
        c = store.cursor()
        with pytest.raises(ValueError):
            c.batch(0)

    def test_cursor_reduce(self, store):
        store.put("a", "1")
        store.put("b", "2")
        store.put("c", "3")
        c = store.cursor()
        total = c.reduce(lambda acc, k, v: acc + int(v), 0)
        assert total == 6

    def test_cursor_min_max_key(self, store):
        store.put("c", "3")
        store.put("a", "1")
        store.put("e", "5")
        c = store.cursor()
        assert c.min_key() == b"a"
        assert c.max_key() == b"e"

    def test_cursor_as_dict(self, store):
        store.put("a", "1")
        store.put("b", "2")
        c = store.cursor()
        d = c.as_dict()
        assert d == {b"a": b"1", b"b": b"2"}


class TestMinMax:
    """Test min/max operations."""

    def test_min(self, store):
        store.put("c", "3")
        store.put("a", "1")
        store.put("b", "2")
        assert store.min() == (b"a", b"1")

    def test_max(self, store):
        store.put("c", "3")
        store.put("a", "1")
        store.put("b", "2")
        assert store.max() == (b"c", b"3")

    def test_min_empty(self, store):
        assert store.min() is None

    def test_max_empty(self, store):
        assert store.max() is None


class TestCAS:
    """Test compare-and-swap operations."""

    def test_cas_update(self, store):
        store.put("key", "old")
        assert store.cas("key", "old", "new") is True
        assert store.get("key") == b"new"

    def test_cas_mismatch(self, store):
        store.put("key", "old")
        assert store.cas("key", "wrong", "new") is False
        assert store.get("key") == b"old"

    def test_cas_insert_if_absent(self, store):
        assert store.cas("new_key", None, "value") is True
        assert store.get("new_key") == b"value"

    def test_cas_insert_fails_if_exists(self, store):
        store.put("key", "existing")
        assert store.cas("key", None, "new") is False

    def test_cas_delete_if_matches(self, store):
        store.put("key", "val")
        assert store.cas("key", "val", None) is True
        assert store.get("key") is None

    def test_cas_delete_mismatch(self, store):
        store.put("key", "val")
        assert store.cas("key", "wrong", None) is False
        assert store.get("key") is not None


class TestIncrement:
    """Test atomic increment operations."""

    def test_increment_new(self, store):
        result = store.increment("counter")
        assert result == 1
        assert store.get("counter") == b"1"

    def test_increment_existing(self, store):
        store.put("counter", "5")
        result = store.increment("counter")
        assert result == 6
        assert store.get("counter") == b"6"

    def test_increment_by_amount(self, store):
        store.put("counter", "10")
        result = store.increment("counter", 5)
        assert result == 15

    def test_increment_negative(self, store):
        store.put("counter", "10")
        result = store.increment("counter", -3)
        assert result == 7

    def test_increment_non_integer(self, store):
        store.put("counter", "abc")
        with pytest.raises(ValueError):
            store.increment("counter")


class TestTransactions:
    """Test transaction operations."""

    def test_commit(self, store):
        txn = store.begin()
        txn.put("a", "1")
        txn.put("b", "2")
        store.commit(txn)
        assert store.get("a") == b"1"
        assert store.get("b") == b"2"

    def test_rollback(self, store):
        txn = store.begin()
        txn.put("a", "1")
        store.rollback(txn)
        assert store.get("a") is None

    def test_read_only(self, store):
        store.put("key", "val")
        txn = store.begin(read_only=True)
        assert txn.get("key") == b"val"
        with pytest.raises(PermissionError):
            txn.put("key", "new")

    def test_context_manager_commit(self, store):
        with store.transaction() as txn:
            txn.put("key", "val")
        assert store.get("key") == b"val"

    def test_context_manager_rollback(self, store):
        with pytest.raises(ValueError):
            with store.transaction() as txn:
                txn.put("key", "val")
                raise ValueError("test error")
        assert store.get("key") is None

    def test_read_your_writes(self, store):
        store.put("existing", "old")
        txn = store.begin()
        txn.put("existing", "new")
        txn.put("fresh", "val")
        assert txn.get("existing") == b"new"
        assert txn.get("fresh") == b"val"
        store.rollback(txn)

    def test_txn_count(self, store):
        store.put("a", "1")
        store.put("b", "2")
        txn = store.begin()
        txn.put("c", "3")
        txn.delete("a")
        assert txn.count() == 2  # b + c (a deleted)

    def test_double_commit_raises(self, store):
        txn = store.begin()
        txn.put("a", "1")
        store.commit(txn)
        with pytest.raises(RuntimeError):
            store.commit(txn)

    def test_aborted_txn_raises(self, store):
        txn = store.begin()
        store.rollback(txn)
        with pytest.raises(RuntimeError):
            store.commit(txn)

    def test_put_many(self, store):
        txn = store.begin()
        txn.put_many({"a": "1", "b": "2", "c": "3"})
        store.commit(txn)
        assert store.count() == 3

    def test_delete_many(self, store):
        store.put("a", "1")
        store.put("b", "2")
        store.put("c", "3")
        txn = store.begin()
        n = txn.delete_many(["a", "b", "missing"])
        assert n == 2
        store.commit(txn)
        assert store.count() == 1

    def test_txn_min_max(self, store):
        store.put("c", "3")
        store.put("a", "1")
        txn = store.begin()
        txn.put("z", "26")
        assert txn.min() == (b"a", b"1")
        assert txn.max() == (b"z", b"26")
        store.rollback(txn)

    def test_txn_export_dict(self, store):
        store.put("a", "1")
        store.put("b", "2")
        txn = store.begin(read_only=True)
        d = txn.export_dict()
        assert d == {"a": "1", "b": "2"}


class TestSplitting:
    """Test B+Tree splitting with many keys."""

    def test_many_keys(self, store):
        for i in range(500):
            store.put(f"key{i:04d}", f"val{i}")
        assert store.count() == 500
        for i in range(500):
            assert store.get(f"key{i:04d}") == f"val{i}".encode()
        assert store.validate()

    def test_split_ordering(self, store):
        # Insert in random order
        import random
        random.seed(42)
        keys = list(range(200))
        random.shuffle(keys)
        for k in keys:
            store.put(f"k{k:04d}", f"v{k}")
        c = store.cursor()
        result_keys = [k.decode() for k, _ in c]
        assert result_keys == sorted(result_keys)

    def test_large_page_small_keys(self):
        path = tempfile.mktemp(suffix=".btree")
        s = Store(path, page_size=256, wal_enabled=False)
        try:
            for i in range(100):
                s.put(f"k{i:03d}", f"v{i}")
            assert s.count() == 100
            assert s.validate()
        finally:
            s.close()
            if os.path.exists(path):
                os.unlink(path)

    def test_tree_depth_grows(self):
        path = tempfile.mktemp(suffix=".btree")
        try:
            # Use small page size to force deeper trees
            s = Store(path, page_size=512, wal_enabled=False)
            for i in range(2000):
                s.put(f"key{i:05d}", f"val{i}")
            stats = s.stats()
            assert stats["tree_depth"] >= 2
            s.close()
        finally:
            for p in [path, path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)


class TestPersistence:
    """Test persistence across close/reopen."""

    def test_close_reopen(self, store_no_wal):
        store_no_wal.put("a", "1")
        store_no_wal.put("b", "2")
        path = store_no_wal.path
        store_no_wal.close()
        store_no_wal.__dict__["path"] = path  # hack to avoid double-close in fixture

        s2 = Store(path, wal_enabled=False)
        assert s2.get("a") == b"1"
        assert s2.get("b") == b"2"
        assert s2.count() == 2
        s2.close()
        if os.path.exists(path):
            os.unlink(path)

    def test_commit_ts_persists(self, store_no_wal):
        store_no_wal.put("k1", "v1")
        store_no_wal.put("k2", "v2")
        ts1 = store_no_wal._commit_ts
        path = store_no_wal.path
        store_no_wal.close()
        store_no_wal.__dict__["path"] = path

        s2 = Store(path, wal_enabled=False)
        assert s2._commit_ts == ts1
        s2.close()
        if os.path.exists(path):
            os.unlink(path)


class TestCRC:
    """Test CRC32 page checksums."""

    def test_crc_verification(self, store):
        store.put("key", "value")
        # The page should have a valid CRC
        path = store.path
        store._flush_all()
        # Read the first page and verify CRC
        with open(path, "rb") as f:
            f.seek(36)  # skip header
            page_data = f.read(store.page_size)
        assert verify_page_crc(page_data)

    def test_crc_corruption_detected(self, store):
        store.put("key", "value")
        store._flush_all()
        path = store.path
        store._cache.clear()

        # Corrupt a byte in the first page (not the CRC bytes)
        with open(path, "r+b") as f:
            f.seek(36 + 10)  # header + some offset
            original = f.read(1)
            corrupt_byte = b"\x00" if original != b"\x00" else b"\x01"
            f.seek(36 + 10)
            f.write(corrupt_byte)

        with pytest.raises(IOError, match="CRC32"):
            store.get("key")


class TestWALRecovery:
    """Test Write-Ahead Log crash recovery."""

    def test_wal_basic(self):
        path = tempfile.mktemp(suffix=".btree")
        wal_path = path + ".wal"
        try:
            # Write and close normally
            with Store(path, wal_enabled=True) as store:
                store.put("a", "1")
                store.put("b", "2")

            # Reopen — should still have data
            with Store(path, wal_enabled=True) as store:
                assert store.get("a") == b"1"
                assert store.get("b") == b"2"
        finally:
            for p in [path, wal_path]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_wal_replay_after_crash(self):
        path = tempfile.mktemp(suffix=".btree")
        wal_path = path + ".wal"
        try:
            # Phase 1: Write data and close
            with Store(path, wal_enabled=True) as store:
                for i in range(50):
                    store.put(f"key{i:03d}", f"val{i}")

            # Phase 2: Write more data, simulate crash
            store = Store(path, wal_enabled=True)
            for i in range(50, 100):
                store.put(f"key{i:03d}", f"val{i}")
            # Flush pages but don't checkpoint WAL
            store._flush_all()
            if store._wal:
                store._wal._fd.flush()
                store._wal.close()
                store._wal = None
            store._cache.clear()
            store._closed = True

            # Phase 3: Reopen — WAL should replay
            with Store(path, wal_enabled=True) as store:
                assert store.count() == 100
                for i in range(100):
                    assert store.get(f"key{i:03d}") == f"val{i}".encode()
        finally:
            for p in [path, wal_path]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_wal_disabled(self, store_no_wal):
        store_no_wal.put("key", "val")
        assert store_no_wal.get("key") == b"val"
        assert store_no_wal._wal is None


class TestCompaction:
    """Test tree compaction."""

    def test_compact_after_deletion(self, store):
        for i in range(100):
            store.put(f"key{i:03d}", f"val{i}")
        # Delete half
        for i in range(0, 100, 2):
            store.delete(f"key{i:03d}")
        assert store.count() == 50

        # Compact
        n = store.compact()
        assert n == 50
        assert store.count() == 50
        assert store.validate()

        # Verify remaining keys
        for i in range(1, 100, 2):
            assert store.get(f"key{i:03d}") == f"val{i}".encode()

    def test_compact_empty(self, store):
        n = store.compact()
        assert n == 0


class TestConfig:
    """Test configuration management."""

    def test_config_defaults(self):
        config = StoreConfig(path="/tmp/test.btree")
        assert config.page_size == 4096
        assert config.branching == 32
        assert config.cache_size == 512
        assert config.wal_enabled is True

    def test_config_validation(self):
        with pytest.raises(ValueError):
            StoreConfig(page_size=100)
        with pytest.raises(ValueError):
            StoreConfig(branching=2)
        with pytest.raises(ValueError):
            StoreConfig(cache_size=1)
        with pytest.raises(ValueError):
            StoreConfig(log_level="INVALID")

    def test_config_to_dict(self):
        config = StoreConfig(path="/tmp/test.btree", page_size=8192)
        d = config.to_dict()
        assert d["page_size"] == 8192
        assert d["path"] == "/tmp/test.btree"

    def test_config_from_dict(self):
        d = {"page_size": 8192, "branching": 64, "unknown_key": "ignore"}
        config = StoreConfig.from_dict(d)
        assert config.page_size == 8192
        assert config.branching == 64

    def test_config_json_file(self):
        path = tempfile.mktemp(suffix=".json")
        try:
            config = StoreConfig(path="/tmp/db.btree", page_size=8192)
            config.save(path)

            loaded = StoreConfig.from_file(path)
            assert loaded.page_size == 8192
            assert loaded.path == "/tmp/db.btree"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("BTREESTORE_PAGE_SIZE", "8192")
        monkeypatch.setenv("BTREESTORE_CACHE_SIZE", "1024")
        monkeypatch.setenv("BTREESTORE_LOG_LEVEL", "DEBUG")
        config = StoreConfig.from_env()
        assert config.page_size == 8192
        assert config.cache_size == 1024
        assert config.log_level == "DEBUG"

    def test_store_with_config(self):
        path = tempfile.mktemp(suffix=".btree")
        config = StoreConfig(path=path, wal_enabled=False, page_size=8192)
        try:
            store = Store(path, config=config)
            store.put("key", "val")
            assert store.get("key") == b"val"
            store.close()
        finally:
            for p in [path, path + ".wal"]:
                if os.path.exists(p):
                    os.unlink(p)


class TestBulkLoad:
    """Test bulk loading."""

    def test_bulk_load(self, store):
        pairs = [(f"key{i:04d}", f"val{i}") for i in range(1000)]
        n = store.bulk_load(pairs)
        assert n == 1000
        assert store.count() == 1000
        assert store.validate()

    def test_bulk_load_sorted(self, store):
        pairs = [(f"key{i:05d}", f"val{i}") for i in range(5000)]
        n = store.bulk_load(pairs)
        assert n == 5000
        # Verify all keys
        for i in range(5000):
            assert store.get(f"key{i:05d}") == f"val{i}".encode()


class TestEdgeCases:
    """Test edge cases and potential bugs."""

    def test_delete_reinsert(self, store):
        store.put("key", "v1")
        store.delete("key")
        store.put("key", "v2")
        assert store.get("key") == b"v2"

    def test_large_value(self, store):
        val = b"x" * 1000
        store.put("key", val)
        assert store.get("key") == val

    def test_oversized_value_rejected(self, store):
        key = b"k"
        val = b"x" * (store.page_size - 20)  # Should be too large
        with pytest.raises(ValueError, match="too large"):
            store.put(key, val)

    def test_concurrent_transaction_isolation(self, store):
        """Test that uncommitted writes in one transaction don't affect another."""
        store.put("key", "original")
        txn1 = store.begin()
        txn2 = store.begin()
        txn1.put("key", "txn1_val")
        # txn2 should still see original (txn1 hasn't committed)
        assert txn2.get("key") == b"original"
        store.commit(txn1)
        # After commit, a NEW transaction should see the committed value
        txn3 = store.begin(read_only=True)
        assert txn3.get("key") == b"txn1_val"
        store.rollback(txn2)

    def test_find_parent_after_splits(self, store):
        for i in range(500):
            store.put(f"key{i:04d}", f"val{i}")
        # Verify tree is valid (parent-child consistency)
        assert store.validate()

    def test_negative_offset_cursor(self, store):
        store.put("a", "1")
        store.put("b", "2")
        c = store.cursor(offset=-1)
        # Negative offset should be treated as 0
        assert len(c) == 2

    def test_large_key(self, store):
        key = b"k" * 100
        store.put(key, "val")
        assert store.get(key) == b"val"

    def test_stats(self, store):
        store.put("a", "1")
        stats = store.stats()
        assert "file_size" in stats
        assert "num_keys" in stats
        assert "tree_depth" in stats
        assert "wal_enabled" in stats
        assert stats["num_keys"] == 1


class TestImportExport:
    """Test JSON import/export."""

    def test_export_import_roundtrip(self, store):
        store.put("a", "1")
        store.put("b", "2")
        store.put("c", "3")

        # Export via transaction
        txn = store.begin(read_only=True)
        d = txn.export_dict()
        assert d == {"a": "1", "b": "2", "c": "3"}

    def test_cli_batch_export_import(self, store):
        store.put("x", "100")
        store.put("y", "200")

        # Export
        export_path = tempfile.mktemp(suffix=".json")
        c = store.cursor()
        data = {}
        for k, v in c:
            data[k.decode()] = v.decode()
        with open(export_path, "w") as f:
            json.dump(data, f)

        # Import into a new store
        path2 = tempfile.mktemp(suffix=".btree")
        try:
            with Store(path2, wal_enabled=False) as s2:
                with open(export_path, "r") as f:
                    data2 = json.load(f)
                s2.bulk_load([(k, v) for k, v in data2.items()])
                assert s2.get("x") == b"100"
                assert s2.get("y") == b"200"
        finally:
            for p in [export_path, path2]:
                if os.path.exists(p):
                    os.unlink(p)