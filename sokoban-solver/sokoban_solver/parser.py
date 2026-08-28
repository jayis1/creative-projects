"""Parsing utilities for Sokoban level text."""

from __future__ import annotations

from collections import deque

from .models import Board, Coord

VALID_TILES = {"#", " ", ".", "$", "*", "@", "+"}


def parse_level(text: str, *, title: str = "untitled") -> Board:
    """Parse a Sokoban level from an ASCII map."""

    lines = [line.rstrip("\n") for line in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise ValueError("level text is empty")

    width = max(len(line) for line in lines)
    height = len(lines)
    walls: set[Coord] = set()
    goals: set[Coord] = set()
    boxes: set[Coord] = set()
    floor: set[Coord] = set()
    player: Coord | None = None

    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            if ch not in VALID_TILES:
                raise ValueError(f"invalid tile {ch!r} at {(r, c)}")
            pos = (r, c)
            if ch == "#":
                walls.add(pos)
                continue
            floor.add(pos)
            if ch in {".", "*", "+"}:
                goals.add(pos)
            if ch in {"$", "*"}:
                boxes.add(pos)
            if ch in {"@", "+"}:
                if player is not None:
                    raise ValueError("level has multiple player positions")
                player = pos

    if player is None:
        raise ValueError("level has no player")

    board = Board(
        width=width,
        height=height,
        walls=frozenset(walls),
        goals=frozenset(goals),
        boxes=frozenset(boxes),
        player=player,
        floor=frozenset(floor),
        title=title,
    )
    issues = board.validate()
    issues.extend(_topology_issues(board))
    if issues:
        raise ValueError("; ".join(issues))
    return board


def _topology_issues(board: Board) -> list[str]:
    """Catch disconnected or obviously malformed traversable regions."""

    issues: list[str] = []
    seen = {board.player}
    queue = deque([board.player])
    walkable = board.floor | board.goals
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nxt = (r + dr, c + dc)
            if nxt in seen or nxt not in walkable or nxt in board.walls:
                continue
            seen.add(nxt)
            queue.append(nxt)

    unreachable_boxes = sorted(box for box in board.boxes if box not in seen)
    unreachable_goals = sorted(goal for goal in board.goals if goal not in seen)
    if unreachable_boxes:
        issues.append(f"unreachable boxes from player start: {unreachable_boxes}")
    if unreachable_goals:
        issues.append(f"unreachable goals from player start: {unreachable_goals}")

    open_edges = _count_open_edges(board)
    if open_edges > 0:
        issues.append(f"board has {open_edges} traversable edge tile(s); levels should usually be walled in")
    return issues


def _count_open_edges(board: Board) -> int:
    edge_count = 0
    for r, c in board.floor | board.goals:
        if r in {0, board.height - 1} or c in {0, board.width - 1}:
            edge_count += 1
    return edge_count
