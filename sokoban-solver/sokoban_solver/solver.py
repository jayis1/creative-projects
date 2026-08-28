"""A* Sokoban solver with dead-square pruning and replay support."""

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
DIRMAP = {name: (dr, dc) for name, dr, dc in DIRECTIONS}


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
        self.corner_deadlocks = self._compute_corner_deadlocks()
        self.dead_squares = self._compute_dead_squares()

    def solve(self, *, max_states: int = 200_000) -> SolveResult:
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
        reachable = self._reachable_cells(self.board.player, self.board.boxes)
        return {
            "title": self.board.title,
            "dimensions": [self.board.height, self.board.width],
            "boxes": len(self.board.boxes),
            "goals": len(self.board.goals),
            "reachable_floor_tiles": len(reachable),
            "corner_deadlocks": sorted(self.corner_deadlocks),
            "dead_squares": sorted(self.dead_squares),
            "solved": self.board.is_solved(),
        }

    def replay(self, result: SolveResult) -> tuple[str, ...]:
        """Render each post-push state of a solution."""
        frames = [self.board.render()]
        path_cells = self._path_cells(result)
        for step in result.steps:
            frames.append(self.board.render(player=step.player_after, boxes=step.boxes, path_cells=path_cells))
        return tuple(frames)

    def _priority(self, state: State, pushes: int, player_steps: int) -> tuple[int, int, int]:
        heuristic = self._heuristic(state.boxes)
        return pushes + heuristic, player_steps + heuristic, heuristic

    def _heuristic(self, boxes: frozenset[Coord]) -> int:
        boxes_list = sorted(boxes)
        goals_list = sorted(self.board.goals)
        if len(boxes_list) <= 6:
            best = None
            for perm in permutations(goals_list):
                total = sum(abs(br - gr) + abs(bc - gc) for (br, bc), (gr, gc) in zip(boxes_list, perm, strict=True))
                if best is None or total < best:
                    best = total
            return 0 if best is None else best
        return sum(min(abs(br - gr) + abs(bc - gc) for gr, gc in goals_list) for br, bc in boxes_list)

    def _push_successors(self, state: State):
        reachable, paths = self._reachable_with_paths(state.player, state.boxes)
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

    def _reachable_cells(self, start: Coord, boxes: frozenset[Coord]) -> frozenset[Coord]:
        return frozenset(self._reachable_with_paths(start, boxes)[0])

    def _reachable_with_paths(self, start: Coord, boxes: frozenset[Coord]) -> tuple[set[Coord], dict[Coord, str]]:
        seen = {start}
        paths = {start: ""}
        queue = deque([start])
        blocked = self.board.walls | boxes
        while queue:
            r, c = queue.popleft()
            for name, dr, dc in DIRECTIONS:
                nxt = (r + dr, c + dc)
                if nxt in seen or nxt in blocked or nxt not in self.walkable:
                    continue
                seen.add(nxt)
                paths[nxt] = paths[(r, c)] + name.lower()
                queue.append(nxt)
        return seen, paths

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

    def _compute_dead_squares(self) -> frozenset[Coord]:
        """Reverse-pull analysis for squares no box can ever leave into a goal.

        A tile is live if a hypothetical box placed there can be pulled to some
        goal while the player stands behind the box. All non-live non-goal tiles
        are static dead squares.
        """
        live: set[Coord] = set(self.board.goals)
        queue = deque(self.board.goals)
        while queue:
            box = queue.popleft()
            for _, dr, dc in DIRECTIONS:
                prev_box = (box[0] - dr, box[1] - dc)
                player_support = (prev_box[0] - dr, prev_box[1] - dc)
                if prev_box not in self.walkable or player_support not in self.walkable:
                    continue
                if prev_box in live:
                    continue
                live.add(prev_box)
                queue.append(prev_box)
        return frozenset(pos for pos in self.walkable if pos not in live and pos not in self.board.goals)

    def _is_deadlock(self, boxes: frozenset[Coord]) -> bool:
        for box in boxes:
            if box not in self.board.goals and (box in self.corner_deadlocks or box in self.dead_squares):
                return True
        return False

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
