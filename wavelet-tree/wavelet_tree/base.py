"""Abstract base class for wavelet tree/matrix structures.

Defines the common interface that all wavelet structures implement,
enabling polymorphic use and consistent behavior across implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator


class WaveletBase(ABC):
    """Abstract base class for all wavelet tree/matrix structures.

    Every concrete structure must implement:
        - access(i):  return symbol at position i
        - rank(c, i): count of symbol c in S[0..i)
        - select(c, k): position of k-th occurrence of c
        - alphabet:   sorted list of unique symbols
        - __len__():  total sequence length

    The base class provides default implementations for:
        - __iter__(): iterate over all symbols via access
        - __getitem__(): indexing via access
        - __contains__(): check if a symbol is in the alphabet
        - count(): total count of a symbol (rank(c, n))
        - index(): position of first occurrence of a symbol (select(c, 0))
    """

    @abstractmethod
    def access(self, i: int) -> Any:
        """Return the symbol at position i. O(log |Σ|) or O(H₀)."""
        raise NotImplementedError

    @abstractmethod
    def rank(self, c: Any, i: int) -> int:
        """Count occurrences of symbol c in S[0..i)."""
        raise NotImplementedError

    @abstractmethod
    def select(self, c: Any, k: int) -> int:
        """Return the position of the k-th (0-indexed) occurrence of c.
        Returns -1 if not found."""
        raise NotImplementedError

    @abstractmethod
    def __len__(self) -> int:
        """Return the total length of the sequence."""
        raise NotImplementedError

    @property
    @abstractmethod
    def alphabet(self) -> list:
        """Return the sorted alphabet."""
        raise NotImplementedError

    # --- Default implementations ---

    def __getitem__(self, i: int) -> Any:
        """Support indexing: wt[i] is equivalent to wt.access(i).

        Supports negative indices (Python slice semantics).
        """
        n = len(self)
        if i < 0:
            i += n
        if i < 0 or i >= n:
            raise IndexError(f"Index {i} out of range [0, {n})")
        return self.access(i)

    def __iter__(self) -> Iterator[Any]:
        """Iterate over all symbols in the sequence."""
        for i in range(len(self)):
            yield self.access(i)

    def __contains__(self, c: Any) -> bool:
        """Check if symbol c is in the alphabet."""
        return c in self.alphabet

    def __reversed__(self) -> Iterator[Any]:
        """Iterate over symbols in reverse order."""
        for i in range(len(self) - 1, -1, -1):
            yield self.access(i)

    def count(self, c: Any) -> int:
        """Total count of symbol c in the sequence."""
        return self.rank(c, len(self))

    def index(self, c: Any, start: int = 0) -> int:
        """Position of the first occurrence of c at or after `start`.
        Returns -1 if not found.
        """
        if start < 0:
            start = max(0, start + len(self))
        base = self.rank(c, start)
        return self.select(c, base)

    def positions(self, c: Any) -> list[int]:
        """Return all positions where symbol c occurs, in order."""
        total = self.count(c)
        return [self.select(c, k) for k in range(total)]

    def to_list(self) -> list:
        """Reconstruct the full sequence as a list."""
        return [self.access(i) for i in range(len(self))]

    def __eq__(self, other: object) -> bool:
        """Two wavelet structures are equal if they represent the same sequence."""
        if not isinstance(other, WaveletBase):
            return NotImplemented
        if len(self) != len(other):
            return False
        return self.to_list() == other.to_list()

    def __hash__(self) -> int:
        """Hash based on the sequence content."""
        return hash(tuple(self.to_list()))