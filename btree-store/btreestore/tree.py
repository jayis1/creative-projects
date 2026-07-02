"""
B+Tree implementation for btreestore.

Provides the core B+Tree data structure with page management,
disk persistence, and structural modifications (splits, validation).
"""

from __future__ import annotations

import bisect
from typing import Iterator, List, Optional, Tuple

from .pages import (
    Page, LeafPage, InternalPage, FreePage,
    CRC_SIZE, LEAF_HEADER_SIZE, INTERNAL_HEADER_SIZE,
    detect_page_type, deserialize_leaf, deserialize_internal,
    serialize_leaf, serialize_internal, verify_page_crc,
)
from .logging_util import get_logger

logger = get_logger()


class BPlusTree:
    """In-memory B+Tree with page management and disk persistence.

    This implementation keeps pages in an LRU cache backed by the store file.
    Structural modifications (splits, merges) are done eagerly on the cached
    pages; dirty pages are flushed on commit or cache eviction.
    """

    def __init__(self, store: "Store"):
        self.store = store
        self.root_id = store.header["root_page_id"]

    def _read_page(self, page_id: int) -> Page:
        return self.store._read_page(page_id)

    def _write_page(self, page: Page) -> None:
        self.store._write_page(page)

    def _new_page(self) -> int:
        return self.store._alloc_page()

    def _free_page(self, page_id: int) -> None:
        self.store._free_page_id(page_id)

    def _search_leaf(self, key: bytes) -> LeafPage:
        """Find the leaf page that should contain key."""
        page_id = self.root_id
        while True:
            page = self._read_page(page_id)
            if isinstance(page, LeafPage):
                return page
            assert isinstance(page, InternalPage)
            # Find child: bisect to find first key >= search key, go left
            idx = bisect.bisect_right(page.keys, key)
            page_id = page.children[idx]

    def get(self, key: bytes) -> Optional[bytes]:
        """Get the value for a key, or None if not present."""
        leaf = self._search_leaf(key)
        idx = bisect.bisect_left(leaf.keys, key)
        if idx < len(leaf.keys) and leaf.keys[idx] == key:
            return leaf.values[idx]
        return None

    def insert(self, key: bytes, value: bytes) -> None:
        """Insert or update a key-value pair in the tree."""
        # Check that key+value can fit in a single page
        max_size = (self.store.page_size - CRC_SIZE) * 0.9
        estimated = len(key) + len(value) + 20  # overhead for headers + varints
        if estimated > max_size:
            raise ValueError(
                f"Key+value too large ({estimated} bytes) for page size "
                f"({self.store.page_size} bytes). Max combined ~{int(max_size)} bytes."
            )
        leaf = self._search_leaf(key)
        idx = bisect.bisect_left(leaf.keys, key)
        if idx < len(leaf.keys) and leaf.keys[idx] == key:
            # Update existing
            leaf.values[idx] = value
            leaf.dirty = True
            return
        leaf.keys.insert(idx, key)
        leaf.values.insert(idx, value)
        leaf.dirty = True
        if self._leaf_needs_split(leaf):
            self._split_leaf(leaf)

    def _leaf_needs_split(self, leaf: LeafPage) -> bool:
        """Check if a leaf page needs to be split."""
        size = LEAF_HEADER_SIZE
        for k, v in zip(leaf.keys, leaf.values):
            size += len(k) + len(v) + 10  # overhead for varints
        return size > (self.store.page_size - CRC_SIZE) * 0.9

    def _split_leaf(self, leaf: LeafPage) -> None:
        """Split a leaf page at the median."""
        mid = len(leaf.keys) // 2
        new_id = self._new_page()
        new_leaf = LeafPage(new_id, prev=leaf.id, next_id=leaf.next)
        new_leaf.keys = leaf.keys[mid:]
        new_leaf.values = leaf.values[mid:]
        leaf.keys = leaf.keys[:mid]
        leaf.values = leaf.values[:mid]
        leaf.next = new_id
        leaf.dirty = True
        new_leaf.dirty = True
        self._write_page(new_leaf)
        self._write_page(leaf)
        # Update linked list: if leaf had a next, fix its prev
        if new_leaf.next != -1:
            next_page = self._read_page(new_leaf.next)
            assert isinstance(next_page, LeafPage)
            next_page.prev = new_id
            next_page.dirty = True
            self._write_page(next_page)
        # Propagate separator up
        self._insert_separator(leaf.id, new_leaf.keys[0], new_id)
        logger.debug(f"Split leaf page {leaf.id} -> {new_id}, sep_key={new_leaf.keys[0]!r}")

    def _insert_separator(self, left_id: int, sep_key: bytes, right_id: int) -> None:
        """Insert a separator key into the parent of left_id."""
        if self.root_id == left_id:
            # Root was a leaf; create new root
            new_root_id = self._new_page()
            new_root = InternalPage(new_root_id)
            new_root.keys = [sep_key]
            new_root.children = [left_id, right_id]
            new_root.dirty = True
            self._write_page(new_root)
            self.root_id = new_root_id
            self.store.header["root_page_id"] = new_root_id
            return
        # Find parent of left_id
        parent = self._find_parent(self.root_id, left_id)
        assert parent is not None, "parent not found"
        idx = parent.children.index(left_id)
        parent.keys.insert(idx, sep_key)
        parent.children.insert(idx + 1, right_id)
        parent.dirty = True
        if self._internal_needs_split(parent):
            self._split_internal(parent)
        else:
            self._write_page(parent)

    def _find_parent(self, page_id: int, child_id: int) -> Optional[InternalPage]:
        """Find the parent of child_id starting from page_id."""
        page = self._read_page(page_id)
        if isinstance(page, LeafPage):
            return None
        if child_id in page.children:
            return page
        # Search down
        for c in page.children:
            parent = self._find_parent(c, child_id)
            if parent is not None:
                return parent
        return None

    def _internal_needs_split(self, page: InternalPage) -> bool:
        """Check if an internal page needs to be split."""
        size = INTERNAL_HEADER_SIZE + 4  # first child
        for k in page.keys:
            size += len(k) + 10
        size += 4 * len(page.children)
        return size > (self.store.page_size - CRC_SIZE) * 0.9 or \
            len(page.children) > self.store.branching * 2

    def _split_internal(self, page: InternalPage) -> None:
        """Split an internal page at the median."""
        mid = len(page.keys) // 2
        sep_key = page.keys[mid]
        new_id = self._new_page()
        new_internal = InternalPage(new_id)
        new_internal.keys = page.keys[mid + 1:]
        new_internal.children = page.children[mid + 1:]
        page.keys = page.keys[:mid]
        page.children = page.children[:mid + 1]
        page.dirty = True
        new_internal.dirty = True
        self._write_page(page)
        self._write_page(new_internal)
        self._insert_separator(page.id, sep_key, new_id)
        logger.debug(f"Split internal page {page.id} -> {new_id}, sep_key={sep_key!r}")

    def delete(self, key: bytes, rebalance: bool = True) -> bool:
        """Delete a key from the tree. Returns True if the key existed.

        When rebalance=True (default), the tree is rebalanced after the
        deletion by borrowing from or merging with sibling pages. This
        keeps the tree dense and prevents sparse pages. Set rebalance=False
        for faster deletions if you plan to compact periodically.
        """
        leaf = self._search_leaf(key)
        idx = bisect.bisect_left(leaf.keys, key)
        if idx >= len(leaf.keys) or leaf.keys[idx] != key:
            return False
        leaf.keys.pop(idx)
        leaf.values.pop(idx)
        leaf.dirty = True
        self._write_page(leaf)

        if rebalance:
            from .merge import Rebalancer
            rebalancer = Rebalancer(self)
            rebalancer.rebalance_leaf(leaf)

        return True

    def scan(self, low: Optional[bytes], high: Optional[bytes],
             include_high: bool = False) -> Iterator[Tuple[bytes, bytes]]:
        """Yield (key, value) pairs in [low, high) or [low, high]."""
        if self.root_id == -1:
            return
        # Find starting leaf
        if low is not None:
            leaf = self._search_leaf(low)
        else:
            leaf = self._leftmost_leaf()
        while leaf is not None:
            for i, k in enumerate(leaf.keys):
                if low is not None and k < low:
                    continue
                if high is not None:
                    if include_high:
                        if k > high:
                            return
                    else:
                        if k >= high:
                            return
                yield (k, leaf.values[i])
            if leaf.next == -1:
                break
            leaf = self._read_page(leaf.next)
            assert isinstance(leaf, LeafPage)

    def _leftmost_leaf(self) -> Optional[LeafPage]:
        """Return the leftmost leaf page, or None if tree is empty."""
        if self.root_id == -1:
            return None
        page_id = self.root_id
        while True:
            page = self._read_page(page_id)
            if isinstance(page, LeafPage):
                return page
            page_id = page.children[0]

    def _rightmost_leaf(self) -> Optional[LeafPage]:
        """Return the rightmost leaf page, or None if tree is empty."""
        if self.root_id == -1:
            return None
        page_id = self.root_id
        while True:
            page = self._read_page(page_id)
            if isinstance(page, LeafPage):
                return page
            page_id = page.children[-1]

    def count(self) -> int:
        """Count total keys in the tree by traversing all leaves."""
        n = 0
        leaf = self._leftmost_leaf()
        while leaf is not None:
            n += len(leaf.keys)
            if leaf.next == -1:
                break
            leaf = self._read_page(leaf.next)
        return n

    def validate(self) -> bool:
        """Check tree invariants: ordering, parent-child consistency."""
        if self.root_id == -1:
            return True
        return self._validate_page(self.root_id, None, None)

    def _validate_page(self, page_id: int, low: Optional[bytes],
                       high: Optional[bytes]) -> bool:
        """Recursively validate a page and its children."""
        page = self._read_page(page_id)
        if isinstance(page, LeafPage):
            for i, k in enumerate(page.keys):
                if low is not None and k < low:
                    return False
                if high is not None and k >= high:
                    return False
                if i > 0 and page.keys[i - 1] >= k:
                    return False
            return True
        if isinstance(page, InternalPage):
            for i, k in enumerate(page.keys):
                if i > 0 and page.keys[i - 1] >= k:
                    return False
            # child[0] < keys[0], child[i] in [keys[i-1], keys[i])
            if not self._validate_page(page.children[0], low, page.keys[0]):
                return False
            for i in range(1, len(page.keys)):
                if not self._validate_page(page.children[i], page.keys[i - 1], page.keys[i]):
                    return False
            if not self._validate_page(page.children[-1], page.keys[-1], high):
                return False
            return True
        return False

    def depth(self) -> int:
        """Return the height of the B+Tree (0 = single leaf)."""
        if self.root_id == -1:
            return 0
        page_id = self.root_id
        d = 0
        while True:
            page = self._read_page(page_id)
            if isinstance(page, LeafPage):
                return d
            d += 1
            page_id = page.children[0]

    def compact(self) -> int:
        """Rebuild the tree by reinserting all keys in sorted order.

        This eliminates sparse pages from deletions and rebuilds
        the tree structure. Returns the number of keys compacted.
        """
        # Collect all entries
        entries: List[Tuple[bytes, bytes]] = list(self.scan(None, None))
        if not entries:
            return 0
        # Free all pages
        # We need to collect all page IDs first
        all_page_ids = self._collect_all_page_ids()
        root_id = self.root_id

        # Reset to a fresh root
        new_root_id = self.store._alloc_page()
        new_root = LeafPage(new_root_id)
        self._write_page(new_root)

        # Free old pages
        for pid in all_page_ids:
            if pid != new_root_id:
                self.store._free_page_id(pid)

        self.root_id = new_root_id
        self.store.header["root_page_id"] = new_root_id

        # Reinsert all entries (they're already sorted from scan)
        for k, v in entries:
            self.insert(k, v)

        logger.info(f"Compacted tree: {len(entries)} keys, freed {len(all_page_ids)} old pages")
        return len(entries)

    def _collect_all_page_ids(self) -> List[int]:
        """Collect all page IDs in the tree (for compaction)."""
        ids: List[int] = []
        if self.root_id == -1:
            return ids
        self._collect_page_ids(self.root_id, ids)
        return ids

    def _collect_page_ids(self, page_id: int, ids: List[int]) -> None:
        """Recursively collect page IDs."""
        ids.append(page_id)
        page = self._read_page(page_id)
        if isinstance(page, InternalPage):
            for child_id in page.children:
                self._collect_page_ids(child_id, ids)