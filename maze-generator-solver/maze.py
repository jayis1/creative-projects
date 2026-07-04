"""
maze-generator-solver: A comprehensive maze generation and solving toolkit.

Supports multiple generation algorithms (recursive backtracking, Prim's,
Kruskal's, Eller's, Wilson's, binary tree, sidewinder), multiple solving
algorithms (BFS, DFS, A*, Dijkstra, bidirectional BFS, greedy best-first),
braid maze support, JSON serialization, PNG export, ASCII rendering with
solution path highlighting, distance heatmaps, multi-solver benchmarking,
maze validation, and statistical analysis.

Author: creative-projects
License: MIT
"""

from __future__ import annotations

import heapq
import json
import math
import random
import struct
import zlib
from collections import deque
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
)

# ---------------------------------------------------------------------------
# Direction
# ---------------------------------------------------------------------------


class Direction(Enum):
    """Compass directions used for wall removal."""

    NORTH = (0, -1)
    EAST = (1, 0)
    SOUTH = (0, 1)
    WEST = (-1, 0)

    @property
    def opposite(self) -> "Direction":
        """Return the direction pointing the other way."""
        return {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }[self]

    @property
    def dx(self) -> int:
        """X-component of the direction vector."""
        return self.value[0]

    @property
    def dy(self) -> int:
        """Y-component of the direction vector."""
        return self.value[1]


# Convenience ordering so we can iterate deterministically.
_ALL_DIRECTIONS: Tuple[Direction, ...] = (
    Direction.NORTH,
    Direction.EAST,
    Direction.SOUTH,
    Direction.WEST,
)

# Heuristic functions for A* and greedy best-first search.
HeuristicFn = Callable[["Cell", "Cell"], float]


def manhattan_distance(a: "Cell", b: "Cell") -> float:
    """Manhattan (L1) distance — admissible for 4-connected grids."""
    return abs(a.x - b.x) + abs(a.y - b.y)


def euclidean_distance(a: "Cell", b: "Cell") -> float:
    """Euclidean (L2) distance — admissible but less tight for grids."""
    return math.hypot(a.x - b.x, a.y - b.y)


def chebyshev_distance(a: "Cell", b: "Cell") -> float:
    """Chebyshev (L∞) distance — admissible for 8-connected grids."""
    return max(abs(a.x - b.x), abs(a.y - b.y))


HEURISTICS: Dict[str, HeuristicFn] = {
    "manhattan": manhattan_distance,
    "euclidean": euclidean_distance,
    "chebyshev": chebyshev_distance,
}


# ---------------------------------------------------------------------------
# Cell
# ---------------------------------------------------------------------------


class Cell:
    """
    A single maze cell.

    Walls are stored as a set of ``Direction`` enums that are *present*
    (i.e. not yet removed).  A cell starts fully walled and walls are
    removed during generation.

    The ``visited`` flag is used by generation and solving algorithms as
    scratch state; it is reset by :meth:`Maze.reset_visited`.
    """

    __slots__ = ("x", "y", "walls", "visited")

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        self.walls: Set[Direction] = set(Direction)
        self.visited: bool = False

    def __repr__(self) -> str:
        return f"Cell({self.x}, {self.y})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cell):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    @property
    def open_count(self) -> int:
        """Number of open passages (walls removed) for this cell."""
        return 4 - len(self.walls)


# ---------------------------------------------------------------------------
# Maze
# ---------------------------------------------------------------------------


