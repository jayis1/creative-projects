"""Comprehensive tests for the B+ Tree Database Engine v2.0."""

import json
import os
import tempfile
import pytest

from bplus_db.bplus_tree import BPlusTree, LeafNode, InternalNode
from bplus_db.database import Database, Transaction, WriteAheadLog
from bplus_db.serializer import Serializer
from bplus_db.query_parser import QueryParser, QueryAST


# ── B+ Tree Tests ─────────────────────────────────────────────

class TestBPlusTree:
    """Tests for core B+ Tree operations."""

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
        assert tree.search("missing") is None

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
        tree.insert("b", 2)
        assert len(tree) == 2

    def test_insert_causes_split(self):
        """Insert enough keys to force a leaf split."""
        tree = BPlusTree(order=4)  # max 3 keys per node
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
        """Test with a small order to force many splits."""
        tree = BPlusTree(order=3)  # minimum order
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
        assert tree.search("b") is None
        assert tree.size == 2

    def test_delete_nonexistent(self):
        tree = BPlusTree(order=4)
        tree.insert("a", 1)
        assert tree.delete("z") is False
        assert tree.size == 1

    def test_delete_all(self):
        tree = BPlusTree(order=4)
        for i in range(10):
            tree.insert("k%d" % i, i)
        for i in range(10):
            assert tree.delete("k%d" % i) is True
        assert tree.size == 0
        assert len(tree) == 0

    def test_delete_with_merge(self):
        """Test deletion causing merges with order=3."""
        tree = BPlusTree(order=3)
        keys = ["a", "b", "c", "d", "e", "f", "g"]
        for k in keys:
            tree.insert(k, k.upper())
        # Delete in various orders, should trigger merges/borrows
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
        # Results should be in sorted order
        for i in range(19):
            assert results[i][0] < results[i + 1][0]

    def test_range_query_with_bounds(self):
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert("k%02d" % i, i)
        results = list(tree.range_query("k05", "k10"))
        assert len(results) == 6
        assert results[0][0] == "k05"
        assert results[-1][0] == "k10"

    def test_range_query_start_only(self):
        tree = BPlusTree(order=4)
        for i in range(10):
            tree.insert(i, i * 100)
        results = list(tree.range_query(start_key=5))
        assert len(results) == 5
        assert results[0] == (5, 500)

    def test_range_query_end_only(self):
        tree = BPlusTree(order=4)
        for i in range(10):
            tree.insert(i, i * 100)
        results = list(tree.range_query(end_key=3))
        assert len(results) == 4
        assert results[-1] == (3, 300)

    def test_range_query_no_results(self):
        tree = BPlusTree(order=4)
        tree.insert("a", 1)
        tree.insert("b", 2)
        results = list(tree.range_query("x", "z"))
        assert len(results) == 0

    def test_iteration(self):
        tree = BPlusTree(order=4)
        for i in range(5):
            tree.insert(i, i)
        results = list(tree)
        assert len(results) == 5
        assert results == [(i, i) for i in range(5)]

    def test_integer_keys(self):
        tree = BPlusTree(order=4)
        for i in range(100):
            tree.insert(i, i * 10)
        for i in range(100):
            assert tree.search(i) == i * 10

    def test_large_dataset(self):
        tree = BPlusTree(order=32)
        n = 1000
        for i in range(n):
            tree.insert(i, "value_%d" % i)
        assert tree.size == n
        for i in range(n):
            assert tree.search(i) == "value_%d" % i

    def test_minimum_order(self):
        """Order 3 is the minimum allowed."""
        tree = BPlusTree(order=3)
        for i in range(20):
            tree.insert(i, i)
        assert tree.size == 20

    def test_invalid_order(self):
        with pytest.raises(ValueError):
            BPlusTree(order=2)

    def test_print_tree(self):
        tree = BPlusTree(order=4)
        for i in range(5):
            tree.insert(i, i)
        output = tree.print_tree()
        assert "Leaf" in output or "Internal" in output

    def test_height(self):
        tree = BPlusTree(order=4)
        tree.insert("a", 1)
        assert tree.height() == 1
        # Add enough to force a split
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
        assert "height" in stats
        assert "leaf_count" in stats


