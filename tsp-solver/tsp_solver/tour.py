"""Immutable tour representation with cached length."""

from __future__ import annotations

from typing import Iterable, List, Sequence


class Tour:
    """An immutable TSP tour.

    A tour is a permutation of city indices ``[0, n-1]``. The length is
    computed once at construction and cached for O(1) retrieval.

    Parameters
    ----------
    order : sequence of int
        The permutation of cities visited in order.
    length : float
        Precomputed tour length. If omitted, computed from *distances*.
    distances : callable (int, int) -> float, optional
        Distance function used when *length* is None.
    """

    __slots__ = ("_order", "_length")

    def __init__(
        self,
        order: Sequence[int],
        length: float | None = None,
        distances=None,
    ) -> None:
        self._order: tuple[int, ...] = tuple(int(c) for c in order)
        if length is None:
            if distances is None:
                raise ValueError("Must provide length or distances.")
            length = 0.0
            o = self._order
            for i in range(len(o)):
                length += distances(o[i], o[(i + 1) % len(o)])
        self._length = float(length)

    @property
    def order(self) -> tuple[int, ...]:
        return self._order

    @property
    def length(self) -> float:
        return self._length

    @property
    def n(self) -> int:
        return len(self._order)

    def edges(self) -> Iterable[tuple[int, int]]:
        """Yield (i, j) directed edges of the tour."""
        o = self._order
        for k in range(len(o)):
            yield (o[k], o[(k + 1) % len(o)])

    def reversed(self) -> "Tour":
        """Return the same tour traversed in reverse (same length)."""
        return Tour(self._order[::-1], self._length)

    def rotated(self, start: int) -> "Tour":
        """Return tour rotated so that city *start* is first."""
        idx = self._order.index(start)
        return Tour(self._order[idx:] + self._order[:idx], self._length)

    def __len__(self) -> int:
        return len(self._order)

    def __getitem__(self, i: int) -> int:
        return self._order[i]

    def __iter__(self):
        return iter(self._order)

    def __contains__(self, city: int) -> bool:
        return city in self._order

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tour):
            return NotImplemented
        return self._order == other._order

    def __hash__(self) -> int:
        return hash(self._order)

    def __repr__(self) -> str:
        return f"Tour(order={list(self._order)}, length={self._length:.4f})"

    def to_list(self) -> List[int]:
        return list(self._order)