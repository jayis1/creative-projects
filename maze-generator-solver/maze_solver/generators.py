"""
Maze generation algorithms.

All generators operate on a :class:`~maze_solver.core.Maze` instance,
modifying its cells' wall sets in place.  Each function assumes the
maze starts fully walled (all four walls present on every cell) with
``visited`` flags cleared.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .core import Cell, Direction, _ALL_DIRECTIONS

GENERATOR_NAMES: List[str] = [
    "recursive_backtracking",
    "prims",
    "kruskals",
    "ellers",
    "wilsons",
    "binary_tree",
    "sidewinder",
    "aldous_broder",
    "recursive_division",
]


# --------------------------------------------------------------------------- #
# Recursive Backtracking
# --------------------------------------------------------------------------- #


def gen_recursive_backtracking(maze) -> None:
    """Depth-first recursive backtracker using an explicit stack.

    Produces long winding corridors with few junctions.
    """
    start = maze.cells[0][0]
    start.visited = True
    stack: List[Cell] = [start]
    while stack:
        current = stack[-1]
        unvisited = [
            (n, d) for n, d in maze.neighbors(current) if not n.visited
        ]
        if unvisited:
            neighbor, _direction = maze.rng.choice(unvisited)
            maze.remove_wall(current, neighbor)
            neighbor.visited = True
            stack.append(neighbor)
        else:
            stack.pop()


# --------------------------------------------------------------------------- #
# Prim's
# --------------------------------------------------------------------------- #


def gen_prims(maze) -> None:
    """Modified Prim's algorithm: grow a frontier set from a random cell."""
    start = maze.cells[0][0]
    start.visited = True
    frontier: List[Tuple[Cell, Cell]] = []
    for n, _ in maze.neighbors(start):
        frontier.append((start, n))
    while frontier:
        idx = maze.rng.randrange(len(frontier))
        parent, child = frontier.pop(idx)
        if not child.visited:
            child.visited = True
            maze.remove_wall(parent, child)
            for n, _ in maze.neighbors(child):
                if not n.visited:
                    frontier.append((child, n))


# --------------------------------------------------------------------------- #
# Kruskal's
# --------------------------------------------------------------------------- #


def gen_kruskals(maze) -> None:
    """Kruskal's algorithm using union-find.

    Produces a uniform spanning tree when edges are randomly ordered.
    Only removes walls between cells in different sets (avoids cycles).
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

    for cell in maze.all_cells():
        parent_map[cell] = cell

    edges: List[Tuple[Cell, Cell]] = []
    for y in range(maze.height):
        for x in range(maze.width):
            cell = maze.cells[y][x]
            if x < maze.width - 1:
                edges.append((cell, maze.cells[y][x + 1]))
            if y < maze.height - 1:
                edges.append((cell, maze.cells[y + 1][x]))
    maze.rng.shuffle(edges)
    for a, b in edges:
        if union(a, b):
            maze.remove_wall(a, b)


# --------------------------------------------------------------------------- #
# Eller's
# --------------------------------------------------------------------------- #


def gen_ellers(maze) -> None:
    """Eller's algorithm: row-by-row with union-find, O(width) memory."""
    parent = list(range(maze.width * maze.height))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for y in range(maze.height):
        # Randomly merge adjacent cells within the row.
        for x in range(maze.width - 1):
            if y == maze.height - 1 or maze.rng.random() < 0.5:
                ci = y * maze.width + x
                ni = y * maze.width + (x + 1)
                if find(ci) != find(ni):
                    union(ci, ni)
                    maze.remove_wall(maze.cells[y][x], maze.cells[y][x + 1])
        # For each set in the row, create at least one vertical passage.
        if y < maze.height - 1:
            sets: Dict[int, List[int]] = {}
            for x in range(maze.width):
                root = find(y * maze.width + x)
                sets.setdefault(root, []).append(x)
            for members in sets.values():
                maze.rng.shuffle(members)
                n_connect = maze.rng.randint(1, len(members))
                for x in members[:n_connect]:
                    ci = y * maze.width + x
                    ni = (y + 1) * maze.width + x
                    union(ci, ni)
                    maze.remove_wall(maze.cells[y][x], maze.cells[y + 1][x])


# --------------------------------------------------------------------------- #
# Wilson's
# --------------------------------------------------------------------------- #


def gen_wilsons(maze) -> None:
    """Wilson's algorithm: uniform spanning tree via loop-erased walks."""
    start = maze.cells[0][0]
    start.visited = True
    remaining = maze.width * maze.height - 1
    while remaining > 0:
        # Pick a random unvisited cell.
        while True:
            x = maze.rng.randrange(maze.width)
            y = maze.rng.randrange(maze.height)
            if not maze.cells[y][x].visited:
                break
        # Loop-erased random walk until we hit the visited set.
        path: List[Cell] = [maze.cells[y][x]]
        direction_from: Dict[Cell, Direction] = {}
        current = maze.cells[y][x]
        while not current.visited:
            neighbors = maze.neighbors(current)
            neighbor, direction = maze.rng.choice(neighbors)
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
            maze.remove_wall(cell_a, cell_b)
        if not path[-1].visited:
            path[-1].visited = True
            remaining -= 1


