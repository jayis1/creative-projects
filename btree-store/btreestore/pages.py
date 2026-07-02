"""
Page types and serialization for the B+Tree store.

Each page is page_size bytes, with the last 4 bytes reserved for a CRC32
checksum of the preceding content. Keys and values use LEB128 varint
length prefixes followed by raw bytes.
"""

from __future__ import annotations

import struct
import zlib
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants and on-disk format
# ---------------------------------------------------------------------------

MAGIC = b"BTREESTR"  # file magic
VERSION = 3  # v3: package structure, WAL support

# File header: magic (8) + version (4) + page_size (4) + root_page_id (4, signed)
# + next_page_id (4, signed) + free_list_head (4, signed) + commit_ts (8, signed) = 36 bytes
HEADER_FMT = "<8sIIiiiq"
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# Page types
PAGE_LEAF = 1
PAGE_INTERNAL = 2
PAGE_FREE = 3

# Leaf page: type(1) + num_keys(2) + prev(4, signed) + next(4, signed)
LEAF_HEADER_FMT = "<BHii"
LEAF_HEADER_SIZE = struct.calcsize(LEAF_HEADER_FMT)

# Internal page: type(1) + num_keys(2)
INTERNAL_HEADER_FMT = "<BH"
INTERNAL_HEADER_SIZE = struct.calcsize(INTERNAL_HEADER_FMT)

# CRC32 checksum stored in the last 4 bytes of every page
CRC_SIZE = 4

DEFAULT_PAGE_SIZE = 4096
DEFAULT_BRANCHING = 32  # order: max children per internal node
DEFAULT_CACHE_SIZE = 512


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _varint_encode(buf: bytearray, value: int) -> None:
    """LEB128 unsigned varint encoding."""
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            buf.append(b | 0x80)
        else:
            buf.append(b)
            break


def _varint_decode(data: bytes, offset: int) -> Tuple[int, int]:
    """Decode LEB128 unsigned varint, return (value, new_offset)."""
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


def _pack_kv(buf: bytearray, key: bytes, value: bytes) -> None:
    """Pack a key-value pair with varint length prefixes."""
    _varint_encode(buf, len(key))
    buf.extend(key)
    _varint_encode(buf, len(value))
    buf.extend(value)


def _unpack_kv(data: bytes, offset: int) -> Tuple[bytes, bytes, int]:
    """Unpack a key-value pair, returning (key, value, new_offset)."""
    klen, offset = _varint_decode(data, offset)
    key = data[offset:offset + klen]
    offset += klen
    vlen, offset = _varint_decode(data, offset)
    value = data[offset:offset + vlen]
    offset += vlen
    return key, value, offset


# ---------------------------------------------------------------------------
# Page types
# ---------------------------------------------------------------------------

class Page:
    """Base class for in-memory pages."""

    __slots__ = ("id", "dirty")

    def __init__(self, page_id: int):
        self.id = page_id
        self.dirty = False


class LeafPage(Page):
    """Leaf node: stores sorted key-value pairs.

    prev/next form a doubly-linked list for efficient cursor iteration
    without traversing internal nodes.
    """

    __slots__ = ("keys", "values", "prev", "next")

    def __init__(self, page_id: int, prev: int = -1, next_id: int = -1):
        super().__init__(page_id)
        self.keys: List[bytes] = []
        self.values: List[bytes] = []
        self.prev = prev
        self.next = next_id

    @property
    def num_keys(self) -> int:
        return len(self.keys)


class InternalPage(Page):
    """Internal node: N separator keys and N+1 child page IDs.

    Layout: child0, key0, child1, key1, ..., key_{n-1}, child_n
    Keys[i] separates child[i] (keys < Keys[i]) and child[i+1] (keys >= Keys[i]).
    """

    __slots__ = ("keys", "children")

    def __init__(self, page_id: int):
        super().__init__(page_id)
        self.keys: List[bytes] = []
        self.children: List[int] = []

    @property
    def num_keys(self) -> int:
        return len(self.keys)


class FreePage(Page):
    """A freed page that is part of the free list."""

    __slots__ = ("next_free",)

    def __init__(self, page_id: int, next_free: int = -1):
        super().__init__(page_id)
        self.next_free = next_free


# ---------------------------------------------------------------------------
# Page serialization
# ---------------------------------------------------------------------------

def _finalize_page(buf: bytearray, page_size: int) -> bytes:
    """Pad buf to page_size - CRC_SIZE, then append CRC32 of the content.

    The CRC covers all bytes before the checksum field, providing integrity
    verification on every page read.
    """
    content_size = page_size - CRC_SIZE
    if len(buf) > content_size:
        raise ValueError(f"Page content too large: {len(buf)} > {content_size}")
    buf.extend(b"\x00" * (content_size - len(buf)))
    crc = zlib.crc32(bytes(buf)) & 0xFFFFFFFF
    buf += struct.pack("<I", crc)
    return bytes(buf)


