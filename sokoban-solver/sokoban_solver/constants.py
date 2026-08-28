"""Shared constants for Sokoban movement and rendering."""

from __future__ import annotations

DIRECTIONS: tuple[tuple[str, int, int], ...] = (
    ("U", -1, 0),
    ("D", 1, 0),
    ("L", 0, -1),
    ("R", 0, 1),
)

DIRMAP: dict[str, tuple[int, int]] = {name: (dr, dc) for name, dr, dc in DIRECTIONS}