class Maze:
    """
    A rectangular grid maze.

    The maze uses a grid of cells where each cell has walls on all four
    sides initially.  Generation algorithms remove walls to carve
    passages, producing a **perfect maze** (exactly one path between any
    two cells).  The maze can optionally be *braided* (dead ends removed)
    via :meth:`braid`.

    Parameters
    ----------
    width : int
        Number of cells horizontally (columns).  Must be ≥ 1.
    height : int
        Number of cells vertically (rows).  Must be ≥ 1.
    seed : int, optional
        Random seed for reproducible generation.
    """

    # Registry of available generation algorithms (name → method).
    GENERATORS: Dict[str, str] = {
        "recursive_backtracking": "_gen_recursive_backtracking",
        "prims": "_gen_prims",
        "kruskals": "_gen_kruskals",
        "ellers": "_gen_ellers",
        "wilsons": "_gen_wilsons",
        "binary_tree": "_gen_binary_tree",
        "sidewinder": "_gen_sidewinder",
    }

    # Registry of available solving algorithms.
    SOLVERS: Dict[str, str] = {
        "bfs": "_solve_bfs",
        "dfs": "_solve_dfs",
        "astar": "_solve_astar",
        "dijkstra": "_solve_dijkstra",
        "bidirectional": "_solve_bidirectional",
        "greedy": "_solve_greedy",
    }

    def __init__(self, width: int, height: int, seed: Optional[int] = None) -> None:
        if not isinstance(width, int) or not isinstance(height, int):
            raise TypeError("Maze dimensions must be integers")
        if width < 1 or height < 1:
            raise ValueError("Maze dimensions must be positive integers")
        self.width = width
        self.height = height
        self.cells: List[List[Cell]] = [
            [Cell(x, y) for x in range(width)] for y in range(height)
        ]
        self.rng = random.Random(seed)
        self.seed = seed
        self._start: Optional[Tuple[int, int]] = None
        self._end: Optional[Tuple[int, int]] = None

    # ------------------------------------------------------------------
    # Start / end accessors
    # ------------------------------------------------------------------

    @property
    def start(self) -> Tuple[int, int]:
        """Return the start coordinate (default: top-left)."""
        return self._start if self._start is not None else (0, 0)

    @property
    def end(self) -> Tuple[int, int]:
        """Return the end coordinate (default: bottom-right)."""
        return (
            self._end
            if self._end is not None
            else (self.width - 1, self.height - 1)
        )

    def set_start(self, x: int, y: int) -> None:
        """Set the start cell.  Validates that coordinates are in range."""
        self._validate_coords(x, y)
        self._start = (x, y)

    def set_end(self, x: int, y: int) -> None:
        """Set the end cell.  Validates that coordinates are in range."""
        self._validate_coords(x, y)
        self._end = (x, y)

    # ------------------------------------------------------------------
    # Coordinate / cell helpers
    # ------------------------------------------------------------------

    def _validate_coords(self, x: int, y: int) -> None:
        """Raise ``ValueError`` if (x, y) is outside the maze bounds."""
        if not (0 <= x < self.width):
            raise ValueError(f"x={x} out of range [0, {self.width})")
        if not (0 <= y < self.height):
            raise ValueError(f"y={y} out of range [0, {self.height})")

    def get_cell(self, x: int, y: int) -> Cell:
        """Return the cell at (x, y).  Raises if out of bounds."""
        self._validate_coords(x, y)
        return self.cells[y][x]

    def neighbors(self, cell: Cell) -> List[Tuple[Cell, Direction]]:
        """
        Return list of ``(neighbor_cell, direction)`` pairs for all
        in-bounds neighbors regardless of walls.
        """
        result: List[Tuple[Cell, Direction]] = []
        for d in _ALL_DIRECTIONS:
            nx, ny = cell.x + d.dx, cell.y + d.dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                result.append((self.cells[ny][nx], d))
        return result

    def accessible_neighbors(self, cell: Cell) -> List[Cell]:
        """Neighbors reachable through removed walls (open passages)."""
        result: List[Cell] = []
        for d in _ALL_DIRECTIONS:
            if d in cell.walls:
                continue
            nx, ny = cell.x + d.dx, cell.y + d.dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                result.append(self.cells[ny][nx])
        return result

    def all_neighbors(self, cell: Cell) -> List[Cell]:
        """All in-bounds neighbors, walls or not."""
        result: List[Cell] = []
        for d in _ALL_DIRECTIONS:
            nx, ny = cell.x + d.dx, cell.y + d.dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                result.append(self.cells[ny][nx])
        return result

    def remove_wall(self, a: Cell, b: Cell) -> None:
        """Remove the wall between two adjacent cells ``a`` and ``b``."""
        if abs(a.x - b.x) + abs(a.y - b.y) != 1:
            raise ValueError("Cells must be adjacent (Manhattan distance 1)")
        if a.x == b.x:
            if a.y < b.y:
                a.walls.discard(Direction.SOUTH)
                b.walls.discard(Direction.NORTH)
            else:
                a.walls.discard(Direction.NORTH)
                b.walls.discard(Direction.SOUTH)
        else:
            if a.x < b.x:
                a.walls.discard(Direction.EAST)
                b.walls.discard(Direction.WEST)
            else:
                a.walls.discard(Direction.WEST)
                b.walls.discard(Direction.EAST)

    def add_wall(self, a: Cell, b: Cell) -> None:
        """Add a wall between two adjacent cells (used by braid undo)."""
        if abs(a.x - b.x) + abs(a.y - b.y) != 1:
            raise ValueError("Cells must be adjacent")
        if a.x == b.x:
            if a.y < b.y:
                a.walls.add(Direction.SOUTH)
                b.walls.add(Direction.NORTH)
            else:
                a.walls.add(Direction.NORTH)
                b.walls.add(Direction.SOUTH)
        else:
            if a.x < b.x:
                a.walls.add(Direction.EAST)
                b.walls.add(Direction.WEST)
            else:
                a.walls.add(Direction.WEST)
                b.walls.add(Direction.EAST)

    def all_cells(self) -> Iterator[Cell]:
        """Yield all cells in the maze (row-major order)."""
        for row in self.cells:
            yield from row

    def reset_visited(self) -> None:
        """Clear the ``visited`` flag on every cell."""
        for cell in self.all_cells():
            cell.visited = False

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, algorithm: str = "recursive_backtracking") -> None:
        """
        Generate the maze using the named algorithm.

        This resets all walls to fully-walled and clears visited flags
        before running the generator.

        Parameters
        ----------
        algorithm : str
            One of: ``recursive_backtracking``, ``prims``, ``kruskals``,
            ``ellers``, ``wilsons``, ``binary_tree``, ``sidewinder``.
        """
        algo = algorithm.lower().strip()
        if algo not in self.GENERATORS:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Available: {list(self.GENERATORS.keys())}"
            )
        # Reset maze state to fully walled.
        for row in self.cells:
            for cell in row:
                cell.walls = set(Direction)
                cell.visited = False
        getattr(self, self.GENERATORS[algo])()

    def _gen_recursive_backtracking(self) -> None:
        """Depth-first recursive backtracker using an explicit stack."""
        start = self.cells[0][0]
        start.visited = True
        stack: List[Cell] = [start]
        while stack:
            current = stack[-1]
            unvisited = [
                (n, d) for n, d in self.neighbors(current) if not n.visited
            ]
            if unvisited:
                neighbor, _direction = self.rng.choice(unvisited)
                self.remove_wall(current, neighbor)
                neighbor.visited = True
                stack.append(neighbor)
            else:
                stack.pop()

    def _gen_prims(self) -> None:
        """
        Modified Prim's algorithm: grow a frontier set from a random cell,
        always connecting a random frontier cell to the existing tree.
        """
        start = self.cells[0][0]
        start.visited = True
        frontier: List[Tuple[Cell, Cell]] = []
        for n, _ in self.neighbors(start):
            frontier.append((start, n))
        while frontier:
            idx = self.rng.randrange(len(frontier))
            parent, child = frontier.pop(idx)
            if not child.visited:
                child.visited = True
                self.remove_wall(parent, child)
                for n, _ in self.neighbors(child):
                    if not n.visited:
                        frontier.append((child, n))

    def _gen_kruskals(self) -> None:
        """
        Kruskal's algorithm using a union-find (disjoint set) to connect
        cells with randomly ordered edges, avoiding cycles.  Produces a
        perfect maze (uniform spanning tree when edges are randomly ordered).
        """
        parent_map: Dict[Cell, Cell] = {}

        def find(c: Cell) -> Cell:
            while parent_map[c] != c:
                parent_map[c] = parent_map[parent_map[c]]  # path compression
                c = parent_map[c]
            return c

        def union(a: Cell, b: Cell) -> bool:
            ra, rb = find(a), find(b)
            if ra == rb:
                return False
            parent_map[ra] = rb
            return True

        for cell in self.all_cells():
            parent_map[cell] = cell

        edges: List[Tuple[Cell, Cell]] = []
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                if x < self.width - 1:
                    edges.append((cell, self.cells[y][x + 1]))
                if y < self.height - 1:
                    edges.append((cell, self.cells[y + 1][x]))
        self.rng.shuffle(edges)
        for a, b in edges:
            if union(a, b):
                self.remove_wall(a, b)

    def _gen_ellers(self) -> None:
        """
        Eller's algorithm: builds the maze row-by-row using union-find,
        so it only needs to keep one row in memory at a time (memory O(width)).
        """
        parent = list(range(self.width * self.height))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj

        for y in range(self.height):
            # Randomly merge adjacent cells within the row.
            for x in range(self.width - 1):
                if y == self.height - 1 or self.rng.random() < 0.5:
                    ci = y * self.width + x
                    ni = y * self.width + (x + 1)
                    if find(ci) != find(ni):
                        union(ci, ni)
                        self.remove_wall(self.cells[y][x], self.cells[y][x + 1])
            # For each set in the row, create at least one vertical passage.
            if y < self.height - 1:
                sets: Dict[int, List[int]] = {}
                for x in range(self.width):
                    root = find(y * self.width + x)
                    sets.setdefault(root, []).append(x)
                for members in sets.values():
                    self.rng.shuffle(members)
                    n_connect = self.rng.randint(1, len(members))
                    for x in members[:n_connect]:
                        ci = y * self.width + x
                        ni = (y + 1) * self.width + x
                        union(ci, ni)
                        self.remove_wall(self.cells[y][x], self.cells[y + 1][x])

    def _gen_wilsons(self) -> None:
        """
        Wilson's algorithm: produces a uniform spanning tree by doing
        loop-erased random walks from unvisited cells to the growing tree.

        This is the slowest algorithm but produces a mathematically
        uniform random spanning tree.
        """
        start = self.cells[0][0]
        start.visited = True
        remaining = self.width * self.height - 1
        while remaining > 0:
            # Pick a random unvisited cell.
            while True:
                x = self.rng.randrange(self.width)
                y = self.rng.randrange(self.height)
                if not self.cells[y][x].visited:
                    break
            # Loop-erased random walk until we hit the visited set.
            path: List[Cell] = [self.cells[y][x]]
            direction_from: Dict[Cell, Direction] = {}
            current = self.cells[y][x]
            while not current.visited:
                neighbors = self.neighbors(current)
                neighbor, direction = self.rng.choice(neighbors)
                direction_from[current] = direction
                if neighbor in direction_from or neighbor.visited:
                    if not neighbor.visited:
                        # Erase the loop back to where we first visited it.
                        loop_start_idx = path.index(neighbor)
                        for c in path[loop_start_idx + 1:]:
                            del direction_from[c]
                        path = path[:loop_start_idx + 1]
                    else:
                        path.append(neighbor)
                else:
                    path.append(neighbor)
                current = neighbor
            # Carve the path into the maze.
            for i in range(len(path) - 1):
                cell_a = path[i]
                cell_b = path[i + 1]
                if not cell_a.visited:
                    cell_a.visited = True
                    remaining -= 1
                self.remove_wall(cell_a, cell_b)
            if not path[-1].visited:
                path[-1].visited = True
                remaining -= 1

    def _gen_binary_tree(self) -> None:
        """
        Binary tree algorithm: for each cell, randomly carve north or east.
        Produces a biased but valid maze with a clear diagonal bias and
        a straight corridor along the top and right edges.
        """
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                choices: List[Direction] = []
                if y > 0:
                    choices.append(Direction.NORTH)
                if x < self.width - 1:
                    choices.append(Direction.EAST)
                if not choices:
                    continue
                d = self.rng.choice(choices)
                nx, ny = cell.x + d.dx, cell.y + d.dy
                self.remove_wall(cell, self.cells[ny][nx])

    def _gen_sidewinder(self) -> None:
        """
        Sidewinder algorithm: for each row, group cells into runs and
        randomly carve upward from a random cell in the run, then continue
        eastward.  Top row is always a straight corridor.
        """
        for y in range(self.height):
            run: List[Cell] = []
            for x in range(self.width):
                cell = self.cells[y][x]
                run.append(cell)
                at_east_boundary = x == self.width - 1
                at_north_boundary = y == 0
                if at_east_boundary or (
                    not at_north_boundary and self.rng.random() < 0.5
                ):
                    # Close the run: carve north from a random cell.
                    if not at_north_boundary:
                        chosen = self.rng.choice(run)
                        nx, ny = chosen.x, chosen.y - 1
                        self.remove_wall(chosen, self.cells[ny][nx])
                    run = []
                else:
                    # Extend the run eastward.
                    if not at_east_boundary:
                        self.remove_wall(cell, self.cells[y][x + 1])

    # ------------------------------------------------------------------
    # Braid — remove dead ends by adding extra passages
    # ------------------------------------------------------------------

    def braid(self, probability: float = 1.0) -> int:
        """
        Remove dead ends by opening a wall to a random neighbor.

        A *braid* maze has no dead ends — every cell has at least two
        openings, creating loops and multiple paths.  This makes mazes
        easier to solve but more interesting to navigate.

        Parameters
        ----------
        probability : float
            Probability (0–1) that any given dead end is braided.
            ``1.0`` (default) braids every dead end; ``0.5`` braids
            roughly half of them.

        Returns
        -------
        int
            Number of dead ends that were braided.
        """
        if not (0.0 <= probability <= 1.0):
            raise ValueError("probability must be in [0, 1]")
        braided = 0
        # Snapshot cells first so we don't re-process cells that become
        # non-dead-ends as a side effect of braiding earlier ones.
        for cell in list(self.all_cells()):
            if cell.open_count != 1:
                continue
            if self.rng.random() > probability:
                continue
            # Find a walled neighbor to connect to (prefer not re-opening
            # the existing passage direction).
            candidates: List[Tuple[Cell, Direction]] = []
            for d in _ALL_DIRECTIONS:
                if d not in cell.walls:
                    continue  # already open
                nx, ny = cell.x + d.dx, cell.y + d.dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    candidates.append((self.cells[ny][nx], d))
            if candidates:
                neighbor, _ = self.rng.choice(candidates)
                self.remove_wall(cell, neighbor)
                braided += 1
        return braided

    # ------------------------------------------------------------------
    # Solving
    # ------------------------------------------------------------------

    def solve(
        self,
        algorithm: str = "bfs",
        start: Optional[Tuple[int, int]] = None,
        end: Optional[Tuple[int, int]] = None,
        heuristic: str = "manhattan",
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Solve the maze from start to end using the named algorithm.

        Parameters
        ----------
        algorithm : str
            One of: ``bfs``, ``dfs``, ``astar``, ``dijkstra``,
            ``bidirectional``, ``greedy``.
        start : (x, y), optional
            Override the maze's default start cell.
        end : (x, y), optional
            Override the maze's default end cell.
        heuristic : str
            Heuristic for A* / greedy: ``manhattan``, ``euclidean``,
            or ``chebyshev``.  Ignored by BFS/DFS/Dijkstra/bidirectional.

        Returns
        -------
        list of (x, y) or None
            Path from start to end, or ``None`` if no solution exists.
        """
        algo = algorithm.lower().strip()
        if algo not in self.SOLVERS:
            raise ValueError(
                f"Unknown solver '{algorithm}'. "
                f"Available: {list(self.SOLVERS.keys())}"
            )
        if heuristic not in HEURISTICS:
            raise ValueError(
                f"Unknown heuristic '{heuristic}'. "
                f"Available: {list(HEURISTICS.keys())}"
            )
        # Temporarily override start/end if provided.
        saved_start, saved_end = self._start, self._end
        try:
            if start is not None:
                self._validate_coords(*start)
                self._start = start
            if end is not None:
                self._validate_coords(*end)
                self._end = end
            self.reset_visited()
            self._heuristic_fn = HEURISTICS[heuristic]
            return getattr(self, self.SOLVERS[algo])()
        finally:
            self._start = saved_start
            self._end = saved_end

    def _reconstruct_path(
        self, came_from: Mapping[Cell, Optional[Cell]], end: Cell
    ) -> List[Tuple[int, int]]:
        """Rebuild the coordinate path from a came-from map."""
        path: List[Tuple[int, int]] = []
        current: Optional[Cell] = end
        while current is not None:
            path.append((current.x, current.y))
            current = came_from.get(current)
        path.reverse()
        return path

    def _solve_bfs(self) -> Optional[List[Tuple[int, int]]]:
        """Breadth-first search — guarantees shortest path."""
        sx, sy = self.start
        ex, ey = self.end
        start_cell = self.cells[sy][sx]
        end_cell = self.cells[ey][ex]
        queue: deque[Cell] = deque([start_cell])
        start_cell.visited = True
        came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
        while queue:
            current = queue.popleft()
            if current == end_cell:
                return self._reconstruct_path(came_from, end_cell)
            for neighbor in self.accessible_neighbors(current):
                if not neighbor.visited:
                    neighbor.visited = True
                    came_from[neighbor] = current
                    queue.append(neighbor)
        return None

    def _solve_dfs(self) -> Optional[List[Tuple[int, int]]]:
        """Depth-first search — finds *a* path (not necessarily shortest)."""
        sx, sy = self.start
        ex, ey = self.end
        start_cell = self.cells[sy][sx]
        end_cell = self.cells[ey][ex]
        stack: List[Cell] = [start_cell]
        came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
        start_cell.visited = True
        while stack:
            current = stack.pop()
            if current == end_cell:
                return self._reconstruct_path(came_from, end_cell)
            for neighbor in self.accessible_neighbors(current):
                if not neighbor.visited:
                    neighbor.visited = True
                    came_from[neighbor] = current
                    stack.append(neighbor)
        return None

    def _solve_astar(self) -> Optional[List[Tuple[int, int]]]:
        """A* search with configurable heuristic — guarantees shortest path."""
        sx, sy = self.start
        ex, ey = self.end
        start_cell = self.cells[sy][sx]
        end_cell = self.cells[ey][ex]
        heuristic = self._heuristic_fn

        open_heap: List[Tuple[float, int, Cell]] = []
        counter = 0
        heapq.heappush(open_heap, (heuristic(start_cell, end_cell), counter, start_cell))
        g_score: Dict[Cell, float] = {start_cell: 0}
        came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
        closed: Set[Cell] = set()
        # Mark start as visited for benchmark explored-count tracking.
        start_cell.visited = True
        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
            current.visited = True  # track explored for benchmark
            if current == end_cell:
                return self._reconstruct_path(came_from, end_cell)
            for neighbor in self.accessible_neighbors(current):
                tentative_g = g_score[current] + 1
                if tentative_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g
                    came_from[neighbor] = current
                    f = tentative_g + heuristic(neighbor, end_cell)
                    counter += 1
                    heapq.heappush(open_heap, (f, counter, neighbor))
        return None

    def _solve_greedy(self) -> Optional[List[Tuple[int, int]]]:
        """
        Greedy best-first search — expands the node that appears closest
        to the goal according to the heuristic.  Fast but does *not*
        guarantee the shortest path.
        """
        sx, sy = self.start
        ex, ey = self.end
        start_cell = self.cells[sy][sx]
        end_cell = self.cells[ey][ex]
        heuristic = self._heuristic_fn

        open_heap: List[Tuple[float, int, Cell]] = []
        counter = 0
        heapq.heappush(open_heap, (heuristic(start_cell, end_cell), counter, start_cell))
        came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
        visited: Set[Cell] = {start_cell}
        start_cell.visited = True  # track explored for benchmark
        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current == end_cell:
                return self._reconstruct_path(came_from, end_cell)
            for neighbor in self.accessible_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    neighbor.visited = True  # track explored
                    came_from[neighbor] = current
                    counter += 1
                    heapq.heappush(
                        open_heap, (heuristic(neighbor, end_cell), counter, neighbor)
                    )
        return None

    def _solve_dijkstra(self) -> Optional[List[Tuple[int, int]]]:
        """Dijkstra's algorithm — equivalent to BFS for uniform-cost grids."""
        sx, sy = self.start
        ex, ey = self.end
        start_cell = self.cells[sy][sx]
        end_cell = self.cells[ey][ex]
        open_heap: List[Tuple[float, int, Cell]] = []
        counter = 0
        heapq.heappush(open_heap, (0, counter, start_cell))
        dist: Dict[Cell, float] = {start_cell: 0}
        came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
        closed: Set[Cell] = set()
        start_cell.visited = True  # track explored for benchmark
        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
            current.visited = True  # track explored
            if current == end_cell:
                return self._reconstruct_path(came_from, end_cell)
            for neighbor in self.accessible_neighbors(current):
                nd = dist[current] + 1
                if nd < dist.get(neighbor, float("inf")):
                    dist[neighbor] = nd
                    came_from[neighbor] = current
                    counter += 1
                    heapq.heappush(open_heap, (nd, counter, neighbor))
        return None

    def _solve_bidirectional(self) -> Optional[List[Tuple[int, int]]]:
        """
        Bidirectional BFS — two BFS frontiers meeting in the middle.
        Guarantees shortest path and can be faster on large mazes.
        """
        sx, sy = self.start
        ex, ey = self.end
        start_cell = self.cells[sy][sx]
        end_cell = self.cells[ey][ex]
        if start_cell == end_cell:
            start_cell.visited = True
            return [(sx, sy)]
        forward_queue: deque[Cell] = deque([start_cell])
        backward_queue: deque[Cell] = deque([end_cell])
        forward_came: Dict[Cell, Optional[Cell]] = {start_cell: None}
        backward_came: Dict[Cell, Optional[Cell]] = {end_cell: None}
        forward_visited: Set[Cell] = {start_cell}
        backward_visited: Set[Cell] = {end_cell}
        # Track visited for benchmark explored-count.
        start_cell.visited = True
        end_cell.visited = True
        meeting_point: Optional[Cell] = None

        while forward_queue and backward_queue:
            # Expand forward frontier by one level.
            if forward_queue:
                current = forward_queue.popleft()
                if current in backward_visited:
                    meeting_point = current
                    break
                for neighbor in self.accessible_neighbors(current):
                    if neighbor not in forward_visited:
                        forward_visited.add(neighbor)
                        neighbor.visited = True  # track explored
                        forward_came[neighbor] = current
                        forward_queue.append(neighbor)
            # Expand backward frontier by one level.
            if backward_queue:
                current = backward_queue.popleft()
                if current in forward_visited:
                    meeting_point = current
                    break
                for neighbor in self.accessible_neighbors(current):
                    if neighbor not in backward_visited:
                        backward_visited.add(neighbor)
                        neighbor.visited = True  # track explored
                        backward_came[neighbor] = current
                        backward_queue.append(neighbor)

        if meeting_point is None:
            return None
        # Reconstruct forward half (start → meeting).
        forward_path: List[Tuple[int, int]] = []
        current: Optional[Cell] = meeting_point
        while current is not None:
            forward_path.append((current.x, current.y))
            current = forward_came.get(current)
        forward_path.reverse()
        # Reconstruct backward half (meeting → end), excluding meeting point.
        backward_path: List[Tuple[int, int]] = []
        current = backward_came.get(meeting_point)
        while current is not None:
            backward_path.append((current.x, current.y))
            current = backward_came.get(current)
        return forward_path + backward_path

    # ------------------------------------------------------------------
    # Multi-point / waypoint pathfinding
    # ------------------------------------------------------------------

    def solve_waypoints(
        self,
        waypoints: List[Tuple[int, int]],
        algorithm: str = "bfs",
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Find a path visiting a sequence of waypoints in order.

        The path starts at ``waypoints[0]``, visits each subsequent
        waypoint, and ends at ``waypoints[-1]``.  Each segment is solved
        independently with the given algorithm.

        Parameters
        ----------
        waypoints : list of (x, y)
            At least two waypoints.
        algorithm : str
            Solver to use for each segment.

        Returns
        -------
        list of (x, y) or None
            Combined path, or None if any segment is unsolvable.
        """
        if len(waypoints) < 2:
            raise ValueError("Need at least 2 waypoints")
        full_path: List[Tuple[int, int]] = []
        for i in range(len(waypoints) - 1):
            segment = self.solve(
                algorithm, start=waypoints[i], end=waypoints[i + 1]
            )
            if segment is None:
                return None
            # Avoid duplicating the junction point between segments.
            if full_path and segment and full_path[-1] == segment[0]:
                full_path.extend(segment[1:])
            else:
                full_path.extend(segment)
        return full_path

    # ------------------------------------------------------------------
    # Distance map (BFS from a source to every cell)
    # ------------------------------------------------------------------

    def distance_map(
        self, source: Optional[Tuple[int, int]] = None
    ) -> List[List[int]]:
        """
        Compute BFS distance from ``source`` to every reachable cell.

        Unreachable cells have distance ``-1``.

        Parameters
        ----------
        source : (x, y), optional
            Source cell (default: maze start).

        Returns
        -------
        list of list of int
            2D grid of distances, indexed as ``dist[y][x]``.
        """
        if source is None:
            source = self.start
        self._validate_coords(*source)
        sx, sy = source
        start_cell = self.cells[sy][sx]
        dist: List[List[int]] = [[-1] * self.width for _ in range(self.height)]
        dist[sy][sx] = 0
        # Reset visited flags BEFORE running BFS (other operations like
        # solve() or is_perfect() may have left them set).
        self.reset_visited()
        start_cell.visited = True
        queue: deque[Cell] = deque([start_cell])
        try:
            while queue:
                current = queue.popleft()
                for neighbor in self.accessible_neighbors(current):
                    if not neighbor.visited:
                        neighbor.visited = True
                        dist[neighbor.y][neighbor.x] = dist[current.y][current.x] + 1
                        queue.append(neighbor)
        finally:
            self.reset_visited()
        return dist

    # ------------------------------------------------------------------
    # Maze validation
    # ------------------------------------------------------------------

    def is_perfect(self) -> bool:
        """
        Check whether the maze is a *perfect maze*: fully connected
        (every cell reachable from every other) with no cycles (loops).

        A perfect maze is a spanning tree of the grid graph.
        """
        # 1. Check connectivity via BFS from (0,0).
        self.reset_visited()
        start = self.cells[0][0]
        start.visited = True
        queue: deque[Cell] = deque([start])
        visited_count = 1
        while queue:
            current = queue.popleft()
            for neighbor in self.accessible_neighbors(current):
                if not neighbor.visited:
                    neighbor.visited = True
                    visited_count += 1
                    queue.append(neighbor)
        self.reset_visited()
        if visited_count != self.width * self.height:
            return False
        # 2. Check for cycles: in a spanning tree the number of removed walls
        #    (edges) equals n - 1 where n = number of cells.  Each removed
        #    wall is counted from both sides, so total openings / 2 = edges.
        total_openings = sum(4 - len(c.walls) for c in self.all_cells())
        edges = total_openings // 2
        return edges == self.width * self.height - 1

    # ------------------------------------------------------------------
    # Benchmarking
    # ------------------------------------------------------------------

    def benchmark(
        self, algorithms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Benchmark multiple solving algorithms on this maze.

        Parameters
        ----------
        algorithms : list of str, optional
            Solvers to benchmark (default: all registered solvers).

        Returns
        -------
        list of dict
            One dict per algorithm with keys: ``algorithm``, ``path_length``,
            ``found``, ``explored`` (cells visited), ``time_ms``.
        """
        import time

        if algorithms is None:
            algorithms = list(self.SOLVERS.keys())

        results: List[Dict[str, Any]] = []
        for algo in algorithms:
            if algo not in self.SOLVERS:
                raise ValueError(f"Unknown solver '{algo}'")
            self.reset_visited()
            t0 = time.perf_counter()
            path = self.solve(algo)
            elapsed = (time.perf_counter() - t0) * 1000
            # Count explored cells (visited flag set during solve).
            explored = sum(1 for c in self.all_cells() if c.visited)
            results.append(
                {
                    "algorithm": algo,
                    "path_length": len(path) if path else 0,
                    "found": path is not None,
                    "explored": explored,
                    "time_ms": round(elapsed, 4),
                }
            )
        return results

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(
        self,
        solution: Optional[List[Tuple[int, int]]] = None,
        mark_start_end: bool = True,
    ) -> str:
        """
        Render the maze as an ASCII art string.

        Parameters
        ----------
        solution : list of (x, y), optional
            Solution path to highlight with ``·`` markers.
        mark_start_end : bool
            Mark start with ``S`` and end with ``E``.
        """
        sol_set: Set[Tuple[int, int]] = set(solution) if solution else set()
        grid_w = self.width * 2 + 1
        grid_h = self.height * 2 + 1
        grid: List[List[str]] = [
            [" " for _ in range(grid_w)] for _ in range(grid_h)
        ]

        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                cx, cy = x * 2 + 1, y * 2 + 1
                # Walls
                if Direction.NORTH in cell.walls:
                    grid[cy - 1][cx] = "-"
                if Direction.WEST in cell.walls:
                    grid[cy][cx - 1] = "|"
                if Direction.SOUTH in cell.walls:
                    grid[cy + 1][cx] = "-"
                if Direction.EAST in cell.walls:
                    grid[cy][cx + 1] = "|"
                # Cell content
                coord = (x, y)
                if mark_start_end and coord == self.start:
                    grid[cy][cx] = "S"
                elif mark_start_end and coord == self.end:
                    grid[cy][cx] = "E"
                elif coord in sol_set:
                    grid[cy][cx] = "·"

        # Fill all corner intersections.
        for y in range(0, grid_h, 2):
            for x in range(0, grid_w, 2):
                grid[y][x] = "+"

        # Draw solution path through passages (between cells).
        if solution and len(solution) > 1:
            for i in range(len(solution) - 1):
                x1, y1 = solution[i]
                x2, y2 = solution[i + 1]
                gx1, gy1 = x1 * 2 + 1, y1 * 2 + 1
                gx2, gy2 = x2 * 2 + 1, y2 * 2 + 1
                mid_x, mid_y = (gx1 + gx2) // 2, (gy1 + gy2) // 2
                if grid[mid_y][mid_x] in (" ", "|", "-"):
                    grid[mid_y][mid_x] = "·"

        return "\n".join("".join(row) for row in grid)

    def render_distance_map(
        self,
        source: Optional[Tuple[int, int]] = None,
        max_width: int = 80,
    ) -> str:
        """
        Render a distance heatmap as ASCII art.

        Cells are colored by distance from source using a gradient
        from dark (close) to bright (far).  Uses ANSI 256-color codes.

        Parameters
        ----------
        source : (x, y), optional
            Source for distance computation (default: maze start).
        max_width : int
            Maximum display width in characters before truncating.
        """
        dist = self.distance_map(source)
        max_dist = max(d for row in dist for d in row if d >= 0)
        lines: List[str] = []
        for y in range(self.height):
            line_parts: List[str] = []
            for x in range(self.width):
                d = dist[y][x]
                if d < 0:
                    line_parts.append("  ")
                elif max_dist == 0:
                    line_parts.append("\033[38;5;21m██\033[0m")
                else:
                    # Map distance to 256-color palette 232–255 (grayscale).
                    shade = 232 + int((d / max_dist) * 23)
                    line_parts.append(f"\033[38;5;{shade}m██\033[0m")
            line = "".join(line_parts)
            if len(line) > max_width:
                line = line[:max_width] + "..."
            lines.append(line)
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()

    def __repr__(self) -> str:
        return f"Maze({self.width}x{self.height}, seed={self.seed})"

    # ------------------------------------------------------------------
    # Serialization (JSON)
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the maze to a JSON-compatible dictionary.

        The maze structure (walls), dimensions, seed, start, and end
        are all stored.  The output of :meth:`from_dict` reconstructs
        an identical maze.
        """
        walls_data: List[List[List[str]]] = []
        for y in range(self.height):
            row: List[List[str]] = []
            for x in range(self.width):
                cell = self.cells[y][x]
                row.append([d.name for d in cell.walls])
            walls_data.append(row)
        return {
            "version": 1,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "start": list(self.start),
            "end": list(self.end),
            "walls": walls_data,
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize the maze to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Maze":
        """
        Reconstruct a maze from a :meth:`to_dict` dictionary.

        Validates that the wall data dimensions match the declared
        width and height, and that all wall names are valid Direction
        enum values.
        """
        width = data["width"]
        height = data["height"]
        if not isinstance(width, int) or not isinstance(height, int):
            raise TypeError("width and height must be integers")
        if width < 1 or height < 1:
            raise ValueError("width and height must be positive")
        maze = cls(width, height, seed=data.get("seed"))
        walls_data = data["walls"]
        if len(walls_data) != height:
            raise ValueError(
                f"walls has {len(walls_data)} rows, expected {height}"
            )
        for y in range(height):
            if len(walls_data[y]) != width:
                raise ValueError(
                    f"walls row {y} has {len(walls_data[y])} cells, "
                    f"expected {width}"
                )
            for x in range(width):
                cell = maze.cells[y][x]
                try:
                    cell.walls = {Direction[w] for w in walls_data[y][x]}
                except KeyError as e:
                    raise ValueError(
                        f"Invalid wall name {e} at cell ({x}, {y})"
                    ) from e
        if "start" in data and data["start"] is not None:
            maze._start = tuple(data["start"])  # type: ignore[assignment]
        if "end" in data and data["end"] is not None:
            maze._end = tuple(data["end"])  # type: ignore[assignment]
        return maze

    @classmethod
    def from_json(cls, json_str: str) -> "Maze":
        """Reconstruct a maze from a JSON string produced by :meth:`to_json`."""
        return cls.from_dict(json.loads(json_str))

    def save(self, path: str) -> None:
        """Save the maze to a JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Maze":
        """Load a maze from a JSON file produced by :meth:`save`."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ------------------------------------------------------------------
    # PNG export (pure stdlib — zlib + struct)
    # ------------------------------------------------------------------

    def to_png(self, path: str, cell_size: int = 10, wall_thickness: int = 2) -> None:
        """
        Export the maze as a PNG file using only the standard library.

        Walls are drawn in black on a white background.  The start and
        end cells are marked with green and red respectively.  If a
        solution has been drawn on the grid (via ``render`` with solution),
        those cells are highlighted.

        Parameters
        ----------
        path : str
            Output file path.
        cell_size : int
            Pixel size of each maze cell.
        wall_thickness : int
            Pixel thickness of walls.
        """
        if cell_size < 2:
            raise ValueError("cell_size must be >= 2")
        if wall_thickness < 1:
            raise ValueError("wall_thickness must be >= 1")

        w = self.width * cell_size + 1
        h = self.height * cell_size + 1
        # RGB pixel buffer (3 bytes per pixel, row-major, top-to-bottom).
        # Initialize all white.
        pixels = bytearray([255, 255, 255] * (w * h))

        def set_pixel(px: int, py: int, r: int, g: int, b: int) -> None:
            if 0 <= px < w and 0 <= py < h:
                idx = (py * w + px) * 3
                pixels[idx] = r
                pixels[idx + 1] = g
                pixels[idx + 2] = b

        def fill_rect(x0: int, y0: int, x1: int, y1: int, r: int, g: int, b: int) -> None:
            for py in range(y0, y1):
                for px in range(x0, x1):
                    set_pixel(px, py, r, g, b)

        # Draw walls in black.
        black = (0, 0, 0)
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                px0 = x * cell_size
                py0 = y * cell_size
                px1 = (x + 1) * cell_size
                py1 = (y + 1) * cell_size
                # North wall
                if Direction.NORTH in cell.walls:
                    fill_rect(px0, py0, px1, py0 + wall_thickness, *black)
                # West wall
                if Direction.WEST in cell.walls:
                    fill_rect(px0, py0, px0 + wall_thickness, py1, *black)
                # South wall
                if Direction.SOUTH in cell.walls:
                    fill_rect(px0, py1 - wall_thickness, px1, py1 + 1, *black)
                # East wall
                if Direction.EAST in cell.walls:
                    fill_rect(px1 - wall_thickness, py0, px1 + 1, py1, *black)

        # Mark start (green) and end (red).
        sx, sy = self.start
        fill_rect(
            sx * cell_size + wall_thickness + 1,
            sy * cell_size + wall_thickness + 1,
            (sx + 1) * cell_size,
            (sy + 1) * cell_size,
            0, 200, 0,
        )
        ex, ey = self.end
        fill_rect(
            ex * cell_size + wall_thickness + 1,
            ey * cell_size + wall_thickness + 1,
            (ex + 1) * cell_size,
            (ey + 1) * cell_size,
            200, 0, 0,
        )

        _write_png(path, pixels, w, h)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self) -> Dict[str, Any]:
        """
        Analyze the maze structure.

        Returns
        -------
        dict
            Keys: ``width``, ``height``, ``total_cells``,
            ``total_walls_remaining``, ``dead_ends``, ``corridors``,
            ``junctions``, ``solution_length``, ``has_solution``,
            ``is_perfect``, ``braid_ratio`` (fraction of non-dead-end cells).
        """
        dead_ends = 0
        junctions = 0
        corridors = 0
        total_walls = 0
        for cell in self.all_cells():
            oc = cell.open_count
            if oc == 1:
                dead_ends += 1
            elif oc >= 3:
                junctions += 1
            elif oc == 2:
                corridors += 1
            total_walls += len(cell.walls)
        solution = self.solve("bfs")
        solution_length = len(solution) if solution else 0
        n = self.width * self.height
        return {
            "width": self.width,
            "height": self.height,
            "total_cells": n,
            "total_walls_remaining": total_walls,
            "dead_ends": dead_ends,
            "corridors": corridors,
            "junctions": junctions,
            "solution_length": solution_length,
            "has_solution": solution is not None,
            "is_perfect": self.is_perfect(),
            "braid_ratio": round((n - dead_ends) / n, 4) if n else 0,
        }


# ---------------------------------------------------------------------------
# PNG writer (pure stdlib)
# ---------------------------------------------------------------------------


def _write_png(path: str, pixels: bytearray, width: int, height: int) -> None:
    """
    Write an RGB pixel buffer to a PNG file using only the stdlib.

    Parameters
    ----------
    path : str
        Output file path.
    pixels : bytearray
        Raw RGB data (3 bytes per pixel, row-major, top-to-bottom).
    width, height : int
        Image dimensions in pixels.
    """

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)

    # PNG signature.
    signature = b"\x89PNG\r\n\x1a\n"
    # IHDR: width, height, bit depth=8, color type=2 (RGB), compression=0,
    # filter=0, interlace=0.
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = make_chunk(b"IHDR", ihdr_data)
    # IDAT: each scanline prefixed with filter byte (0 = None).
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter type: None
        raw.extend(pixels[y * stride:(y + 1) * stride])
    compressed = zlib.compress(bytes(raw), level=9)
    idat = make_chunk(b"IDAT", compressed)
    # IEND.
    iend = make_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(signature)
        f.write(ihdr)
        f.write(idat)
        f.write(iend)


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------


def main() -> None:
    """Command-line interface for the maze generator and solver."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description=(
            "Maze Generator & Solver — generate and solve mazes with "
            "multiple algorithms, braid support, PNG export, and analysis."
        )
    )
    parser.add_argument(
        "-W", "--width", type=int, default=20, help="Maze width (default 20)"
    )
    parser.add_argument(
        "-H", "--height", type=int, default=10, help="Maze height (default 10)"
    )
    parser.add_argument(
        "-g", "--generator", default="recursive_backtracking",
        choices=list(Maze.GENERATORS.keys()),
        help="Generation algorithm (default: recursive_backtracking)",
    )
    parser.add_argument(
        "-s", "--solver", default="bfs",
        choices=list(Maze.SOLVERS.keys()),
        help="Solving algorithm (default: bfs)",
    )
    parser.add_argument(
        "--heuristic", default="manhattan",
        choices=list(HEURISTICS.keys()),
        help="Heuristic for A*/greedy solvers (default: manhattan)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--solve", action="store_true", help="Solve the maze and display the path"
    )
    parser.add_argument(
        "--analyze", action="store_true", help="Print maze analysis statistics"
    )
    parser.add_argument(
        "--braid", type=float, nargs="?", const=1.0, default=None,
        help="Braid the maze (remove dead ends). Optional probability 0-1 (default 1.0)",
    )
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Benchmark all solvers on this maze",
    )
    parser.add_argument(
        "--heatmap", action="store_true",
        help="Print a distance heatmap from the start cell",
    )
    parser.add_argument(
        "--save", metavar="FILE", help="Save the maze to a JSON file",
    )
    parser.add_argument(
        "--load", metavar="FILE", help="Load a maze from a JSON file (ignores -g)",
    )
    parser.add_argument(
        "--png", metavar="FILE", help="Export the maze as a PNG image",
    )
    parser.add_argument(
        "--no-display", action="store_true", help="Don't print the maze"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Check if the maze is a perfect maze (connected, no loops)",
    )

    args = parser.parse_args()

    # Load or create the maze.
    if args.load:
        maze = Maze.load(args.load)
    else:
        maze = Maze(args.width, args.height, seed=args.seed)
        maze.generate(args.generator)

    # Braid if requested.
    if args.braid is not None:
        n_braided = maze.braid(args.braid)
        print(f"Braided {n_braided} dead ends (probability={args.braid})")

    # Validate.
    if args.validate:
        perfect = maze.is_perfect()
        print(f"Perfect maze: {perfect}")

    # Solve.
    solution = None
    if args.solve or args.analyze or args.benchmark or args.png:
        solution = maze.solve(args.solver, heuristic=args.heuristic)

    # Display.
    if not args.no_display:
        if args.heatmap:
            print("--- Distance Heatmap ---")
            print(maze.render_distance_map())
        elif args.solve and solution:
            print(maze.render(solution=solution))
            print(f"\nSolution length: {len(solution)} steps")
        else:
            print(maze.render())

    # Benchmark.
    if args.benchmark:
        print("\n--- Solver Benchmark ---")
        results = maze.benchmark()
        print(f"{'Algorithm':<16} {'Found':<6} {'Length':<8} {'Explored':<10} {'Time (ms)':<10}")
        print("-" * 52)
        for r in results:
            print(
                f"{r['algorithm']:<16} {str(r['found']):<6} "
                f"{r['path_length']:<8} {r['explored']:<10} {r['time_ms']:<10}"
            )

    # Analysis.
    if args.analyze:
        stats = maze.analyze()
        print("\n--- Maze Analysis ---")
        for key, val in stats.items():
            print(f"  {key}: {val}")

    # Save.
    if args.save:
        maze.save(args.save)
        print(f"Maze saved to {args.save}")

    # PNG export.
    if args.png:
        maze.to_png(args.png)
        print(f"Maze exported to {args.png}")


if __name__ == "__main__":
    main()