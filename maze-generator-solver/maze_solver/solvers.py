"""
Pathfinding / maze-solving algorithms.

Each solver takes a :class:`~maze_solver.core.Maze` (with start/end
already set) and returns a list of ``(x, y)`` coordinates from start
to end, or ``None`` if no path exists.  All solvers set ``cell.visited``
on explored cells so that :meth:`Maze.benchmark` can count them.
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Dict, List, Optional, Set

from .core import Cell
from .heuristics import HeuristicFn

SOLVER_NAMES: List[str] = [
    "bfs",
    "dfs",
    "astar",
    "dijkstra",
    "bidirectional",
    "greedy",
    "ida_star",
]


# --------------------------------------------------------------------------- #
# BFS
# --------------------------------------------------------------------------- #


def solve_bfs(maze) -> Optional[List[tuple]]:
    """Breadth-first search — guarantees shortest path."""
    sx, sy = maze.start
    ex, ey = maze.end
    start_cell = maze.cells[sy][sx]
    end_cell = maze.cells[ey][ex]
    queue: deque[Cell] = deque([start_cell])
    start_cell.visited = True
    came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
    while queue:
        current = queue.popleft()
        if current == end_cell:
            return maze._reconstruct_path(came_from, end_cell)
        for neighbor in maze.accessible_neighbors(current):
            if not neighbor.visited:
                neighbor.visited = True
                came_from[neighbor] = current
                queue.append(neighbor)
    return None


# --------------------------------------------------------------------------- #
# DFS
# --------------------------------------------------------------------------- #


def solve_dfs(maze) -> Optional[List[tuple]]:
    """Depth-first search — finds *a* path (not necessarily shortest)."""
    sx, sy = maze.start
    ex, ey = maze.end
    start_cell = maze.cells[sy][sx]
    end_cell = maze.cells[ey][ex]
    stack: List[Cell] = [start_cell]
    came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
    start_cell.visited = True
    while stack:
        current = stack.pop()
        if current == end_cell:
            return maze._reconstruct_path(came_from, end_cell)
        for neighbor in maze.accessible_neighbors(current):
            if not neighbor.visited:
                neighbor.visited = True
                came_from[neighbor] = current
                stack.append(neighbor)
    return None


# --------------------------------------------------------------------------- #
# A*
# --------------------------------------------------------------------------- #


def solve_astar(maze, heuristic: HeuristicFn) -> Optional[List[tuple]]:
    """A* search with configurable heuristic — guarantees shortest path."""
    sx, sy = maze.start
    ex, ey = maze.end
    start_cell = maze.cells[sy][sx]
    end_cell = maze.cells[ey][ex]

    open_heap: List[tuple] = []
    counter = 0
    heapq.heappush(open_heap, (heuristic(start_cell, end_cell), counter, start_cell))
    g_score: Dict[Cell, float] = {start_cell: 0}
    came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
    closed: Set[Cell] = set()
    start_cell.visited = True
    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        current.visited = True
        if current == end_cell:
            return maze._reconstruct_path(came_from, end_cell)
        for neighbor in maze.accessible_neighbors(current):
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                f = tentative_g + heuristic(neighbor, end_cell)
                counter += 1
                heapq.heappush(open_heap, (f, counter, neighbor))
    return None


# --------------------------------------------------------------------------- #
# Greedy Best-First
# --------------------------------------------------------------------------- #


def solve_greedy(maze, heuristic: HeuristicFn) -> Optional[List[tuple]]:
    """Greedy best-first search — fast, not guaranteed shortest."""
    sx, sy = maze.start
    ex, ey = maze.end
    start_cell = maze.cells[sy][sx]
    end_cell = maze.cells[ey][ex]

    open_heap: List[tuple] = []
    counter = 0
    heapq.heappush(open_heap, (heuristic(start_cell, end_cell), counter, start_cell))
    came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
    visited: Set[Cell] = {start_cell}
    start_cell.visited = True
    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current == end_cell:
            return maze._reconstruct_path(came_from, end_cell)
        for neighbor in maze.accessible_neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                neighbor.visited = True
                came_from[neighbor] = current
                counter += 1
                heapq.heappush(
                    open_heap, (heuristic(neighbor, end_cell), counter, neighbor)
                )
    return None


# --------------------------------------------------------------------------- #
# Dijkstra
# --------------------------------------------------------------------------- #


def solve_dijkstra(maze) -> Optional[List[tuple]]:
    """Dijkstra's algorithm — equivalent to BFS for uniform-cost grids."""
    sx, sy = maze.start
    ex, ey = maze.end
    start_cell = maze.cells[sy][sx]
    end_cell = maze.cells[ey][ex]
    open_heap: List[tuple] = []
    counter = 0
    heapq.heappush(open_heap, (0, counter, start_cell))
    dist: Dict[Cell, float] = {start_cell: 0}
    came_from: Dict[Cell, Optional[Cell]] = {start_cell: None}
    closed: Set[Cell] = set()
    start_cell.visited = True
    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        current.visited = True
        if current == end_cell:
            return maze._reconstruct_path(came_from, end_cell)
        for neighbor in maze.accessible_neighbors(current):
            nd = dist[current] + 1
            if nd < dist.get(neighbor, float("inf")):
                dist[neighbor] = nd
                came_from[neighbor] = current
                counter += 1
                heapq.heappush(open_heap, (nd, counter, neighbor))
    return None


