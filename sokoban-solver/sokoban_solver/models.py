"""Core data models for Sokoban boards and solver output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

Coord = tuple[int, int]


@dataclass(frozen=True)
class Board:
    """Immutable Sokoban board description.

    Coordinates use `(row, column)` order.
    """

    width: int
    height: int
    walls: frozenset[Coord]
    goals: frozenset[Coord]
    boxes: frozenset[Coord]
    player: Coord
    floor: frozenset[Coord]
    title: str = "untitled"

    def render(
        self,
        *,
        player: Coord | None = None,
        boxes: Iterable[Coord] | None = None,
        path_cells: frozenset[Coord] | None = None,
    ) -> str:
        """Render the board to an ASCII string."""
        player = self.player if player is None else player
        boxes_set = self.boxes if boxes is None else frozenset(boxes)
        path_cells = frozenset() if path_cells is None else path_cells
        rows: list[str] = []
        for r in range(self.height):
            chars: list[str] = []
            for c in range(self.width):
                pos = (r, c)
                if pos in self.walls:
                    chars.append("#")
                elif pos == player:
                    chars.append("+" if pos in self.goals else "@")
                elif pos in boxes_set:
                    chars.append("*" if pos in self.goals else "$")
                elif pos in path_cells:
                    chars.append("·")
                elif pos in self.goals:
                    chars.append(".")
                elif pos in self.floor:
                    chars.append(" ")
                else:
                    chars.append(" ")
            rows.append("".join(chars).rstrip())
        return "\n".join(rows)

    def is_solved(self, boxes: frozenset[Coord] | None = None) -> bool:
        boxes = self.boxes if boxes is None else boxes
        return boxes == self.goals

    def validate(self) -> list[str]:
        issues: list[str] = []
        if not self.goals:
            issues.append("board has no goals")
        if len(self.goals) != len(self.boxes):
            issues.append("number of boxes must equal number of goals")
        if self.player in self.walls:
            issues.append("player cannot start inside a wall")
        if self.player not in self.floor and self.player not in self.goals:
            issues.append("player must start on a traversable tile")
        for box in self.boxes:
            if box in self.walls:
                issues.append(f"box at {box} overlaps a wall")
        for goal in self.goals:
            if goal in self.walls:
                issues.append(f"goal at {goal} overlaps a wall")
        return issues


@dataclass(frozen=True)
class Stats:
    pushes: int
    player_steps: int
    explored_states: int
    generated_states: int
    deadlocks_pruned: int
    repeated_states: int
    frontier_max: int


@dataclass(frozen=True)
class SolutionStep:
    move: str
    player: Coord
    boxes: frozenset[Coord]
    pushed_box_from: Coord | None = None
    pushed_box_to: Coord | None = None


@dataclass(frozen=True)
class SolveResult:
    solved: bool
    move_sequence: str
    steps: tuple[SolutionStep, ...]
    stats: Stats
    reason: str

    @property
    def pushes(self) -> int:
        return sum(1 for step in self.steps if step.pushed_box_to is not None)
