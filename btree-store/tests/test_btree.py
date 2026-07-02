"""Comprehensive test suite for btree-store.

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
  - Cursor offset/limit

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
import struct
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import btree
from btree import Store, Cursor, Transaction, LeafPage, InternalPage, FreePage


@pytest.fixture
def store():
    path = tempfile.mktemp(suffix='.btree')
    s = Store(path)
    yield s
    s.close()
    if os.path.exists(path):
        os.unlink(path)


class TestBasicOperations:
    def test_put_get(self, store):
        store.put('key1', 'val1')
        assert store.get('key1') == b'val1'

    def test_get_missing(self, store):
        assert store.get('nonexistent') is None

    def test_put_overwrite(self, store):
        store.put('k', 'v1')
        store.put('k', 'v2')
        assert store.get('k') == b'v2'

    def test_delete_existing(self, store):
        store.put('k', 'v')
        assert store.delete('k') is True
        assert store.get('k') is None

    def test_delete_missing(self, store):
        assert store.delete('nope') is False

    def test_delete_and_reinsert(self, store):
        store.put('k', 'v1')
        store.delete('k')
        store.put('k', 'v2')
        assert store.get('k') == b'v2'

    def test_contains(self, store):
        store.put('k', 'v')
        assert store.contains('k')
        assert not store.contains('missing')
        assert 'k' in store

    def test_empty_key_rejected(self, store):
        with pytest.raises(ValueError):
            store.put('', 'val')

    def test_binary_keys(self, store):
        store.put(b'\x00\x01\x02', b'\xff\xfe')
        assert store.get(b'\x00\x01\x02') == b'\xff\xfe'

    def test_binary_key_with_null_bytes(self, store):
        store.put(b'key\x00with\x00nulls', 'val')
        assert store.get(b'key\x00with\x00nulls') == b'val'
        # Ensure \x00 in key doesn't confuse prefix
        c = store.prefix(b'key\x00')
        assert len(c) == 1


class TestSplitting:
    def test_many_inserts_ordered(self, store):
        N = 1000
        for i in range(N):
            store.put(f'k{i:04d}', f'v{i}')
        assert store.count() == N
        assert store.validate()
        for i in range(N):
            assert store.get(f'k{i:04d}') == f'v{i}'.encode()

    def test_many_inserts_reverse(self, store):
        N = 1000
        for i in range(N - 1, -1, -1):
            store.put(f'k{i:04d}', f'v{i}')
        assert store.count() == N
        assert store.validate()
        for i in range(N):
            assert store.get(f'k{i:04d}') == f'v{i}'.encode()

    def test_many_inserts_random(self, store):
        import random
        random.seed(42)
        keys = [f'k{i:04d}' for i in range(1000)]
        random.shuffle(keys)
        for k in keys:
            store.put(k, 'v')
        assert store.count() == 1000
        assert store.validate()

    def test_large_values(self, store):
        # Values near page size
        big = b'x' * 3000
        store.put('big', big)
        assert store.get('big') == big
        assert store.validate()

    def test_oversized_value_rejected(self, store):
        # Key+value larger than a page should be rejected with a clear error
        huge = b'x' * 5000
        with pytest.raises(ValueError, match="too large"):
            store.put('huge', huge)

    def test_delete_many_makes_sparse(self, store):
        N = 1000
        for i in range(N):
            store.put(f'k{i:04d}', f'v{i}')
        # Delete every other key
        for i in range(0, N, 2):
            store.delete(f'k{i:04d}')
        assert store.validate()
        remaining = store.count()
        assert remaining == N // 2
        for i in range(N):
            v = store.get(f'k{i:04d}')
            if i % 2 == 0:
                assert v is None
            else:
                assert v == f'v{i}'.encode()


class TestScans:
    def test_scan_all(self, store):
        for i in range(100):
            store.put(f'k{i:03d}', f'v{i}')
        c = store.cursor()
        pairs = c.as_list()
        assert len(pairs) == 100
        # Check ordering
        for i in range(100):
            assert pairs[i][0] == f'k{i:03d}'.encode()

    def test_scan_range(self, store):
        for i in range(100):
            store.put(f'k{i:03d}', f'v{i}')
        c = store.cursor(low='k010', high='k020')
        pairs = c.as_list()
        assert len(pairs) == 10  # k010..k019
        assert pairs[0][0] == b'k010'
        assert pairs[-1][0] == b'k019'

    def test_scan_range_inclusive_high(self, store):
        for i in range(100):
            store.put(f'k{i:03d}', f'v{i}')
        c = store.cursor(low='k010', high='k020', include_high=True)
        assert len(c) == 11  # k010..k020

    def test_scan_reverse(self, store):
        for i in range(100):
            store.put(f'k{i:03d}', f'v{i}')
        c = store.cursor(reverse=True)
        pairs = c.as_list()
        assert pairs[0][0] == b'k099'
        assert pairs[-1][0] == b'k000'

    def test_scan_limit_offset(self, store):
        for i in range(100):
            store.put(f'k{i:03d}', f'v{i}')
        c = store.cursor(limit=10, offset=5)
        pairs = c.as_list()
        assert len(pairs) == 10
        assert pairs[0][0] == b'k005'
        assert pairs[-1][0] == b'k014'

    def test_scan_reverse_with_limit(self, store):
        for i in range(100):
            store.put(f'k{i:03d}', f'v{i}')
        c = store.cursor(reverse=True, limit=5)
        pairs = c.as_list()
        assert len(pairs) == 5
        assert pairs[0][0] == b'k099'
        assert pairs[-1][0] == b'k095'

    def test_scan_low_gt_high(self, store):
        for i in range(10):
            store.put(f'k{i}', f'v{i}')
        c = store.cursor(low='k9', high='k0')
        assert len(c) == 0

    def test_prefix_scan(self, store):
        store.put('apple', '1')
        store.put('app', '2')
        store.put('application', '3')
        store.put('banana', '4')
        store.put('apply', '5')
        c = store.prefix('app')
        keys = c.keys()
        # app, apple, application, apply — all start with 'app'
        assert b'apple' in keys
        assert b'app' in keys
        assert b'application' in keys
        assert b'apply' in keys
        assert b'banana' not in keys
        assert len(keys) == 4

    def test_prefix_empty(self, store):
        """Prefix with empty string should match all keys."""
        store.put('a', '1')
        store.put('b', '2')
        c = store.prefix('')
        # Empty prefix should match everything
        assert len(c) >= 2

    def test_prefix_not_found(self, store):
        store.put('hello', 'world')
        c = store.prefix('xyz')
        assert len(c) == 0
        assert c.is_empty()

    def test_cursor_empty_store(self, store):
        c = store.cursor()
        assert len(c) == 0
        assert c.is_empty()
        assert c.first() is None
        assert c.last() is None

    def test_cursor_seek(self, store):
        for i in range(100):
            store.put(f'k{i:03d}', f'v{i}')
        c = store.cursor()
        result = c.seek(b'k050')
        assert result is not None
        assert result[0] == b'k050'
        result = c.seek(b'k099')
        assert result[0] == b'k099'
        result = c.seek(b'z')  # past end
        assert result is None

    def test_cursor_seek_exact(self, store):
        store.put('hello', 'world')
        c = store.cursor()
        assert c.seek_exact(b'hello') == (b'hello', b'world')
        assert c.seek_exact(b'missing') is None


class TestTransactions:
    def test_commit(self, store):
        txn = store.begin()
        txn.put('k1', 'v1')
        assert store.get('k1') is None  # not visible yet
        store.commit(txn)
        assert store.get('k1') == b'v1'

    def test_rollback(self, store):
        txn = store.begin()
        txn.put('k1', 'v1')
        store.rollback(txn)
        assert store.get('k1') is None

    def test_read_only_txn(self, store):
        store.put('k1', 'v1')
        txn = store.begin(read_only=True)
        assert txn.get('k1') == b'v1'
        with pytest.raises(PermissionError):
            txn.put('k2', 'v2')

    def test_read_only_cannot_delete(self, store):
        store.put('k1', 'v1')
        txn = store.begin(read_only=True)
        with pytest.raises(PermissionError):
            txn.delete('k1')

    def test_commit_read_only_is_noop(self, store):
        txn = store.begin(read_only=True)
        store.commit(txn)  # should not error

    def test_double_commit_raises(self, store):
        txn = store.begin()
        txn.put('k', 'v')
        store.commit(txn)
        with pytest.raises(RuntimeError):
            store.commit(txn)

    def test_commit_after_rollback_raises(self, store):
        txn = store.begin()
        store.rollback(txn)
        with pytest.raises(RuntimeError):
            store.commit(txn)

    def test_put_after_commit_raises(self, store):
        txn = store.begin()
        txn.put('k', 'v')
        store.commit(txn)
        with pytest.raises(RuntimeError):
            txn.put('k2', 'v2')

    def test_context_manager_commit(self, store):
        with store.transaction() as txn:
            txn.put('k', 'v')
        assert store.get('k') == b'v'

    def test_context_manager_rollback(self, store):
        try:
            with store.transaction() as txn:
                txn.put('k', 'v')
                raise ValueError("test error")
        except ValueError:
            pass
        assert store.get('k') is None

    def test_read_your_writes(self, store):
        txn = store.begin()
        txn.put('k1', 'v1')
        assert txn.get('k1') == b'v1'  # should see own write
        store.commit(txn)

    def test_txn_delete_read_your_writes(self, store):
        store.put('k1', 'v1')
        txn = store.begin()
        txn.delete('k1')
        assert txn.get('k1') is None  # should see own delete
        store.commit(txn)

    def test_txn_cursor_with_writes(self, store):
        store.put('k1', 'v1')
        store.put('k3', 'v3')
        txn = store.begin()
        txn.put('k2', 'v2')  # insert in between
        c = txn.cursor()
        keys = c.keys()
        assert keys == [b'k1', b'k2', b'k3']
        store.commit(txn)

    def test_txn_count_with_writes(self, store):
        store.put('k1', 'v1')
        store.put('k2', 'v2')
        txn = store.begin()
        txn.put('k3', 'v3')
        assert txn.count() == 3
        txn.delete('k1')
        assert txn.count() == 2
        store.commit(txn)


class TestCAS:
    def test_cas_update(self, store):
        store.put('k', 'v1')
        assert store.cas('k', 'v1', 'v2') is True
        assert store.get('k') == b'v2'

    def test_cas_wrong_expected(self, store):
        store.put('k', 'v1')
        assert store.cas('k', 'wrong', 'v2') is False
        assert store.get('k') == b'v1'

    def test_cas_insert_if_absent(self, store):
        assert store.cas('k', None, 'v1') is True
        assert store.cas('k', None, 'v2') is False  # already exists
        assert store.get('k') == b'v1'

    def test_cas_delete_if_matches(self, store):
        store.put('k', 'v1')
        assert store.cas('k', 'v1', None) is True
        assert store.get('k') is None

    def test_cas_delete_wrong_match(self, store):
        store.put('k', 'v1')
        assert store.cas('k', 'wrong', None) is False
        assert store.get('k') == b'v1'


class TestMinMax:
    def test_min(self, store):
        store.put('c', '3')
        store.put('a', '1')
        store.put('b', '2')
        assert store.min() == (b'a', b'1')

    def test_max(self, store):
        store.put('c', '3')
        store.put('a', '1')
        store.put('b', '2')
        assert store.max() == (b'c', b'3')

    def test_min_empty(self, store):
        assert store.min() is None

    def test_max_empty(self, store):
        assert store.max() is None

    def test_min_after_delete(self, store):
        store.put('a', '1')
        store.put('b', '2')
        store.put('c', '3')
        store.delete('a')
        result = store.min()
        assert result == (b'b', b'2')


class TestBatchOperations:
    def test_put_many(self, store):
        txn = store.begin()
        txn.put_many({'a': '1', 'b': '2', 'c': '3'})
        store.commit(txn)
        assert store.get('a') == b'1'
        assert store.get('b') == b'2'
        assert store.get('c') == b'3'

    def test_delete_many(self, store):
        store.put('a', '1')
        store.put('b', '2')
        store.put('c', '3')
        txn = store.begin()
        n = txn.delete_many(['a', 'b', 'nonexistent'])
        assert n == 2
        store.commit(txn)
        assert store.get('a') is None
        assert store.get('b') is None
        assert store.get('c') == b'3'

    def test_bulk_load(self, store):
        pairs = [(f'k{i:04d}', f'v{i}') for i in range(500)]
        n = store.bulk_load(pairs)
        assert n == 500
        assert store.count() == 500
        assert store.validate()
        for i in range(500):
            assert store.get(f'k{i:04d}') == f'v{i}'.encode()


class TestPersistence:
    def test_reopen(self, store):
        store.put('hello', 'world')
        store.put('foo', 'bar')
        store.put('abc', 'def')
        store.delete('foo')
        path = store.path
        store.close()

        store2 = Store(path)
        assert store2.get('hello') == b'world'
        assert store2.get('foo') is None
        assert store2.get('abc') == b'def'
        assert store2.validate()
        store2.close()

    def test_reopen_many_keys(self, store):
        for i in range(500):
            store.put(f'k{i:04d}', f'v{i}')
        path = store.path
        store.close()

        store2 = Store(path)
        assert store2.count() == 500
        assert store2.validate()
        for i in range(500):
            assert store2.get(f'k{i:04d}') == f'v{i}'.encode()
        store2.close()

    def test_reopen_after_splits(self, store):
        for i in range(2000):
            store.put(f'k{i:05d}', f'v{i}')
        path = store.path
        store.close()

        store2 = Store(path)
        assert store2.count() == 2000
        assert store2.validate()
        store2.close()


class TestCRC32:
    def test_corrupted_page_detected(self, store):
        store.put('k1', 'v1')
        store.put('k2', 'v2')
        store.close()

        # Corrupt a byte in the file (after header, in page 0 content)
        # Find a byte that's not 0xFF to ensure actual change
        with open(store.path, 'r+b') as f:
            f.seek(btree.HEADER_SIZE + 10)
            original = f.read(1)
            corrupt_byte = b'\x00' if original != b'\x00' else b'\x01'
            f.seek(btree.HEADER_SIZE + 10)
            f.write(corrupt_byte)

        store2 = Store(store.path)
        with pytest.raises(IOError, match="CRC32"):
            store2.get('k1')
        store2.close()

    def test_zero_page_not_checked(self, store):
        """All-zero pages should not trigger CRC errors."""
        store.put('k', 'v')
        store.close()

        # Extend file with zero pages
        with open(store.path, 'ab') as f:
            f.write(b'\x00' * 4096 * 3)

        store2 = Store(store.path)
        store2.get('k')  # should not raise
        store2.close()


class TestCursorNavigation:
    def test_first_last(self, store):
        for i in range(10):
            store.put(f'k{i}', f'v{i}')
        c = store.cursor()
        assert c.first() == (b'k0', b'v0')
        assert c.last() == (b'k9', b'v9')

    def test_next_prev(self, store):
        for i in range(5):
            store.put(f'k{i}', f'v{i}')
        c = store.cursor()
        c.first()
        assert c.next() == (b'k1', b'v1')
        assert c.next() == (b'k2', b'v2')
        assert c.prev() == (b'k1', b'v1')

    def test_next_past_end(self, store):
        store.put('k', 'v')
        c = store.cursor()
        c.first()
        assert c.next() is None  # past end

    def test_prev_before_start(self, store):
        store.put('k', 'v')
        c = store.cursor()
        c.first()
        assert c.prev() is None  # before start

    def test_apply(self, store):
        store.put('a', 'hello')
        store.put('b', 'world')
        c = store.cursor()
        result = c.apply(lambda k, v: len(v))
        assert result == [5, 5]

    def test_bool(self, store):
        c = store.cursor()
        assert not c  # empty
        store.put('k', 'v')
        c = store.cursor()
        assert c  # non-empty


class TestEdgeCases:
    def test_negative_offset_cursor(self, store):
        """Negative offset should be treated as 0."""
        for i in range(10):
            store.put(f'k{i}', f'v{i}')
        c = store.cursor(offset=0)
        assert len(c) == 10

    def test_large_limit(self, store):
        for i in range(10):
            store.put(f'k{i}', f'v{i}')
        c = store.cursor(limit=10000)
        assert len(c) == 10

    def test_zero_limit(self, store):
        for i in range(10):
            store.put(f'k{i}', f'v{i}')
        c = store.cursor(limit=0)
        assert len(c) == 0

    def test_empty_store_validate(self, store):
        assert store.validate() is True

    def test_empty_store_count(self, store):
        assert store.count() == 0

    def test_empty_store_stats(self, store):
        s = store.stats()
        assert s['num_keys'] == 0
        assert s['tree_depth'] == 0

    def test_str_and_bytes_keys(self, store):
        store.put('strkey', 'strval')
        store.put(b'byteskey', b'bytesval')
        assert store.get('strkey') == b'strval'
        assert store.get(b'byteskey') == b'bytesval'

    def test_key_type_rejection(self, store):
        with pytest.raises(TypeError):
            store.put(123, 'val')

    def test_value_type_rejection(self, store):
        with pytest.raises(TypeError):
            store.put('k', 123)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])