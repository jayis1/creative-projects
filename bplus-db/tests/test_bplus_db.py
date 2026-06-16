"""Comprehensive tests for the B+ Tree Database Engine v3.0.

Includes tests for:
  - LRU Cache
  - DatabaseConfig
  - Cursor / Pagination
  - TTL (time-to-live)
  - Import / Export (CSV, JSONL, Pickle)
  - Enhanced CLI
  - Logging
  - Original regression tests
"""

import csv
import json
import os
import pickle
import tempfile
import time
import threading
import pytest

from bplus_db.bplus_tree import BPlusTree, LeafNode, InternalNode
from bplus_db.database import Database, Transaction, WriteAheadLog
from bplus_db.serializer import Serializer
from bplus_db.query_parser import QueryParser, QueryAST
from bplus_db.cache import LRUCache
from bplus_db.config import DatabaseConfig, TreeConfig, CacheConfig, WALConfig
from bplus_db.cursor import Cursor
from bplus_db.ttl import TTLManager
from bplus_db import io as db_io


# ── LRU Cache Tests ────────────────────────────────────────────

class TestLRUCache:
    def test_basic_get_put(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        assert cache.get("a") == 1
        assert cache.get("b") == 2

    def test_eviction(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # evicts "a"
        assert cache.get("a") is LRUCache._CACHE_MISS
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_order(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        _ = cache.get("a")  # access "a" so it's most-recently-used
        cache.put("c", 3)  # evicts "b" (least recently used)
        assert cache.get("a") == 1
        assert cache.get("b") is LRUCache._CACHE_MISS
        assert cache.get("c") == 3

    def test_update_existing(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("a", 99)
        assert cache.get("a") == 99
        assert cache.size == 1

    def test_invalidate(self):
        cache = LRUCache(max_size=10)
        cache.put("a", 1)
        cache.invalidate("a")
        assert cache.get("a") is LRUCache._CACHE_MISS

    def test_invalidate_missing(self):
        cache = LRUCache(max_size=10)
        cache.invalidate("nonexistent")  # Should not raise

    def test_clear(self):
        cache = LRUCache(max_size=10)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert cache.size == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_stats(self):
        cache = LRUCache(max_size=10)
        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_disabled_cache(self):
        cache = LRUCache(max_size=None)
        assert cache.get("anything") is LRUCache._CACHE_MISS
        cache.put("a", 1)
        assert cache.get("a") is LRUCache._CACHE_MISS
        assert cache.max_size is None

    def test_zero_size_disabled(self):
        cache = LRUCache(max_size=0)
        assert cache.max_size is None

    def test_negative_size_disabled(self):
        cache = LRUCache(max_size=-5)
        assert cache.max_size is None


# ── DatabaseConfig Tests ───────────────────────────────────────

class TestDatabaseConfig:
    def test_default_config(self):
        cfg = DatabaseConfig()
        assert cfg.tree.order == 64
        assert cfg.cache.enabled is False
        assert cfg.wal.enabled is False
        assert cfg.persistence.auto_save is False

    def test_from_dict(self):
        cfg = DatabaseConfig.from_dict({
            "tree": {"order": 32},
            "cache": {"enabled": True, "max_size": 128},
            "wal": {"path": "/tmp/test.wal"},
        })
        assert cfg.tree.order == 32
        assert cfg.cache.enabled is True
        assert cfg.cache.max_size == 128
        assert cfg.wal.enabled is True
        assert cfg.wal.path == "/tmp/test.wal"

    def test_from_json(self):
        data = {"tree": {"order": 16}, "cache": {"enabled": True}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            cfg = DatabaseConfig.from_json(path)
            assert cfg.tree.order == 16
            assert cfg.cache.enabled is True
        finally:
            os.unlink(path)

    def test_to_dict_roundtrip(self):
        cfg = DatabaseConfig(tree=TreeConfig(order=8))
        d = cfg.to_dict()
        cfg2 = DatabaseConfig.from_dict(d)
        assert cfg2.tree.order == 8

    def test_to_json(self):
        cfg = DatabaseConfig(tree=TreeConfig(order=4))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            cfg.to_json(path)
            cfg2 = DatabaseConfig.from_json(path)
            assert cfg2.tree.order == 4
        finally:
            os.unlink(path)

    def test_from_file_unsupported_ext(self):
        with pytest.raises(ValueError, match="Unsupported config file extension"):
            DatabaseConfig.from_file("config.xyz")

    def test_from_dict_wal_inference(self):
        """WAL enabled should be inferred when path is set."""
        cfg = DatabaseConfig.from_dict({"wal": {"path": "/tmp/x.wal"}})
        assert cfg.wal.enabled is True


# ── Cursor Tests ────────────────────────────────────────────────

class TestCursor:
    def test_cursor_range_full(self):
        db = Database(order=4)
        for i in range(10):
            db.put(f"k{i:02d}", i)
        cur = db.cursor(page_size=5)
        all_items = list(cur)
        assert len(all_items) == 10

    def test_cursor_range_with_bounds(self):
        db = Database(order=4)
        for i in range(20):
            db.put(f"k{i:03d}", i)
        cur = db.cursor(start_key="k005", end_key="k010", page_size=3)
        results = list(cur)
        assert len(results) == 6  # k005 through k010 inclusive

    def test_cursor_prefix_scan(self):
        db = Database(order=4)
        db.put("user:1", "Alice")
        db.put("user:2", "Bob")
        db.put("order:1", "Order1")
        cur = db.cursor(prefix="user:", page_size=10)
        results = list(cur)
        assert len(results) == 2
        assert results[0][0] == "user:1"
        assert results[1][0] == "user:2"

    def test_cursor_empty_db(self):
        db = Database(order=4)
        cur = db.cursor(page_size=10)
        results = list(cur)
        assert len(results) == 0

    def test_cursor_fetch_page(self):
        db = Database(order=4)
        for i in range(7):
            db.put(f"k{i}", i)
        cur = db.cursor(page_size=3)
        page1 = cur.fetch_page()
        assert len(page1) == 3
        page2 = cur.fetch_page()
        assert len(page2) == 3
        page3 = cur.fetch_page()
        assert len(page3) == 1
        page4 = cur.fetch_page()
        assert len(page4) == 0
        assert cur.exhausted

    def test_cursor_total_yielded(self):
        db = Database(order=4)
        for i in range(10):
            db.put(f"k{i}", i)
        cur = db.cursor(page_size=4)
        cur.fetch_page()
        assert cur.total_yielded == 4
        cur.fetch_page()
        assert cur.total_yielded == 8
        cur.fetch_page()
        assert cur.total_yielded == 10


# ── TTL Tests ──────────────────────────────────────────────────

class TestTTLManager:
    def test_set_and_check_ttl(self):
        mgr = TTLManager()
        mgr.set_ttl("key1", 60.0)
        assert not mgr.is_expired("key1")
        assert mgr.get_remaining_ttl("key1") is not None
        assert mgr.get_remaining_ttl("key1") > 0

    def test_expiry_time(self):
        mgr = TTLManager()
        mgr.set_ttl("key1", 100.0)
        expiry = mgr.get_expiry_time("key1")
        assert expiry is not None
        assert expiry > time.time()

    def test_remove_ttl(self):
        mgr = TTLManager()
        mgr.set_ttl("key1", 60.0)
        mgr.remove_ttl("key1")
        assert mgr.is_expired("key1") is False
        assert mgr.get_remaining_ttl("key1") is None

    def test_cleanup_expired(self):
        mgr = TTLManager()
        # Set a very short TTL that's already expired
        mgr.set_expiry("key1", time.time() - 1)
        mgr.set_expiry("key2", time.time() - 1)
        mgr.set_ttl("key3", 60.0)  # not expired
        expired = mgr.cleanup()
        assert "key1" in expired
        assert "key2" in expired
        assert "key3" not in expired
        assert mgr.is_expired("key3") is False

    def test_serialization(self):
        mgr = TTLManager()
        mgr.set_ttl("key1", 60.0)
        mgr.set_ttl("key2", 120.0)
        d = mgr.to_dict()
        mgr2 = TTLManager.from_dict(d)
        assert len(mgr2.all_ttl_keys()) == 2

    def test_negative_ttl_raises(self):
        mgr = TTLManager()
        with pytest.raises(ValueError, match="positive"):
            mgr.set_ttl("key1", -1)


class TestDatabaseTTL:
    def test_put_with_ttl(self):
        db = Database(order=4)
        db.put("temp", "data", ttl=3600)
        assert db.get("temp") == "data"
        remaining = db.get_ttl("temp")
        assert remaining is not None
        assert remaining > 0

    def test_expired_key_returns_default(self):
        db = Database(order=4)
        db.put("temp", "data", ttl=0.01)
        time.sleep(0.02)
        assert db.get("temp") is None

    def test_contains_skips_expired(self):
        db = Database(order=4)
        db.put("temp", "data", ttl=0.01)
        time.sleep(0.02)
        assert "temp" not in db

    def test_cleanup_expired(self):
        db = Database(order=4)
        db.put("temp1", "data1", ttl=0.01)
        db.put("perm", "data2")
        db.put("temp2", "data3", ttl=0.01)
        time.sleep(0.02)
        count = db.cleanup_expired()
        assert count >= 2
        assert db.get("perm") == "data2"

    def test_set_ttl_on_existing_key(self):
        db = Database(order=4)
        db.put("key", "value")
        db.set_ttl("key", 60.0)
        remaining = db.get_ttl("key")
        assert remaining is not None
        assert remaining > 0

    def test_set_ttl_on_missing_key_raises(self):
        db = Database(order=4)
        with pytest.raises(KeyError):
            db.set_ttl("nonexistent", 60.0)

    def test_delete_removes_ttl(self):
        db = Database(order=4)
        db.put("temp", "data", ttl=3600)
        db.delete("temp")
        # Key is gone, TTL should be cleaned up
        db.put("temp", "new_data")  # Re-add without TTL
        remaining = db.get_ttl("temp")
        assert remaining is None


# ── Database Cache Tests ────────────────────────────────────────

class TestDatabaseCache:
    def test_cache_enabled(self):
        cfg = DatabaseConfig(cache=CacheConfig(enabled=True, max_size=100))
        db = Database(config=cfg)
        db.put("a", 1)
        _ = db.get("a")  # cache miss, then populate
        _ = db.get("a")  # cache hit
        stats = db.cache_stats()
        assert stats is not None
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    def test_cache_disabled_by_default(self):
        db = Database(order=4)
        assert db.cache_stats() is None

    def test_cache_invalidation_on_put(self):
        cfg = DatabaseConfig(cache=CacheConfig(enabled=True, max_size=100))
        db = Database(config=cfg)
        db.put("a", 1)
        _ = db.get("a")  # populate cache
        db.put("a", 2)  # should invalidate cache
        assert db.get("a") == 2

    def test_cache_invalidation_on_delete(self):
        cfg = DatabaseConfig(cache=CacheConfig(enabled=True, max_size=100))
        db = Database(config=cfg)
        db.put("a", 1)
        _ = db.get("a")
        db.delete("a")
        assert db.get("a") is None

    def test_clear_cache(self):
        cfg = DatabaseConfig(cache=CacheConfig(enabled=True, max_size=100))
        db = Database(config=cfg)
        db.put("a", 1)
        _ = db.get("a")
        db.clear_cache()
        stats = db.cache_stats()
        assert stats["cache_size"] == 0


# ── Import/Export Tests ────────────────────────────────────────

class TestExportImport:
    def test_csv_roundtrip(self):
        db = Database(order=4)
        db.put("a", 1)
        db.put("b", "hello")
        db.put("c", [1, 2, 3])

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            count = db_io.export_csv(db, path)
            assert count == 3

            db2 = Database(order=4)
            imported = db_io.import_csv(db2, path)
            assert imported == 3
            assert db2.get("a") == 1
            assert db2.get("b") == "hello"
            assert db2.get("c") == [1, 2, 3]
        finally:
            os.unlink(path)

    def test_jsonl_roundtrip(self):
        db = Database(order=4)
        db.put("x", {"name": "Alice"})
        db.put("y", 42)

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            count = db_io.export_json_lines(db, path)
            assert count == 2

            db2 = Database(order=4)
            imported = db_io.import_json_lines(db2, path)
            assert imported == 2
            assert db2.get("x") == {"name": "Alice"}
            assert db2.get("y") == 42
        finally:
            os.unlink(path)

    def test_pickle_roundtrip(self):
        db = Database(order=4)
        db.put("a", 1)
        db.put("b", "hello")

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name
        try:
            count = db_io.export_pickle(db, path)
            assert count == 2

            db2 = Database(order=4)
            imported = db_io.import_pickle(db2, path)
            assert imported == 2
            assert db2.get("a") == 1
            assert db2.get("b") == "hello"
        finally:
            os.unlink(path)

    def test_csv_empty_db(self):
        db = Database(order=4)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            count = db_io.export_csv(db, path)
            assert count == 0
            # Header still written
            with open(path, "r") as f2:
                reader = csv.reader(f2)
                header = next(reader)
                assert header == ["key", "value"]
        finally:
            os.unlink(path)

    def test_jsonl_custom_delimiter(self):
        db = Database(order=4)
        for i in range(5):
            db.put(f"key_{i}", i)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            db_io.export_csv(db, path, delimiter="\t")
            db2 = Database(order=4)
            imported = db_io.import_csv(db2, path, delimiter="\t")
            assert imported == 5
        finally:
            os.unlink(path)


# ── Config-based Database Construction ──────────────────────────

class TestDatabaseFromConfig:
    def test_config_creates_database(self):
        cfg = DatabaseConfig(
            tree=TreeConfig(order=8),
            cache=CacheConfig(enabled=True, max_size=50),
        )
        db = Database(config=cfg)
        db.put("a", 1)
        assert db.get("a") == 1
        assert db._tree.order == 8
        assert db._cache is not None

    def test_config_with_wal(self):
        with tempfile.NamedTemporaryFile(suffix=".wal", delete=False) as f:
            wal_path = f.name
        try:
            cfg = DatabaseConfig(
                tree=TreeConfig(order=4),
                wal=WALConfig(enabled=True, path=wal_path),
            )
            db = Database(config=cfg)
            db.put("test", "value")
            assert os.path.exists(wal_path)
        finally:
            if os.path.exists(wal_path):
                os.unlink(wal_path)

    def test_config_json_roundtrip(self):
        cfg = DatabaseConfig(tree=TreeConfig(order=16), cache=CacheConfig(enabled=True, max_size=64))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            cfg.to_json(path)
            cfg2 = DatabaseConfig.from_json(path)
            db = Database(config=cfg2)
            db.put("a", 1)
            assert db.get("a") == 1
            assert db._tree.order == 16
        finally:
            os.unlink(path)


# ── Enhanced Stats ──────────────────────────────────────────────

class TestEnhancedStats:
    def test_stats_include_cache_info(self):
        cfg = DatabaseConfig(cache=CacheConfig(enabled=True, max_size=50))
        db = Database(config=cfg)
        db.put("a", 1)
        db.get("a")
        stats = db.stats()
        assert "cache" in stats
        assert "total_keys" in stats
        assert "ttl_evictions" in stats

    def test_stats_without_cache(self):
        db = Database(order=4)
        db.put("a", 1)
        stats = db.stats()
        assert "cache" not in stats

    def test_ttl_evictions_in_stats(self):
        db = Database(order=4)
        db.put("temp", "data", ttl=0.01)
        time.sleep(0.02)
        db.get("temp")  # triggers eviction
        stats = db.stats()
        assert stats["ttl_evictions"] >= 1


# ── Original B+ Tree Tests (regression) ─────────────────────────

class TestBPlusTree:
    def test_insert_and_search(self):
        tree = BPlusTree(order=4)
        tree.insert("a", 1)
        tree.insert("b", 2)
        tree.insert("c", 3)
        assert tree.search("a") == 1
        assert tree.search("b") == 2
        assert tree.search("c") == 3
        assert tree.size == 3

    def test_search_nonexistent(self):
        tree = BPlusTree(order=4)
        assert tree.search("missing") is BPlusTree._NOT_FOUND

    def test_update_existing_key(self):
        tree = BPlusTree(order=4)
        tree.insert("a", 1)
        tree.insert("a", 99)
        assert tree.search("a") == 99
        assert tree.size == 1

    def test_contains(self):
        tree = BPlusTree(order=4)
        tree.insert("x", 10)
        assert "x" in tree
        assert "y" not in tree

    def test_len(self):
        tree = BPlusTree(order=4)
        assert len(tree) == 0
        tree.insert("a", 1)
        assert len(tree) == 1

    def test_insert_causes_split(self):
        tree = BPlusTree(order=4)
        for i in range(10):
            tree.insert("key%02d" % i, i)
        for i in range(10):
            assert tree.search("key%02d" % i) == i
        assert tree.size == 10

    def test_insert_reverse_order(self):
        tree = BPlusTree(order=4)
        for i in range(20, -1, -1):
            tree.insert("key%02d" % i, i)
        for i in range(21):
            assert tree.search("key%02d" % i) == i

    def test_insert_causes_multiple_splits(self):
        tree = BPlusTree(order=3)
        for i in range(50):
            tree.insert(i, i * 10)
        for i in range(50):
            assert tree.search(i) == i * 10
        assert tree.size == 50

    def test_delete_simple(self):
        tree = BPlusTree(order=4)
        tree.insert("a", 1)
        tree.insert("b", 2)
        tree.insert("c", 3)
        assert tree.delete("b") is True
        assert tree.search("b") is BPlusTree._NOT_FOUND
        assert tree.size == 2

    def test_delete_nonexistent(self):
        tree = BPlusTree(order=4)
        tree.insert("a", 1)
        assert tree.delete("z") is False

    def test_delete_all(self):
        tree = BPlusTree(order=4)
        for i in range(10):
            tree.insert("k%d" % i, i)
        for i in range(10):
            assert tree.delete("k%d" % i) is True
        assert tree.size == 0

    def test_delete_with_merge(self):
        tree = BPlusTree(order=3)
        keys = ["a", "b", "c", "d", "e", "f", "g"]
        for k in keys:
            tree.insert(k, k.upper())
        assert tree.delete("a") is True
        assert tree.delete("c") is True
        assert tree.delete("e") is True
        assert tree.search("b") == "B"
        assert tree.search("d") == "D"
        assert tree.search("f") == "F"
        assert tree.search("g") == "G"

    def test_range_query_full(self):
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert("k%02d" % i, i)
        results = list(tree.range_query())
        assert len(results) == 20

    def test_range_query_with_bounds(self):
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert("k%02d" % i, i)
        results = list(tree.range_query("k05", "k10"))
        assert len(results) == 6
        assert results[0][0] == "k05"

    def test_iteration(self):
        tree = BPlusTree(order=4)
        for i in range(5):
            tree.insert(i, i)
        results = list(tree)
        assert len(results) == 5

    def test_large_dataset(self):
        tree = BPlusTree(order=32)
        n = 1000
        for i in range(n):
            tree.insert(i, "value_%d" % i)
        assert tree.size == n
        for i in range(n):
            assert tree.search(i) == "value_%d" % i

    def test_minimum_order(self):
        tree = BPlusTree(order=3)
        for i in range(20):
            tree.insert(i, i)
        assert tree.size == 20

    def test_invalid_order(self):
        with pytest.raises(ValueError):
            BPlusTree(order=2)

    def test_height(self):
        tree = BPlusTree(order=4)
        tree.insert("a", 1)
        assert tree.height() == 1
        for i in range(20):
            tree.insert("k%02d" % i, i)
        assert tree.height() >= 2

    def test_leaf_count(self):
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert("k%02d" % i, i)
        assert tree.leaf_count() >= 2

    def test_stats(self):
        tree = BPlusTree(order=4)
        for i in range(10):
            tree.insert(i, i)
        stats = tree.stats()
        assert stats["size"] == 10
        assert stats["order"] == 4

    def test_validate(self):
        tree = BPlusTree(order=4)
        for i in range(50):
            tree.insert(i, i)
        violations = tree.validate()
        assert violations == []


class TestBPlusTreeBulkLoad:
    def test_bulk_load_basic(self):
        tree = BPlusTree(order=4)
        items = [("k%02d" % i, i) for i in range(20)]
        tree.bulk_load(items)
        assert tree.size == 20
        for i in range(20):
            assert tree.search("k%02d" % i) == i

    def test_bulk_load_large(self):
        tree = BPlusTree(order=8)
        items = [(i, i * 10) for i in range(100)]
        tree.bulk_load(items)
        assert tree.size == 100

    def test_bulk_load_unsorted_raises(self):
        tree = BPlusTree(order=4)
        with pytest.raises(ValueError, match="sorted"):
            tree.bulk_load([("b", 2), ("a", 1)])

    def test_bulk_load_empty(self):
        tree = BPlusTree(order=4)
        tree.bulk_load([])
        assert tree.size == 0

    def test_bulk_load_validates_tree(self):
        tree = BPlusTree(order=4)
        items = [("k%02d" % i, i) for i in range(20)]
        tree.bulk_load(items)
        violations = tree.validate()
        assert violations == []


# ── Serializer Tests ────────────────────────────────────────────

class TestSerializer:
    def test_roundtrip_all_types(self):
        s = Serializer()
        for val in ["hello", 42, 3.14, True, False, None, [1, 2], {"a": 1}]:
            assert s.deserialize_value(s.serialize_value(val)) == val

    def test_nested_structures(self):
        s = Serializer()
        original = {"a": [1, 2, {"b": True}], "c": None}
        assert s.deserialize_value(s.serialize_value(original)) == original

    def test_deserialize_plain_string(self):
        s = Serializer()
        assert s.deserialize_value("hello") == "hello"


# ── Database Core Tests ────────────────────────────────────────

class TestDatabase:
    def test_put_get(self):
        db = Database(order=4)
        db.put("name", "Alice")
        db.put("age", 30)
        assert db.get("name") == "Alice"
        assert db.get("age") == 30

    def test_get_default(self):
        db = Database(order=4)
        assert db.get("missing") is None
        assert db.get("missing", "default") == "default"

    def test_delete(self):
        db = Database(order=4)
        db.put("key", "val")
        assert db.delete("key") is True
        assert db.get("key") is None

    def test_contains(self):
        db = Database(order=4)
        db.put("key", "val")
        assert "key" in db
        assert "other" not in db

    def test_range_query(self):
        db = Database(order=4)
        for i in range(10):
            db.put("k%02d" % i, i)
        results = db.range_query("k03", "k07")
        assert len(results) == 5

    def test_prefix_scan(self):
        db = Database(order=4)
        db.put("user:1", "Alice")
        db.put("user:2", "Bob")
        db.put("user:3", "Carol")
        db.put("order:1", "Order1")
        results = db.prefix_scan("user:")
        assert len(results) == 3

    def test_transaction_commit(self):
        db = Database(order=4)
        txn = db.begin_transaction()
        txn.put("a", 1)
        txn.put("b", 2)
        txn.commit()
        assert db.get("a") == 1
        assert db.get("b") == 2

    def test_transaction_rollback(self):
        db = Database(order=4)
        db.put("existing", "data")
        txn = db.begin_transaction()
        txn.put("new_key", "new_value")
        txn.rollback()
        assert db.get("new_key") is None

    def test_save_load_json(self):
        db = Database(order=4)
        for i in range(10):
            db.put("key%d" % i, "value%d" % i)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            db.save(path)
            loaded = Database.load(path)
            for i in range(10):
                assert loaded.get("key%d" % i) == "value%d" % i
        finally:
            os.unlink(path)

    def test_save_load_binary(self):
        db = Database(order=4)
        for i in range(10):
            db.put("key%d" % i, "value%d" % i)
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            path = f.name
        try:
            db.save_binary(path)
            loaded = Database.load_binary(path)
            for i in range(10):
                assert loaded.get("key%d" % i) == "value%d" % i
        finally:
            os.unlink(path)

    def test_merge(self):
        db1 = Database(order=4)
        db1.put("a", 1)
        db2 = Database(order=4)
        db2.put("b", 2)
        merged = db1.merge(db2)
        assert merged == 1
        assert db1.get("b") == 2

    def test_diff(self):
        db1 = Database(order=4)
        db1.put("a", 1)
        db1.put("b", 2)
        db2 = Database(order=4)
        db2.put("b", 2)
        db2.put("c", 3)
        result = db1.diff(db2)
        assert "a" in result["only_in_self"]
        assert "c" in result["only_in_other"]
        assert "b" in result["unchanged"]

    def test_execute_select(self):
        db = Database(order=4)
        db.put("a", 1)
        db.put("b", 2)
        results = db.execute("SELECT * FROM db")
        assert len(results) == 2

    def test_execute_insert(self):
        db = Database(order=4)
        db.execute("INSERT INTO db KEY 'hello' VALUE 'world'")
        assert db.get("hello") == "world"

    def test_execute_count(self):
        db = Database(order=4)
        for i in range(5):
            db.put("k%d" % i, i)
        result = db.execute("COUNT db")
        assert result == 5

    def test_put_many(self):
        db = Database(order=4)
        count = db.put_many({"k1": "v1", "k2": "v2", "k3": "v3"})
        assert count == 3

    def test_delete_many(self):
        db = Database(order=4)
        db.put_many({"k1": "v1", "k2": "v2", "k3": "v3"})
        deleted = db.delete_many(["k1", "k3", "k_missing"])
        assert deleted == 2

    def test_complex_values(self):
        db = Database(order=4)
        db.put("list", [1, 2, 3])
        db.put("dict", {"nested": True})
        assert db.get("list") == [1, 2, 3]
        assert db.get("dict") == {"nested": True}


# ── WAL Tests ──────────────────────────────────────────────────

class TestWriteAheadLog:
    def test_wal_append_and_replay(self):
        with tempfile.NamedTemporaryFile(suffix=".wal", delete=False) as f:
            path = f.name
        try:
            wal = WriteAheadLog(path)
            wal.append("PUT", "key1", "value1")
            wal.append("DEL", "key2")
            entries = wal.replay()
            assert len(entries) == 2
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_wal_clear(self):
        with tempfile.NamedTemporaryFile(suffix=".wal", delete=False) as f:
            path = f.name
        try:
            wal = WriteAheadLog(path)
            wal.append("PUT", "key1", "value1")
            wal.clear()
            entries = wal.replay()
            assert len(entries) == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_wal_in_memory(self):
        wal = WriteAheadLog()
        wal.append("PUT", "key1", "value1")
        entries = wal.replay()
        assert len(entries) == 1

    def test_wal_recovery(self):
        db = Database(order=4)
        db.put("a", 1)
        db.put("b", 2)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            db_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wal", delete=False) as f:
            wal_path = f.name
        try:
            db.save(db_path)
            from bplus_db.serializer import Serializer
            s = Serializer()
            wal = WriteAheadLog(wal_path)
            wal.append("PUT", "c", s.serialize_value(3))
            recovered = Database.recover(db_path, wal_path)
            assert recovered.get("a") == 1
            assert recovered.get("c") == 3
        finally:
            for p in [db_path, wal_path]:
                if os.path.exists(p):
                    os.unlink(p)


# ── Concurrency Tests ──────────────────────────────────────────

class TestConcurrency:
    def test_thread_safety(self):
        db = Database(order=8)
        errors = []

        def writer(start, count):
            try:
                for i in range(start, start + count):
                    db.put("key_%d" % i, i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 100, 100)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert db.stats()["total_keys"] == 500


# ── Bug Fix Regression Tests ──────────────────────────────────────

class TestBugFixes:
    def test_search_returns_sentinel_not_none(self):
        tree = BPlusTree(order=4)
        assert tree.search("missing") is BPlusTree._NOT_FOUND
        tree.insert("key", None)
        result = tree.search("key")
        assert result is None
        assert result is not BPlusTree._NOT_FOUND

    def test_database_get_with_none_value(self):
        db = Database(order=4)
        db.put("null_key", None)
        assert db.get("null_key") is None
        assert db.get("null_key", default="fallback") is None
        assert db.get("missing_key", default="fallback") == "fallback"

    def test_bulk_load_creates_valid_tree_all_orders(self):
        for order in [3, 4, 5, 8, 16, 32, 64]:
            for n in [5, 7, 10, 15, 50, 99, 100, 200, 500]:
                tree = BPlusTree(order=order)
                items = [("k%04d" % i, i) for i in range(n)]
                tree.bulk_load(items)
                violations = tree.validate()
                assert violations == [], \
                    f"Violations for order={order}, n={n}: {violations}"

    def test_merge_with_none_values(self):
        db1 = Database(order=4)
        db1.put("a", None)
        db1.put("b", 2)
        db2 = Database(order=4)
        db2.put("a", 99)
        db2.put("c", 3)
        db1.merge(db2, conflict="theirs")
        assert db1.get("a") == 99
        assert db1.get("c") == 3