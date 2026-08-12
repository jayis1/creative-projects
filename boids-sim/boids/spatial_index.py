"""Abstract base class for spatial indexing strategies used in neighbor queries.

Provides a common interface so that different spatial index implementations
(SpatialHashGrid, QuadTree, etc.) can be swapped without changing simulation code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator, Protocol


class SpatialIndex(Protocol):
    """Protocol for spatial index implementations.

    Any spatial index used by the simulation must implement these methods.
    """

    def insert(self, obj: Any, x: float, y: float) -> None:
        """Insert *obj* at world position (x, y)."""
        ...

    def query(self, x: float, y: float, radius: float) -> Iterator[Any]:
        """Yield objects within *radius* of (x, y)."""
        ...

    def clear(self) -> None:
        """Remove all objects from the index."""
        ...

    def __len__(self) -> int:
        """Return the number of objects in the index."""
        ...