class TestBPlusTreeBulkLoad:
    """Tests for bulk loading."""

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
        for i in range(100):
            assert tree.search(i) == i * 10

    def test_bulk_load_unsorted_raises(self):
        tree = BPlusTree(order=4)
        with pytest.raises(ValueError, match="sorted"):
            tree.bulk_load([("b", 2), ("a", 1)])

    def test_bulk_load_duplicate_keys_raises(self):
        tree = BPlusTree(order=4)
        with pytest.raises(ValueError, match="sorted"):
            tree.bulk_load([("a", 1), ("a", 2)])

    def test_bulk_load_empty(self):
        tree = BPlusTree(order=4)
        tree.bulk_load([])
        assert tree.size == 0

    def test_bulk_load_single(self):
        tree = BPlusTree(order=4)
        tree.bulk_load([("a", 1)])
        assert tree.size == 1
        assert tree.search("a") == 1

    def test_bulk_load_replaces_existing(self):
        tree = BPlusTree(order=4)
        tree.insert("x", 99)
        items = [("a", 1), ("b", 2), ("c", 3)]
        tree.bulk_load(items)
        assert tree.size == 3
        assert tree.search("x") is None

    def test_bulk_load_validates_tree(self):
        tree = BPlusTree(order=4)
        items = [("k%02d" % i, i) for i in range(20)]
        tree.bulk_load(items)
        violations = tree.validate()
        assert violations == []


class TestBPlusTreeValidation:
    """Tests for tree validation."""

    def test_valid_tree(self):
        tree = BPlusTree(order=4)
        for i in range(50):
            tree.insert(i, i)
        violations = tree.validate()
        assert violations == []

    def test_valid_tree_after_deletions(self):
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert(i, i)
        for i in range(0, 20, 2):  # Delete evens
            tree.delete(i)
        violations = tree.validate()
        assert violations == []

    def test_empty_tree_valid(self):
        tree = BPlusTree(order=4)
        violations = tree.validate()
        assert violations == []


class TestBPlusTreeDeleteRobust:
    """Stress tests for deletion with various patterns."""

    def test_delete_from_left(self):
        """Delete keys starting from the leftmost."""
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert(i, i)
        for i in range(20):
            assert tree.delete(i) is True
        assert tree.size == 0

    def test_delete_from_right(self):
        """Delete keys starting from the rightmost."""
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert(i, i)
        for i in range(19, -1, -1):
            assert tree.delete(i) is True
        assert tree.size == 0

    def test_delete_alternating(self):
        """Delete every other key."""
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert(i, i)
        for i in range(0, 20, 2):
            assert tree.delete(i) is True
        assert tree.size == 10
        for i in range(1, 20, 2):
            assert tree.search(i) == i

    def test_delete_with_order_3(self):
        """Delete with minimum order to stress merge logic."""
        tree = BPlusTree(order=3)
        for i in range(30):
            tree.insert(i, i)
        # Delete first 10
        for i in range(10):
            assert tree.delete(i) is True
        # Verify remaining
        for i in range(10, 30):
            assert tree.search(i) == i

    def test_delete_and_reinsert(self):
        """Delete all then reinsert."""
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert(i, i)
        for i in range(20):
            tree.delete(i)
        assert tree.size == 0
        # Reinsert
        for i in range(20):
            tree.insert(i, i * 2)
        for i in range(20):
            assert tree.search(i) == i * 2


# ── Serializer Tests ──────────────────────────────────────────

class TestSerializer:
    def test_serialize_deserialize_string(self):
        s = Serializer()
        original = "hello world"
        assert s.deserialize_value(s.serialize_value(original)) == original

    def test_serialize_deserialize_int(self):
        s = Serializer()
        original = 42
        assert s.deserialize_value(s.serialize_value(original)) == original

    def test_serialize_deserialize_float(self):
        s = Serializer()
        original = 3.14
        assert s.deserialize_value(s.serialize_value(original)) == original

    def test_serialize_deserialize_bool(self):
        s = Serializer()
        assert s.deserialize_value(s.serialize_value(True)) is True
        assert s.deserialize_value(s.serialize_value(False)) is False

    def test_serialize_deserialize_none(self):
        s = Serializer()
        assert s.deserialize_value(s.serialize_value(None)) is None

    def test_serialize_deserialize_list(self):
        s = Serializer()
        original = [1, "two", 3.0]
        assert s.deserialize_value(s.serialize_value(original)) == original

    def test_serialize_deserialize_dict(self):
        s = Serializer()
        original = {"key": "value", "num": 42}
        assert s.deserialize_value(s.serialize_value(original)) == original

    def test_roundtrip_all_types(self):
        s = Serializer()
        for val in ["hello", 42, 3.14, True, False, None, [1, 2], {"a": 1}]:
            assert s.deserialize_value(s.serialize_value(val)) == val

    def test_deserialize_plain_string(self):
        """Backward compatibility: plain strings deserialize as-is."""
        s = Serializer()
        # If data is not tagged JSON, return raw string
        assert s.deserialize_value("hello") == "hello"

    def test_nested_structures(self):
        s = Serializer()
        original = {"a": [1, 2, {"b": True}], "c": None}
        assert s.deserialize_value(s.serialize_value(original)) == original


