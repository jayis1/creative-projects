"""
Backward-compatibility shim for the original btree.py module.

This module re-exports all public symbols from the new btreestore package
so existing code using `import btree` continues to work.
"""

from btreestore.store import Store
from btreestore.transaction import Transaction
from btreestore.cursor import Cursor
from btreestore.tree import BPlusTree
from btreestore.pages import (
    Page, LeafPage, InternalPage, FreePage,
    MAGIC, VERSION, HEADER_FMT, HEADER_SIZE,
    PAGE_LEAF, PAGE_INTERNAL, PAGE_FREE, CRC_SIZE,
    DEFAULT_PAGE_SIZE, DEFAULT_BRANCHING, DEFAULT_CACHE_SIZE,
    LEAF_HEADER_FMT, LEAF_HEADER_SIZE,
    INTERNAL_HEADER_FMT, INTERNAL_HEADER_SIZE,
    detect_page_type, verify_page_crc,
    serialize_leaf, deserialize_leaf,
    serialize_internal, deserialize_internal,
    serialize_free, deserialize_free,
    _varint_encode, _varint_decode,
    _pack_kv, _unpack_kv,
    _finalize_page,
    _prefix_upper_bound,
)

# Backward-compatible alias
CACHE_SIZE = DEFAULT_CACHE_SIZE

__all__ = [
    "Store", "Transaction", "Cursor", "BPlusTree",
    "Page", "LeafPage", "InternalPage", "FreePage",
    "MAGIC", "VERSION", "HEADER_FMT", "HEADER_SIZE",
    "PAGE_LEAF", "PAGE_INTERNAL", "PAGE_FREE", "CRC_SIZE",
    "DEFAULT_PAGE_SIZE", "DEFAULT_BRANCHING", "CACHE_SIZE",
    "LEAF_HEADER_FMT", "LEAF_HEADER_SIZE",
    "INTERNAL_HEADER_FMT", "INTERNAL_HEADER_SIZE",
    "detect_page_type", "verify_page_crc",
    "serialize_leaf", "deserialize_leaf",
    "serialize_internal", "deserialize_internal",
    "serialize_free", "deserialize_free",
    "_varint_encode", "_varint_decode",
    "_pack_kv", "_unpack_kv",
    "_finalize_page",
    "_prefix_upper_bound",
]