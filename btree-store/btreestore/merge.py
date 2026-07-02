"""
B+Tree rebalancing: merge and borrow operations for self-balancing deletes.

When a leaf or internal page becomes too empty after a deletion, the tree
rebalances by either:
  - **Borrowing** a key from a sibling (left or right), or
  - **Merging** the page with a sibling if neither has enough keys to spare.

This keeps pages well-filled, preventing the tree from becoming sparse
after many deletions (which was previously only fixable via compaction).

The minimum fill factor is 25% of the page capacity. A page is considered
underflowing when its serialized size drops below 25% of usable capacity,
or when an internal node has fewer than ceil(branching/2) children.
"""

from __future__ import annotations

import bisect
from typing import Optional, TYPE_CHECKING

from .pages import (
    Page, LeafPage, InternalPage,
    CRC_SIZE, LEAF_HEADER_SIZE, INTERNAL_HEADER_SIZE,
)
from .logging_util import get_logger

if TYPE_CHECKING:
    from .tree import BPlusTree

logger = get_logger()


class Rebalancer:
    """Handles B+Tree rebalancing after deletions.

    Created per-rebalance operation by the BPlusTree. Walks up from
    the underflowing leaf to the root, rebalancing at each level.
    """

    def __init__(self, tree: "BPlusTree"):
        self.tree = tree
        self.store = tree.store

    def rebalance_leaf(self, leaf: LeafPage) -> None:
        """Rebalance a leaf page that may be underflowing.

        Attempts to borrow from a sibling first; if that fails, merges
        with a sibling. Propagates underflow up the tree.
        """
        if not self._leaf_underflow(leaf):
            return

        if self.tree.root_id == leaf.id:
            # Root leaf: no siblings to borrow/merge from. It's fine
            # for the root to be small.
            return

        parent = self.tree._find_parent(self.tree.root_id, leaf.id)
        if parent is None:
            logger.warning(f"rebalance_leaf: no parent for leaf {leaf.id}")
            return

        child_idx = parent.children.index(leaf.id)
        left_sibling = self._try_borrow_left_leaf(parent, child_idx)
        if left_sibling:
            logger.debug(f"Borrowed from left sibling for leaf {leaf.id}")
            return

        right_sibling = self._try_borrow_right_leaf(parent, child_idx)
        if right_sibling:
            logger.debug(f"Borrowed from right sibling for leaf {leaf.id}")
            return

        # Can't borrow — merge with a sibling
        if child_idx > 0:
            self._merge_leaf(parent, child_idx - 1, child_idx)
            logger.debug(f"Merged leaf {leaf.id} into left sibling")
        else:
            self._merge_leaf(parent, child_idx, child_idx + 1)
            logger.debug(f"Merged right sibling into leaf {leaf.id}")

        # Propagate underflow to parent
        self._rebalance_internal(parent)

    def _leaf_underflow(self, leaf: LeafPage) -> bool:
        """Check if a leaf page is underflowing (< 25% capacity and has a sibling)."""
        if len(leaf.keys) == 0:
            return True
        size = LEAF_HEADER_SIZE
        for k, v in zip(leaf.keys, leaf.values):
            size += len(k) + len(v) + 10
        threshold = (self.store.page_size - CRC_SIZE) * 0.25
        return size < threshold

    def _try_borrow_left_leaf(self, parent: InternalPage,
                               child_idx: int) -> bool:
        """Try to borrow the last key from the left sibling.

        Returns True if the borrow succeeded.
        """
        if child_idx == 0:
            return False  # no left sibling
        left_id = parent.children[child_idx - 1]
        left = self.tree._read_page(left_id)
        if not isinstance(left, LeafPage):
            return False

        # Check if left sibling has enough keys to spare
        if len(left.keys) <= 1:
            return False
        left_size = LEAF_HEADER_SIZE
        for k, v in zip(left.keys, left.values):
            left_size += len(k) + len(v) + 10
        if left_size < (self.store.page_size - CRC_SIZE) * 0.35:
            return False  # sibling too small to share

        # Move the last key from left to the front of our leaf
        leaf_id = parent.children[child_idx]
        leaf = self.tree._read_page(leaf_id)
        assert isinstance(leaf, LeafPage)

        borrowed_key = left.keys.pop()
        borrowed_val = left.values.pop()
        leaf.keys.insert(0, borrowed_key)
        leaf.values.insert(0, borrowed_val)

        # Update separator key in parent
        parent.keys[child_idx - 1] = leaf.keys[0]

        left.dirty = True
        leaf.dirty = True
        parent.dirty = True
        self.tree._write_page(left)
        self.tree._write_page(leaf)
        self.tree._write_page(parent)
        return True

    def _try_borrow_right_leaf(self, parent: InternalPage,
                                child_idx: int) -> bool:
        """Try to borrow the first key from the right sibling.

        Returns True if the borrow succeeded.
        """
        if child_idx >= len(parent.children) - 1:
            return False  # no right sibling
        right_id = parent.children[child_idx + 1]
        right = self.tree._read_page(right_id)
        if not isinstance(right, LeafPage):
            return False

        if len(right.keys) <= 1:
            return False
        right_size = LEAF_HEADER_SIZE
        for k, v in zip(right.keys, right.values):
            right_size += len(k) + len(v) + 10
        if right_size < (self.store.page_size - CRC_SIZE) * 0.35:
            return False

        leaf_id = parent.children[child_idx]
        leaf = self.tree._read_page(leaf_id)
        assert isinstance(leaf, LeafPage)

        borrowed_key = right.keys.pop(0)
        borrowed_val = right.values.pop(0)
        leaf.keys.append(borrowed_key)
        leaf.values.append(borrowed_val)

        # Update separator key in parent
        parent.keys[child_idx] = right.keys[0]

        right.dirty = True
        leaf.dirty = True
        parent.dirty = True
        self.tree._write_page(right)
        self.tree._write_page(leaf)
        self.tree._write_page(parent)
        return True

    def _merge_leaf(self, parent: InternalPage, left_idx: int,
                    right_idx: int) -> None:
        """Merge the right leaf into the left leaf.

        Removes the right leaf from the parent and frees its page.
        Updates the linked-list pointers.
        """
        left_id = parent.children[left_idx]
        right_id = parent.children[right_idx]
        left = self.tree._read_page(left_id)
        right = self.tree._read_page(right_id)
        assert isinstance(left, LeafPage)
        assert isinstance(right, LeafPage)

        # Merge right's keys into left
        left.keys.extend(right.keys)
        left.values.extend(right.values)
        left.next = right.next
        left.dirty = True

        # Fix linked list: if right had a next, update its prev
        if right.next != -1:
            next_page = self.tree._read_page(right.next)
            if isinstance(next_page, LeafPage):
                next_page.prev = left_id
                next_page.dirty = True
                self.tree._write_page(next_page)

        # Remove separator and right child from parent
        parent.keys.pop(left_idx)
        parent.children.pop(right_idx)
        parent.dirty = True

        # Free the right page
        self.store._free_page_id(right_id)
        self.tree._write_page(left)
        self.tree._write_page(parent)

    def _rebalance_internal(self, page: InternalPage) -> None:
        """Rebalance an internal page, propagating up to the root."""
        # Check if the root has only one child — collapse it
        if page.id == self.tree.root_id:
            if len(page.children) == 1 and len(page.keys) == 0:
                # Root has one child: make that child the new root
                old_root = self.tree.root_id
                self.tree.root_id = page.children[0]
                self.store.header["root_page_id"] = self.tree.root_id
                self.store._free_page_id(old_root)
                logger.debug(f"Collapsed root: {old_root} -> {self.tree.root_id}")
            return

        if not self._internal_underflow(page):
            return

        parent = self.tree._find_parent(self.tree.root_id, page.id)
        if parent is None:
            return

        child_idx = parent.children.index(page.id)

        # Try to borrow from left internal sibling
        if child_idx > 0:
            if self._try_borrow_left_internal(parent, child_idx):
                return

        # Try to borrow from right internal sibling
        if child_idx < len(parent.children) - 1:
            if self._try_borrow_right_internal(parent, child_idx):
                return

        # Merge with a sibling
        if child_idx > 0:
            self._merge_internal(parent, child_idx - 1, child_idx)
        else:
            self._merge_internal(parent, child_idx, child_idx + 1)

        self._rebalance_internal(parent)

    def _internal_underflow(self, page: InternalPage) -> bool:
        """Check if an internal page is underflowing."""
        min_children = max(2, self.store.branching // 2)
        return len(page.children) < min_children

    def _try_borrow_left_internal(self, parent: InternalPage,
                                   child_idx: int) -> bool:
        """Try to borrow a child from the left internal sibling."""
        if child_idx == 0:
            return False
        left_id = parent.children[child_idx - 1]
        left = self.tree._read_page(left_id)
        if not isinstance(left, InternalPage):
            return False

        min_children = max(2, self.store.branching // 2)
        if len(left.children) <= min_children:
            return False

        page_id = parent.children[child_idx]
        page = self.tree._read_page(page_id)
        assert isinstance(page, InternalPage)

        # Rotate: parent's separator key moves down to page,
        # left's last key moves up to parent, left's last child moves to page
        sep_key = parent.keys[child_idx - 1]
        page.keys.insert(0, sep_key)
        page.children.insert(0, left.children.pop())

        parent.keys[child_idx - 1] = left.keys.pop()

        left.dirty = True
        page.dirty = True
        parent.dirty = True
        self.tree._write_page(left)
        self.tree._write_page(page)
        self.tree._write_page(parent)
        return True

    def _try_borrow_right_internal(self, parent: InternalPage,
                                    child_idx: int) -> bool:
        """Try to borrow a child from the right internal sibling."""
        if child_idx >= len(parent.children) - 1:
            return False
        right_id = parent.children[child_idx + 1]
        right = self.tree._read_page(right_id)
        if not isinstance(right, InternalPage):
            return False

        min_children = max(2, self.store.branching // 2)
        if len(right.children) <= min_children:
            return False

        page_id = parent.children[child_idx]
        page = self.tree._read_page(page_id)
        assert isinstance(page, InternalPage)

        sep_key = parent.keys[child_idx]
        page.keys.append(sep_key)
        page.children.append(right.children.pop(0))

        parent.keys[child_idx] = right.keys.pop(0)

        right.dirty = True
        page.dirty = True
        parent.dirty = True
        self.tree._write_page(right)
        self.tree._write_page(page)
        self.tree._write_page(parent)
        return True

    def _merge_internal(self, parent: InternalPage, left_idx: int,
                        right_idx: int) -> None:
        """Merge the right internal page into the left internal page."""
        left_id = parent.children[left_idx]
        right_id = parent.children[right_idx]
        left = self.tree._read_page(left_id)
        right = self.tree._read_page(right_id)
        assert isinstance(left, InternalPage)
        assert isinstance(right, InternalPage)

        # The parent's separator key moves down into the merged node
        sep_key = parent.keys.pop(left_idx)
        left.keys.append(sep_key)
        left.keys.extend(right.keys)
        left.children.extend(right.children)

        parent.children.pop(right_idx)
        parent.dirty = True
        left.dirty = True

        self.store._free_page_id(right_id)
        self.tree._write_page(left)
        self.tree._write_page(parent)