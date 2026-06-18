"""Tile definitions with adjacency constraints.

A :class:`Tile` is the atomic unit of a WFC generation. Each tile carries a
name, an optional display *data* (e.g. a symbol or small sub-grid), a
non-negative weight used for weighted-random collapse, and per-side
adjacency constraints describing which other tiles may sit next to it.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Set, Union

logger = logging.getLogger(__name__)

# Clockwise order of the four cardinal sides.
SIDES = ("top", "right", "bottom", "left")

# Map a side to its geometric opposite.
OPPOSITE_SIDE: Dict[str, str] = {
    "top": "bottom",
    "bottom": "top",
    "left": "right",
    "right": "left",
}

NeighborSpec = Union[str, Iterable[str]]


class Tile:
    """A single tile with per-side adjacency constraints.

    Parameters
    ----------
    name:
        Unique identifier for this tile within a :class:`~wfc_generator.tileset.TileSet`.
    data:
        Optional display/rendering payload.  For tiled generation this is
        typically a single character symbol; for the overlap model it is a
        tuple of symbols forming an ``n x n`` sub-pattern.
    weight:
        Non-negative relative probability weight used during weighted-random
        collapse.  Defaults to ``1.0``.
    color:
        Optional CSS color string (``#rrggbb``) used by renderers.

    Sides are: ``top``, ``right``, ``bottom``, ``left`` (clockwise from top).
    """

    SIDES = list(SIDES)

    def __init__(self, name: str, data: Any = None, weight: float = 1.0, color: str = ""):
        if not isinstance(name, str) or not name:
            raise ValueError("Tile name must be a non-empty string")
        self.name = name
        self.data = data
        self.weight = weight
        self.color = color
        # side -> set of tile names allowed on that side
        self.constraints: Dict[str, Set[str]] = {side: set() for side in SIDES}

    # ------------------------------------------------------------------ #
    # Constraint management
    # ------------------------------------------------------------------ #
    def add_constraint(self, side: str, neighbor_name: NeighborSpec) -> None:
        """Allow ``neighbor_name``(s) on the given side.

        ``neighbor_name`` may be a single string or any iterable of strings.
        Raises :class:`ValueError` for an invalid side.
        """
        if side not in self.constraints:
            raise ValueError(f"Invalid side {side!r}. Must be one of {self.SIDES}")
        if isinstance(neighbor_name, (list, tuple, set, frozenset)):
            self.constraints[side].update(neighbor_name)
        else:
            self.constraints[side].add(neighbor_name)

    def remove_constraint(self, side: str, neighbor_name: NeighborSpec) -> None:
        """Remove ``neighbor_name``(s) from the allowed set on ``side``."""
        if side not in self.constraints:
            raise ValueError(f"Invalid side {side!r}. Must be one of {self.SIDES}")
        if isinstance(neighbor_name, (list, tuple, set, frozenset)):
            self.constraints[side] -= set(neighbor_name)
        else:
            self.constraints[side].discard(neighbor_name)

    def get_constraint(self, side: str) -> Set[str]:
        """Return the set of tile names allowed on ``side``."""
        return self.constraints.get(side, set())

    def has_constraint(self, side: str) -> bool:
        """Return True if any explicit constraint exists on ``side``."""
        return len(self.constraints.get(side, set())) > 0

    # ------------------------------------------------------------------ #
    # Dunder methods
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return (
            f"Tile({self.name!r}, weight={self.weight}, "
            f"constraints={dict(self.constraints)})"
        )

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tile):
            return self.name == other.name
        return NotImplemented