"""A* Sokoban solver with dead-square pruning, overlays, and pack helpers."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from typing import Any

from .analysis import (
    assignment_lower_bound,
    compute_corner_deadlocks,
    compute_dead_squares,
    is_static_deadlock,
    reachable_cells,
    reachable_with_paths,
    render_explain_overlay,
)
from .constants import DIRMAP, DIRECTIONS
from .io import LevelEntry
from .models import Board, Coord, SolutionStep, SolveResult, Stats
from .parser import parse_level


@dataclass(frozen=True)
class State:
    player: Coord
    boxes: frozenset[Coord]


class SokobanSolver:
    """Solve Sokoban levels using push-aware A* search.

    Search cost is lexicographic on `(pushes, player_steps)`, which keeps
    solutions push-efficient while preferring shorter walks among equal-push
    candidates.
    """

    def __init__(self, board: Board) -> None:
        self.board = board
        self.walkable = board.floor | board.goals
        self.corner_deadlocks = compute_corner_deadlocks(board)
        self.dead_squares = compute_dead_squares(board)
        self._heuristic_cache: dict[frozenset[Coord], int] = {}

    def solve(self, *, max_states: int = 200_000) -> SolveResult:
        if max_states <= 0:
            raise ValueError("max_states must be positive")

        start = State(self.board.player, self.board.boxes)
        if self.board.is_solved(start.boxes):
            stats = Stats(0, 0, 1, 1, 0, 0, 1, 0)
            return SolveResult(True, "", "", tuple(), stats, "already solved")

        frontier: list[tuple[int, int, int, int, State]] = []
        sequence = count()
        start_cost = (0, 0)
        heappush(frontier, (*self._priority(start, *start_cost), next(sequence), start))
        parents: dict[State, tuple[State | None, SolutionStep | None]] = {start: (None, None)}
        best_cost: dict[State, tuple[int, int]] = {start: start_cost}
        explored_states = 0
        generated_states = 1
        deadlocks_pruned = 0
        repeated_states = 0
        frontier_max = 1

        while frontier:
            frontier_max = max(frontier_max, len(frontier))
            _, _, _, _, state = heappop(frontier)
            pushes, player_steps = best_cost[state]
            explored_states += 1
            if explored_states > max_states:
                stats = Stats(pushes, player_steps, explored_states, generated_states, deadlocks_pruned, repeated_states, frontier_max, 0)
                return SolveResult(False, "", "", tuple(), stats, f"search limit reached ({max_states})")
            if self.board.is_solved(state.boxes):
                steps, moves, pushes_str = self._reconstruct(state, parents)
                stats = Stats(
                    pushes=len(pushes_str),
                    player_steps=len(moves),
                    explored_states=explored_states,
                    generated_states=generated_states,
                    deadlocks_pruned=deadlocks_pruned,
                    repeated_states=repeated_states,
                    frontier_max=frontier_max,
                    solved_depth=len(steps),
                )
                return SolveResult(True, moves, pushes_str, steps, stats, "solved")

            for next_state, step in self._push_successors(state):
                new_cost = (pushes + 1, player_steps + len(step.walk_path) + 1)
                if self._is_deadlock(next_state.boxes):
                    deadlocks_pruned += 1
                    continue
                old_cost = best_cost.get(next_state)
                if old_cost is not None and new_cost >= old_cost:
                    repeated_states += 1
                    continue
                best_cost[next_state] = new_cost
                parents[next_state] = (state, step)
                generated_states += 1
                heappush(frontier, (*self._priority(next_state, *new_cost), next(sequence), next_state))

        stats = Stats(0, 0, explored_states, generated_states, deadlocks_pruned, repeated_states, frontier_max, 0)
        return SolveResult(False, "", "", tuple(), stats, "no solution found")

    def analyze(self) -> dict[str, object]:
        reachable = reachable_cells(self.board.player, self.board.boxes, self.board)
        return {
            "title": self.board.title,
            "dimensions": [self.board.height, self.board.width],
            "boxes": len(self.board.boxes),
            "goals": len(self.board.goals),
            "reachable_floor_tiles": len(reachable),
            "corner_deadlocks": sorted(self.corner_deadlocks),
            "dead_squares": sorted(self.dead_squares),
            "dead_square_count": len(self.dead_squares),
            "heuristic_lower_bound": self._heuristic(self.board.boxes),
            "solved": self.board.is_solved(),
        }

    def explain(self) -> dict[str, object]:
        reachable = reachable_cells(self.board.player, self.board.boxes, self.board)
        payload = self.analyze()
        payload["legend"] = {"#": "wall", ".": "goal", "$": "box", "@": "player", "c": "corner deadlock", "x": "dead square", "·": "reachable floor"}
        payload["overlay"] = render_explain_overlay(
            self.board,
            reachable=reachable,
            corner_deadlocks=self.corner_deadlocks,
            dead_squares=self.dead_squares,
        )
        return payload

    def replay(self, result: SolveResult) -> tuple[str, ...]:
        """Render each post-push state of a solution."""

        frames = [self.board.render()]
        path_cells = self._path_cells(result)
        for step in result.steps:
            frames.append(self.board.render(player=step.player_after, boxes=step.boxes, path_cells=path_cells))
        return tuple(frames)

    def export_solution(self, result: SolveResult, *, include_frames: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "board": {"title": self.board.title, "width": self.board.width, "height": self.board.height},
            "solved": result.solved,
            "reason": result.reason,
            "move_sequence": result.move_sequence,
            "push_sequence": result.push_sequence,
            "pushes": result.pushes,
            "stats": {
                "pushes": result.stats.pushes,
                "player_steps": result.stats.player_steps,
                "explored_states": result.stats.explored_states,
                "generated_states": result.stats.generated_states,
                "deadlocks_pruned": result.stats.deadlocks_pruned,
                "repeated_states": result.stats.repeated_states,
                "frontier_max": result.stats.frontier_max,
                "solved_depth": result.stats.solved_depth,
            },
            "steps": [
                {
                    "move": step.move,
                    "walk_path": step.walk_path,
                    "player_before": list(step.player_before),
                    "player_after": list(step.player_after),
                    "pushed_box_from": list(step.pushed_box_from) if step.pushed_box_from else None,
                    "pushed_box_to": list(step.pushed_box_to) if step.pushed_box_to else None,
                    "boxes": [list(box) for box in sorted(step.boxes)],
                }
                for step in result.steps
            ],
        }
        if include_frames:
            payload["frames"] = list(self.replay(result))
        return payload

    def _priority(self, state: State, pushes: int, player_steps: int) -> tuple[int, int, int]:
        heuristic = self._heuristic(state.boxes)
        return pushes + heuristic, player_steps + heuristic, heuristic

    def _heuristic(self, boxes: frozenset[Coord]) -> int:
        cached = self._heuristic_cache.get(boxes)
        if cached is not None:
            return cached
        value = assignment_lower_bound(tuple(sorted(boxes)), tuple(sorted(self.board.goals)))
        self._heuristic_cache[boxes] = value
        return value

    def _push_successors(self, state: State):
        reachable, paths = reachable_with_paths(state.player, state.boxes, self.board)
        for pr, pc in reachable:
            for move, dr, dc in DIRECTIONS:
                box = (pr + dr, pc + dc)
                if box not in state.boxes:
                    continue
                target = (box[0] + dr, box[1] + dc)
                if target not in self.walkable or target in state.boxes:
                    continue
                new_boxes = set(state.boxes)
                new_boxes.remove(box)
                new_boxes.add(target)
                walk_path = paths[(pr, pc)]
                yield State(box, frozenset(new_boxes)), SolutionStep(
                    move=move,
                    walk_path=walk_path,
                    player_before=state.player,
                    player_after=box,
                    boxes=frozenset(new_boxes),
                    pushed_box_from=box,
                    pushed_box_to=target,
                )

    def _is_deadlock(self, boxes: frozenset[Coord]) -> bool:
        return is_static_deadlock(boxes, self.board.goals, self.corner_deadlocks, self.dead_squares)

    def _reconstruct(self, state: State, parents: dict[State, tuple[State | None, SolutionStep | None]]):
        path: list[SolutionStep] = []
        moves: list[str] = []
        pushes: list[str] = []
        cursor = state
        while True:
            parent, step = parents[cursor]
            if parent is None or step is None:
                break
            moves.append(step.walk_path + step.move)
            pushes.append(step.move)
            path.append(step)
            cursor = parent
        path.reverse()
        moves.reverse()
        pushes.reverse()
        return tuple(path), "".join(moves), "".join(pushes)

    def _path_cells(self, result: SolveResult) -> frozenset[Coord]:
        pos = self.board.player
        path_cells: set[Coord] = {pos}
        for ch in result.move_sequence:
            dr, dc = DIRMAP[ch.upper()]
            pos = (pos[0] + dr, pos[1] + dc)
            path_cells.add(pos)
        return frozenset(path_cells)


def solve_level_pack(entries: tuple[LevelEntry, ...], *, max_states: int = 200_000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        board = parse_level(entry.text, title=entry.title)
        solver = SokobanSolver(board)
        result = solver.solve(max_states=max_states)
        rows.append(
            {
                "level": entry.title,
                "solved": result.solved,
                "reason": result.reason,
                "pushes": result.pushes,
                "player_steps": result.stats.player_steps,
                "explored_states": result.stats.explored_states,
                "deadlocks_pruned": result.stats.deadlocks_pruned,
                "move_sequence": result.move_sequence,
            }
        )
    return rows
