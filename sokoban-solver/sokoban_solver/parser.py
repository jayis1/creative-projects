"""Parsing utilities for Sokoban level text."""

from __future__ import annotations

from .models import Board, Coord

VALID_TILES = {"#", " ", ".", "$", "*", "@", "+"}


def parse_level(text: str, *, title: str = "untitled") -> Board:
    """Parse a Sokoban level from an ASCII map.

    Supported symbols follow the de facto convention:

    - `#`: wall
    - ` `: floor
    - `.`: goal
    - `$`: box on floor
    - `*`: box on goal
    - `@`: player on floor
    - `+`: player on goal
    """

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
        padded = line.ljust(width)
        for c, ch in enumerate(padded):
            if ch not in VALID_TILES:
                raise ValueError(f"invalid tile {ch!r} at {(r, c)}")
            pos = (r, c)
            if ch == "#":
                walls.add(pos)
                continue
            if ch in {" ", ".", "$", "*", "@", "+"}:
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
    if issues:
        raise ValueError("; ".join(issues))
    return board