# ── Database Tests ─────────────────────────────────────────────

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
        assert results[0][0] == "k03"
        assert results[-1][0] == "k07"

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

    def test_transaction_double_commit_raises(self):
        db = Database(order=4)
        txn = db.begin_transaction()
        txn.commit()
        with pytest.raises(RuntimeError):
            txn.commit()

    def test_transaction_after_rollback_raises(self):
        db = Database(order=4)
        txn = db.begin_transaction()
        txn.rollback()
        with pytest.raises(RuntimeError):
            txn.commit()

    def test_transaction_ops_after_commit_raises(self):
        db = Database(order=4)
        txn = db.begin_transaction()
        txn.commit()
        with pytest.raises(RuntimeError):
            txn.put("key", "val")

    def test_transaction_is_active(self):
        db = Database(order=4)
        txn = db.begin_transaction()
        assert txn.is_active is True
        txn.commit()
        assert txn.is_active is False

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
            assert len(loaded) == 10
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
            assert len(loaded) == 10
        finally:
            os.unlink(path)

    def test_stats(self):
        db = Database(order=4)
        db.put("a", 1)
        db.put("b", 2)
        _ = db.get("a")
        _ = db.get("c")  # miss
        stats = db.stats()
        assert stats["total_keys"] == 2
        assert stats["gets"] == 2
        assert stats["puts"] == 2
        assert "tree_height" in stats
        assert "leaf_count" in stats

    def test_complex_values(self):
        db = Database(order=4)
        db.put("list", [1, 2, 3])
        db.put("dict", {"nested": True})
        db.put("number", 42.5)
        assert db.get("list") == [1, 2, 3]
        assert db.get("dict") == {"nested": True}
        assert db.get("number") == 42.5

    def test_repr(self):
        db = Database(order=4)
        db.put("a", 1)
        r = repr(db)
        assert "keys=1" in r
        assert "order=4" in r

    def test_put_many(self):
        db = Database(order=4)
        count = db.put_many({"k1": "v1", "k2": "v2", "k3": "v3"})
        assert count == 3
        assert db.get("k1") == "v1"
        assert db.get("k2") == "v2"
        assert db.get("k3") == "v3"

    def test_delete_many(self):
        db = Database(order=4)
        db.put_many({"k1": "v1", "k2": "v2", "k3": "v3"})
        deleted = db.delete_many(["k1", "k3", "k_missing"])
        assert deleted == 2
        assert db.get("k1") is None
        assert db.get("k2") == "v2"

    def test_keys(self):
        db = Database(order=4)
        db.put("c", 3)
        db.put("a", 1)
        db.put("b", 2)
        assert db.keys() == ["a", "b", "c"]

    def test_values(self):
        db = Database(order=4)
        db.put("c", 3)
        db.put("a", 1)
        db.put("b", 2)
        assert db.values() == [1, 2, 3]

    def test_items(self):
        db = Database(order=4)
        db.put("c", 3)
        db.put("a", 1)
        db.put("b", 2)
        assert db.items() == [("a", 1), ("b", 2), ("c", 3)]

    def test_validate(self):
        db = Database(order=4)
        for i in range(20):
            db.put("k%02d" % i, i)
        violations = db.validate()
        assert violations == []

    def test_tree_structure(self):
        db = Database(order=4)
        db.put("a", 1)
        s = db.tree_structure()
        assert "Leaf" in s

    def test_merge(self):
        db1 = Database(order=4)
        db1.put("a", 1)
        db1.put("b", 2)
        db2 = Database(order=4)
        db2.put("c", 3)
        db2.put("d", 4)
        merged = db1.merge(db2)
        assert merged == 2
        assert db1.get("c") == 3
        assert db1.get("d") == 4

    def test_merge_conflict_ours(self):
        db1 = Database(order=4)
        db1.put("a", 1)
        db2 = Database(order=4)
        db2.put("a", 99)
        merged = db1.merge(db2, conflict="ours")
        assert merged == 0
        assert db1.get("a") == 1

    def test_merge_conflict_theirs(self):
        db1 = Database(order=4)
        db1.put("a", 1)
        db2 = Database(order=4)
        db2.put("a", 99)
        merged = db1.merge(db2, conflict="theirs")
        assert merged == 1
        assert db1.get("a") == 99

    def test_merge_conflict_error(self):
        db1 = Database(order=4)
        db1.put("a", 1)
        db2 = Database(order=4)
        db2.put("a", 99)
        with pytest.raises(KeyError):
            db1.merge(db2, conflict="error")

    def test_diff(self):
        db1 = Database(order=4)
        db1.put("a", 1)
        db1.put("b", 2)
        db1.put("c", 3)
        db2 = Database(order=4)
        db2.put("b", 2)
        db2.put("c", 99)
        db2.put("d", 4)
        result = db1.diff(db2)
        assert set(result["only_in_self"]) == {"a"}
        assert set(result["only_in_other"]) == {"d"}
        assert set(result["changed"]) == {"c"}
        assert set(result["unchanged"]) == {"b"}


