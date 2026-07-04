"""
maze-generator-solver: A comprehensive maze generation and solving toolkit.

Supports multiple generation algorithms (recursive backtracking, Prim's,
Kruskal's, Eller's, Wilson's) and multiple solving algorithms (BFS, DFS,
A*, Dijkstra, bidirectional BFS) with ASCII rendering and analysis.

Author: creative-projects
License: MIT
"""

from __future__ import annotations

import heapq
import random
import math
from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Iterator, Callable, Mapping
from enum import Enum

# ---------------------------------------------------------------------------
# Cell and Maze data structures
# ---------------------------------------------------------------------------

class Direction(Enum):
    """Compass directions used for wall removal."""
    NORTH = (0, -1)
    EAST = (1, 0)
    SOUTH = (0, 1)
    WEST = (-1, 0)

    @property
    def opposite(self) -> "Direction":
        opp_map = {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }
        return opp_map[self]


class Cell:
    """
    A single maze cell.

    Walls are stored as a set of Direction enums that are *present*
    (i.e. not yet removed).  A cell starts fully walled and walls are
    removed during generation.
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


class Maze:
    """
    A rectangular grid maze.

    The maze uses a grid of cells where each cell has walls on
    all four sides initially.  Generation algorithms remove walls
    to carve passages.

    Parameters
    ----------
    width : int
        Number of cells horizontally (columns).
    height : int
        Number of cells vertically (rows).
    seed : int, optional
        Random seed for reproducibility.
    """

    def __init__(self, width: int, height: int, seed: Optional[int] = None) -> None:
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

    # -- grid helpers -------------------------------------------------------

    @property
    def start(self) -> Tuple[int, int]:
        if self._start is None:
            return (0, 0)
        return self._start

    @property
    def end(self) -> Tuple[int, int]:
        if self._end is None:
            return (self.width - 1, self.height - 1)
        return self._end

    def set_start(self, x: int, y: int) -> None:
        self._validate_coords(x, y)
        self._start = (x, y)

    def set_end(self, x: int, y: int) -> None:
        self._validate_coords(x, y)
        self._end = (x, y)

    def _validate_coords(self, x: int, y: int) -> None:
        if not (0 <= x < self.width):
            raise ValueError(f"x={x} out of range [0, {self.width})")
        if not (0 <= y < self.height):
            raise ValueError(f"y={y} out of range [0, {self.height})")

    def get_cell(self, x: int, y: int) -> Cell:
        self._validate_coords(x, y)
        return self.cells[y][x]

    def neighbors(self, cell: Cell) -> List[Tuple[Cell, Direction]]:
        """
        Return list of (neighbor_cell, direction) pairs for all
        in-bounds neighbors regardless of walls.
        """
        result = []
        for d in Direction:
            nx, ny = cell.x + d.value[0], cell.y + d.value[1]
            if 0 <= nx < self.width and 0 <= ny < self.height:
                result.append((self.cells[ny][nx], d))
        return result

    def accessible_neighbors(self, cell: Cell) -> List[Cell]:
        """Neighbors reachable through removed walls (open passages)."""
        result = []
        for d in Direction:
            if d in cell.walls:
                continue
            nx, ny = cell.x + d.value[0], cell.y + d.value[1]
            if 0 <= nx < self.width and 0 <= ny < self.height:
                result.append(self.cells[ny][nx])
        return result

    def all_neighbors(self, cell: Cell) -> List[Cell]:
        """All in-bounds neighbors, walls or not."""
        result = []
        for d in Direction:
            nx, ny = cell.x + d.value[0], cell.y + d.value[1]
            if 0 <= nx < self.width and 0 <= ny < self.height:
                result.append(self.cells[ny][nx])
        return result

    def remove_wall(self, a: Cell, b: Cell) -> None:
        """Remove the wall between two adjacent cells a and b."""
        if abs(a.x - b.x) + abs(a.y - b.y) != 1:
            raise ValueError("Cells must be adjacent")
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

    def all_cells(self) -> Iterator[Cell]:
        """Yield all cells in the maze."""
        for row in self.cells:
            yield from row

    def reset_visited(self) -> None:
        """Clear the visited flag on every cell."""
        for cell in self.all_cells():
            cell.visited = False

    # -- generation dispatcher ----------------------------------------------

    def generate(self, algorithm: str = "recursive_backtracking") -> None:
        """Generate the maze using the named algorithm."""
        algo = algorithm.lower().strip()
        generators = {
            "recursive_backtracking": self._gen_recursive_backtracking,
            "prims": self._gen_prims,
            "kruskals": self._gen_kruskals,
            "ellers": self._gen_ellers,
            "wilsons": self._gen_wilsons,
            "binary_tree": self._gen_binary_tree,
            "sidewinder": self._gen_sidewinder,
        }
        if algo not in generators:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. Available: {list(generators.keys())}"
            )
        # Reset maze state
        for row in self.cells:
            for cell in row:
                cell.walls = set(Direction)
                cell.visited = False
        generators[algo]()

    # -- generation algorithms ----------------------------------------------

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
                neighbor, direction = self.rng.choice(unvisited)
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
        cells with randomly ordered edges, avoiding cycles.
        """
        parent_map: Dict[Cell, Cell] = {}

        def find(c: Cell) -> Cell:
            while parent_map[c] != c:
                parent_map[c] = parent_map[parent_map[c]]
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
        # Union-find on cell IDs (y*width + x)
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
            # Randomly merge adjacent cells within the row
            for x in range(self.width - 1):
                if y == self.height - 1 or self.rng.random() < 0.5:
                    ci = y * self.width + x
                    ni = y * self.width + (x + 1)
                    if find(ci) != find(ni):
                        union(ci, ni)
                        self.remove_wall(self.cells[y][x], self.cells[y][x + 1])
            # For each set in the row, create at least one vertical passage
            if y < self.height - 1:
                sets: Dict[int, List[int]] = {}
                for x in range(self.width):
                    root = find(y * self.width + x)
                    sets.setdefault(root, []).append(x)
                for members in sets.values():
                    # Pick at least one to connect downward
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
        """
        start = self.cells[0][0]
        start.visited = True
        remaining = self.width * self.height - 1
        while remaining > 0:
            # Pick a random unvisited cell
            while True:
                x = self.rng.randrange(self.width)
                y = self.rng.randrange(self.height)
                if not self.cells[y][x].visited:
                    break
            # Do a loop-erased random walk
            path: List[Cell] = [self.cells[y][x]]
            direction_from: Dict[Cell, Direction] = {}
            current = self.cells[y][x]
            while not current.visited:
                neighbors = self.neighbors(current)
                neighbor, direction = self.rng.choice(neighbors)
                direction_from[current] = direction
                if neighbor in direction_from or neighbor.visited:
                    # Erase loop
                    if not neighbor.visited:
                        # Find the loop start and erase
                        loop_start_idx = path.index(neighbor)
                        for c in path[loop_start_idx + 1:]:
                            del direction_from[c]
                        path = path[:loop_start_idx + 1]
                    else:
                        path.append(neighbor)
                else:
                    path.append(neighbor)
                current = neighbor
            # Carve the path
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
        Produces a biased but valid maze with a clear diagonal bias.
        """
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                choices = []
                if y > 0:
                    choices.append(Direction.NORTH)
                if x < self.width - 1:
                    choices.append(Direction.EAST)
                if not choices:
                    continue
                d = self.rng.choice(choices)
                nx, ny = cell.x + d.value[0], cell.y + d.value[1]
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
                at_east_boundary = (x == self.width - 1)
                at_north_boundary = (y == 0)
                if at_east_boundary or (not at_north_boundary and self.rng.random() < 0.5):
                    # Close the run: carve north from a random cell
                    if not at_north_boundary:
                        chosen = self.rng.choice(run)
                        nx, ny = chosen.x, chosen.y - 1
                        self.remove_wall(chosen, self.cells[ny][nx])
                    run = []
                else:
                    # Extend the run eastward
                    if not at_east_boundary:
                        self.remove_wall(cell, self.cells[y][x + 1])

    # -- solving dispatcher -------------------------------------------------

    def solve(self, algorithm: str = "bfs") -> Optional[List[Tuple[int, int]]]:
        """
        Solve the maze from start to end using the named algorithm.

        Returns a list of (x, y) coordinates from start to end, or None
        if no solution exists.
        """
        algo = algorithm.lower().strip()
        solvers = {
            "bfs": self._solve_bfs,
            "dfs": self._solve_dfs,
            "astar": self._solve_astar,
            "dijkstra": self._solve_dijkstra,
            "bidirectional": self._solve_bidirectional,
        }
        if algo not in solvers:
            raise ValueError(
                f"Unknown solver '{algorithm}'. Available: {list(solvers.keys())}"
            )
        self.reset_visited()
        return solvers[algo]()

    def _reconstruct_path(
        self, came_from: Mapping[Cell, Optional[Cell]], end: Cell
    ) -> List[Tuple[int, int]]:
        path = []
        current: Optional[Cell] = end
        while current is not None:
            path.append((current.x, current.y))
            current = came_from.get(current)
        path.reverse()
        return path

    def _solve_bfs(self) -> Optional[List[Tuple[int, int]]]:
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
        sx, sy = self.start
        ex, ey = self.end
        start_cell = self.cells[sy][sx]
        end_cell = self.cells[ey][ex]

        def heuristic(cell: Cell) -> float:
            return math.hypot(cell.x - ex, cell.y - ey)

        open_heap: List[Tuple[float, int, Cell]] = []
        counter = 0
        heapq.heappush(open_heap, (heuristic(start_cell), counter, start_cell))
        g_score: Dict[Cell, float] = {start_cell: 0}
        came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
        closed: Set[Cell] = set()
        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
            if current == end_cell:
                return self._reconstruct_path(came_from, end_cell)
            for neighbor in self.accessible_neighbors(current):
                tentative_g = g_score[current] + 1
                if tentative_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g
                    came_from[neighbor] = current
                    f = tentative_g + heuristic(neighbor)
                    counter += 1
                    heapq.heappush(open_heap, (f, counter, neighbor))
        return None

    def _solve_dijkstra(self) -> Optional[List[Tuple[int, int]]]:
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
        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
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
        sx, sy = self.start
        ex, ey = self.end
        start_cell = self.cells[sy][sx]
        end_cell = self.cells[ey][ex]
        if start_cell == end_cell:
            return [(sx, sy)]
        forward_queue: deque[Cell] = deque([start_cell])
        backward_queue: deque[Cell] = deque([end_cell])
        forward_came: Dict[Cell, Optional[Cell]] = {start_cell: None}
        backward_came: Dict[Cell, Optional[Cell]] = {end_cell: None}
        forward_visited: Set[Cell] = {start_cell}
        backward_visited: Set[Cell] = {end_cell}
        meeting_point: Optional[Cell] = None

        while forward_queue and backward_queue:
            # Expand forward
            if forward_queue:
                current = forward_queue.popleft()
                if current in backward_visited:
                    meeting_point = current
                    break
                for neighbor in self.accessible_neighbors(current):
                    if neighbor not in forward_visited:
                        forward_visited.add(neighbor)
                        forward_came[neighbor] = current
                        forward_queue.append(neighbor)
            # Expand backward
            if backward_queue:
                current = backward_queue.popleft()
                if current in forward_visited:
                    meeting_point = current
                    break
                for neighbor in self.accessible_neighbors(current):
                    if neighbor not in backward_visited:
                        backward_visited.add(neighbor)
                        backward_came[neighbor] = current
                        backward_queue.append(neighbor)

        if meeting_point is None:
            return None
        # Reconstruct: forward path from start to meeting, then backward reversed
        forward_path: List[Tuple[int, int]] = []
        current: Optional[Cell] = meeting_point
        while current is not None:
            forward_path.append((current.x, current.y))
            current = forward_came.get(current)
        forward_path.reverse()
        backward_path: List[Tuple[int, int]] = []
        current = backward_came.get(meeting_point)
        while current is not None:
            backward_path.append((current.x, current.y))
            current = backward_came.get(current)
        return forward_path + backward_path

    # -- rendering ----------------------------------------------------------

    def to_string(
        self,
        solution: Optional[List[Tuple[int, int]]] = None,
        mark_start_end: bool = True,
    ) -> str:
        """
        Render the maze as an ASCII art string.

        Parameters
        ----------
        solution : list of (x, y), optional
            Solution path to highlight with dots.
        mark_start_end : bool
            Mark start with 'S' and end with 'E'.
        """
        lines: List[str] = []
        sol_set: Set[Tuple[int, int]] = set(solution) if solution else set()
        # Top boundary
        top = " " + "___ " * self.width
        lines.append(top)
        for y in range(self.height):
            row_line = "|"
            for x in range(self.width):
                cell = self.cells[y][x]
                coord = (x, y)
                if mark_start_end and coord == self.start:
                    body = " S "
                elif mark_start_end and coord == self.end:
                    body = " E "
                elif coord in sol_set:
                    body = " · "
                else:
                    body = "   "
                south_wall = "_" if Direction.SOUTH in cell.walls else " "
                if Direction.EAST in cell.walls:
                    row_line += body + "|"
                else:
                    row_line += body + south_wall if False else body + " "
                # Rebuild: need to handle south wall correctly
            # This approach is tricky; let me use a cleaner method
            lines.pop()
            break
        # Restart with cleaner rendering
        return self._render_clean(solution, mark_start_end)

    def _render_clean(
        self,
        solution: Optional[List[Tuple[int, int]]] = None,
        mark_start_end: bool = True,
    ) -> str:
        """Clean ASCII renderer using character grids."""
        sol_set: Set[Tuple[int, int]] = set(solution) if solution else set()
        # Each cell occupies 2 chars wide, 2 chars tall in the output grid
        # We use a grid of characters: width*2+1 columns, height*2+1 rows
        grid_w = self.width * 2 + 1
        grid_h = self.height * 2 + 1
        grid: List[List[str]] = [[" " for _ in range(grid_w)] for _ in range(grid_h)]

        # Draw borders and walls
        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                cx, cy = x * 2 + 1, y * 2 + 1  # cell center in grid
                # Corners
                grid[cy - 1][cx - 1] = "+"
                # Walls
                if Direction.NORTH in cell.walls:
                    grid[cy - 1][cx] = "-"
                if Direction.WEST in cell.walls:
                    grid[cy][cx - 1] = "|"
                # South wall (drawn as the north wall of the row below)
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
                # Corners for south and east
                grid[cy + 1][cx + 1] = "+"
                if Direction.SOUTH in cell.walls and Direction.EAST in cell.walls:
                    grid[cy + 1][cx + 1] = "+"

        # Fill all + corners at intersections
        for y in range(0, grid_h, 2):
            for x in range(0, grid_w, 2):
                grid[y][x] = "+"

        # Draw solution path through passages
        if solution and len(solution) > 1:
            for i in range(len(solution) - 1):
                x1, y1 = solution[i]
                x2, y2 = solution[i + 1]
                gx1, gy1 = x1 * 2 + 1, y1 * 2 + 1
                gx2, gy2 = x2 * 2 + 1, y2 * 2 + 1
                # Mark the passage between them
                mid_x, mid_y = (gx1 + gx2) // 2, (gy1 + gy2) // 2
                if grid[mid_y][mid_x] in (" ", "|", "-"):
                    grid[mid_y][mid_x] = "·"

        lines = ["".join(row) for row in grid]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self._render_clean()

    def __repr__(self) -> str:
        return f"Maze({self.width}x{self.height}, seed={self.seed})"

    # -- analysis ----------------------------------------------------------

    def analyze(self) -> Dict[str, object]:
        """
        Analyze the maze: count dead ends, corridor lengths, solution length.
        """
        dead_ends = 0
        junctions = 0
        corridors = 0
        total_walls = 0
        for cell in self.all_cells():
            open_count = 4 - len(cell.walls)
            if open_count == 1:
                dead_ends += 1
            elif open_count >= 3:
                junctions += 1
            elif open_count == 2:
                corridors += 1
            total_walls += len(cell.walls)
        solution = self.solve("bfs")
        solution_length = len(solution) if solution else 0
        return {
            "width": self.width,
            "height": self.height,
            "total_cells": self.width * self.height,
            "total_walls_remaining": total_walls,
            "dead_ends": dead_ends,
            "corridors": corridors,
            "junctions": junctions,
            "solution_length": solution_length,
            "has_solution": solution is not None,
        }


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for the maze generator and solver."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Maze Generator & Solver — generate and solve mazes with multiple algorithms."
    )
    parser.add_argument("-W", "--width", type=int, default=20, help="Maze width (default 20)")
    parser.add_argument("-H", "--height", type=int, default=10, help="Maze height (default 10)")
    parser.add_argument(
        "-g", "--generator", default="recursive_backtracking",
        choices=["recursive_backtracking", "prims", "kruskals", "ellers",
                 "wilsons", "binary_tree", "sidewinder"],
        help="Generation algorithm",
    )
    parser.add_argument(
        "-s", "--solver", default="bfs",
        choices=["bfs", "dfs", "astar", "dijkstra", "bidirectional"],
        help="Solving algorithm",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--solve", action="store_true", help="Solve the maze and display the path")
    parser.add_argument("--analyze", action="store_true", help="Print maze analysis statistics")
    parser.add_argument("--no-display", action="store_true", help="Don't print the maze")

    args = parser.parse_args()

    maze = Maze(args.width, args.height, seed=args.seed)
    maze.generate(args.generator)

    solution = None
    if args.solve or args.analyze:
        solution = maze.solve(args.solver)

    if not args.no_display:
        if args.solve and solution:
            print(maze._render_clean(solution=solution))
            print(f"\nSolution length: {len(solution)} steps")
        else:
            print(maze._render_clean())

    if args.analyze:
        stats = maze.analyze()
        print("\n--- Maze Analysis ---")
        for key, val in stats.items():
            print(f"  {key}: {val}")


if __name__ == "__main__":
    main()