# --------------------------------------------------------------------------- #
# Binary Tree
# --------------------------------------------------------------------------- #


def gen_binary_tree(maze) -> None:
    """Binary tree algorithm: for each cell, randomly carve north or east.

    Produces a biased maze with a diagonal bias and a straight corridor
    along the top and right edges.
    """
    for y in range(maze.height):
        for x in range(maze.width):
            cell = maze.cells[y][x]
            choices: List[Direction] = []
            if y > 0:
                choices.append(Direction.NORTH)
            if x < maze.width - 1:
                choices.append(Direction.EAST)
            if not choices:
                continue
            d = maze.rng.choice(choices)
            nx, ny = cell.x + d.dx, cell.y + d.dy
            maze.remove_wall(cell, maze.cells[ny][nx])


# --------------------------------------------------------------------------- #
# Sidewinder
# --------------------------------------------------------------------------- #


def gen_sidewinder(maze) -> None:
    """Sidewinder algorithm: run-based generation with upward carves."""
    for y in range(maze.height):
        run: List[Cell] = []
        for x in range(maze.width):
            cell = maze.cells[y][x]
            run.append(cell)
            at_east_boundary = x == maze.width - 1
            at_north_boundary = y == 0
            if at_east_boundary or (
                not at_north_boundary and maze.rng.random() < 0.5
            ):
                # Close the run: carve north from a random cell.
                if not at_north_boundary:
                    chosen = maze.rng.choice(run)
                    nx, ny = chosen.x, chosen.y - 1
                    maze.remove_wall(chosen, maze.cells[ny][nx])
                run = []
            else:
                # Extend the run eastward.
                if not at_east_boundary:
                    maze.remove_wall(cell, maze.cells[y][x + 1])


# --------------------------------------------------------------------------- #
# Aldous-Broder
# --------------------------------------------------------------------------- #


def gen_aldous_broder(maze) -> None:
    """Aldous-Broder algorithm: uniform spanning tree via random walk.

    Visits every cell by performing a random walk.  When the walk
    enters an unvisited cell, the wall between the previous cell and
    the new cell is removed.  Produces a uniform spanning tree (like
    Wilson's) but with no memory of the path — simpler but potentially
    slow on large mazes since the walk may revisit cells many times.
    """
    start = maze.cells[0][0]
    start.visited = True
    remaining = maze.width * maze.height - 1
    current = start
    while remaining > 0:
        neighbors = maze.neighbors(current)
        neighbor, _ = maze.rng.choice(neighbors)
        if not neighbor.visited:
            maze.remove_wall(current, neighbor)
            neighbor.visited = True
            remaining -= 1
        current = neighbor


# --------------------------------------------------------------------------- #
# Recursive Division
# --------------------------------------------------------------------------- #


def gen_recursive_division(maze) -> None:
    """Recursive division algorithm.

    Starts with an empty (wall-less) interior and recursively adds walls
    with a single passage hole until every cell is separated.  Unlike
    the other generators which *remove* walls from a fully-walled grid,
    this one *adds* walls to a fully-open grid.  Border walls are
    re-added to produce a proper maze.
    """
    # Start with all walls removed (fully open).
    for cell in maze.all_cells():
        cell.walls = set()
    # Re-add border walls.
    for x in range(maze.width):
        maze.cells[0][x].walls.add(Direction.NORTH)
        maze.cells[maze.height - 1][x].walls.add(Direction.SOUTH)
    for y in range(maze.height):
        maze.cells[y][0].walls.add(Direction.WEST)
        maze.cells[y][maze.width - 1].walls.add(Direction.EAST)
    _divide(maze, 0, 0, maze.width, maze.height)


def _divide(maze, x: int, y: int, w: int, h: int) -> None:
    """Recursively divide the region (x, y, w, h) with walls + holes."""
    if w < 2 or h < 2:
        return
    # Choose orientation: horizontal if h > w, vertical if w > h,
    # random if square.
    if h > w:
        horizontal = True
    elif w > h:
        horizontal = False
    else:
        horizontal = maze.rng.random() < 0.5

    if horizontal:
        # Wall line between row (y + wall_y) and (y + wall_y + 1).
        wall_y = maze.rng.randrange(y, y + h - 1)
        # Hole position along the wall.
        hole_x = maze.rng.randrange(x, x + w)
        for cx in range(x, x + w):
            if cx == hole_x:
                continue
            top = maze.cells[wall_y][cx]
            bottom = maze.cells[wall_y + 1][cx]
            maze.add_wall(top, bottom)
        # Recurse into the two sub-regions.
        _divide(maze, x, y, w, wall_y - y + 1)
        _divide(maze, x, wall_y + 1, w, h - (wall_y - y + 1))
    else:
        # Wall line between column (x + wall_x) and (x + wall_x + 1).
        wall_x = maze.rng.randrange(x, x + w - 1)
        hole_y = maze.rng.randrange(y, y + h)
        for cy in range(y, y + h):
            if cy == hole_y:
                continue
            left = maze.cells[cy][wall_x]
            right = maze.cells[cy][wall_x + 1]
            maze.add_wall(left, right)
        _divide(maze, x, y, wall_x - x + 1, h)
        _divide(maze, wall_x + 1, y, w - (wall_x - x + 1), h)