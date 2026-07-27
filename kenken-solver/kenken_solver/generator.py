"""KenKen puzzle generator with guaranteed unique solutions.

Strategy
--------

1. **Random Latin square** — a base cyclic Latin square is constructed, then
   randomized via independent row, column, and symbol permutations.
2. **Cage partitioning** — starting from random seed cells, cages grow by
   absorbing unassigned orthogonal neighbors until reaching a random size.
3. **Operator selection** — for each cage, all valid ``(operator, target)``
   pairs are computed from the solution values. A weighted random choice is
   made based on the difficulty level.
4. **Uniqueness verification** — the solver is invoked with
   ``max_solutions=2``. If exactly one solution exists, the puzzle is
   accepted; otherwise the process repeats.
"""

from __future__ import annotations

import logging
import random
from itertools import permutations
from typing import List, Optional, Set, Tuple

from kenken_solver.cage import Cage
from kenken_solver.puzzle import KenKenPuzzle
from kenken_solver.solver import KenKenSolver
from kenken_solver.types import Cell, neighbors

logger = logging.getLogger(__name__)


class KenKenGenerator:
    """Generates KenKen puzzles with unique solutions.

    Parameters
    ----------
    size:
        Grid dimension (the puzzle will be *size*×*size*).
    seed:
        Optional random seed for reproducibility.
    max_cage_size:
        Maximum number of cells in a single cage (default 4).
    difficulty:
        One of ``"easy"``, ``"medium"``, or ``"hard"`` — influences the
        operator weighting.
    allow_singletons:
        Whether to allow single-cell cages (default ``True``).
    """

    def __init__(
        self,
        size: int,
        seed: Optional[int] = None,
        max_cage_size: int = 4,
        difficulty: str = "medium",
        allow_singletons: bool = True,
    ) -> None:
        self.size: int = size
        self.max_cage_size: int = max_cage_size
        self.difficulty: str = difficulty
        self.allow_singletons: bool = allow_singletons
        self.rng: random.Random = random.Random(seed)
        self._solution: Optional[List[List[int]]] = None

    # -- Latin square generation -----------------------------------------

    def _random_latin_square(self) -> List[List[int]]:
        """Generate a random Latin square of order *size*.

        Builds a base cyclic Latin square, then applies independent random
        permutations of rows, columns, and symbols.
        """
        n = self.size
        base = [[((r + c) % n) + 1 for c in range(n)] for r in range(n)]
        rows = list(range(n))
        cols = list(range(n))
        syms = list(range(1, n + 1))
        self.rng.shuffle(rows)
        self.rng.shuffle(cols)
        self.rng.shuffle(syms)
        sym_map = {i + 1: syms[i] for i in range(n)}
        return [
            [sym_map[base[rows[r]][cols[c]]] for c in range(n)]
            for r in range(n)
        ]

    # -- cage partitioning -----------------------------------------------

    def _partition_into_cages(self) -> List[List[Cell]]:
        """Partition the grid into contiguous cages via random-region growth."""
        n = self.size
        unassigned: Set[Cell] = {
            (r, c) for r in range(n) for c in range(n)
        }
        cages: List[List[Cell]] = []
        while unassigned:
            start = self.rng.choice(sorted(unassigned))
            cage_cells: List[Cell] = [start]
            unassigned.remove(start)
            min_size = 1 if self.allow_singletons else 2
            cage_size = self.rng.randint(min_size, self.max_cage_size)
            while len(cage_cells) < cage_size:
                frontier: Set[Cell] = set()
                for cell in cage_cells:
                    for nb in neighbors(cell, n):
                        if nb in unassigned:
                            frontier.add(nb)
                if not frontier:
                    break
                pick = self.rng.choice(sorted(frontier))
                cage_cells.append(pick)
                unassigned.remove(pick)
            cages.append(cage_cells)
        # If singletons are disallowed, merge any orphan singletons into an
        # adjacent cage.
        if not self.allow_singletons:
            cages = self._merge_singletons(cages, n)
        return cages

    def _merge_singletons(
        self, cages: List[List[Cell]], n: int
    ) -> List[List[Cell]]:
        """Merge any single-cell cages into an adjacent cage."""
        changed = True
        while changed:
            changed = False
            for i, cage in enumerate(cages):
                if len(cage) == 1:
                    cell = cage[0]
                    for nb in neighbors(cell, n):
                        for j, other_cage in enumerate(cages):
                            if i != j and nb in other_cage:
                                other_cage.extend(cage)
                                cages.pop(i)
                                changed = True
                                break
                        if changed:
                            break
                    if changed:
                        break
        return cages

    # -- operator selection ----------------------------------------------

    def _choose_operator(self, values: List[int]) -> Tuple[str, int]:
        """Given the solution values in a cage, pick an operator+target.

        Respects difficulty:
          easy   → prefer ``+`` and ``=``, allow ``-``, small ``*``
          medium → allow ``+``, ``-``, ``*``, ``/``
          hard   → prefer ``*``, ``/``, and larger cages
        """
        diff = self.difficulty
        if len(values) == 1:
            return ("=", values[0])
        candidates: List[Tuple[str, int]] = []
        s = sum(values)
        candidates.append(("+", s))
        p = 1
        for v in values:
            p *= v
        candidates.append(("*", p))
        # Subtraction: for two-cell cages use the absolute difference
        # (canonical KenKen form). For larger cages keep any permutation
        # result that is positive — KenKen targets are traditionally positive.
        sub_targets: Set[int] = set()
        for perm in permutations(values):
            r = perm[0]
            for v in perm[1:]:
                r = r - v
            if len(values) == 2:
                sub_targets.add(abs(r))
            elif r > 0:
                sub_targets.add(r)
        for t in sub_targets:
            candidates.append(("-", t))
        # Division: only if evenly divisible for some permutation
        div_targets: Set[int] = set()
        for perm in permutations(values):
            r = perm[0]
            ok = True
            for v in perm[1:]:
                if v == 0 or r % v != 0:
                    ok = False
                    break
                r = r // v
            if ok and r > 0:
                div_targets.add(r)
        for t in div_targets:
            candidates.append(("/", t))
        # Difficulty filtering via weights
        if diff == "easy":
            weights = {"+": 3, "=": 3, "-": 2, "*": 1, "/": 0}
        elif diff == "hard":
            weights = {"+": 1, "=": 0, "-": 2, "*": 3, "/": 3}
        else:  # medium
            weights = {"+": 2, "=": 1, "-": 2, "*": 2, "/": 2}
        weighted: List[Tuple[Tuple[str, int], int]] = [
            (cand, weights.get(cand[0], 1)) for cand in candidates
        ]
        positive = [wc for wc in weighted if wc[1] > 0]
        if not positive:
            positive = weighted
        total = sum(w for _, w in positive)
        r = self.rng.randint(1, total)
        acc = 0
        for cand, w in positive:
            acc += w
            if r <= acc:
                return cand
        return positive[-1][0]

    # -- main generate ----------------------------------------------------

    def generate(self, max_attempts: int = 100) -> KenKenPuzzle:
        """Generate a puzzle with a unique solution.

        Parameters
        ----------
        max_attempts:
            Maximum number of generation attempts before giving up.

        Raises
        ------
        RuntimeError
            If no unique puzzle could be generated in *max_attempts* tries.
        """
        for attempt in range(max_attempts):
            solution = self._random_latin_square()
            cage_cell_lists = self._partition_into_cages()
            cages: List[Cage] = []
            for i, cells in enumerate(cage_cell_lists):
                values = [solution[r][c] for (r, c) in cells]
                op, target = self._choose_operator(values)
                cages.append(
                    Cage(cells=cells, op=op, target=target, label=str(i + 1))
                )
            puzzle = KenKenPuzzle(size=self.size, cages=cages)
            solver = KenKenSolver(puzzle, max_solutions=2)
            solver.solve()
            if len(solver.solutions) == 1:
                self._solution = solution
                logger.debug(
                    "Generated unique %dx%d puzzle on attempt %d",
                    self.size,
                    self.size,
                    attempt + 1,
                )
                return puzzle
        raise RuntimeError(
            f"Failed to generate unique puzzle in {max_attempts} attempts"
        )

    @property
    def solution(self) -> List[List[int]]:
        """Return the intended solution grid (after :meth:`generate` was called)."""
        if self._solution is None:
            raise RuntimeError("generate() must be called first")
        return self._solution


__all__ = ["KenKenGenerator"]