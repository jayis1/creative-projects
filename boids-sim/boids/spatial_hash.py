"""Uniform-grid spatial hash for O(n) neighbor queries."""

from __future__ import annotations
from typing import Iterator


class SpatialHashGrid:
    """A uniform grid that partitions 2D space into cells for fast neighbor lookups.

    Insert boids, query nearby boids by position in O(1) amortized per cell.
    """

    __slots__ = ("cell_size", "cells", "_inverse")

    def __init__(self, cell_size: float):
        if cell_size <= 0:
            raise ValueError("cell_size must be positive")
        self.cell_size = float(cell_size)
        self.cells: dict[tuple[int, int], list] = {}
        self._inverse: dict[int, tuple[int, int]] = {}

    def _key(self, x: float, y: float) -> tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def insert(self, obj, x: float, y: float) -> None:
        """Insert *obj* at world position (x, y)."""
        key = self._key(x, y)
        bucket = self.cells.get(key)
        if bucket is None:
            bucket = []
            self.cells[key] = bucket
        bucket.append(obj)
        self._inverse[id(obj)] = key

    def query(self, x: float, y: float, radius: float) -> Iterator:
        """Yield objects within *radius* of (x, y), inclusive of neighbor cells."""
        cx, cy = self._key(x, y)
        cell_r = int(radius // self.cell_size) + 1
        for dx in range(-cell_r, cell_r + 1):
            for dy in range(-cell_r, cell_r + 1):
                bucket = self.cells.get((cx + dx, cy + dy))
                if bucket:
                    yield from bucket

    def query_cell_range(self, x: float, y: float, cell_range: int = 1) -> Iterator:
        """Yield objects in cells within *cell_range* cells of (x, y)."""
        cx, cy = self._key(x, y)
        for dx in range(-cell_range, cell_range + 1):
            for dy in range(-cell_range, cell_range + 1):
                bucket = self.cells.get((cx + dx, cy + dy))
                if bucket:
                    yield from bucket

    def clear(self) -> None:
        self.cells.clear()
        self._inverse.clear()

    def __len__(self) -> int:
        return sum(len(b) for b in self.cells.values())