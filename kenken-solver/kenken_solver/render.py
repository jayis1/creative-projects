"""ASCII rendering utilities for KenKen puzzles and solutions."""

from __future__ import annotations

from typing import Dict, List, Optional

from kenken_solver.puzzle import KenKenPuzzle
from kenken_solver.types import Cell


def render_puzzle(puzzle: KenKenPuzzle) -> str:
    """Render the puzzle as an ASCII grid showing cage targets and operators.

    Each cage's target and operator are shown in the top-left cell of that
    cage (determined by reading order).
    """
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


def render_solved_puzzle(
    puzzle: KenKenPuzzle, grid: Optional[List[List[int]]]
) -> str:
    """Render the puzzle with both cage labels (top) and solution values (bottom).

    If *grid* is ``None`` (no solution), renders the puzzle without values.
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


__all__ = [
    "render_puzzle",
    "render_solution",
    "render_cage_map",
    "render_solved_puzzle",
]