def serialize_leaf(page: LeafPage, page_size: int) -> bytes:
    """Serialize a leaf page to bytes with CRC32 trailer."""
    buf = bytearray()
    buf += struct.pack(LEAF_HEADER_FMT, PAGE_LEAF, len(page.keys), page.prev, page.next)
    for k, v in zip(page.keys, page.values):
        _pack_kv(buf, k, v)
    return _finalize_page(buf, page_size)


def deserialize_leaf(data: bytes, page_id: int) -> LeafPage:
    """Deserialize a leaf page from bytes."""
    ptype, num_keys, prev, next_id = struct.unpack(LEAF_HEADER_FMT, data[:LEAF_HEADER_SIZE])
    page = LeafPage(page_id, prev=prev, next_id=next_id)
    offset = LEAF_HEADER_SIZE
    for _ in range(num_keys):
        k, v, offset = _unpack_kv(data, offset)
        page.keys.append(k)
        page.values.append(v)
    return page


def serialize_internal(page: InternalPage, page_size: int) -> bytes:
    """Serialize an internal page to bytes with CRC32 trailer."""
    buf = bytearray()
    buf += struct.pack(INTERNAL_HEADER_FMT, PAGE_INTERNAL, len(page.keys))
    # first child
    buf += struct.pack("<I", page.children[0])
    for i in range(len(page.keys)):
        _varint_encode(buf, len(page.keys[i]))
        buf.extend(page.keys[i])
        buf += struct.pack("<I", page.children[i + 1])
    return _finalize_page(buf, page_size)


def deserialize_internal(data: bytes, page_id: int) -> InternalPage:
    """Deserialize an internal page from bytes."""
    ptype, num_keys = struct.unpack(INTERNAL_HEADER_FMT, data[:INTERNAL_HEADER_SIZE])
    page = InternalPage(page_id)
    offset = INTERNAL_HEADER_SIZE
    child0 = struct.unpack("<I", data[offset:offset + 4])[0]
    page.children.append(child0)
    offset += 4
    for _ in range(num_keys):
        klen, offset = _varint_decode(data, offset)
        key = data[offset:offset + klen]
        offset += klen
        child = struct.unpack("<I", data[offset:offset + 4])[0]
        offset += 4
        page.keys.append(key)
        page.children.append(child)
    return page


def serialize_free(page: FreePage, page_size: int) -> bytes:
    """Serialize a free page to bytes with CRC32 trailer."""
    buf = bytearray()
    buf += struct.pack("<Bi", PAGE_FREE, page.next_free)
    return _finalize_page(buf, page_size)


def deserialize_free(data: bytes, page_id: int) -> FreePage:
    """Deserialize a free page from bytes."""
    ptype, next_free = struct.unpack("<Bi", data[:5])
    return FreePage(page_id, next_free=next_free)


def detect_page_type(data: bytes) -> int:
    """Detect the page type from the first byte of serialized data."""
    return struct.unpack("<B", data[:1])[0]


def verify_page_crc(data: bytes) -> bool:
    """Verify the CRC32 checksum of a serialized page.

    The last 4 bytes are the CRC32 of the preceding content.
    Returns True if the checksum matches, False otherwise.
    """
    if len(data) < CRC_SIZE:
        return False
    content = data[:-CRC_SIZE]
    stored_crc = struct.unpack("<I", data[-CRC_SIZE:])[0]
    return (zlib.crc32(content) & 0xFFFFFFFF) == stored_crc


# ---------------------------------------------------------------------------
# Prefix upper bound computation
# ---------------------------------------------------------------------------

def _prefix_upper_bound(prefix: bytes) -> Optional[bytes]:
    """Compute the smallest key strictly greater than all keys with the given prefix.

    This is done by treating the prefix as a big-endian number and adding 1
    to the last non-0xFF byte. If the prefix is all 0xFF bytes, there is no
    finite upper bound — we return None to signal "no upper bound".

    Special case: empty prefix b'' matches all keys. We return None to
    signal "no upper bound".
    """
    if not prefix:
        return None  # empty prefix = match everything
    for i in range(len(prefix) - 1, -1, -1):
        if prefix[i] != 0xFF:
            return prefix[:i] + bytes([prefix[i] + 1]) + b"\x00" * (len(prefix) - i - 1)
    # All 0xFF — no finite upper bound exists
    return None