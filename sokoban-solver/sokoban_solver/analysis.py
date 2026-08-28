"""Static analysis and reachability helpers for Sokoban boards."""

from __future__ import annotations

from collections import deque
from functools import lru_cache

from .constants import DIRECTIONS
from .models import Board, Coord


def reachable_with_paths(start: Coord, boxes: frozenset[Coord], board: Board) -> tuple[set[Coord], dict[Coord, str]]:
    """Return every reachable player tile and the shortest walk string to it."""

    seen = {start}
    paths = {start: ""}
    queue = deque([start])
    blocked = board.walls | boxes
    walkable = board.floor | board.goals
    while queue:
        r, c = queue.popleft()
        for name, dr, dc in DIRECTIONS:
            nxt = (r + dr, c + dc)
            if nxt in seen or nxt in blocked or nxt not in walkable:
                continue
            seen.add(nxt)
            paths[nxt] = paths[(r, c)] + name.lower()
            queue.append(nxt)
    return seen, paths


def reachable_cells(start: Coord, boxes: frozenset[Coord], board: Board) -> frozenset[Coord]:
    return frozenset(reachable_with_paths(start, boxes, board)[0])


def compute_corner_deadlocks(board: Board) -> frozenset[Coord]:
    walkable = board.floor | board.goals
    deadlocks: set[Coord] = set()
    for pos in walkable:
        if pos in board.goals:
            continue
        up = (pos[0] - 1, pos[1]) in board.walls
        down = (pos[0] + 1, pos[1]) in board.walls
        left = (pos[0], pos[1] - 1) in board.walls
        right = (pos[0], pos[1] + 1) in board.walls
        if (up or down) and (left or right):
            deadlocks.add(pos)
    return frozenset(deadlocks)


def compute_dead_squares(board: Board) -> frozenset[Coord]:
    """Reverse-pull analysis for squares no box can ever leave into a goal."""

    walkable = board.floor | board.goals
    live: set[Coord] = set(board.goals)
    queue = deque(board.goals)
    while queue:
        box = queue.popleft()
        for _, dr, dc in DIRECTIONS:
            prev_box = (box[0] - dr, box[1] - dc)
            player_support = (prev_box[0] - dr, prev_box[1] - dc)
            if prev_box not in walkable or player_support not in walkable:
                continue
            if prev_box in live:
                continue
            live.add(prev_box)
            queue.append(prev_box)
    return frozenset(pos for pos in walkable if pos not in live and pos not in board.goals)


def is_static_deadlock(boxes: frozenset[Coord], goals: frozenset[Coord], corner_deadlocks: frozenset[Coord], dead_squares: frozenset[Coord]) -> bool:
    for box in boxes:
        if box not in goals and (box in corner_deadlocks or box in dead_squares):
            return True
    return False


@lru_cache(maxsize=None)
def assignment_lower_bound(boxes: tuple[Coord, ...], goals: tuple[Coord, ...]) -> int:
    """Exact minimum bipartite Manhattan matching via bitmask DP."""

    if len(boxes) != len(goals):
        raise ValueError("boxes and goals must have matching cardinality")
    if not boxes:
        return 0

    costs = [
        [abs(br - gr) + abs(bc - gc) for gr, gc in goals]
        for br, bc in boxes
    ]

    @lru_cache(maxsize=None)
    def dp(i: int, used_mask: int) -> int:
        if i == len(boxes):
            return 0
        best = 10**9
        for goal_idx in range(len(goals)):
            if used_mask & (1 << goal_idx):
                continue
            total = costs[i][goal_idx] + dp(i + 1, used_mask | (1 << goal_idx))
            if total < best:
                best = total
        return best

    return dp(0, 0)


def render_explain_overlay(
    board: Board,
    *,
    reachable: frozenset[Coord],
    corner_deadlocks: frozenset[Coord],
    dead_squares: frozenset[Coord],
) -> str:
    """Render an annotated board for human debugging.

    Legend:
    - `x`: reverse-pull dead square
    - `c`: corner deadlock square
    - `·`: reachable empty floor tile
    """

    overlay: dict[Coord, str] = {}
    for pos in reachable:
        if pos not in board.goals and pos != board.player and pos not in board.boxes:
            overlay[pos] = "·"
    for pos in corner_deadlocks:
        if pos not in board.goals and pos != board.player and pos not in board.boxes:
            overlay[pos] = "c"
    for pos in dead_squares:
        if pos not in board.goals and pos != board.player and pos not in board.boxes:
            overlay[pos] = "x"
    return board.render(overlay=overlay)
