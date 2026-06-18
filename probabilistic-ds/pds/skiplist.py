"""Skip list: probabilistic ordered map.

A skip list provides O(log n) expected search/insert/delete with
probabilistic balancing (no rotations needed).  Used internally as
a support structure and exposed as a general-purpose ordered map.

Based on Pugh (1990).
"""
import random


class _SkipNode:
    __slots__ = ("key", "value", "forward")

    def __init__(self, key, value, level: int):
        self.key = key
        self.value = value
        self.forward: list[_SkipNode | None] = [None] * (level + 1)


class SkipList:
    """Probabilistic ordered map with O(log n) expected operations.

    Parameters
    ----------
    max_level : int
        Maximum number of levels.  Default 16 supports ~65k elements well.
    p : float
        Probability of promoting a node to the next level (default 0.5).

    Examples
    --------
    >>> sl = SkipList()
    >>> sl.insert(3, "c")
    >>> sl.insert(1, "a")
    >>> sl.insert(2, "b")
    >>> [k for k, v in sl]
    [1, 2, 3]
    >>> sl.search(2)
    'b'
    """

    def __init__(self, max_level: int = 16, p: float = 0.5):
        if max_level < 1:
            raise ValueError("max_level must be >= 1")
        if not (0 < p < 1):
            raise ValueError("p must be in (0, 1)")
        self.max_level = max_level
        self.p = p
        self._header = _SkipNode(None, None, max_level)
        self._level = 0
        self._size = 0

    def _random_level(self) -> int:
        lvl = 0
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def insert(self, key, value) -> None:
        """Insert or update a key-value pair."""
        update = [self._header] * (self.max_level + 1)
        x = self._header
        for i in range(self._level, -1, -1):
            while x.forward[i] is not None and x.forward[i].key < key:
                x = x.forward[i]
            update[i] = x
        x = x.forward[0]

        if x is not None and x.key == key:
            x.value = value  # update
        else:
            lvl = self._random_level()
            if lvl > self._level:
                for i in range(self._level + 1, lvl + 1):
                    update[i] = self._header
                self._level = lvl
            new_node = _SkipNode(key, value, lvl)
            for i in range(lvl + 1):
                new_node.forward[i] = update[i].forward[i]
                update[i].forward[i] = new_node
            self._size += 1

    def search(self, key):
        """Return value for key, or raise KeyError if not found."""
        x = self._header
        for i in range(self._level, -1, -1):
            while x.forward[i] is not None and x.forward[i].key < key:
                x = x.forward[i]
        x = x.forward[0]
        if x is not None and x.key == key:
            return x.value
        raise KeyError(key)

    def __contains__(self, key) -> bool:
        try:
            self.search(key)
            return True
        except KeyError:
            return False

    def delete(self, key) -> bool:
        """Delete a key. Returns True if found and removed."""
        update = [self._header] * (self.max_level + 1)
        x = self._header
        for i in range(self._level, -1, -1):
            while x.forward[i] is not None and x.forward[i].key < key:
                x = x.forward[i]
            update[i] = x
        x = x.forward[0]
        if x is None or x.key != key:
            return False

        for i in range(self._level + 1):
            if update[i].forward[i] is not x:
                break
            update[i].forward[i] = x.forward[i]

        while self._level > 0 and self._header.forward[self._level] is None:
            self._level -= 1
        self._size -= 1
        return True

    def __iter__(self):
        x = self._header.forward[0]
        while x is not None:
            yield (x.key, x.value)
            x = x.forward[0]

    def __len__(self) -> int:
        return self._size

    def min(self):
        """Return the minimum key-value pair, or None if empty."""
        x = self._header.forward[0]
        return (x.key, x.value) if x else None

    def max(self):
        """Return the maximum key-value pair, or None if empty."""
        x = self._header
        for i in range(self._level, -1, -1):
            while x.forward[i] is not None:
                x = x.forward[i]
        if x is self._header:
            return None
        return (x.key, x.value)

    def range(self, low, high):
        """Yield (key, value) pairs with low <= key <= high in order."""
        x = self._header
        for i in range(self._level, -1, -1):
            while x.forward[i] is not None and x.forward[i].key < low:
                x = x.forward[i]
        x = x.forward[0]
        while x is not None and x.key <= high:
            yield (x.key, x.value)
            x = x.forward[0]