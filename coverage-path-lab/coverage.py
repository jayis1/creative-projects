"""Grid coverage route planning with boustrophedon decomposition and A* connectors."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Iterable

Cell = tuple[int, int]

@dataclass(frozen=True)
class CoveragePlan:
    cells: tuple[Cell, ...]
    distance: float


def _grid(rows: Iterable[str]) -> tuple[tuple[str, ...], int, int]:
    grid = tuple(rows)
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError("grid must be a non-empty rectangle")
    if any(ch not in ".#" for row in grid for ch in row):
        raise ValueError("grid cells must be '.' (free) or '#' (blocked)")
    if sum(row.count(".") for row in grid) == 0:
        raise ValueError("grid has no traversable cells")
    return grid, len(grid), len(grid[0])


def _astar(grid: tuple[str, ...], start: Cell, goal: Cell) -> list[Cell]:
    h, w = len(grid), len(grid[0])
    frontier = [(abs(start[0]-goal[0])+abs(start[1]-goal[1]), 0, start)]
    came: dict[Cell, Cell | None] = {start: None}
    cost = {start: 0}
    while frontier:
        _, g, cur = heapq.heappop(frontier)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur); cur = came[cur]
            return path[::-1]
        if g != cost[cur]:
            continue
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nxt = cur[0]+dr, cur[1]+dc
            if 0 <= nxt[0] < h and 0 <= nxt[1] < w and grid[nxt[0]][nxt[1]] == ".":
                ng = g+1
                if ng < cost.get(nxt, math.inf):
                    cost[nxt] = ng; came[nxt] = cur
                    heapq.heappush(frontier, (ng+abs(nxt[0]-goal[0])+abs(nxt[1]-goal[1]), ng, nxt))
    raise ValueError(f"no path between {start} and {goal}")


def plan_coverage(rows: Iterable[str], start: Cell | None = None) -> CoveragePlan:
    """Visit every free cell; sweep rows alternately and connect sweep runs by A*."""
    grid, h, w = _grid(rows)
    free = {(r,c) for r in range(h) for c in range(w) if grid[r][c] == "."}
    if start is None:
        start = min(free)
    if start not in free:
        raise ValueError("start must be a traversable in-bounds cell")
    # A full coverage walk exists only when all free cells are connected.
    reached = set(_astar(grid, start, start))
    stack = [start]
    while stack:
        r,c = stack.pop()
        for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
            n=(r+dr,c+dc)
            if n in free and n not in reached:
                reached.add(n); stack.append(n)
    if reached != free:
        raise ValueError("all traversable cells must be connected")
    targets = [(r,c) for r in range(h) for c in (range(w) if r % 2 == 0 else range(w-1,-1,-1)) if (r,c) in free]
    tour = [start]
    for target in targets:
        segment = _astar(grid, tour[-1], target)
        tour.extend(segment[1:])
    distance = sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(tour,tour[1:]))
    return CoveragePlan(tuple(tour), float(distance))


def render(rows: Iterable[str], plan: CoveragePlan) -> str:
    """Render the grid, showing first visits by order modulo 10."""
    grid, h, w = _grid(rows)
    marks = {}
    for i, cell in enumerate(plan.cells):
        if cell not in marks:
            marks[cell] = str(i % 10)
    return "\n".join("".join("#" if grid[r][c] == "#" else marks.get((r,c), ".") for c in range(w)) for r in range(h))
