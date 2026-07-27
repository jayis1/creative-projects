"""Backtracking KenKen solver with constraint propagation.

The solver combines several well-known techniques:

1. **Domain tracking** — each cell maintains a set of candidate values
   ``{1..n}`` reduced by row and column constraints.
2. **MRV heuristic** — at each step, the unassigned cell with the fewest
   candidates is selected first.
3. **Naked-single propagation** — cells reduced to a single candidate are
   assigned automatically (AC-1 style).
4. **Cage feasibility pruning** — for ``+`` and ``*`` cages, bounds on the
   partial sum/product are used to prune infeasible branches early.
5. **Full-domain snapshots** — a complete snapshot of all domains is saved
   before each branch to guarantee correct restoration after backtracking.
"""

from __future__ import annotations

import logging
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from kenken_solver.cage import Cage
from kenken_solver.puzzle import KenKenPuzzle
from kenken_solver.types import Cell

logger = logging.getLogger(__name__)


class KenKenSolver:
    """Backtracking solver with constraint propagation and the MRV heuristic.

    Parameters
    ----------
    puzzle:
        The :class:`~kenken_solver.puzzle.KenKenPuzzle` to solve.
    max_solutions:
        Stop after finding this many solutions (default 1).

    Attributes
    ----------
    solutions:
        List of solution dictionaries found (one per solution).
    stats:
        Dictionary with ``nodes``, ``backtracks``, and ``propagations``
        counters for performance analysis.
    """

    def __init__(
        self, puzzle: KenKenPuzzle, max_solutions: int = 1
    ) -> None:
        self.puzzle = puzzle
        self.n: int = puzzle.size
        self.max_solutions: int = max_solutions
        self.solutions: List[Dict[Cell, int]] = []
        self.stats: Dict[str, int] = {
            "nodes": 0,
            "backtracks": 0,
            "propagations": 0,
        }

    # -- incremental domain tracking --------------------------------------

    def _init_domains(self) -> Dict[Cell, Set[int]]:
        """Initialize domains for all cells to {1..n}."""
        full = set(range(1, self.n + 1))
        return {
            (r, c): set(full)
            for r in range(self.n)
            for c in range(self.n)
        }

    def _propagate(
        self,
        assignment: Dict[Cell, int],
        domains: Dict[Cell, Set[int]],
    ) -> bool:
        """Propagate row/column constraint reductions and naked singles.

        Naked singles are assigned into *assignment* — this is a valid
        inference (a cell with only one possible value must take it), so the
        solver finds solutions deterministically once enough cells are filled.

        Returns ``True`` if propagation succeeds (no empty domains),
        ``False`` if a contradiction is found.
        """
        changed = True
        while changed:
            changed = False
            self.stats["propagations"] += 1
            # Phase 1: Reduce domains based on row/column assignments.
            # Process ALL row/col reductions before checking for naked
            # singles, so that a newly-assigned cell's constraints are
            # fully propagated before any other cell is auto-assigned.
            for cell, val in assignment.items():
                r, c = cell
                for cc in range(self.n):
                    other = (r, cc)
                    if other != cell and val in domains[other]:
                        domains[other].discard(val)
                        if not domains[other] and other not in assignment:
                            return False
                        changed = True
                for rr in range(self.n):
                    other = (rr, c)
                    if other != cell and val in domains[other]:
                        domains[other].discard(val)
                        if not domains[other] and other not in assignment:
                            return False
                        changed = True
            # Phase 2: Assign naked singles (cells with exactly one
            # remaining candidate).  Only assign ONE per iteration so that
            # its row/col constraints are propagated before the next naked
            # single is assigned.
            for cell in list(domains.keys()):
                if cell not in assignment and len(domains[cell]) == 1:
                    val = next(iter(domains[cell]))
                    assignment[cell] = val
                    cage = self.puzzle.cage_for(cell)
                    if not self._cage_feasible(assignment, cage):
                        return False
                    changed = True
                    break  # Re-loop to propagate this assignment first
        return True

    def _candidates(
        self, domains: Dict[Cell, Set[int]], cell: Cell
    ) -> List[int]:
        """Return sorted candidate values for *cell*."""
        return sorted(domains[cell])

    def _cage_feasible(
        self, assignment: Dict[Cell, int], cage: Cage
    ) -> bool:
        """Quick feasibility check for a cage given a partial assignment.

        Returns ``True`` if the cage can still possibly be satisfied.
        For ``+`` and ``*`` we can prune early using bounds; for ``-`` and
        ``/`` we defer to the full check when complete.
        """
        vals = [assignment.get(c) for c in cage.cells]
        assigned = [v for v in vals if v is not None]
        unassigned = len(vals) - len(assigned)
        op = cage.op
        t = cage.target
        if unassigned == 0:
            return bool(cage._evaluate(assigned))
        if op == "+":
            s = sum(assigned)
            if s + unassigned > t:
                return False
            if s + unassigned * self.n < t:
                return False
            return True
        if op == "*":
            p = 1
            for v in assigned:
                p *= v
            # Values are 1..n, so product can never be 0.
            # min product = p * 1^unassigned = p
            # max product = p * n^unassigned
            max_v = p * (self.n ** unassigned)
            if p > t:
                return False
            if max_v < t:
                return False
            return True
        # For - and / we cannot easily prune with partial assignments.
        return True

    # -- main solve -------------------------------------------------------

    def solve(self) -> List[Dict[Cell, int]]:
        """Solve the puzzle. Returns a list of solution dictionaries."""
        self.solutions = []
        self.stats = {"nodes": 0, "backtracks": 0, "propagations": 0}
        assignment: Dict[Cell, int] = {}
        domains = self._init_domains()
        self._backtrack(assignment, domains)
        logger.debug(
            "solve(): found %d solution(s) in %d nodes, %d backtracks",
            len(self.solutions),
            self.stats["nodes"],
            self.stats["backtracks"],
        )
        return self.solutions

    def _backtrack(
        self,
        assignment: Dict[Cell, int],
        domains: Dict[Cell, Set[int]],
    ) -> None:
        if len(self.solutions) >= self.max_solutions:
            return
        self.stats["nodes"] += 1
        all_cells = {
            (r, c) for r in range(self.n) for c in range(self.n)
        }
        unassigned = [c for c in all_cells if c not in assignment]
        if not unassigned:
            if all(cg.satisfied(assignment) for cg in self.puzzle.cages):
                self.solutions.append(dict(assignment))
            return
        # MRV: pick the unassigned cell with fewest candidates
        best_cell: Optional[Cell] = None
        best_cands: List[int] = []
        best_count = self.n + 1
        for cell in unassigned:
            cands = self._candidates(domains, cell)
            if len(cands) < best_count:
                best_count = len(cands)
                best_cell = cell
                best_cands = cands
                if best_count == 0:
                    break
        if best_cell is None or best_count == 0:
            self.stats["backtracks"] += 1
            return
        for val in best_cands:
            # Save full domain snapshot for backtracking.
            # Propagation modifies many domains (not just the row/col of
            # best_cell), so we must save and restore ALL domains.
            assignment[best_cell] = val
            cage = self.puzzle.cage_for(best_cell)
            if self._cage_feasible(assignment, cage):
                domain_snapshot: Dict[Cell, FrozenSet[int]] = {
                    k: frozenset(v) for k, v in domains.items()
                }
                r, c = best_cell
                for cc in range(self.n):
                    domains[(r, cc)].discard(val)
                for rr in range(self.n):
                    domains[(rr, c)].discard(val)
                domains[best_cell] = {val}

                prop_assignment = dict(assignment)
                prop_ok = self._propagate(prop_assignment, domains)
                if prop_ok:
                    self._backtrack(prop_assignment, domains)
                    if len(self.solutions) >= self.max_solutions:
                        for k, v in domain_snapshot.items():
                            domains[k] = set(v)
                        del assignment[best_cell]
                        return
                # Restore all domains from snapshot
                for k, v in domain_snapshot.items():
                    domains[k] = set(v)
            del assignment[best_cell]
        self.stats["backtracks"] += 1

    # -- solution counting ------------------------------------------------

    def count_solutions(self, limit: int = 10**9) -> int:
        """Count solutions without storing them. Stops at *limit*."""
        self.solutions = []
        self.stats = {"nodes": 0, "backtracks": 0, "propagations": 0}
        self._count = 0
        self._count_limit = limit
        assignment: Dict[Cell, int] = {}
        domains = self._init_domains()
        self._backtrack_count(assignment, domains)
        logger.debug(
            "count_solutions(): %d solution(s) in %d nodes",
            self._count,
            self.stats["nodes"],
        )
        return self._count

    def _backtrack_count(
        self,
        assignment: Dict[Cell, int],
        domains: Dict[Cell, Set[int]],
    ) -> None:
        if self._count >= self._count_limit:
            return
        self.stats["nodes"] += 1
        all_cells = {
            (r, c) for r in range(self.n) for c in range(self.n)
        }
        unassigned = [c for c in all_cells if c not in assignment]
        if not unassigned:
            if all(cg.satisfied(assignment) for cg in self.puzzle.cages):
                self._count += 1
            return
        best_cell: Optional[Cell] = None
        best_cands: List[int] = []
        best_count = self.n + 1
        for cell in unassigned:
            cands = self._candidates(domains, cell)
            if len(cands) < best_count:
                best_count = len(cands)
                best_cell = cell
                best_cands = cands
                if best_count == 0:
                    break
        if best_cell is None or best_count == 0:
            self.stats["backtracks"] += 1
            return
        for val in best_cands:
            assignment[best_cell] = val
            cage = self.puzzle.cage_for(best_cell)
            if self._cage_feasible(assignment, cage):
                domain_snapshot: Dict[Cell, FrozenSet[int]] = {
                    k: frozenset(v) for k, v in domains.items()
                }
                r, c = best_cell
                for cc in range(self.n):
                    domains[(r, cc)].discard(val)
                for rr in range(self.n):
                    domains[(rr, c)].discard(val)
                domains[best_cell] = {val}

                prop_assignment = dict(assignment)
                prop_ok = self._propagate(prop_assignment, domains)
                if prop_ok:
                    self._backtrack_count(prop_assignment, domains)
                    if self._count >= self._count_limit:
                        for k, v in domain_snapshot.items():
                            domains[k] = set(v)
                        del assignment[best_cell]
                        return
                for k, v in domain_snapshot.items():
                    domains[k] = set(v)
            del assignment[best_cell]
        self.stats["backtracks"] += 1

    # -- hints ------------------------------------------------------------

    def get_hint(
        self, partial: Dict[Cell, int], num: int = 1
    ) -> List[Tuple[Cell, int]]:
        """Return up to *num* cell-value hints consistent with *partial*.

        Solves the puzzle and checks that the partial assignment is consistent
        with the solution.  If the partial assignment conflicts with the cage
        constraints or the unique solution, no hints are returned.

        Raises
        ------
        ValueError
            If the partial assignment has row/column conflicts or
            out-of-range values.
        """
        # Verify the partial assignment is consistent
        for cell, val in partial.items():
            if val < 1 or val > self.n:
                raise ValueError(f"Value {val} out of range for cell {cell}")
            if cell not in self.puzzle._cell_cage:
                raise ValueError(f"Cell {cell} is not in the puzzle")
        # Check row/col conflicts in partial
        for (r, c), v in partial.items():
            for (r2, c2), v2 in partial.items():
                if (r, c) != (r2, c2):
                    if r == r2 and v == v2:
                        raise ValueError(
                            f"Row conflict: {(r, c)} and {(r2, c2)} both {v}"
                        )
                    if c == c2 and v == v2:
                        raise ValueError(
                            f"Col conflict: {(r, c)} and {(r2, c2)} both {v}"
                        )
        # Check cage constraint violations in the partial assignment
        for cage in self.puzzle.cages:
            cage_vals = {c: partial[c] for c in cage.cells if c in partial}
            if cage_vals:
                if cage.op == "=" and len(cage.cells) == 1:
                    if cage.cells[0] in cage_vals:
                        if cage_vals[cage.cells[0]] != cage.target:
                            return []
                if len(cage_vals) == len(cage.cells):
                    if not cage._evaluate(list(cage_vals.values())):
                        return []
                if cage.op == "+" and len(cage_vals) < len(cage.cells):
                    partial_sum = sum(cage_vals.values())
                    remaining = len(cage.cells) - len(cage_vals)
                    if partial_sum + remaining > cage.target:
                        return []
                if cage.op == "*" and len(cage_vals) < len(cage.cells):
                    partial_prod = 1
                    for v in cage_vals.values():
                        partial_prod *= v
                    remaining = len(cage.cells) - len(cage_vals)
                    if partial_prod > cage.target and cage.target > 0:
                        return []
        # Solve the puzzle
        solutions = self.solve()
        if not solutions:
            return []
        sol = solutions[0]
        # Verify the partial assignment is consistent with the solution
        for cell, val in partial.items():
            if sol.get(cell) != val:
                return []
        hints: List[Tuple[Cell, int]] = []
        for cell, val in sol.items():
            if cell not in partial:
                hints.append((cell, val))
                if len(hints) >= num:
                    break
        return hints

    # -- convenience ------------------------------------------------------

    def solve_grid(self) -> Optional[List[List[int]]]:
        """Solve and return the solution as a 2-D list, or ``None``."""
        sols = self.solve()
        if not sols:
            return None
        sol = sols[0]
        return [
            [sol[(r, c)] for c in range(self.n)]
            for r in range(self.n)
        ]


__all__ = ["KenKenSolver"]