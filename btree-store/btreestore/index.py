"""
Secondary indexes for btreestore.

Provides a secondary index layer on top of the Store. Indexes map
indexed values back to primary keys, enabling efficient lookups by
attributes other than the primary key.

Each index is itself a B+Tree store, where:
  - Key = indexed value (bytes)
  - Value = serialized list of primary keys that have that indexed value

This allows many-to-one relationships (multiple primary keys can share
the same indexed value) and efficient equality and range queries on
the indexed field.

Usage:
    from btreestore import Store
    from btreestore.index import IndexManager, Index

    with Store("primary.btree") as store:
        mgr = IndexManager(store)

        # Create an index on the "email" field
        email_idx = mgr.create_index("email")

        # Index some records
        store.put("user:1", b'{"name":"alice","email":"alice@x.com"}')
        email_idx.add("alice@x.com", b"user:1")

        # Look up by indexed field
        keys = email_idx.find("alice@x.com")
        # -> [b"user:1"]
"""

from __future__ import annotations

import os
import struct
import tempfile
from typing import Dict, List, Optional, Union, Iterator, Tuple
from .logging_util import get_logger

logger = get_logger()


def _varint_encode(value: int) -> bytes:
    buf = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            buf.append(b | 0x80)
        else:
            buf.append(b)
            break
    return bytes(buf)


def _varint_decode(data: bytes, offset: int) -> Tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, offset


def _encode_key_list(keys: List[bytes]) -> bytes:
    """Serialize a list of primary keys into a single value."""
    buf = bytearray()
    buf += _varint_encode(len(keys))
    for k in keys:
        buf += _varint_encode(len(k))
        buf += k
    return bytes(buf)


def _decode_key_list(data: bytes) -> List[bytes]:
    """Deserialize a list of primary keys from a value."""
    if not data:
        return []
    offset = 0
    count, offset = _varint_decode(data, offset)
    keys: List[bytes] = []
    for _ in range(count):
        klen, offset = _varint_decode(data, offset)
        keys.append(data[offset:offset + klen])
        offset += klen
    return keys


class Index:
    """A secondary index on a Store.

    Maps indexed values to lists of primary keys.
    """

    def __init__(self, name: str, store_path: str, primary_store):
        """Create or open an index.

        Args:
            name: Index name (used for file naming).
            store_path: Path to the index's B+Tree file.
            primary_store: The primary Store this index is attached to.
        """
        self.name = name
        self.path = store_path
        self.primary = primary_store

        # Lazy import to avoid circular dependency
        from .store import Store
        self.store = Store(store_path, wal_enabled=False)

    def add(self, indexed_value: Union[str, bytes],
            primary_key: Union[str, bytes]) -> None:
        """Add a primary key under an indexed value."""
        iv = self._coerce(indexed_value)
        pk = self._coerce(primary_key)

        existing = self.store.get(iv)
        if existing is None:
            keys = [pk]
        else:
            keys = _decode_key_list(existing)
            if pk not in keys:
                keys.append(pk)
        self.store.put(iv, _encode_key_list(keys))

    def remove(self, indexed_value: Union[str, bytes],
               primary_key: Union[str, bytes]) -> bool:
        """Remove a primary key from an indexed value.

        Returns True if the key was found and removed.
        """
        iv = self._coerce(indexed_value)
        pk = self._coerce(primary_key)

        existing = self.store.get(iv)
        if existing is None:
            return False
        keys = _decode_key_list(existing)
        if pk not in keys:
            return False
        keys.remove(pk)
        if keys:
            self.store.put(iv, _encode_key_list(keys))
        else:
            self.store.delete(iv)
        return True

    def find(self, indexed_value: Union[str, bytes]) -> List[bytes]:
        """Find all primary keys matching the indexed value."""
        iv = self._coerce(indexed_value)
        existing = self.store.get(iv)
        if existing is None:
            return []
        return _decode_key_list(existing)

    def find_one(self, indexed_value: Union[str, bytes]) -> Optional[bytes]:
        """Find the first primary key matching the indexed value."""
        keys = self.find(indexed_value)
        return keys[0] if keys else None

    def range(self, low: Union[str, bytes, None] = None,
              high: Union[str, bytes, None] = None) -> Iterator[Tuple[bytes, List[bytes]]]:
        """Iterate over indexed values in a range, yielding (value, primary_keys)."""
        c = self.store.cursor(low=low, high=high)
        for k, v in c:
            yield (k, _decode_key_list(v))

    def count(self) -> int:
        """Return the number of distinct indexed values."""
        return self.store.count()

    def clear(self) -> None:
        """Remove all entries from the index."""
        # Delete all keys
        c = self.store.cursor()
        for k, _ in c:
            self.store.delete(k)

    def close(self) -> None:
        self.store.close()

    @staticmethod
    def _coerce(val: Union[str, bytes]) -> bytes:
        if isinstance(val, str):
            return val.encode("utf-8")
        if isinstance(val, bytes):
            return val
        raise TypeError(f"expected str or bytes, got {type(val).__name__}")


class IndexManager:
    """Manages multiple secondary indexes for a Store.

    Index files are stored alongside the primary store file with
    a `.idx.<name>.btree` suffix.
    """

    def __init__(self, store):
        self.store = store
        self._indexes: Dict[str, Index] = {}
        self._base_dir = os.path.dirname(os.path.abspath(store.path))

    def create_index(self, name: str) -> Index:
        """Create or open a secondary index by name."""
        if name in self._indexes:
            return self._indexes[name]
        idx_path = os.path.join(
            self._base_dir,
            f"{os.path.basename(self.store.path)}.idx.{name}.btree",
        )
        idx = Index(name, idx_path, self.store)
        self._indexes[name] = idx
        logger.info(f"Created index '{name}' at {idx_path}")
        return idx

    def get_index(self, name: str) -> Optional[Index]:
        return self._indexes.get(name)

    def drop_index(self, name: str) -> bool:
        """Drop an index, deleting its file."""
        idx = self._indexes.pop(name, None)
        if idx is None:
            return False
        path = idx.path
        idx.close()
        for p in [path, path + ".wal"]:
            if os.path.exists(p):
                os.unlink(p)
        logger.info(f"Dropped index '{name}'")
        return True

    def close_all(self) -> None:
        """Close all managed indexes."""
        for idx in self._indexes.values():
            idx.close()
        self._indexes.clear()

    def index_names(self) -> List[str]:
        return list(self._indexes.keys())