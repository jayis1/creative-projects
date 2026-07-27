#!/usr/bin/env python3
"""KenKen puzzle generator and solver.

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

* ``KenKenPuzzle``  — immutable representation of a puzzle (size, cages).
* ``KenKenSolver``  — backtracking solver with constraint propagation, the
                      minimum-remaining-values (MRV) heuristic, and forward
                      checking.  Returns all solutions (or just one).
* ``KenKenGenerator`` — generates solvable puzzles of a given size and
                        difficulty, guaranteeing a unique solution.

Pure standard-library Python; no external dependencies required.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from copy import deepcopy
from itertools import permutations
from typing import Dict, List, Optional, Set, Tuple

__all__ = [
    "Cage",
    "KenKenPuzzle",
    "KenKenSolver",
    "KenKenGenerator",
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


# ---------------------------------------------------------------------------
# Cage
# ---------------------------------------------------------------------------

class Cage:
    """A cage: a set of cells, an operator, and a target value."""

    __slots__ = ("cells", "op", "target", "label")

    def __init__(self, cells: List[Cell], op: str, target: int, label: str = "") -> None:
        if not cells:
            raise ValueError("Cage must contain at least one cell")
        self.cells = list(cells)
        self.op = op
        self.target = target
        self.label = label

    @property
    def size(self) -> int:
        return len(self.cells)

    def _evaluate(self, values: List[int]) -> int:
        """Evaluate the cage operator on the given list of cell values.

        For binary operators with >2 operands, the operation is treated as the
        reduction (associative). For subtraction and division, all permutations
        are checked against the target — the cage is satisfied if any ordering
        of the values yields the target when applied left-to-right.
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
            # Single-cell cage (freebie)
            return len(values) == 1 and values[0] == t
        raise ValueError(f"Unknown operator: {op}")

    def satisfied(self, assignment: Dict[Cell, int]) -> bool:
        """Check whether the cage is satisfied given a (partial) assignment.

        Only checks if all cage cells are assigned.
        """
        vals = [assignment.get(c) for c in self.cells]
        if any(v is None for v in vals):
            return True  # not yet fully assigned → don't reject
        return self._evaluate([v for v in vals if v is not None])  # type: ignore[list-item]

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

    def __init__(self, size: int, cages: List[Cage]) -> None:
        if size < 2:
            raise ValueError("KenKen grid must be at least 2x2")
        self.size = size
        self.cages = list(cages)
        # Build cell -> cage map for fast lookup
        self._cell_cage: Dict[Cell, Cage] = {}
        self._validate_partition()
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

    def __repr__(self) -> str:
        return f"KenKenPuzzle(size={self.size}, cages={len(self.cages)})"


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class KenKenSolver:
    """Backtracking solver with constraint propagation and MRV heuristic.

    Algorithm:
      1. Compute candidate domain for each cell as 1..n.
      2. Select the unassigned cell with fewest candidates (MRV).
      3. Try each candidate; immediately reject if it violates the row,
         column, or (when fully assigned) cage constraint.
      4. Recurse. Backtrack on failure.
    """

    def __init__(self, puzzle: KenKenPuzzle, max_solutions: int = 1) -> None:
        self.puzzle = puzzle
        self.n = puzzle.size
        self.max_solutions = max_solutions
        self.solutions: List[Dict[Cell, int]] = []
        self.stats = {"nodes": 0, "backtracks": 0}

    # -- domain helpers ---------------------------------------------------

    def _row_used(self, assignment: Dict[Cell, int], row: int) -> Set[int]:
        return {v for (r, c), v in assignment.items() if r == row}

    def _col_used(self, assignment: Dict[Cell, int], col: int) -> Set[int]:
        return {v for (r, c), v in assignment.items() if c == col}

    def _candidates(self, assignment: Dict[Cell, int], cell: Cell) -> List[int]:
        r, c = cell
        used = self._row_used(assignment, r) | self._col_used(assignment, c)
        return [v for v in range(1, self.n + 1) if v not in used]

    def _cage_feasible(self, assignment: Dict[Cell, int], cage: Cage) -> bool:
        """Quick feasibility check for a cage given partial assignment.

        Returns True if the cage can still possibly be satisfied.
        For + and * we can prune early using bounds; for - and / we just
        defer to the full check when complete.
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
            # min possible = s + unassigned*1, max = s + unassigned*n
            if s + unassigned > t:
                return False
            if s + unassigned * self.n < t:
                return False
            return True
        if op == "*":
            p = 1
            for v in assigned:
                p *= v
            if p == 0:
                return False
            min_v = p
            max_v = p
            for _ in range(unassigned):
                min_v *= 1
                max_v *= self.n
            if min_v > t:
                return False
            if max_v < t:
                return False
            return True
        # For - and / we cannot easily prune; just ensure no duplicate
        # within the cage that would make - or / impossible (actually
        # duplicates are allowed in a cage across rows/cols as long as
        # they don't share row or column, so we don't prune).
        return True

    # -- main solve -------------------------------------------------------

    def solve(self) -> List[Dict[Cell, int]]:
        self.solutions = []
        self.stats = {"nodes": 0, "backtracks": 0}
        assignment: Dict[Cell, int] = {}
        self._backtrack(assignment)
        return self.solutions

    def _backtrack(self, assignment: Dict[Cell, int]) -> None:
        if len(self.solutions) >= self.max_solutions:
            return
        self.stats["nodes"] += 1
        all_cells = {(r, c) for r in range(self.n) for c in range(self.n)}
        unassigned = [c for c in all_cells if c not in assignment]
        if not unassigned:
            # Full assignment — verify all cages
            if all(cg.satisfied(assignment) for cg in self.puzzle.cages):
                self.solutions.append(dict(assignment))
            return
        # MRV: pick the unassigned cell with fewest candidates
        best_cell: Optional[Cell] = None
        best_cands: List[int] = []
        best_count = self.n + 1
        for cell in unassigned:
            cands = self._candidates(assignment, cell)
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
            # Check cage feasibility for the cage this cell belongs to
            cage = self.puzzle.cage_for(best_cell)
            if self._cage_feasible(assignment, cage):
                self._backtrack(assignment)
                if len(self.solutions) >= self.max_solutions:
                    del assignment[best_cell]
                    return
            del assignment[best_cell]
        self.stats["backtracks"] += 1

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
                 max_cage_size: int = 4, difficulty: str = "medium") -> None:
        self.size = size
        self.max_cage_size = max_cage_size
        self.difficulty = difficulty
        self.rng = random.Random(seed)

    # -- Latin square generation -----------------------------------------

    def _random_latin_square(self) -> List[List[int]]:
        n = self.size
        # Start with a base cyclic Latin square, then apply random
        # row/column permutations and symbol relabeling.
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
            # Start a new cage from a random unassigned cell
            start = self.rng.choice(sorted(unassigned))
            cage_cells: List[Cell] = [start]
            unassigned.remove(start)
            cage_size = self.rng.randint(1, self.max_cage_size)
            while len(cage_cells) < cage_size:
                # Find neighbors of current cage cells that are unassigned
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
        # Compute all possible (op, target) pairs
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
        # Difficulty filtering
        if diff == "easy":
            # Prefer + and =, allow -; avoid * and /
            weighted: List[Tuple[Tuple[str, int], int]] = []
            for cand in candidates:
                op = cand[0]
                w = {"+": 3, "=": 3, "-": 2, "*": 1, "/": 0}[op]
                weighted.append((cand, w))
        elif diff == "hard":
            weighted = []
            for cand in candidates:
                op = cand[0]
                w = {"+": 1, "=": 0, "-": 2, "*": 3, "/": 3}[op]
                weighted.append((cand, w))
        else:  # medium
            weighted = []
            for cand in candidates:
                op = cand[0]
                w = {"+": 2, "=": 1, "-": 2, "*": 2, "/": 2}[op]
                weighted.append((cand, w))
        # Filter zero-weight unless it's the only option
        positive = [wc for wc in weighted if wc[1] > 0]
        if not positive:
            positive = weighted
        # Weighted random choice
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
            # Verify uniqueness
            solver = KenKenSolver(puzzle, max_solutions=2)
            solver.solve()
            if len(solver.solutions) == 1:
                # Store the solution for later retrieval
                self._solution = solution
                return puzzle
        raise RuntimeError(f"Failed to generate unique puzzle in {max_attempts} attempts")

    @property
    def solution(self) -> List[List[int]]:
        if not hasattr(self, "_solution"):
            raise RuntimeError("generate() must be called first")
        return self._solution


# ---------------------------------------------------------------------------
# Rendering / printing
# ---------------------------------------------------------------------------

def render_puzzle(puzzle: KenKenPuzzle) -> str:
    """Render the puzzle as an ASCII grid showing cage targets and operators."""
    n = puzzle.size
    # Build a grid of labels
    cell_cage = puzzle._cell_cage
    # For display, show cage label + target+op in the top-left cell of each cage
    # Determine top-left-most cell of each cage
    cage_topleft: Dict[int, Cell] = {}
    for cage in puzzle.cages:
        top = min(cage.cells, key=lambda c: (c[0], c[1]))
        cage_topleft[id(cage)] = top
    lines: List[str] = []
    # Header
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
        # Value line (empty for unsolved)
        val_line = "|"
        for c in range(n):
            val_line += f"{'':^{cell_w}}|"
        lines.append(val_line)
    lines.append(sep)
    return "\n".join(lines)


def render_solution(grid: List[List[int]]) -> str:
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="KenKen puzzle generator and solver",
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
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a new KenKen puzzle")
    gen.add_argument("--size", type=int, default=5, help="Grid size (default 5)")
    gen.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    gen.add_argument("--seed", type=int, default=None, help="Random seed")
    gen.add_argument("--max-cage-size", type=int, default=4)
    gen.add_argument("--solve", action="store_true", help="Also print the solution")
    gen.add_argument("--output", "-o", type=str, default=None, help="Write puzzle JSON to file")
    gen.add_argument("--format", choices=["grid", "json", "both"], default="grid")

    sol = sub.add_parser("solve", help="Solve a puzzle from JSON")
    sol.add_argument("--input", "-i", type=str, required=True, help="Puzzle JSON file")
    sol.add_argument("--all", action="store_true", help="Find all solutions")
    sol.add_argument("--stats", action="store_true", help="Print solver statistics")

    ver = sub.add_parser("verify", help="Verify a puzzle has a unique solution")
    ver.add_argument("--input", "-i", type=str, required=True, help="Puzzle JSON file")

    args = parser.parse_args(argv)

    if args.command == "generate":
        gen_obj = KenKenGenerator(
            size=args.size,
            seed=args.seed,
            max_cage_size=args.max_cage_size,
            difficulty=args.difficulty,
        )
        puzzle = gen_obj.generate()
        if args.format in ("grid", "both"):
            print(render_puzzle(puzzle))
            print()
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
                print(render_solution(grid))
            else:
                print("No solution found.")
        return 0

    if args.command == "solve":
        with open(args.input) as f:
            puzzle = KenKenPuzzle.from_json(f.read())
        max_sol = 999999 if args.all else 1
        solver = KenKenSolver(puzzle, max_solutions=max_sol)
        solver.solve()
        if not solver.solutions:
            print("No solution found.")
            return 1
        for i, soln in enumerate(solver.solutions):
            grid = [[soln[(r, c)] for c in range(puzzle.size)] for r in range(puzzle.size)]
            if args.all:
                print(f"Solution {i + 1}:")
            print(render_solution(grid))
        if args.stats:
            print(f"\nSolver stats: {solver.stats}")
        return 0

    if args.command == "verify":
        with open(args.input) as f:
            puzzle = KenKenPuzzle.from_json(f.read())
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

    return 0


if __name__ == "__main__":
    sys.exit(main())