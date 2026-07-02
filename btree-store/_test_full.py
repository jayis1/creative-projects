import btree
import tempfile, os, random

path = tempfile.mktemp(suffix='.btree')
store = btree.Store(path)

# Test splitting by inserting many keys
N = 500
for i in range(N):
    store.put(f'key{i:04d}', f'value{i}')
assert store.count() == N, f'count={store.count()} expected {N}'
assert store.validate(), 'tree invalid after inserts'

# Verify all keys
for i in range(N):
    v = store.get(f'key{i:04d}')
    assert v == f'value{i}'.encode(), f'key{i:04d} got {v}'

# Test ordered scan
c = store.cursor()
keys = c.keys()
assert len(keys) == N
for i in range(N):
    assert keys[i] == f'key{i:04d}'.encode(), f'unordered at {i}: {keys[i]}'
print(f'Ordered scan: {N} keys verified')

# Test range queries
c = store.cursor(low='key0100', high='key0200', include_high=True)
pairs = c.as_list()
assert len(pairs) == 101, f'range count={len(pairs)}'
assert pairs[0][0] == b'key0100'
assert pairs[-1][0] == b'key0200'
print(f'Range [key0100, key0200]: {len(pairs)} entries')

# Test prefix scan
c = store.prefix('key01')
pairs = c.as_list()
assert all(k.startswith(b'key01') for k, _ in pairs)
print(f'Prefix key01: {len(pairs)} entries')

# Delete some keys
for i in range(0, N, 3):
    assert store.delete(f'key{i:04d}')
assert store.validate()
remaining = store.count()
print(f'After deleting every 3rd key: {remaining} keys')
for i in range(N):
    v = store.get(f'key{i:04d}')
    if i % 3 == 0:
        assert v is None, f'key{i:04d} should be deleted'
    else:
        assert v == f'value{i}'.encode()
print('Deletes verified')

# Test persistence
store.close()
store2 = btree.Store(path)
assert store2.count() == remaining
assert store2.validate()
for i in range(N):
    v = store2.get(f'key{i:04d}')
    if i % 3 == 0:
        assert v is None
    else:
        assert v == f'value{i}'.encode()
print('Persistence verified')

# Test binary keys
store2.put(b'\x00\x01\x02', b'binary_val')
assert store2.get(b'\x00\x01\x02') == b'binary_val'
print('Binary keys verified')

# Test transactions
txn = store2.begin()
txn.put('txn_key', 'txn_val')
assert txn.get('txn_key') == b'txn_val'
# Should not be visible outside txn yet
assert store2.get('txn_key') is None
store2.commit(txn)
assert store2.get('txn_key') == b'txn_val'
print('Transaction commit verified')

# Test rollback
txn2 = store2.begin()
txn2.put('rollback_key', 'val')
store2.rollback(txn2)
assert store2.get('rollback_key') is None
print('Transaction rollback verified')

# Test read-only txn
txn3 = store2.begin(read_only=True)
try:
    txn3.put('readonly_key', 'val')
    assert False, 'should have raised'
except PermissionError:
    print('Read-only txn enforces no writes')

# Test stats
stats = store2.stats()
print(f'Stats: {stats}')

store2.close()
os.unlink(path)
print('ALL TESTS PASSED')