# ── Write-Ahead Log Tests ──────────────────────────────────────

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
            assert entries[0] == ("PUT", "key1", "value1")
            assert entries[1] == ("DEL", "key2", None)
        finally:
            os.unlink(path)

    def test_wal_clear(self):
        with tempfile.NamedTemporaryFile(suffix=".wal", delete=False) as f:
            path = f.name
        try:
            wal = WriteAheadLog(path)
            wal.append("PUT", "key1", "value1")
            wal.clear()
            # After clear, the file is deleted, so replay from in-memory entries
            entries = wal.replay()
            assert len(entries) == 0
        finally:
            # File may already be deleted by clear()
            if os.path.exists(path):
                os.unlink(path)

    def test_wal_in_memory(self):
        """WAL without a path stores in memory only."""
        wal = WriteAheadLog()
        wal.append("PUT", "key1", "value1")
        entries = wal.replay()
        assert len(entries) == 1

    def test_wal_recovery(self):
        """Test full recovery flow using Database.recover."""
        db = Database(order=4)
        db.put("a", 1)
        db.put("b", 2)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            db_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wal", delete=False) as f:
            wal_path = f.name

        try:
            db.save(db_path)
            # Simulate some uncommitted WAL entries
            wal = WriteAheadLog(wal_path)
            # WAL stores serialized values, so use a string that matches what
            # the serializer would produce for the integer 3
            from bplus_db.serializer import Serializer
            s = Serializer()
            wal.append("PUT", "c", s.serialize_value(3))
            recovered = Database.recover(db_path, wal_path)
            assert recovered.get("a") == 1
            assert recovered.get("b") == 2
            assert recovered.get("c") == 3
        finally:
            for p in [db_path, wal_path]:
                if os.path.exists(p):
                    os.unlink(p)


# ── Query Parser Tests ─────────────────────────────────────────

class TestQueryParser:
    def test_select_all(self):
        ast = QueryParser("SELECT * FROM db").parse()
        assert ast.command == "select"
        assert ast.conditions == []

    def test_select_where_equals(self):
        ast = QueryParser("SELECT * FROM db WHERE key = 'test'").parse()
        assert ast.command == "select"
        assert len(ast.conditions) == 1
        assert ast.conditions[0]["op"] == "="
        assert ast.conditions[0]["value"] == "test"

    def test_select_where_range(self):
        ast = QueryParser("SELECT * FROM db WHERE key >= 'a' AND key <= 'z'").parse()
        assert len(ast.conditions) == 2
        assert ast.conditions[0]["op"] == ">="
        assert ast.conditions[1]["op"] == "<="

    def test_select_where_greater(self):
        ast = QueryParser("SELECT * FROM db WHERE key > 'm'").parse()
        assert ast.conditions[0]["op"] == ">"
        assert ast.conditions[0]["value"] == "m"

    def test_select_where_less(self):
        ast = QueryParser("SELECT * FROM db WHERE key < 'n'").parse()
        assert ast.conditions[0]["op"] == "<"

    def test_insert(self):
        ast = QueryParser("INSERT INTO db KEY 'mykey' VALUE 'myval'").parse()
        assert ast.command == "insert"
        assert ast.key == "mykey"
        assert ast.value == "myval"

    def test_delete(self):
        ast = QueryParser("DELETE FROM db WHERE key = 'x'").parse()
        assert ast.command == "delete"
        assert ast.key == "x"

    def test_count(self):
        ast = QueryParser("COUNT db").parse()
        assert ast.command == "count"

    def test_empty_query_raises(self):
        with pytest.raises(SyntaxError):
            QueryParser("").parse()

    def test_unknown_command_raises(self):
        with pytest.raises(SyntaxError):
            QueryParser("UPDATE db SET x=1").parse()

    def test_case_insensitive_keywords(self):
        ast = QueryParser("select * from db").parse()
        assert ast.command == "select"

    def test_numeric_value(self):
        ast = QueryParser("INSERT INTO db KEY 'x' VALUE 42").parse()
        assert ast.command == "insert"
        assert ast.key == "x"
        assert ast.value == "42"

    def test_select_where_gte(self):
        ast = QueryParser("SELECT * FROM db WHERE key >= 'start'").parse()
        assert ast.conditions[0]["op"] == ">="

    def test_select_where_neq(self):
        ast = QueryParser("SELECT * FROM db WHERE key != 'excluded'").parse()
        assert ast.conditions[0]["op"] == "!="


