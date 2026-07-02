"""
Streaming cursor: memory-efficient iteration over large ranges.

Unlike the regular Cursor (which materializes all results at creation),
the StreamingCursor reads pages lazily from the B+Tree as iteration
proceeds. This allows iterating over millions of entries without
loading them all into memory at once.

Usage:
    from btreestore import Store
    from btreestore.streaming_cursor import StreamingCursor

    with Store("mydb.btree") as store:
        for key, value in StreamingCursor(store):
            process(key, value)
"""

from __future__ import annotations

from typing import Iterator, Optional, Tuple, Union

from .pages import LeafPage


class StreamingCursor:
    """Lazily iterate over (key, value) pairs from the B+Tree.

    Reads leaf pages one at a time, yielding entries as it goes.
    Memory usage is O(1 page) instead of O(total entries).
    """

    def __init__(
        self,
        store,
        low: Optional[bytes] = None,
        high: Optional[bytes] = None,
        include_high: bool = False,
        reverse: bool = False,
        limit: Optional[int] = None,
    ):
        """Create a streaming cursor.

        Args:
            store: A btreestore.Store instance.
            low: Lower bound key (inclusive), or None for unbounded.
            high: Upper bound key (exclusive unless include_high=True).
            include_high: If True, high is inclusive.
            reverse: If True, iterate in descending key order.
            limit: Maximum number of entries to yield.
        """
        self.store = store
        self._low = low
        self._high = high
        self._include_high = include_high
        self._reverse = reverse
        self._limit = limit
        self._count = 0

    def __iter__(self) -> Iterator[Tuple[bytes, bytes]]:
        return self._iterate()

    def _iterate(self) -> Iterator[Tuple[bytes, bytes]]:
        if self.store.tree is None or self.store.tree.root_id == -1:
            return

        if self._reverse:
            yield from self._iterate_reverse()
        else:
            yield from self._iterate_forward()

    def _iterate_forward(self) -> Iterator[Tuple[bytes, bytes]]:
        tree = self.store.tree
        # Find starting leaf
        if self._low is not None:
            leaf = tree._search_leaf(self._low)
        else:
            leaf = tree._leftmost_leaf()

        while leaf is not None:
            for i, k in enumerate(leaf.keys):
                if self._low is not None and k < self._low:
                    continue
                if self._high is not None:
                    if self._include_high:
                        if k > self._high:
                            return
                    else:
                        if k >= self._high:
                            return
                yield (k, leaf.values[i])
                self._count += 1
                if self._limit is not None and self._count >= self._limit:
                    return

            if leaf.next == -1:
                break
            leaf = tree._read_page(leaf.next)
            if not isinstance(leaf, LeafPage):
                break

    def _iterate_reverse(self) -> Iterator[Tuple[bytes, bytes]]:
        tree = self.store.tree
        # Find ending leaf (rightmost in range)
        if self._high is not None:
            leaf = tree._search_leaf(self._high)
        else:
            leaf = tree._rightmost_leaf()

        while leaf is not None:
            # Iterate keys in reverse within the leaf
            for i in range(len(leaf.keys) - 1, -1, -1):
                k = leaf.keys[i]
                if self._high is not None:
                    if self._include_high:
                        if k > self._high:
                            continue
                    else:
                        if k >= self._high:
                            continue
                if self._low is not None and k < self._low:
                    return
                yield (k, leaf.values[i])
                self._count += 1
                if self._limit is not None and self._count >= self._limit:
                    return

            if leaf.prev == -1:
                break
            leaf = tree._read_page(leaf.prev)
            if not isinstance(leaf, LeafPage):
                break

    def count(self) -> int:
        """Return the number of entries yielded so far."""
        return self._count