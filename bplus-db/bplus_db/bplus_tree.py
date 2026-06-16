"""B+ Tree implementation with full CRUD, range queries, and serialization.

This module implements a generic B+ tree where:
- Internal nodes store keys and child pointers for navigation
- Leaf nodes store key-value pairs and are linked in a doubly-linked list
- All operations (insert, delete, search, range) are O(log n)
"""

from __future__ import annotations
import struct
from typing import Any, Iterator, Optional


class BPlusTreeNode:
    """Base class for B+ tree nodes."""

    def __init__(self, is_leaf: bool = False):
        self.is_leaf: bool = is_leaf
        self.keys: list = []
        self.parent: Optional[InternalNode] = None

    def is_root(self) -> bool:
        return self.parent is None


class LeafNode(BPlusTreeNode):
    """Leaf node storing key-value pairs with sibling links."""

    def __init__(self):
        super().__init__(is_leaf=True)
        self.values: list = []
        self.next: Optional[LeafNode] = None
        self.prev: Optional[LeafNode] = None

    def find_key_index(self, key) -> int:
        """Find the index where key is or should be inserted."""
        lo, hi = 0, len(self.keys)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.keys[mid] < key:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def insert_kv(self, key, value) -> None:
        """Insert a key-value pair into the leaf node."""
        idx = self.find_key_index(key)
        if idx < len(self.keys) and self.keys[idx] == key:
            # Update existing key
            self.values[idx] = value
        else:
            self.keys.insert(idx, key)
            self.values.insert(idx, value)

    def split(self) -> tuple:
        """Split this leaf node and return (new_leaf, split_key)."""
        mid = len(self.keys) // 2
        new_leaf = LeafNode()
        new_leaf.keys = self.keys[mid:]
        new_leaf.values = self.values[mid:]
        self.keys = self.keys[:mid]
        self.values = self.values[:mid]
        # Update sibling links
        new_leaf.next = self.next
        new_leaf.prev = self
        if self.next:
            self.next.prev = new_leaf
        self.next = new_leaf
        split_key = new_leaf.keys[0]
        return new_leaf, split_key

    def remove_key(self, key) -> bool:
        """Remove a key from the leaf. Returns True if found."""
        idx = self.find_key_index(key)
        if idx < len(self.keys) and self.keys[idx] == key:
            self.keys.pop(idx)
            self.values.pop(idx)
            return True
        return False


class InternalNode(BPlusTreeNode):
    """Internal node storing keys and child pointers."""

    def __init__(self):
        super().__init__(is_leaf=False)
        self.children: list[BPlusTreeNode] = []

    def find_child_index(self, key) -> int:
        """Find the child index to descend into for the given key.
        
        In B+ trees, equal keys go to the right subtree (children[i+1]).
        So we find the first key that is strictly greater than the search key.
        """
        lo, hi = 0, len(self.keys)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.keys[mid] <= key:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def insert_child(self, key, child) -> None:
        """Insert a key-child pair into this internal node."""
        idx = self.find_child_index(key)
        self.keys.insert(idx, key)
        self.children.insert(idx + 1, child)
        child.parent = self

    def split(self) -> tuple:
        """Split this internal node and return (new_node, pushed_key)."""
        mid = len(self.keys) // 2
        pushed_key = self.keys[mid]
        new_node = InternalNode()
        new_node.keys = self.keys[mid + 1:]
        new_node.children = self.children[mid + 1:]
        self.keys = self.keys[:mid]
        self.children = self.children[:mid + 1]
        # Update parent pointers
        for child in new_node.children:
            child.parent = new_node
        return new_node, pushed_key


