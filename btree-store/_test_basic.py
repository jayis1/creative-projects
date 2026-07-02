import btree
import tempfile, os

path = tempfile.mktemp(suffix='.btree')
store = btree.Store(path)
# Basic put/get
store.put('hello', 'world')
assert store.get('hello') == b'world', f'got {store.get("hello")}'
store.put('foo', 'bar')
store.put('abc', 'def')
assert store.get('foo') == b'bar'
assert store.get('abc') == b'def'
assert store.get('missing') is None

# Delete
assert store.delete('foo') == True
assert store.get('foo') is None
assert store.delete('foo') == False  # already deleted

# Count
print('count:', store.count())

# Cursor
store.put('key:01', 'val1')
store.put('key:02', 'val2')
store.put('key:03', 'val3')
store.put('other', 'val')

c = store.cursor()
print('all keys:', [k.decode() for k in c.keys()])

c = store.prefix('key:')
print('prefix keys:', [k.decode() for k in c.keys()])

# Range
c = store.cursor(low='abc', high='key:02')
print('range keys:', [k.decode() for k in c.keys()])

store.close()
os.unlink(path)
print('BASIC TESTS PASSED')