# --------------------------------------------------------------------------- #
# Bidirectional BFS
# --------------------------------------------------------------------------- #


def solve_bidirectional(maze) -> Optional[List[tuple]]:
    """Bidirectional BFS — two frontiers meeting in the middle."""
    sx, sy = maze.start
    ex, ey = maze.end
    start_cell = maze.cells[sy][sx]
    end_cell = maze.cells[ey][ex]
    if start_cell == end_cell:
        start_cell.visited = True
        return [(sx, sy)]

    forward_queue: deque[Cell] = deque([start_cell])
    backward_queue: deque[Cell] = deque([end_cell])
    forward_came: Dict[Cell, Optional[Cell]] = {start_cell: None}
    backward_came: Dict[Cell, Optional[Cell]] = {end_cell: None}
    forward_visited: Set[Cell] = {start_cell}
    backward_visited: Set[Cell] = {end_cell}
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
            for neighbor in maze.accessible_neighbors(current):
                if neighbor not in forward_visited:
                    forward_visited.add(neighbor)
                    neighbor.visited = True
                    forward_came[neighbor] = current
                    forward_queue.append(neighbor)
        # Expand backward frontier by one level.
        if backward_queue:
            current = backward_queue.popleft()
            if current in forward_visited:
                meeting_point = current
                break
            for neighbor in maze.accessible_neighbors(current):
                if neighbor not in backward_visited:
                    backward_visited.add(neighbor)
                    neighbor.visited = True
                    backward_came[neighbor] = current
                    backward_queue.append(neighbor)

    if meeting_point is None:
        return None
    # Reconstruct forward half (start → meeting).
    forward_path: List[tuple] = []
    current: Optional[Cell] = meeting_point
    while current is not None:
        forward_path.append((current.x, current.y))
        current = forward_came.get(current)
    forward_path.reverse()
    # Reconstruct backward half (meeting → end), excluding meeting point.
    backward_path: List[tuple] = []
    current = backward_came.get(meeting_point)
    while current is not None:
        backward_path.append((current.x, current.y))
        current = backward_came.get(current)
    return forward_path + backward_path


# --------------------------------------------------------------------------- #
# IDA* (Iterative Deepening A*)
# --------------------------------------------------------------------------- #


def solve_ida_star(maze, heuristic: HeuristicFn) -> Optional[List[tuple]]:
    """IDA* — iterative deepening A*.

    Memory-efficient optimal search that uses a depth-first search
    bounded by a cost threshold, increasing the threshold each
    iteration.  Guarantees the shortest path while using O(path_length)
    memory instead of O(n) like A*.
    """
    sx, sy = maze.start
    ex, ey = maze.end
    start_cell = maze.cells[sy][sx]
    end_cell = maze.cells[ey][ex]

    if start_cell == end_cell:
        start_cell.visited = True
        return [(sx, sy)]

    threshold = heuristic(start_cell, end_cell)
    # Track globally visited cells for benchmark counting.
    visited_count: Set[Cell] = {start_cell}

    while threshold < float("inf"):
        # DFS with cost bound.  Returns (found_path, next_threshold).
        result, next_threshold = _ida_search(
            maze, start_cell, end_cell, 0, threshold, heuristic,
            set(), visited_count,
        )
        if result is not None:
            # Mark all visited cells for benchmark.
            for c in visited_count:
                c.visited = True
            return result
        if next_threshold == float("inf"):
            return None
        threshold = next_threshold


def _ida_search(
    maze,
    current: Cell,
    end_cell: Cell,
    g: int,
    threshold: float,
    heuristic: HeuristicFn,
    path_set: Set[Cell],
    visited_count: Set[Cell],
) -> tuple:
    """Recursive DFS step for IDA*. Returns (path_or_None, next_threshold)."""
    f = g + heuristic(current, end_cell)
    if f > threshold:
        return None, f
    if current == end_cell:
        # Reconstruct path from path_set tracking.
        return [(current.x, current.y)], f  # placeholder; rebuilt below

    path_set.add(current)
    visited_count.add(current)

    min_threshold = float("inf")
    for neighbor in maze.accessible_neighbors(current):
        if neighbor in path_set:
            continue
        result, next_t = _ida_search(
            maze, neighbor, end_cell, g + 1, threshold, heuristic,
            path_set, visited_count,
        )
        if result is not None:
            # Prepend current cell to the found path.
            return [(current.x, current.y)] + result, next_t
        if next_t < min_threshold:
            min_threshold = next_t

    path_set.discard(current)
    return None, min_threshold