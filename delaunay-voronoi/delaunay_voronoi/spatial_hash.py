"""
Spatial hash grid for accelerated point and proximity queries.

A :class:`SpatialHashGrid` partitions 2-D space into uniform cells and
maps each cell to the list of points it contains.  This turns nearest-
neighbour and range queries from O(n) brute-force scans into O(k)
lookups where *k* is the number of points in the nearby cells.

The grid is used by:

  * :func:`nearest_neighbor_brute` → :func:`nearest_neighbor_grid`
    (the PPM renderer and spatial query module)
  * Range / radius searches
  * Fast deduplication of near-identical points
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple

from .geometry import Point


class SpatialHashGrid:
    """A uniform-grid spatial hash for 2-D points.

    Parameters
    ----------
    cell_size : width/height of each grid cell.  Choose ≈ the expected
        nearest-neighbour distance for best performance.
    """

    def __init__(self, cell_size: float) -> None:
        if cell_size <= 0:
            raise ValueError("cell_size must be positive")
        self.cell_size = float(cell_size)
        self._cells: Dict[Tuple[int, int], List[Point]] = {}
        self._all_points: List[Point] = []

    # ------------------------------------------------------------------ #
    #  Building
    # ------------------------------------------------------------------ #

    @classmethod
    def from_points(cls, points: List[Point], cell_size: Optional[float] = None
                    ) -> "SpatialHashGrid":
        """Build a grid from *points*.

        If *cell_size* is not given, it is estimated from the average
        nearest-neighbour distance (cheap heuristic: sqrt(domain_area / n)).
        """
        if cell_size is None:
            cell_size = cls._estimate_cell_size(points)
        grid = cls(cell_size)
        for p in points:
            grid.insert(p)
        return grid

    @staticmethod
    def _estimate_cell_size(points: List[Point]) -> float:
        if not points:
            return 1.0
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        w = max(xs) - min(xs) or 1.0
        h = max(ys) - min(ys) or 1.0
        # Average cell should contain ~1 point
        return max(math.sqrt(w * h / max(len(points), 1)), 1e-6)

    def insert(self, p: Point) -> None:
        key = self._key(p)
        self._cells.setdefault(key, []).append(p)
        self._all_points.append(p)

    # ------------------------------------------------------------------ #
    #  Queries
    # ------------------------------------------------------------------ #

    def _key(self, p: Point) -> Tuple[int, int]:
        return (int(math.floor(p.x / self.cell_size)),
                int(math.floor(p.y / self.cell_size)))

    def cell_points(self, cx: int, cy: int) -> List[Point]:
        return self._cells.get((cx, cy), [])

    def points_in_radius(self, center: Point, radius: float) -> List[Point]:
        """Return all points within *radius* of *center*."""
        result: List[Point] = []
        r_cells = int(math.ceil(radius / self.cell_size))
        cx, cy = self._key(center)
        r2 = radius * radius
        for dx in range(-r_cells, r_cells + 1):
            for dy in range(-r_cells, r_cells + 1):
                for p in self._cells.get((cx + dx, cy + dy), []):
                    if (p.x - center.x) ** 2 + (p.y - center.y) ** 2 <= r2:
                        result.append(p)
        return result

    def nearest(self, query: Point) -> Optional[Point]:
        """Find the nearest stored point to *query*.

        Expands the search ring outward until a candidate is found, then
        verifies it against one more ring to guard against boundary cases.
        """
        if not self._all_points:
            return None
        cx, cy = self._key(query)
        # Expand rings until we find at least one candidate
        best: Optional[Point] = None
        best_d2 = float("inf")
        ring = 0
        max_ring = max(1, int(math.ceil(
            max(abs(query.x), abs(query.y)) / self.cell_size)) + 2)
        while ring <= max_ring:
            candidates: List[Point] = []
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    if max(abs(dx), abs(dy)) == ring:  # ring boundary
                        candidates.extend(
                            self._cells.get((cx + dx, cy + dy), []))
            for p in candidates:
                d2 = (p.x - query.x) ** 2 + (p.y - query.y) ** 2
                if d2 < best_d2:
                    best_d2 = d2
                    best = p
            if best is not None:
                # One more ring to be safe
                next_ring = ring + 1
                more: List[Point] = []
                for dx in range(-next_ring, next_ring + 1):
                    for dy in range(-next_ring, next_ring + 1):
                        if max(abs(dx), abs(dy)) == next_ring:
                            more.extend(
                                self._cells.get((cx + dx, cy + dy), []))
                for p in more:
                    d2 = (p.x - query.x) ** 2 + (p.y - query.y) ** 2
                    if d2 < best_d2:
                        best_d2 = d2
                        best = p
                return best
            ring += 1
        return best

    def __len__(self) -> int:
        return len(self._all_points)

    @property
    def points(self) -> List[Point]:
        return list(self._all_points)

    @property
    def num_cells(self) -> int:
        return len(self._cells)


# --------------------------------------------------------------------------- #
#  Convenience functions
# --------------------------------------------------------------------------- #

def nearest_neighbor_grid(grid: SpatialHashGrid, query: Point) -> Optional[Point]:
    """Nearest-neighbour lookup using a pre-built :class:`SpatialHashGrid`."""
    return grid.nearest(query)


def deduplicate_points(points: List[Point], tolerance: float = 1e-9
                       ) -> List[Point]:
    """Remove near-duplicate points (within *tolerance*) using a spatial hash."""
    if not points:
        return []
    grid = SpatialHashGrid(max(tolerance, 1e-12))
    result: List[Point] = []
    for p in points:
        near = grid.points_in_radius(p, tolerance)
        if not near:
            grid.insert(p)
            result.append(p)
    return result