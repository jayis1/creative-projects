"""
Core data structures for maze-generator-solver.

Defines the ``Direction`` enum, ``Cell`` class, and the ``Maze`` class
that serves as the central data model for all generation, solving,
rendering, and analysis operations.
"""

from __future__ import annotations

import heapq
import json
import math
import random
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

from .heuristics import HEURISTICS, HeuristicFn

# --------------------------------------------------------------------------- #
# Direction
# --------------------------------------------------------------------------- #


class Direction(Enum):
    """Compass directions used for wall removal.

    Each direction stores a ``(dx, dy)`` tuple representing the unit
    movement vector in grid coordinates.
    """

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


# Convenience ordering for deterministic iteration.
_ALL_DIRECTIONS: Tuple[Direction, ...] = (
    Direction.NORTH,
    Direction.EAST,
    Direction.SOUTH,
    Direction.WEST,
)

# Valid wall names for JSON serialization validation.
_VALID_WALL_NAMES: Set[str] = {d.name for d in Direction}


# --------------------------------------------------------------------------- #
# Cell
# --------------------------------------------------------------------------- #


class Cell:
    """A single maze cell.

    Walls are stored as a set of :class:`Direction` enums that are
    *present* (i.e. not yet removed).  A cell starts fully walled and
    walls are removed during generation.

    The ``visited`` flag is scratch state used by generation and solving
    algorithms; it is reset by :meth:`Maze.reset_visited`.
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


# --------------------------------------------------------------------------- #
# Maze
# --------------------------------------------------------------------------- #


class Maze:
    """A rectangular grid maze.

    The maze uses a grid of cells where each cell has walls on all four
    sides initially.  Generation algorithms remove walls to carve
    passages, producing a **perfect maze** (exactly one path between
    any two cells).  The maze can optionally be *braided* (dead ends
    removed) via :meth:`braid`.

    Parameters
    ----------
    width : int
        Number of cells horizontally (columns).  Must be >= 1.
    height : int
        Number of cells vertically (rows).  Must be >= 1.
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
        "aldous_broder": "_gen_aldous_broder",
        "recursive_division": "_gen_recursive_division",
    }

    # Registry of available solving algorithms.
    SOLVERS: Dict[str, str] = {
        "bfs": "_solve_bfs",
        "dfs": "_solve_dfs",
        "astar": "_solve_astar",
        "dijkstra": "_solve_dijkstra",
        "bidirectional": "_solve_bidirectional",
        "greedy": "_solve_greedy",
        "ida_star": "_solve_ida_star",
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
        # Heuristic function set during solve(); default Manhattan.
        self._heuristic_fn: HeuristicFn = HEURISTICS["manhattan"]

    # ------------------------------------------------------------------ #
    # Start / end accessors
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Coordinate / cell helpers
    # ------------------------------------------------------------------ #

    def _validate_coords(self, x: int, y: int) -> None:
        """Raise ``ValueError`` if (x, y) is outside the maze bounds."""
        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError(f"Coordinates must be integers, got ({x!r}, {y!r})")
        if not (0 <= x < self.width):
            raise ValueError(f"x={x} out of range [0, {self.width})")
        if not (0 <= y < self.height):
            raise ValueError(f"y={y} out of range [0, {self.height})")

    def get_cell(self, x: int, y: int) -> Cell:
        """Return the cell at (x, y).  Raises if out of bounds."""
        self._validate_coords(x, y)
        return self.cells[y][x]

    def neighbors(self, cell: Cell) -> List[Tuple[Cell, Direction]]:
        """Return list of ``(neighbor_cell, direction)`` pairs for all
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
        """Add a wall between two adjacent cells."""
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

    # ------------------------------------------------------------------ #
    # Generation dispatch
    # ------------------------------------------------------------------ #

    def generate(self, algorithm: str = "recursive_backtracking") -> None:
        """Generate the maze using the named algorithm.

        This resets all walls to fully-walled and clears visited flags
        before running the generator.

        Parameters
        ----------
        algorithm : str
            One of the keys in :attr:`GENERATORS`.
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

    # ------------------------------------------------------------------ #
    # Generation algorithms (delegated to generators.py via methods)
    # ------------------------------------------------------------------ #

    def _gen_recursive_backtracking(self) -> None:
        from .generators import gen_recursive_backtracking

        gen_recursive_backtracking(self)

    def _gen_prims(self) -> None:
        from .generators import gen_prims

        gen_prims(self)

    def _gen_kruskals(self) -> None:
        from .generators import gen_kruskals

        gen_kruskals(self)

    def _gen_ellers(self) -> None:
        from .generators import gen_ellers

        gen_ellers(self)

    def _gen_wilsons(self) -> None:
        from .generators import gen_wilsons

        gen_wilsons(self)

    def _gen_binary_tree(self) -> None:
        from .generators import gen_binary_tree

        gen_binary_tree(self)

    def _gen_sidewinder(self) -> None:
        from .generators import gen_sidewinder

        gen_sidewinder(self)

    def _gen_aldous_broder(self) -> None:
        from .generators import gen_aldous_broder

        gen_aldous_broder(self)

    def _gen_recursive_division(self) -> None:
        from .generators import gen_recursive_division

        gen_recursive_division(self)

    # ------------------------------------------------------------------ #
    # Braid — remove dead ends by adding extra passages
    # ------------------------------------------------------------------ #

    def braid(self, probability: float = 1.0) -> int:
        """Remove dead ends by opening a wall to a random neighbor.

        A *braid* maze has no dead ends — every cell has at least two
        openings, creating loops and multiple paths.

        Parameters
        ----------
        probability : float
            Probability (0–1) that any given dead end is braided.

        Returns
        -------
        int
            Number of dead ends that were braided.
        """
        if not isinstance(probability, (int, float)):
            raise TypeError("probability must be a number")
        if not (0.0 <= probability <= 1.0):
            raise ValueError("probability must be in [0, 1]")
        braided = 0
        for cell in list(self.all_cells()):
            if cell.open_count != 1:
                continue
            if self.rng.random() > probability:
                continue
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

    # ------------------------------------------------------------------ #
    # Solving dispatch
    # ------------------------------------------------------------------ #

    def solve(
        self,
        algorithm: str = "bfs",
        start: Optional[Tuple[int, int]] = None,
        end: Optional[Tuple[int, int]] = None,
        heuristic: str = "manhattan",
    ) -> Optional[List[Tuple[int, int]]]:
        """Solve the maze from start to end using the named algorithm.

        Parameters
        ----------
        algorithm : str
            One of the keys in :attr:`SOLVERS`.
        start : (x, y), optional
            Override the maze's default start cell.
        end : (x, y), optional
            Override the maze's default end cell.
        heuristic : str
            Heuristic for A* / greedy / IDA*: ``manhattan``,
            ``euclidean``, or ``chebyshev``.

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

    # ------------------------------------------------------------------ #
    # Solving algorithms (delegated to solvers.py)
    # ------------------------------------------------------------------ #

    def _solve_bfs(self) -> Optional[List[Tuple[int, int]]]:
        from .solvers import solve_bfs

        return solve_bfs(self)

    def _solve_dfs(self) -> Optional[List[Tuple[int, int]]]:
        from .solvers import solve_dfs

        return solve_dfs(self)

    def _solve_astar(self) -> Optional[List[Tuple[int, int]]]:
        from .solvers import solve_astar

        return solve_astar(self, self._heuristic_fn)

    def _solve_greedy(self) -> Optional[List[Tuple[int, int]]]:
        from .solvers import solve_greedy

        return solve_greedy(self, self._heuristic_fn)

    def _solve_dijkstra(self) -> Optional[List[Tuple[int, int]]]:
        from .solvers import solve_dijkstra

        return solve_dijkstra(self)

    def _solve_bidirectional(self) -> Optional[List[Tuple[int, int]]]:
        from .solvers import solve_bidirectional

        return solve_bidirectional(self)

    def _solve_ida_star(self) -> Optional[List[Tuple[int, int]]]:
        from .solvers import solve_ida_star

        return solve_ida_star(self, self._heuristic_fn)

    # ------------------------------------------------------------------ #
    # Multi-point / waypoint pathfinding
    # ------------------------------------------------------------------ #

    def solve_waypoints(
        self,
        waypoints: List[Tuple[int, int]],
        algorithm: str = "bfs",
    ) -> Optional[List[Tuple[int, int]]]:
        """Find a path visiting a sequence of waypoints in order.

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
            if full_path and segment and full_path[-1] == segment[0]:
                full_path.extend(segment[1:])
            else:
                full_path.extend(segment)
        return full_path

    # ------------------------------------------------------------------ #
    # Distance map
    # ------------------------------------------------------------------ #

    def distance_map(
        self, source: Optional[Tuple[int, int]] = None
    ) -> List[List[int]]:
        """Compute BFS distance from ``source`` to every reachable cell.

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
        self.reset_visited()
        start_cell.visited = True
        queue: deque[Cell] = deque([start_cell])
        try:
            while queue:
                current = queue.popleft()
                for neighbor in self.accessible_neighbors(current):
                    if not neighbor.visited:
                        neighbor.visited = True
                        dist[neighbor.y][neighbor.x] = (
                            dist[current.y][current.x] + 1
                        )
                        queue.append(neighbor)
        finally:
            self.reset_visited()
        return dist

    # ------------------------------------------------------------------ #
    # Maze validation
    # ------------------------------------------------------------------ #

    def is_perfect(self) -> bool:
        """Check whether the maze is a *perfect maze*.

        A perfect maze is fully connected (every cell reachable from
        every other) with no cycles (loops), i.e. a spanning tree.
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
        # 2. Check for cycles: edges == n - 1.
        total_openings = sum(4 - len(c.walls) for c in self.all_cells())
        edges = total_openings // 2
        return edges == self.width * self.height - 1

    # ------------------------------------------------------------------ #
    # Benchmarking
    # ------------------------------------------------------------------ #

    def benchmark(
        self, algorithms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Benchmark multiple solving algorithms on this maze.

        Parameters
        ----------
        algorithms : list of str, optional
            Solvers to benchmark (default: all registered solvers).

        Returns
        -------
        list of dict
            One dict per algorithm with keys: ``algorithm``,
            ``path_length``, ``found``, ``explored``, ``time_ms``.
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

    # ------------------------------------------------------------------ #
    # Serialization (JSON)
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the maze to a JSON-compatible dictionary."""
        walls_data: List[List[List[str]]] = []
        for y in range(self.height):
            row: List[List[str]] = []
            for x in range(self.width):
                cell = self.cells[y][x]
                row.append([d.name for d in cell.walls])
            walls_data.append(row)
        return {
            "version": 2,
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
        """Reconstruct a maze from a :meth:`to_dict` dictionary.

        Validates wall data dimensions and wall names.
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
                wall_names = walls_data[y][x]
                validated: Set[Direction] = set()
                for w_name in wall_names:
                    if w_name not in _VALID_WALL_NAMES:
                        raise ValueError(
                            f"Invalid wall name '{w_name}' at cell ({x}, {y})"
                        )
                    validated.add(Direction[w_name])
                cell.walls = validated
        if "start" in data and data["start"] is not None:
            maze._start = tuple(data["start"])  # type: ignore[assignment]
        if "end" in data and data["end"] is not None:
            maze._end = tuple(data["end"])  # type: ignore[assignment]
        return maze

    @classmethod
    def from_json(cls, json_str: str) -> "Maze":
        """Reconstruct a maze from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save(self, path: str) -> None:
        """Save the maze to a JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Maze":
        """Load a maze from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ------------------------------------------------------------------ #
    # Rendering convenience methods (delegated to renderers.py)
    # ------------------------------------------------------------------ #

    def render(
        self,
        solution: Optional[List[Tuple[int, int]]] = None,
        mark_start_end: bool = True,
    ) -> str:
        """Render the maze as an ASCII art string.

        Parameters
        ----------
        solution : list of (x, y), optional
            Solution path to highlight with ``·`` markers.
        mark_start_end : bool
            Mark start with ``S`` and end with ``E``.
        """
        from .renderers import render_ascii

        return render_ascii(self, solution=solution, mark_start_end=mark_start_end)

    def render_distance_map(
        self,
        source: Optional[Tuple[int, int]] = None,
        max_width: int = 80,
    ) -> str:
        """Render a distance heatmap as ANSI-colored ASCII art."""
        from .renderers import render_distance_map as _rdm

        return _rdm(self, source=source, max_width=max_width)

    def to_png(
        self,
        path: str,
        cell_size: int = 10,
        wall_thickness: int = 2,
        solution: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        """Export the maze as a PNG file.

        Parameters
        ----------
        path : str
            Output file path.
        cell_size : int
            Pixel size of each maze cell.
        wall_thickness : int
            Pixel thickness of walls.
        solution : list of (x, y), optional
            Solution path to draw in blue.
        """
        from .renderers import write_png

        write_png(self, path, cell_size=cell_size,
                  wall_thickness=wall_thickness, solution=solution)

    def to_svg(
        self,
        path: str,
        cell_size: int = 20,
        wall_width: int = 2,
        solution: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        """Export the maze as an SVG file.

        Parameters
        ----------
        path : str
            Output file path.
        cell_size : int
            Size of each maze cell in the SVG coordinate system.
        wall_width : int
            Stroke width for walls.
        solution : list of (x, y), optional
            Solution path to draw as a colored polyline.
        """
        from .renderers import write_svg

        write_svg(self, path, cell_size=cell_size,
                  wall_width=wall_width, solution=solution)

    # ------------------------------------------------------------------ #
    # Analysis (delegated to analysis.py)
    # ------------------------------------------------------------------ #

    def analyze(self) -> Dict[str, Any]:
        """Analyze the maze structure.

        Returns
        -------
        dict
            Keys: ``width``, ``height``, ``total_cells``,
            ``total_walls_remaining``, ``dead_ends``, ``corridors``,
            ``junctions``, ``solution_length``, ``has_solution``,
            ``is_perfect``, ``braid_ratio``, ``difficulty_score``.
        """
        from .analysis import analyze_maze

        return analyze_maze(self)

    def difficulty_score(self) -> float:
        """Compute a difficulty score (0–100) for this maze."""
        from .analysis import difficulty_score as _ds

        return _ds(self)

    # ------------------------------------------------------------------ #
    # Dunder methods
    # ------------------------------------------------------------------ #

    def __str__(self) -> str:
        from .renderers import render_ascii

        return render_ascii(self)

    def __repr__(self) -> str:
        return f"Maze({self.width}x{self.height}, seed={self.seed})"

    def __len__(self) -> int:
        return self.width * self.height

    def __contains__(self, coord: Tuple[int, int]) -> bool:
        x, y = coord
        return 0 <= x < self.width and 0 <= y < self.height