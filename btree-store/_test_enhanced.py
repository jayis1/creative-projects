import btree
import tempfile, os

path = tempfile.mktemp(suffix='.btree')
store = btree.Store(path)

# Basic put/get
store.put('hello', 'world')
assert store.get('hello') == b'world'
store.put('foo', 'bar')
store.put('abc', 'def')
assert store.get('foo') == b'bar'
assert store.get('missing') is None

# Delete
assert store.delete('foo') == True
assert store.get('foo') is None

# contains
assert store.contains('hello')
assert not store.contains('foo')
assert 'hello' in store  # __contains__

# min/max
mn = store.min()
assert mn == (b'abc', b'def'), f'min={mn}'
mx = store.max()
assert mx == (b'hello', b'world'), f'max={mx}'

# Splitting: insert many keys
N = 500
for i in range(N):
    store.put(f'key{i:04d}', f'value{i}')
assert store.count() == N + 2  # abc, hello + 500 keys
assert store.validate()

# Range with limit and offset
c = store.cursor(low='key0000', high='key0100', limit=10, offset=5)
pairs = c.as_list()
assert len(pairs) == 10, f'limit/offset: {len(pairs)}'
assert pairs[0][0] == b'key0005', f'first={pairs[0][0]}'
assert pairs[-1][0] == b'key0014', f'last={pairs[-1][0]}'

# Reverse cursor
c = store.cursor(low='key0000', high='key0010', reverse=True)
pairs = c.as_list()
assert pairs[0][0] == b'key0009', f'reverse first={pairs[0][0]}'
assert pairs[-1][0] == b'key0000'

# Prefix scan with limit
c = store.prefix('key01', limit=5)
pairs = c.as_list()
assert len(pairs) == 5
assert all(k.startswith(b'key01') for k, _ in pairs)

# CAS
assert store.cas('hello', 'world', 'universe') == True
assert store.get('hello') == b'universe'
assert store.cas('hello', 'world', 'galaxy') == False  # wrong expected
assert store.get('hello') == b'universe'

# CAS insert-if-absent
assert store.cas('new_key', None, 'new_val') == True
assert store.cas('new_key', None, 'other') == False  # already exists

# CAS delete-if-matches
assert store.cas('new_key', 'new_val', None) == True
assert store.get('new_key') is None

# put_many
txn = store.begin()
txn.put_many({'a:1': '1', 'a:2': '2', 'a:3': '3'})
store.commit(txn)
assert store.get('a:1') == b'1'
assert store.get('a:2') == b'2'

# delete_many
txn = store.begin()
n = txn.delete_many(['a:1', 'a:2', 'nonexistent'])
assert n == 2, f'delete_many returned {n}'
store.commit(txn)
assert store.get('a:1') is None
assert store.get('a:3') == b'3'

# Context manager transaction (commit)
with store.transaction() as txn:
    txn.put('ctx_key', 'ctx_val')
assert store.get('ctx_key') == b'ctx_val'

# Context manager transaction (rollback on exception)
try:
    with store.transaction() as txn:
        txn.put('rollback_key', 'val')
        raise ValueError("test")
except ValueError:
    pass
assert store.get('rollback_key') is None

# bulk_load
pairs_list = [(f'bulk{i:03d}', f'bv{i}') for i in range(200)]
n = store.bulk_load(pairs_list)
assert n == 200
assert store.get('bulk000') == b'bv0'
assert store.get('bulk199') == b'bv199'

# Empty key rejection
try:
    store.put('', 'val')
    assert False, 'should reject empty key'
except ValueError:
    pass

# CRC verification
store.close()

# Reopen and verify CRC works
store2 = btree.Store(path)
assert store2.get('hello') == b'universe'
assert store2.validate()
assert store2.count() > 0

# Stats with tree depth
stats = store2.stats()
print(f'Stats: file_size={stats["file_size"]}, tree_depth={stats["tree_depth"]}, '
      f'num_keys={stats["num_keys"]}, total_pages={stats["total_pages"]}')
assert stats['tree_depth'] >= 0
assert stats['num_keys'] > 0

store2.close()
os.unlink(path)
print('ENHANCED TESTS PASSED')