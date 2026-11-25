"""Deterministic weighted-grid pathfinding using octile A*."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Iterable


@dataclass(frozen=True)
class Grid:
    """Rectangular grid; ``None`` is blocked and positive numbers are terrain cost."""
    rows: tuple[tuple[float | None, ...], ...]

    @classmethod
    def from_rows(cls, rows: Iterable[Iterable[float | None]]) -> "Grid":
        data = tuple(tuple(row) for row in rows)
        if not data or not data[0] or any(len(row) != len(data[0]) for row in data):
            raise ValueError("grid must be a non-empty rectangle")
        for row in data:
            for value in row:
                if value is not None and (not math.isfinite(value) or value <= 0):
                    raise ValueError("terrain costs must be finite and positive")
        return cls(data)

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        return len(self.rows[0])

    def traversable(self, point: tuple[int, int]) -> bool:
        x, y = point
        return 0 <= x < self.width and 0 <= y < self.height and self.rows[y][x] is not None


@dataclass(frozen=True)
class Route:
    points: tuple[tuple[int, int], ...]
    cost: float
    expanded: int


def _heuristic(a: tuple[int, int], b: tuple[int, int], minimum: float) -> float:
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return minimum * (max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy))


def find_path(grid: Grid, start: tuple[int, int], goal: tuple[int, int]) -> Route | None:
    """Find an optimal 8-connected route; diagonal corner cutting is disallowed."""
    for label, point in (("start", start), ("goal", goal)):
        if (not isinstance(point, tuple) or len(point) != 2
                or any(type(v) is not int for v in point) or not grid.traversable(point)):
            raise ValueError(f"{label} must be an integer coordinate on traversable terrain")
    if start == goal:
        return Route((start,), 0.0, 0)
    min_cost = min(v for row in grid.rows for v in row if v is not None)
    frontier = [(0.0, 0, start)]
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    costs = {start: 0.0}
    serial, expanded = 0, 0
    directions = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current == goal:
            path = []
            cursor = goal
            while cursor is not None:
                path.append(cursor)
                cursor = came_from[cursor]
            path.reverse()
            return Route(tuple(path), costs[goal], expanded)
        expanded += 1
        for dx, dy in directions:
            nxt = (current[0] + dx, current[1] + dy)
            if not grid.traversable(nxt):
                continue
            if dx and dy and (not grid.traversable((current[0] + dx, current[1]))
                              or not grid.traversable((current[0], current[1] + dy))):
                continue
            terrain = grid.rows[nxt[1]][nxt[0]]
            assert terrain is not None
            step = terrain * (math.sqrt(2) if dx and dy else 1.0)
            candidate = costs[current] + step
            if candidate + 1e-12 < costs.get(nxt, math.inf):
                costs[nxt] = candidate
                came_from[nxt] = current
                serial += 1
                heapq.heappush(frontier, (candidate + _heuristic(nxt, goal, min_cost), serial, nxt))
    return None