class BPlusTree:
    """B+ Tree with configurable order, supporting full CRUD and range queries.

    Attributes:
        order: The maximum number of children for internal nodes.
               Minimum keys per node (except root) = ceil(order/2) - 1.
        size: Number of key-value pairs stored.
    """

    def __init__(self, order: int = 64):
        if order < 3:
            raise ValueError("B+ tree order must be at least 3")
        self.order = order
        self.root: BPlusTreeNode = LeafNode()
        self.size: int = 0

    def search(self, key) -> Optional[Any]:
        """Search for a key and return its value, or None if not found."""
        leaf = self._find_leaf(key)
        idx = leaf.find_key_index(key)
        if idx < len(leaf.keys) and leaf.keys[idx] == key:
            return leaf.values[idx]
        return None

    def insert(self, key, value) -> None:
        """Insert a key-value pair. Overwrites existing value if key exists."""
        leaf = self._find_leaf(key)
        was_update = key in leaf.keys
        leaf.insert_kv(key, value)

        if was_update:
            return  # No structural change needed

        self.size += 1

        if len(leaf.keys) > self.order - 1:
            self._split_leaf(leaf)

    def delete(self, key) -> bool:
        """Delete a key-value pair. Returns True if key was found."""
        leaf = self._find_leaf(key)
        if not leaf.remove_key(key):
            return False

        self.size -= 1

        # Handle underflow (except for root)
        if not leaf.is_root() and len(leaf.keys) < (self.order + 1) // 2 - 1:
            self._handle_underflow(leaf)

        # If root is empty internal node, make its only child the new root
        if not self.root.is_leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]
            self.root.parent = None

        return True

    def range_query(self, start_key=None, end_key=None) -> Iterator[tuple]:
        """Yield (key, value) pairs in the range [start_key, end_key].

        Args:
            start_key: Inclusive lower bound. If None, start from minimum.
            end_key: Inclusive upper bound. If None, go to maximum.
        """
        if start_key is not None:
            leaf = self._find_leaf(start_key)
            idx = leaf.find_key_index(start_key)
        else:
            # Start from leftmost leaf
            leaf = self._leftmost_leaf()
            idx = 0

        while leaf is not None:
            while idx < len(leaf.keys):
                key = leaf.keys[idx]
                if end_key is not None and key > end_key:
                    return
                yield key, leaf.values[idx]
                idx += 1
            leaf = leaf.next
            idx = 0

    def __len__(self) -> int:
        return self.size

    def __contains__(self, key) -> bool:
        return self.search(key) is not None

    def __iter__(self) -> Iterator[tuple]:
        yield from self.range_query()

    def _find_leaf(self, key) -> LeafNode:
        """Navigate the tree to find the leaf that should contain key."""
        node = self.root
        while not node.is_leaf:
            idx = node.find_child_index(key)
            node = node.children[idx]
        return node

    def _leftmost_leaf(self) -> LeafNode:
        """Return the leftmost leaf node."""
        node = self.root
        while not node.is_leaf:
            node = node.children[0]
        return node

    def _split_leaf(self, leaf: LeafNode) -> None:
        """Split an overfull leaf node and propagate up."""
        new_leaf, split_key = leaf.split()
        if leaf.is_root():
            new_root = InternalNode()
            new_root.keys = [split_key]
            new_root.children = [leaf, new_leaf]
            leaf.parent = new_root
            new_leaf.parent = new_root
            self.root = new_root
        else:
            parent = leaf.parent
            parent.insert_child(split_key, new_leaf)
            if len(parent.keys) > self.order - 1:
                self._split_internal(parent)

    def _split_internal(self, node: InternalNode) -> None:
        """Split an overfull internal node and propagate up."""
        new_node, pushed_key = node.split()
        if node.is_root():
            new_root = InternalNode()
            new_root.keys = [pushed_key]
            new_root.children = [node, new_node]
            node.parent = new_root
            new_node.parent = new_root
            self.root = new_root
        else:
            parent = node.parent
            parent.insert_child(pushed_key, new_node)
            if len(parent.keys) > self.order - 1:
                self._split_internal(parent)

    def _handle_underflow(self, node: BPlusTreeNode) -> None:
        """Handle underflow by borrowing from siblings or merging."""
        if node.is_root():
            return  # Root can have fewer keys

        parent = node.parent
        idx_in_parent = parent.children.index(node)
        min_keys = (self.order + 1) // 2 - 1

        if node.is_leaf:
            # Try borrowing from left sibling
            if idx_in_parent > 0:
                left_sib = parent.children[idx_in_parent - 1]
                if len(left_sib.keys) > min_keys:
                    self._borrow_from_left_leaf(node, left_sib, parent, idx_in_parent)
                    return

            # Try borrowing from right sibling
            if idx_in_parent < len(parent.children) - 1:
                right_sib = parent.children[idx_in_parent + 1]
                if len(right_sib.keys) > min_keys:
                    self._borrow_from_right_leaf(node, right_sib, parent, idx_in_parent)
                    return

            # Merge with a sibling
            if idx_in_parent > 0:
                self._merge_leaves(parent.children[idx_in_parent - 1], node, parent, idx_in_parent - 1)
            else:
                self._merge_leaves(node, parent.children[idx_in_parent + 1], parent, idx_in_parent)

        else:
            # Internal node underflow
            if idx_in_parent > 0:
                left_sib = parent.children[idx_in_parent - 1]
                if len(left_sib.keys) > min_keys:
                    self._borrow_from_left_internal(node, left_sib, parent, idx_in_parent)
                    return

            if idx_in_parent < len(parent.children) - 1:
                right_sib = parent.children[idx_in_parent + 1]
                if len(right_sib.keys) > min_keys:
                    self._borrow_from_right_internal(node, right_sib, parent, idx_in_parent)
                    return

            # Merge
            if idx_in_parent > 0:
                self._merge_internals(parent.children[idx_in_parent - 1], node, parent, idx_in_parent - 1)
            else:
                self._merge_internals(node, parent.children[idx_in_parent + 1], parent, idx_in_parent)

    def _borrow_from_left_leaf(self, node, left_sib, parent, idx_in_parent):
        """Borrow a key from the left sibling leaf."""
        key = left_sib.keys.pop()
        value = left_sib.values.pop()
        node.keys.insert(0, key)
        node.values.insert(0, value)
        parent.keys[idx_in_parent - 1] = node.keys[0]

    def _borrow_from_right_leaf(self, node, right_sib, parent, idx_in_parent):
        """Borrow a key from the right sibling leaf."""
        key = right_sib.keys.pop(0)
        value = right_sib.values.pop(0)
        node.keys.append(key)
        node.values.append(value)
        parent.keys[idx_in_parent] = right_sib.keys[0]

    def _borrow_from_left_internal(self, node, left_sib, parent, idx_in_parent):
        """Borrow a key from the left sibling internal node."""
        parent_key = parent.keys[idx_in_parent - 1]
        borrowed_key = left_sib.keys.pop()
        borrowed_child = left_sib.children.pop()

        node.keys.insert(0, parent_key)
        node.children.insert(0, borrowed_child)
        borrowed_child.parent = node

        parent.keys[idx_in_parent - 1] = borrowed_key

    def _borrow_from_right_internal(self, node, right_sib, parent, idx_in_parent):
        """Borrow a key from the right sibling internal node."""
        parent_key = parent.keys[idx_in_parent]
        borrowed_key = right_sib.keys.pop(0)
        borrowed_child = right_sib.children.pop(0)

        node.keys.append(parent_key)
        node.children.append(borrowed_child)
        borrowed_child.parent = node

        parent.keys[idx_in_parent] = borrowed_key

    def _merge_leaves(self, left: LeafNode, right: LeafNode, parent: InternalNode, sep_idx: int):
        """Merge right leaf into left leaf."""
        left.keys.extend(right.keys)
        left.values.extend(right.values)
        left.next = right.next
        if right.next:
            right.next.prev = left

        parent.keys.pop(sep_idx)
        parent.children.remove(right)

        if not parent.is_root() and len(parent.keys) < (self.order + 1) // 2 - 1:
            self._handle_underflow(parent)
        elif parent.is_root() and len(parent.keys) == 0:
            self.root = left
            left.parent = None

    def _merge_internals(self, left: InternalNode, right: InternalNode, parent: InternalNode, sep_idx: int):
        """Merge right internal node into left internal node."""
        sep_key = parent.keys[sep_idx]
        left.keys.append(sep_key)
        left.keys.extend(right.keys)
        left.children.extend(right.children)
        for child in right.children:
            child.parent = left

        parent.keys.pop(sep_idx)
        parent.children.remove(right)

        if not parent.is_root() and len(parent.keys) < (self.order + 1) // 2 - 1:
            self._handle_underflow(parent)
        elif parent.is_root() and len(parent.keys) == 0:
            self.root = left
            left.parent = None

    def print_tree(self, node=None, level=0) -> str:
        """Return a string representation of the tree structure."""
        if node is None:
            node = self.root
        lines = []
        prefix = "  " * level
        if node.is_leaf:
            lines.append(f"{prefix}Leaf: {node.keys}")
        else:
            lines.append(f"{prefix}Internal: {node.keys}")
            for child in node.children:
                lines.append(self.print_tree(child, level + 1))
        return "\n".join(lines)