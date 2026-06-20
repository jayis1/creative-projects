"""Relation storage with hash-based indexing for fast joins.

A ``Relation_`` holds a set of tuples and lazily builds hash indexes on
whatever column positions the join evaluator requests.  This gives O(1)
lookup on indexed columns while keeping memory overhead proportional to
the number of distinct index configurations actually used.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from .engine_types import Relation


def _index_key(
    arity: int, tuple_: Tuple, positions: Tuple[int, ...]
) -> Tuple:
    """Extract the key tuple for the given positions from a row."""
    return tuple(tuple_[p] for p in positions)


class Relation_:
    """A stored relation with optional hash indexes for fast joins.

    Attributes
    ----------
    arity : int
        Number of columns (arguments) in each tuple.
    tuples : set[tuple]
        The set of tuples stored in this relation.
    """

    __slots__ = ("arity", "tuples", "_indexes")

    def __init__(self, arity: int) -> None:
        self.arity = arity
        self.tuples: Relation = set()
        self._indexes: Dict[
            Tuple[int, ...], Dict[Tuple, List[Tuple]]
        ] = {}

    def add(self, tup: Tuple) -> bool:
        """Add a tuple. Returns True if new, False if already present.

        Raises
        ------
        DatalogError
            If the tuple arity doesn't match the relation arity.
        """
        if len(tup) != self.arity:
            from .errors import DatalogError
            raise DatalogError(
                f"arity mismatch: expected {self.arity}, got {len(tup)}"
            )
        if tup in self.tuples:
            return False
        self.tuples.add(tup)
        for positions, idx in self._indexes.items():
            idx.setdefault(
                _index_key(self.arity, tup, positions), []
            ).append(tup)
        return True

    def discard(self, tup: Tuple) -> bool:
        """Remove a tuple. Returns True if it existed, False otherwise.

        All indexes are invalidated after removal (they will be rebuilt
        on next lookup) because removing from a list-backed index is
        more expensive than rebuilding for the typically small relations
        we deal with.
        """
        if tup not in self.tuples:
            return False
        self.tuples.discard(tup)
        self._indexes.clear()
        return True

    def ensure_index(self, positions: Tuple[int, ...]) -> None:
        """Build a hash index on the given column positions if not present."""
        if positions in self._indexes:
            return
        idx: Dict[Tuple, List[Tuple]] = defaultdict(list)
        for tup in self.tuples:
            idx[_index_key(self.arity, tup, positions)].append(tup)
        self._indexes[positions] = idx

    def lookup(
        self, positions: Tuple[int, ...], key: Tuple
    ) -> List[Tuple]:
        """Return all tuples matching the key on the given positions.

        Builds the index on first use for a given position set.
        """
        self.ensure_index(positions)
        return self._indexes[positions].get(key, [])

    def clear(self) -> None:
        """Remove all tuples and invalidate indexes."""
        self.tuples.clear()
        self._indexes.clear()

    def __len__(self) -> int:
        return len(self.tuples)

    def __contains__(self, tup: Tuple) -> bool:
        return tup in self.tuples

    def __iter__(self):
        return iter(self.tuples)