# ── Database Query Execution Tests ──────────────────────────────

class TestDatabaseQueryExecution:
    def test_execute_select_all(self):
        db = Database(order=4)
        db.put("a", 1)
        db.put("b", 2)
        results = db.execute("SELECT * FROM db")
        assert len(results) == 2

    def test_execute_select_where_equals(self):
        db = Database(order=4)
        db.put("a", 1)
        db.put("b", 2)
        result = db.execute("SELECT * FROM db WHERE key = 'a'")
        assert result == 1

    def test_execute_select_range(self):
        db = Database(order=4)
        for i in range(10):
            db.put("k%02d" % i, i)
        results = db.execute("SELECT * FROM db WHERE key >= 'k03' AND key <= 'k07'")
        assert len(results) == 5

    def test_execute_insert(self):
        db = Database(order=4)
        db.execute("INSERT INTO db KEY 'hello' VALUE 'world'")
        assert db.get("hello") == "world"

    def test_execute_delete(self):
        db = Database(order=4)
        db.put("x", 99)
        db.execute("DELETE FROM db WHERE key = 'x'")
        assert db.get("x") is None

    def test_execute_count(self):
        db = Database(order=4)
        for i in range(5):
            db.put("k%d" % i, i)
        result = db.execute("COUNT db")
        assert result == 5


# ── Persistence Edge Cases ───────────────────────────────────────

class TestPersistenceEdgeCases:
    def test_empty_database_save_load(self):
        db = Database(order=4)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            db.save(path)
            loaded = Database.load(path)
            assert len(loaded) == 0
        finally:
            os.unlink(path)

    def test_large_dataset_save_load(self):
        db = Database(order=16)
        for i in range(500):
            db.put("key_%04d" % i, "value_%d" % i)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            db.save(path)
            loaded = Database.load(path)
            assert len(loaded) == 500
            for i in range(500):
                assert loaded.get("key_%04d" % i) == "value_%d" % i
        finally:
            os.unlink(path)

    def test_overwrite_save(self):
        db = Database(order=4)
        db.put("a", 1)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            db.save(path)
            db.put("b", 2)
            db.save(path)
            loaded = Database.load(path)
            assert loaded.get("a") == 1
            assert loaded.get("b") == 2
        finally:
            os.unlink(path)

    def test_save_without_path_raises(self):
        db = Database(order=4)
        with pytest.raises(ValueError):
            db.save()

    def test_binary_format_version_check(self):
        db = Database(order=4)
        db.put("test", "data")
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            path = f.name
        try:
            db.save_binary(path)
            loaded = Database.load_binary(path)
            assert loaded.get("test") == "data"
        finally:
            os.unlink(path)

    def test_binary_bad_magic_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            path = f.name
        try:
            with open(path, "wb") as f2:
                f2.write(b"XXXX" + b"\x00" * 20)
            with pytest.raises(ValueError, match="Invalid file format"):
                Database.load_binary(path)
        finally:
            os.unlink(path)


# ── Concurrency Tests ──────────────────────────────────────────

class TestConcurrency:
    def test_thread_safety(self):
        """Test that concurrent operations don't corrupt the tree."""
        import threading
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