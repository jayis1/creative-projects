"""Comprehensive tests for the B+ Tree Database Engine."""

import json
import os
import tempfile
import pytest

from bplus_db.bplus_tree import BPlusTree, LeafNode, InternalNode
from bplus_db.database import Database, Transaction
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
            tree.insert(f"key{i:02d}", i)
        for i in range(10):
            assert tree.search(f"key{i:02d}") == i
        assert tree.size == 10

    def test_insert_reverse_order(self):
        tree = BPlusTree(order=4)
        for i in range(20, -1, -1):
            tree.insert(f"key{i:02d}", i)
        for i in range(21):
            assert tree.search(f"key{i:02d}") == i

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
            tree.insert(f"k{i}", i)
        for i in range(10):
            assert tree.delete(f"k{i}") is True
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
            tree.insert(f"k{i:02d}", i)
        results = list(tree.range_query())
        assert len(results) == 20
        # Results should be in sorted order
        for i in range(19):
            assert results[i][0] < results[i + 1][0]

    def test_range_query_with_bounds(self):
        tree = BPlusTree(order=4)
        for i in range(20):
            tree.insert(f"k{i:02d}", i)
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
            tree.insert(i, f"value_{i}")
        assert tree.size == n
        for i in range(n):
            assert tree.search(i) == f"value_{i}"

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
            db.put(f"k{i:02d}", i)
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
        txn.delete("c")
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

    def test_save_load_json(self):
        db = Database(order=4)
        for i in range(10):
            db.put(f"key{i}", f"value{i}")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            db.save(path)
            loaded = Database.load(path)
            for i in range(10):
                assert loaded.get(f"key{i}") == f"value{i}"
            assert len(loaded) == 10
        finally:
            os.unlink(path)

    def test_save_load_binary(self):
        db = Database(order=4)
        for i in range(10):
            db.put(f"key{i}", f"value{i}")

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            path = f.name

        try:
            db.save_binary(path)
            loaded = Database.load_binary(path)
            for i in range(10):
                assert loaded.get(f"key{i}") == f"value{i}"
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
            db.put(f"k{i:02d}", i)
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
            db.put(f"k{i}", i)
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
            db.put(f"key_{i:04d}", f"value_{i}")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            db.save(path)
            loaded = Database.load(path)
            assert len(loaded) == 500
            for i in range(500):
                assert loaded.get(f"key_{i:04d}") == f"value_{i}"
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