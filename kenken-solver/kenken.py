#!/usr/bin/env python3
"""KenKen puzzle generator, solver, and verifier.

KenKen (also known as KenDoku, Calcudoku, or Mathdoku) is an arithmetical-logic
puzzle invented by Japanese mathematics teacher Tetsuya Miyamoto in 2004.

A KenKen puzzle is an *n x n* grid.  Each row and each column must contain each
of the numbers 1..n exactly once (i.e. each row/column is a Latin square of
order *n*).  The grid is partitioned into "cages" — heavily outlined groups of
one or more contiguous cells.  Each cage displays a target number and an
arithmetic operator (+, -, *, /).  The numbers placed in the cage must combine
via that operator to produce the target.  For cages of size 1, the operator is
implicit (the single cell simply equals the target).

This module provides:

* ``Cage``           — a cage (cells, operator, target).
* ``KenKenPuzzle``   — immutable representation of a puzzle (size, cages).
* ``KenKenSolver``   — backtracking solver with constraint propagation, the
                       minimum-remaining-values (MRV) heuristic, forward
                       checking, and naked-single propagation.  Returns all
                       solutions (or just one).  Also supports solution
                       counting without storing them.
* ``KenKenGenerator`` — generates solvable puzzles of a given size and
                        difficulty, guaranteeing a unique solution.
* ``PuzzleAnalyzer``  — analyzes puzzle difficulty and properties.
* ``hint`` / ``batch`` / ``analyze`` CLI subcommands.

Pure standard-library Python; no external dependencies required.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from itertools import permutations
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

__all__ = [
    "Cage",
    "KenKenPuzzle",
    "KenKenSolver",
    "KenKenGenerator",
    "PuzzleAnalyzer",
    "render_puzzle",
    "render_solution",
    "render_cage_map",
    "main",
]

# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

Cell = Tuple[int, int]  # (row, col), 0-indexed


def _neighbors(cell: Cell, n: int) -> List[Cell]:
    """Return orthogonally-adjacent cells within an n x n grid."""
    r, c = cell
    out: List[Cell] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n:
            out.append((nr, nc))
    return out


def _is_contiguous(cells: List[Cell], n: int) -> bool:
    """Check that a set of cells forms a single connected region (4-connectivity)."""
    if not cells:
        return True
    cell_set = set(cells)
    visited: Set[Cell] = set()
    stack = [cells[0]]
    while stack:
        c = stack.pop()
        if c in visited:
            continue
        visited.add(c)
        for nb in _neighbors(c, n):
            if nb in cell_set and nb not in visited:
                stack.append(nb)
    return visited == cell_set


# ---------------------------------------------------------------------------
# Cage
# ---------------------------------------------------------------------------

VALID_OPS = frozenset({"+", "-", "*", "/", "="})


class Cage:
    """A cage: a set of cells, an operator, and a target value.

    Operators:
      ``+`` — sum of all cell values equals target.
      ``*`` — product of all cell values equals target.
      ``-`` — some left-to-right ordering of the values subtracts to target.
              For two-cell cages, this is equivalent to absolute difference.
      ``/`` — some left-to-right ordering of the values divides to target
              (evenly, no remainder).
      ``=`` — single-cell cage; the value equals the target.
    """

    __slots__ = ("cells", "op", "target", "label")

    def __init__(self, cells: List[Cell], op: str, target: int, label: str = "") -> None:
        if not cells:
            raise ValueError("Cage must contain at least one cell")
        if op not in VALID_OPS:
            raise ValueError(f"Invalid operator {op!r}; must be one of {sorted(VALID_OPS)}")
        if target <= 0 and op != "-":
            raise ValueError(f"Target must be positive for operator {op!r}, got {target}")
        if op == "=" and len(cells) != 1:
            raise ValueError("'=' operator requires exactly one cell")
        self.cells = list(cells)
        self.op = op
        self.target = target
        self.label = label

    @property
    def size(self) -> int:
        return len(self.cells)

    def _evaluate(self, values: List[int]) -> bool:
        """Evaluate the cage operator on the given list of cell values.

        For subtraction and division, all permutations are checked — the cage
        is satisfied if any ordering of the values yields the target when
        applied left-to-right.
        """
        op = self.op
        t = self.target
        if op == "+":
            return sum(values) == t
        if op == "*":
            p = 1
            for v in values:
                p *= v
            return p == t
        if op == "-":
            if len(values) == 1:
                return values[0] == t
            for perm in permutations(values):
                result = perm[0]
                for v in perm[1:]:
                    result = result - v
                if result == t:
                    return True
            return False
        if op == "/":
            if len(values) == 1:
                return values[0] == t
            for perm in permutations(values):
                result = perm[0]
                ok = True
                for v in perm[1:]:
                    if v == 0 or result % v != 0:
                        ok = False
                        break
                    result = result // v
                if ok and result == t:
                    return True
            return False
        if op == "=":
            return len(values) == 1 and values[0] == t
        raise ValueError(f"Unknown operator: {op}")

    def satisfied(self, assignment: Dict[Cell, int]) -> bool:
        """Check whether the cage is satisfied given a (partial) assignment.

        Returns True (vacuously) if not all cage cells are assigned yet.
        """
        vals = [assignment.get(c) for c in self.cells]
        if any(v is None for v in vals):
            return True
        return self._evaluate([v for v in vals if v is not None])  # type: ignore[list-item]

    def possible_targets(self, n: int) -> Set[Tuple[str, int]]:
        """Return all (op, target) pairs achievable by this cage's cells
        for a grid of size *n*, considering the Latin-square constraint
        (no repeated values in a row or column — but cage cells may share
        neither, so we only require values from 1..n with no constraint
        on repeats across non-conflicting cells).

        This is used for validation and analysis.
        """
        results: Set[Tuple[str, int]] = set()
        # Generate all possible value assignments from 1..n (with repetition
        # allowed, since cage cells may be in different rows/columns).
        k = len(self.cells)
        # For small k and n this is fine; for large k it's exponential but
        # cages are typically ≤5 cells.
        from itertools import product
        for combo in product(range(1, n + 1), repeat=k):
            s = sum(combo)
            results.add(("+", s))
            p = 1
            for v in combo:
                p *= v
            results.add(("*", p))
            if k == 2:
                a, b = combo
                results.add(("-", abs(a - b)))
                if b != 0 and a % b == 0:
                    results.add(("/", a // b))
                if a != 0 and b % a == 0:
                    results.add(("/", b // a))
            elif k > 2:
                for perm in permutations(combo):
                    r = perm[0]
                    for v in perm[1:]:
                        r = r - v
                    if r > 0:
                        results.add(("-", r))
                    # Division check
                    r2 = perm[0]
                    div_ok = True
                    for v in perm[1:]:
                        if v == 0 or r2 % v != 0:
                            div_ok = False
                            break
                        r2 = r2 // v
                    if div_ok and r2 > 0:
                        results.add(("/", r2))
        if k == 1:
            for v in range(1, n + 1):
                results.add(("=", v))
        return results

    def to_dict(self) -> dict:
        return {
            "cells": [list(c) for c in self.cells],
            "op": self.op,
            "target": self.target,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Cage":
        return cls(
            cells=[(int(r), int(c)) for r, c in d["cells"]],
            op=d["op"],
            target=int(d["target"]),
            label=d.get("label", ""),
        )

    def __repr__(self) -> str:
        return f"Cage(cells={self.cells}, op={self.op!r}, target={self.target})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cage):
            return NotImplemented
        return (
            set(self.cells) == set(other.cells)
            and self.op == other.op
            and self.target == other.target
        )

    def __hash__(self) -> int:
        return hash((frozenset(self.cells), self.op, self.target))


# ---------------------------------------------------------------------------
# Puzzle representation
# ---------------------------------------------------------------------------

class KenKenPuzzle:
    """Immutable representation of a KenKen puzzle."""

    def __init__(self, size: int, cages: List[Cage], validate: bool = True) -> None:
        if size < 2:
            raise ValueError("KenKen grid must be at least 2x2")
        self.size = size
        self.cages = list(cages)
        self._cell_cage: Dict[Cell, Cage] = {}
        if validate:
            self._validate_partition()
            self._validate_cages()
        else:
            # Still build the cell->cage map without full validation
            for cage in self.cages:
                for c in cage.cells:
                    self._cell_cage[c] = cage
        # Precompute cage cell-sets
        self._cage_sets: List[Set[Cell]] = [set(cg.cells) for cg in self.cages]

    def _validate_partition(self) -> None:
        seen: Set[Cell] = set()
        for cage in self.cages:
            for c in cage.cells:
                if c in seen:
                    raise ValueError(f"Cell {c} belongs to more than one cage")
                if not (0 <= c[0] < self.size and 0 <= c[1] < self.size):
                    raise ValueError(f"Cell {c} out of bounds for size {self.size}")
                seen.add(c)
                self._cell_cage[c] = cage
        expected = {(r, c) for r in range(self.size) for c in range(self.size)}
        missing = expected - seen
        if missing:
            raise ValueError(f"Cells not covered by any cage: {sorted(missing)}")

    def _validate_cages(self) -> None:
        """Validate that each cage is contiguous and has a consistent operator."""
        for i, cage in enumerate(self.cages):
            if not _is_contiguous(cage.cells, self.size):
                raise ValueError(f"Cage {i} (label={cage.label}) cells {cage.cells} "
                                 f"are not contiguous")
            if cage.op == "=" and cage.size != 1:
                raise ValueError(f"Cage {i} has '=' operator but size {cage.size}")

    def cage_for(self, cell: Cell) -> Cage:
        return self._cell_cage[cell]

    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "cages": [c.to_dict() for c in self.cages],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KenKenPuzzle":
        return cls(size=int(d["size"]), cages=[Cage.from_dict(cd) for cd in d["cages"]])

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, s: str) -> "KenKenPuzzle":
        return cls.from_dict(json.loads(s))

    def to_text(self) -> str:
        """Export to a compact human-readable text format.

        Format:
            size: N
            R,C R,C ... op target
            ...

        Each line after the header is a cage: space-separated cell coordinates
        (row,col pairs), then the operator, then the target.
        """
        lines = [f"size: {self.size}"]
        for cage in self.cages:
            cells_str = " ".join(f"{r},{c}" for (r, c) in cage.cells)
            lines.append(f"{cells_str} {cage.op} {cage.target}")
        return "\n".join(lines) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "KenKenPuzzle":
        """Parse the compact text format produced by ``to_text``."""
        lines = [l.strip() for l in text.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
        if not lines:
            raise ValueError("Empty puzzle text")
        size = None
        cage_specs: List[Tuple[List[Cell], str, int]] = []
        for line in lines:
            if line.lower().startswith("size:"):
                size = int(line.split(":")[1].strip())
                continue
            parts = line.split()
            if len(parts) < 3:
                raise ValueError(f"Invalid cage line: {line!r}")
            op = parts[-2]
            target = int(parts[-1])
            cell_parts = parts[:-2]
            cells: List[Cell] = []
            for cp in cell_parts:
                r_str, c_str = cp.split(",")
                cells.append((int(r_str), int(c_str)))
            cage_specs.append((cells, op, target))
        if size is None:
            raise ValueError("Missing 'size:' header")
        cages = [Cage(cells=cs, op=op, target=target, label=str(i + 1))
                 for i, (cs, op, target) in enumerate(cage_specs)]
        return cls(size=size, cages=cages)

    def __repr__(self) -> str:
        return f"KenKenPuzzle(size={self.size}, cages={len(self.cages)})"


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class KenKenSolver:
    """Backtracking solver with constraint propagation and MRV heuristic.

    Algorithm:
      1. Maintain per-cell domains {1..n}, minus values used in the same
         row or column.
      2. Propagate naked singles: if a cell's domain has been reduced to one
         value, assign it immediately (iteratively, like AC-1).
      3. Select the unassigned cell with fewest candidates (MRV).
      4. Try each candidate; check cage feasibility bounds.
      5. Recurse. Backtrack on failure.

    The solver also supports ``count_solutions()`` which counts all solutions
    without storing them (useful for very large solution spaces).
    """

    def __init__(self, puzzle: KenKenPuzzle, max_solutions: int = 1) -> None:
        self.puzzle = puzzle
        self.n = puzzle.size
        self.max_solutions = max_solutions
        self.solutions: List[Dict[Cell, int]] = []
        self.stats = {"nodes": 0, "backtracks": 0, "propagations": 0}

    # -- incremental domain tracking --------------------------------------

    def _init_domains(self) -> Dict[Cell, Set[int]]:
        """Initialize domains for all cells to {1..n}."""
        full = set(range(1, self.n + 1))
        return {(r, c): set(full) for r in range(self.n) for c in range(self.n)}

    def _propagate(self, assignment: Dict[Cell, int],
                   domains: Dict[Cell, Set[int]]) -> bool:
        """Propagate row/column constraint reductions and naked singles.

        Naked singles are assigned into *assignment* — this is a valid
        inference (a cell with only one possible value must take it),
        but it means the solver finds solutions deterministically once
        enough cells are filled.  This does NOT eliminate valid solutions
        because a naked single is logically forced.

        Returns True if propagation succeeds (no empty domains), False if a
        contradiction is found.
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

    def _candidates(self, domains: Dict[Cell, Set[int]], cell: Cell) -> List[int]:
        return sorted(domains[cell])

    def _cage_feasible(self, assignment: Dict[Cell, int], cage: Cage) -> bool:
        """Quick feasibility check for a cage given partial assignment.

        Returns True if the cage can still possibly be satisfied.
        For + and * we can prune early using bounds; for - and / we defer
        to the full check when complete.
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
        return self.solutions

    def _backtrack(self, assignment: Dict[Cell, int],
                   domains: Dict[Cell, Set[int]]) -> None:
        if len(self.solutions) >= self.max_solutions:
            return
        self.stats["nodes"] += 1
        all_cells = {(r, c) for r in range(self.n) for c in range(self.n)}
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
                # Snapshot all domains before modification
                domain_snapshot: Dict[Cell, FrozenSet[int]] = {
                    k: frozenset(v) for k, v in domains.items()
                }
                # Update domains for row/column of best_cell
                r, c = best_cell
                for cc in range(self.n):
                    domains[(r, cc)].discard(val)
                for rr in range(self.n):
                    domains[(rr, c)].discard(val)
                domains[best_cell] = {val}

                # Propagate naked singles
                prop_assignment = dict(assignment)
                prop_ok = self._propagate(prop_assignment, domains)
                if prop_ok:
                    self._backtrack(prop_assignment, domains)
                    if len(self.solutions) >= self.max_solutions:
                        # Restore and return
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
        return self._count

    def _backtrack_count(self, assignment: Dict[Cell, int],
                         domains: Dict[Cell, Set[int]]) -> None:
        if self._count >= self._count_limit:
            return
        self.stats["nodes"] += 1
        all_cells = {(r, c) for r in range(self.n) for c in range(self.n)}
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
                # Snapshot all domains before modification
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

    def get_hint(self, partial: Dict[Cell, int], num: int = 1) -> List[Tuple[Cell, int]]:
        """Return up to *num* cell-value hints consistent with the partial
        assignment.

        Solves the puzzle and checks that the partial assignment is
        consistent with the solution.  If the partial assignment conflicts
        with the cage constraints or the unique solution, no hints are
        returned.

        Raises ValueError if the partial assignment has row/column conflicts
        or out-of-range values.
        """
        # Verify the partial assignment is consistent
        for cell, val in partial.items():
            if val < 1 or val > self.n:
                raise ValueError(f"Value {val} out of range for cell {cell}")
            # Check that the cell exists in the puzzle
            if cell not in self.puzzle._cell_cage:
                raise ValueError(f"Cell {cell} is not in the puzzle")
        # Check row/col conflicts in partial
        for (r, c), v in partial.items():
            for (r2, c2), v2 in partial.items():
                if (r, c) != (r2, c2):
                    if r == r2 and v == v2:
                        raise ValueError(f"Row conflict: {(r, c)} and {(r2, c2)} both {v}")
                    if c == c2 and v == v2:
                        raise ValueError(f"Col conflict: {(r, c)} and {(r2, c2)} both {v}")
        # Check cage constraint violations in the partial assignment
        for cage in self.puzzle.cages:
            cage_vals = {c: partial[c] for c in cage.cells if c in partial}
            if cage_vals:
                # For single-cell cages, the value must match the target
                if cage.op == "=" and len(cage.cells) == 1:
                    if cage.cells[0] in cage_vals:
                        if cage_vals[cage.cells[0]] != cage.target:
                            return []  # Cage constraint violated
                # For multi-cell cages with all cells assigned, check full constraint
                if len(cage_vals) == len(cage.cells):
                    if not cage._evaluate(list(cage_vals.values())):
                        return []
                # For + cages, check if partial sum already exceeds target
                if cage.op == "+" and len(cage_vals) < len(cage.cells):
                    partial_sum = sum(cage_vals.values())
                    remaining = len(cage.cells) - len(cage_vals)
                    if partial_sum + remaining > cage.target:
                        return []  # Even minimum additions exceed target
                # For * cages, check if partial product already exceeds target
                if cage.op == "*" and len(cage_vals) < len(cage.cells):
                    partial_prod = 1
                    for v in cage_vals.values():
                        partial_prod *= v
                    remaining = len(cage.cells) - len(cage_vals)
                    if partial_prod > cage.target and cage.target > 0:
                        return []  # Product already exceeds target
        # Solve the puzzle
        solutions = self.solve()
        if not solutions:
            return []
        sol = solutions[0]
        # Verify the partial assignment is consistent with the solution
        for cell, val in partial.items():
            if sol.get(cell) != val:
                # The partial assignment doesn't match the unique solution
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
        sols = self.solve()
        if not sols:
            return None
        sol = sols[0]
        return [[sol[(r, c)] for c in range(self.n)] for r in range(self.n)]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class KenKenGenerator:
    """Generates KenKen puzzles with unique solutions.

    Strategy:
      1. Generate a random Latin square of order *n* as the solution.
      2. Partition the grid into contiguous cages using random-region growth.
      3. For each cage, compute the target and operator from the solution.
      4. Optionally restrict operators by difficulty.
      5. Verify uniqueness via the solver. If not unique, regenerate cages.
    """

    def __init__(self, size: int, seed: Optional[int] = None,
                 max_cage_size: int = 4, difficulty: str = "medium",
                 allow_singletons: bool = True) -> None:
        self.size = size
        self.max_cage_size = max_cage_size
        self.difficulty = difficulty
        self.allow_singletons = allow_singletons
        self.rng = random.Random(seed)
        self._solution: Optional[List[List[int]]] = None

    # -- Latin square generation -----------------------------------------

    def _random_latin_square(self) -> List[List[int]]:
        n = self.size
        base = [[((r + c) % n) + 1 for c in range(n)] for r in range(n)]
        rows = list(range(n))
        cols = list(range(n))
        syms = list(range(1, n + 1))
        self.rng.shuffle(rows)
        self.rng.shuffle(cols)
        self.rng.shuffle(syms)
        sym_map = {i + 1: syms[i] for i in range(n)}
        return [[sym_map[base[rows[r]][cols[c]]] for c in range(n)] for r in range(n)]

    # -- cage partitioning -----------------------------------------------

    def _partition_into_cages(self) -> List[List[Cell]]:
        n = self.size
        unassigned: Set[Cell] = {(r, c) for r in range(n) for c in range(n)}
        cages: List[List[Cell]] = []
        while unassigned:
            start = self.rng.choice(sorted(unassigned))
            cage_cells: List[Cell] = [start]
            unassigned.remove(start)
            # Determine target cage size
            min_size = 1 if self.allow_singletons else 2
            cage_size = self.rng.randint(min_size, self.max_cage_size)
            while len(cage_cells) < cage_size:
                frontier: Set[Cell] = set()
                for cell in cage_cells:
                    for nb in _neighbors(cell, n):
                        if nb in unassigned:
                            frontier.add(nb)
                if not frontier:
                    break
                pick = self.rng.choice(sorted(frontier))
                cage_cells.append(pick)
                unassigned.remove(pick)
            cages.append(cage_cells)
        # If singletons are disallowed, merge any orphan singletons into an
        # adjacent cage. This happens when a cell has no unassigned neighbors
        # at the time it's picked (e.g. it's surrounded by already-assigned
        # cages).
        if not self.allow_singletons:
            cages = self._merge_singletons(cages, n)
        return cages

    def _merge_singletons(self, cages: List[List[Cell]], n: int) -> List[List[Cell]]:
        """Merge any single-cell cages into an adjacent cage."""
        changed = True
        while changed:
            changed = False
            for i, cage in enumerate(cages):
                if len(cage) == 1:
                    cell = cage[0]
                    # Find an adjacent cage to merge into
                    for nb in _neighbors(cell, n):
                        for j, other_cage in enumerate(cages):
                            if i != j and nb in other_cage:
                                # Merge cage i into cage j
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
          easy   → prefer + and =, allow -, small *
          medium → allow +, -, *, /
          hard   → prefer *, /, and larger cages
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
        # Subtraction: for two-cell cages use the absolute difference (canonical
        # KenKen form). For larger cages keep any permutation result that is
        # positive — KenKen targets are traditionally positive.
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
        for attempt in range(max_attempts):
            solution = self._random_latin_square()
            cage_cell_lists = self._partition_into_cages()
            cages: List[Cage] = []
            for i, cells in enumerate(cage_cell_lists):
                values = [solution[r][c] for (r, c) in cells]
                op, target = self._choose_operator(values)
                cages.append(Cage(cells=cells, op=op, target=target, label=str(i + 1)))
            puzzle = KenKenPuzzle(size=self.size, cages=cages)
            solver = KenKenSolver(puzzle, max_solutions=2)
            solver.solve()
            if len(solver.solutions) == 1:
                self._solution = solution
                return puzzle
        raise RuntimeError(f"Failed to generate unique puzzle in {max_attempts} attempts")

    @property
    def solution(self) -> List[List[int]]:
        if self._solution is None:
            raise RuntimeError("generate() must be called first")
        return self._solution


# ---------------------------------------------------------------------------
# Puzzle Analyzer
# ---------------------------------------------------------------------------

class PuzzleAnalyzer:
    """Analyzes puzzle properties and difficulty."""

    def __init__(self, puzzle: KenKenPuzzle) -> None:
        self.puzzle = puzzle
        self.n = puzzle.size

    def analyze(self) -> dict:
        """Return a dictionary of analysis metrics."""
        cages = self.puzzle.cages
        n = self.n
        # Basic stats
        num_cages = len(cages)
        cage_sizes = [c.size for c in cages]
        avg_cage_size = sum(cage_sizes) / num_cages if num_cages else 0
        max_cage_size = max(cage_sizes) if cage_sizes else 0
        num_singletons = sum(1 for c in cages if c.size == 1)
        # Operator distribution
        op_counts: Dict[str, int] = {}
        for c in cages:
            op_counts[c.op] = op_counts.get(c.op, 0) + 1
        # Difficulty heuristics
        # 1. Larger cages → harder (more combinations to check)
        # 2. *, / → harder than +, -
        # 3. Fewer singletons → harder
        # 4. Larger grid → harder
        difficulty_score = 0
        difficulty_score += n * 2  # base grid size
        difficulty_score += int(avg_cage_size * 3)
        difficulty_score += op_counts.get("*", 0) * 3
        difficulty_score += op_counts.get("/", 0) * 4
        difficulty_score += op_counts.get("-", 0) * 2
        difficulty_score -= num_singletons * 2
        # Categorize
        if difficulty_score <= 15:
            category = "easy"
        elif difficulty_score <= 30:
            category = "medium"
        else:
            category = "hard"
        # Solver complexity: count solver nodes for one solution
        solver = KenKenSolver(self.puzzle, max_solutions=1)
        solver.solve()
        node_count = solver.stats["nodes"]
        backtrack_count = solver.stats["backtracks"]
        return {
            "size": n,
            "num_cages": num_cages,
            "avg_cage_size": round(avg_cage_size, 2),
            "max_cage_size": max_cage_size,
            "num_singletons": num_singletons,
            "operator_distribution": op_counts,
            "difficulty_score": difficulty_score,
            "difficulty_category": category,
            "solver_nodes": node_count,
            "solver_backtracks": backtrack_count,
        }


# ---------------------------------------------------------------------------
# Rendering / printing
# ---------------------------------------------------------------------------

def render_puzzle(puzzle: KenKenPuzzle) -> str:
    """Render the puzzle as an ASCII grid showing cage targets and operators."""
    n = puzzle.size
    cell_cage = puzzle._cell_cage
    cage_topleft: Dict[int, Cell] = {}
    for cage in puzzle.cages:
        top = min(cage.cells, key=lambda c: (c[0], c[1]))
        cage_topleft[id(cage)] = top
    lines: List[str] = []
    cell_w = max(4, len(str(n * n)) + 2)
    sep = "+" + ("-" * cell_w + "+") * n
    for r in range(n):
        lines.append(sep)
        row_line = "|"
        for c in range(n):
            cage = cell_cage[(r, c)]
            tl = cage_topleft[id(cage)]
            if (r, c) == tl:
                label = f"{cage.target}{cage.op}"
            else:
                label = ""
            row_line += f"{label:^{cell_w}}|"
        lines.append(row_line)
        val_line = "|"
        for c in range(n):
            val_line += f"{'':^{cell_w}}|"
        lines.append(val_line)
    lines.append(sep)
    return "\n".join(lines)


def render_solution(grid: List[List[int]]) -> str:
    """Render a solution grid as an ASCII table."""
    n = len(grid)
    cell_w = 4
    sep = "+" + ("-" * cell_w + "+") * n
    lines: List[str] = []
    for r in range(n):
        lines.append(sep)
        line = "|"
        for c in range(n):
            line += f"{grid[r][c]:^{cell_w}}|"
        lines.append(line)
    lines.append(sep)
    return "\n".join(lines)


def render_cage_map(puzzle: KenKenPuzzle) -> str:
    """Render a map showing which cage each cell belongs to (by label)."""
    n = puzzle.size
    cell_w = max(4, len(str(n * n)) + 1)
    sep = "+" + ("-" * cell_w + "+") * n
    lines: List[str] = []
    for r in range(n):
        lines.append(sep)
        line = "|"
        for c in range(n):
            cage = puzzle._cell_cage[(r, c)]
            line += f"{cage.label:^{cell_w}}|"
        lines.append(line)
    lines.append(sep)
    return "\n".join(lines)


def render_solved_puzzle(puzzle: KenKenPuzzle, grid: Optional[List[List[int]]]) -> str:
    """Render the puzzle with both cage labels (top) and solution values (bottom).

    If *grid* is None (no solution), renders the puzzle without values.
    """
    if grid is None:
        return render_puzzle(puzzle)
    n = puzzle.size
    cell_cage = puzzle._cell_cage
    cage_topleft: Dict[int, Cell] = {}
    for cage in puzzle.cages:
        top = min(cage.cells, key=lambda c: (c[0], c[1]))
        cage_topleft[id(cage)] = top
    lines: List[str] = []
    cell_w = max(5, len(str(n * n)) + 3)
    sep = "+" + ("-" * cell_w + "+") * n
    for r in range(n):
        lines.append(sep)
        row_line = "|"
        for c in range(n):
            cage = cell_cage[(r, c)]
            tl = cage_topleft[id(cage)]
            if (r, c) == tl:
                label = f"{cage.target}{cage.op}"
            else:
                label = ""
            row_line += f"{label:^{cell_w}}|"
        lines.append(row_line)
        val_line = "|"
        for c in range(n):
            val_line += f"{grid[r][c]:^{cell_w}}|"
        lines.append(val_line)
    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="KenKen puzzle generator, solver, and verifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Generate a 5x5 puzzle
  python3 kenken.py generate --size 5

  # Generate a hard 6x6 puzzle with seed
  python3 kenken.py generate --size 6 --difficulty hard --seed 42

  # Solve a puzzle from a JSON file
  python3 kenken.py solve --input puzzle.json

  # Generate and immediately solve
  python3 kenken.py generate --size 4 --solve

  # Verify a puzzle has a unique solution
  python3 kenken.py verify --input puzzle.json

  # Analyze puzzle difficulty
  python3 kenken.py analyze --input puzzle.json

  # Batch generate 10 puzzles
  python3 kenken.py batch --size 5 --count 10 --output-dir puzzles/

  # Get a hint for a partially solved puzzle
  python3 kenken.py hint --input puzzle.json --cells 0,0=3 1,1=2
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a new KenKen puzzle")
    gen.add_argument("--size", type=int, default=5, help="Grid size (default 5)")
    gen.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    gen.add_argument("--seed", type=int, default=None, help="Random seed")
    gen.add_argument("--max-cage-size", type=int, default=4)
    gen.add_argument("--no-singletons", action="store_true", help="Avoid single-cell cages")
    gen.add_argument("--solve", action="store_true", help="Also print the solution")
    gen.add_argument("--output", "-o", type=str, default=None, help="Write puzzle JSON to file")
    gen.add_argument("--format", choices=["grid", "json", "text", "both"], default="grid")

    sol = sub.add_parser("solve", help="Solve a puzzle from JSON or text")
    sol.add_argument("--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)")
    sol.add_argument("--all", action="store_true", help="Find all solutions")
    sol.add_argument("--stats", action="store_true", help="Print solver statistics")
    sol.add_argument("--max-solutions", type=int, default=None,
                     help="Maximum solutions to find (default 1, or 999999 with --all)")

    ver = sub.add_parser("verify", help="Verify a puzzle has a unique solution")
    ver.add_argument("--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)")

    ana = sub.add_parser("analyze", help="Analyze puzzle difficulty and properties")
    ana.add_argument("--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)")

    bat = sub.add_parser("batch", help="Batch generate multiple puzzles")
    bat.add_argument("--size", type=int, default=5)
    bat.add_argument("--count", type=int, default=10, help="Number of puzzles to generate")
    bat.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    bat.add_argument("--seed", type=int, default=None)
    bat.add_argument("--output-dir", "-o", type=str, required=True, help="Output directory")
    bat.add_argument("--format", choices=["json", "text"], default="json")

    hnt = sub.add_parser("hint", help="Get hints for a partially solved puzzle")
    hnt.add_argument("--input", "-i", type=str, required=True, help="Puzzle file (JSON or text)")
    hnt.add_argument("--cells", nargs="*", default=[], help="Pre-filled cells as R,C=V pairs")
    hnt.add_argument("--num", type=int, default=1, help="Number of hints to return")

    args = parser.parse_args(argv)

    def load_puzzle(path: str) -> KenKenPuzzle:
        with open(path) as f:
            content = f.read()
        if content.strip().startswith("{"):
            return KenKenPuzzle.from_json(content)
        else:
            return KenKenPuzzle.from_text(content)

    if args.command == "generate":
        gen_obj = KenKenGenerator(
            size=args.size,
            seed=args.seed,
            max_cage_size=args.max_cage_size,
            difficulty=args.difficulty,
            allow_singletons=not args.no_singletons,
        )
        puzzle = gen_obj.generate()
        if args.format in ("grid", "both"):
            print(render_puzzle(puzzle))
            print()
        if args.format == "text":
            print(puzzle.to_text())
        if args.format in ("json", "both"):
            print(puzzle.to_json())
        if args.output:
            with open(args.output, "w") as f:
                f.write(puzzle.to_json())
            print(f"Puzzle written to {args.output}", file=sys.stderr)
        if args.solve:
            solver = KenKenSolver(puzzle)
            grid = solver.solve_grid()
            if grid:
                print("Solution:")
                print(render_solved_puzzle(puzzle, grid))
            else:
                print("No solution found.")
        return 0

    if args.command == "solve":
        puzzle = load_puzzle(args.input)
        if args.max_solutions is not None:
            max_sol = args.max_solutions
        elif args.all:
            max_sol = 999999
        else:
            max_sol = 1
        solver = KenKenSolver(puzzle, max_solutions=max_sol)
        solver.solve()
        if not solver.solutions:
            print("No solution found.")
            return 1
        for i, soln in enumerate(solver.solutions):
            grid = [[soln[(r, c)] for c in range(puzzle.size)] for r in range(puzzle.size)]
            if args.all or max_sol > 1:
                print(f"Solution {i + 1}:")
            print(render_solution(grid))
        if args.stats:
            print(f"\nSolver stats: {solver.stats}")
        return 0

    if args.command == "verify":
        puzzle = load_puzzle(args.input)
        solver = KenKenSolver(puzzle, max_solutions=2)
        solver.solve()
        if len(solver.solutions) == 1:
            print("UNIQUE — puzzle has exactly one solution.")
            return 0
        elif len(solver.solutions) == 0:
            print("UNSOLVABLE — puzzle has no solution.")
            return 1
        else:
            print(f"NOT UNIQUE — puzzle has at least {len(solver.solutions)} solutions.")
            return 1

    if args.command == "analyze":
        puzzle = load_puzzle(args.input)
        analyzer = PuzzleAnalyzer(puzzle)
        results = analyzer.analyze()
        print(json.dumps(results, indent=2))
        return 0

    if args.command == "batch":
        import os
        os.makedirs(args.output_dir, exist_ok=True)
        stats = {"generated": 0, "failed": 0, "times": []}
        for i in range(args.count):
            seed = args.seed + i if args.seed is not None else None
            gen_obj = KenKenGenerator(
                size=args.size,
                seed=seed,
                difficulty=args.difficulty,
            )
            t0 = time.time()
            try:
                puzzle = gen_obj.generate()
            except RuntimeError:
                stats["failed"] += 1
                continue
            elapsed = time.time() - t0
            stats["times"].append(elapsed)
            stats["generated"] += 1
            ext = "json" if args.format == "json" else "txt"
            path = os.path.join(args.output_dir, f"puzzle_{i:03d}.{ext}")
            with open(path, "w") as f:
                if args.format == "json":
                    f.write(puzzle.to_json())
                else:
                    f.write(puzzle.to_text())
        print(f"Generated {stats['generated']}/{args.count} puzzles "
              f"({stats['failed']} failed)")
        if stats["times"]:
            avg_t = sum(stats["times"]) / len(stats["times"])
            print(f"Average generation time: {avg_t:.3f}s")
            print(f"Total time: {sum(stats['times']):.3f}s")
        return 0

    if args.command == "hint":
        puzzle = load_puzzle(args.input)
        partial: Dict[Cell, int] = {}
        for spec in args.cells:
            cell_str, val_str = spec.split("=")
            r_str, c_str = cell_str.split(",")
            partial[(int(r_str), int(c_str))] = int(val_str)
        solver = KenKenSolver(puzzle)
        try:
            hints = solver.get_hint(partial, num=args.num)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if not hints:
            print("No hints available (puzzle may be unsolvable with given cells).")
            return 1
        for cell, val in hints:
            print(f"Cell ({cell[0]},{cell[1]}) = {val}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())