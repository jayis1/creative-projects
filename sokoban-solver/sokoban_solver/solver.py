"""A* Sokoban solver with simple static deadlock pruning."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count, permutations

from .models import Board, Coord, SolutionStep, SolveResult, Stats

DIRECTIONS: tuple[tuple[str, int, int], ...] = (
    ("U", -1, 0),
    ("D", 1, 0),
    ("L", 0, -1),
    ("R", 0, 1),
)


@dataclass(frozen=True)
class State:
    player: Coord
    boxes: frozenset[Coord]


class SokobanSolver:
    """Solve Sokoban levels using push-aware A* search."""

    def __init__(self, board: Board) -> None:
        self.board = board
        self.walkable = board.floor | board.goals
        self.corner_deadlocks = self._compute_corner_deadlocks()

    def solve(self, *, max_states: int = 200_000) -> SolveResult:
        start = State(self.board.player, self.board.boxes)
        if self.board.is_solved(start.boxes):
            stats = Stats(0, 0, 1, 1, 0, 0, 1)
            return SolveResult(True, "", tuple(), stats, "already solved")

        frontier: list[tuple[int, int, int, State]] = []
        sequence = count()
        heappush(frontier, (self._priority(start, 0), 0, next(sequence), start))
        parents: dict[State, tuple[State | None, str | None, Coord | None, Coord | None]] = {
            start: (None, None, None, None)
        }
        best_cost: dict[State, int] = {start: 0}
        explored_states = 0
        generated_states = 1
        deadlocks_pruned = 0
        repeated_states = 0
        frontier_max = 1

        while frontier:
            frontier_max = max(frontier_max, len(frontier))
            _, pushes, _, state = heappop(frontier)
            if pushes != best_cost.get(state):
                continue
            explored_states += 1
            if explored_states > max_states:
                stats = Stats(pushes, 0, explored_states, generated_states, deadlocks_pruned, repeated_states, frontier_max)
                return SolveResult(False, "", tuple(), stats, f"search limit reached ({max_states})")
            if self.board.is_solved(state.boxes):
                steps, moves = self._reconstruct(state, parents)
                stats = Stats(sum(1 for step in steps if step.pushed_box_to), len(moves), explored_states, generated_states, deadlocks_pruned, repeated_states, frontier_max)
                return SolveResult(True, moves, steps, stats, "solved")

            for move, next_state, pushed_from, pushed_to in self._successors(state):
                new_pushes = pushes + (1 if pushed_to is not None else 0)
                if pushed_to is not None and self._is_deadlock(next_state.boxes):
                    deadlocks_pruned += 1
                    continue
                old_cost = best_cost.get(next_state)
                if old_cost is not None and new_pushes >= old_cost:
                    repeated_states += 1
                    continue
                best_cost[next_state] = new_pushes
                parents[next_state] = (state, move, pushed_from, pushed_to)
                generated_states += 1
                heappush(frontier, (self._priority(next_state, new_pushes), new_pushes, next(sequence), next_state))

        stats = Stats(0, 0, explored_states, generated_states, deadlocks_pruned, repeated_states, frontier_max)
        return SolveResult(False, "", tuple(), stats, "no solution found")

    def analyze(self) -> dict[str, object]:
        reachable = self._reachable_cells(self.board.player, self.board.boxes)
        return {
            "title": self.board.title,
            "dimensions": [self.board.height, self.board.width],
            "boxes": len(self.board.boxes),
            "goals": len(self.board.goals),
            "reachable_floor_tiles": len(reachable),
            "corner_deadlocks": sorted(self.corner_deadlocks),
        }

    def _priority(self, state: State, pushes: int) -> int:
        return pushes * 10 + self._heuristic(state.boxes)

    def _heuristic(self, boxes: frozenset[Coord]) -> int:
        boxes_list = list(boxes)
        goals_list = list(self.board.goals)
        if len(boxes_list) <= 6:
            best = None
            for perm in permutations(goals_list):
                total = sum(abs(br - gr) + abs(bc - gc) for (br, bc), (gr, gc) in zip(boxes_list, perm, strict=True))
                if best is None or total < best:
                    best = total
            return 0 if best is None else best
        total = 0
        for br, bc in boxes_list:
            total += min(abs(br - gr) + abs(bc - gc) for gr, gc in goals_list)
        return total

    def _successors(self, state: State):
        reachable = self._reachable_cells(state.player, state.boxes)
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
                yield move, State(box, frozenset(new_boxes)), box, target

    def _reachable_cells(self, start: Coord, boxes: frozenset[Coord]) -> frozenset[Coord]:
        seen = {start}
        queue = deque([start])
        blocked = self.board.walls | boxes
        while queue:
            r, c = queue.popleft()
            for _, dr, dc in DIRECTIONS:
                nxt = (r + dr, c + dc)
                if nxt in seen or nxt in blocked or nxt not in self.walkable:
                    continue
                seen.add(nxt)
                queue.append(nxt)
        return frozenset(seen)

    def _compute_corner_deadlocks(self) -> frozenset[Coord]:
        deadlocks: set[Coord] = set()
        for pos in self.walkable:
            if pos in self.board.goals:
                continue
            up = (pos[0] - 1, pos[1]) in self.board.walls
            down = (pos[0] + 1, pos[1]) in self.board.walls
            left = (pos[0], pos[1] - 1) in self.board.walls
            right = (pos[0], pos[1] + 1) in self.board.walls
            if (up or down) and (left or right):
                deadlocks.add(pos)
        return frozenset(deadlocks)

    def _is_deadlock(self, boxes: frozenset[Coord]) -> bool:
        for box in boxes:
            if box in self.corner_deadlocks and box not in self.board.goals:
                return True
        return False

    def _reconstruct(self, state: State, parents):
        path: list[SolutionStep] = []
        moves: list[str] = []
        cursor = state
        while True:
            parent, move, pushed_from, pushed_to = parents[cursor]
            if parent is None or move is None:
                break
            moves.append(move)
            path.append(
                SolutionStep(
                    move=move,
                    player=cursor.player,
                    boxes=cursor.boxes,
                    pushed_box_from=pushed_from,
                    pushed_box_to=pushed_to,
                )
            )
            cursor = parent
        path.reverse()
        moves.reverse()
        return tuple(path), "".join(moves)
