"""Exact-cover polyomino tiling solver using bit-mask Algorithm X.

Each legal placement is a row in the exact-cover matrix. Recursive search
chooses the uncovered cell with the fewest compatible placements (MRV).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Placement:
    piece: int
    cells: tuple[tuple[int, int], ...]
    mask: int


def normalize(cells: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """Translate coordinates so the minimum row and column are zero."""
    points = tuple(cells)
    if not points:
        raise ValueError("a piece orientation cannot be empty")
    r0 = min(r for r, _ in points)
    c0 = min(c for _, c in points)
    return tuple(sorted((r-r0, c-c0) for r, c in points))


def orientations(piece: Iterable[tuple[int, int]], reflections: bool = True):
    """Return distinct rotations (and optionally reflections) of a piece."""
    base = normalize(piece)
    if len(set(base)) != len(base):
        raise ValueError("piece contains duplicate cells")
    seen = set()
    for mirror in ((1, -1) if reflections else (1,)):
        for turns in range(4):
            pts = [(r, mirror*c) for r, c in base]
            for _ in range(turns):
                pts = [(c, -r) for r, c in pts]
            shape = normalize(pts)
            if shape not in seen:
                seen.add(shape)
                yield shape


class TilingSolver:
    """Solve a board tiling where every board cell and piece is used once."""

    def __init__(self, board: Iterable[tuple[int, int]], pieces: Iterable[Iterable[tuple[int, int]]], *, reflections: bool = True):
        self.board = tuple(sorted(set(board)))
        if not self.board:
            raise ValueError("board must contain at least one cell")
        if len(self.board) != len(tuple(board)):
            raise ValueError("board contains duplicate cells")
        self.cell_index = {cell: i for i, cell in enumerate(self.board)}
        self.pieces = tuple(normalize(p) for p in pieces)
        if not self.pieces or any(not p for p in self.pieces):
            raise ValueError("at least one non-empty piece is required")
        if sum(map(len, self.pieces)) != len(self.board):
            raise ValueError("total piece area must equal board area")
        self.all_cells = (1 << len(self.board)) - 1
        self.placements: list[Placement] = []
        self.by_cell: list[list[int]] = [[] for _ in self.board]
        for pi, piece in enumerate(self.pieces):
            for shape in orientations(piece, reflections):
                height = max(r for r, _ in shape) + 1
                width = max(c for _, c in shape) + 1
                for dr in range(max(r for r, _ in self.board) + 1):
                    for dc in range(max(c for _, c in self.board) + 1):
                        cells = tuple((dr+r, dc+c) for r, c in shape)
                        if all(cell in self.cell_index for cell in cells):
                            mask = sum(1 << self.cell_index[cell] for cell in cells)
                            index = len(self.placements)
                            self.placements.append(Placement(pi, cells, mask))
                            for bit in range(len(self.board)):
                                if mask >> bit & 1:
                                    self.by_cell[bit].append(index)

    def solve(self, limit: int = 1) -> list[list[Placement]]:
        """Return up to limit tilings; identical pieces are treated as distinct."""
        if limit < 1:
            raise ValueError("limit must be positive")
        results = []
        used_pieces = 0

        def search(occupied: int, chosen: list[Placement]):
            nonlocal used_pieces
            if len(results) >= limit:
                return
            if occupied == self.all_cells:
                results.append(chosen.copy())
                return
            best = None
            options = None
            for cell_id in range(len(self.board)):
                bit = 1 << cell_id
                if occupied & bit:
                    continue
                valid = []
                for idx in self.by_cell[cell_id]:
                    p = self.placements[idx]
                    if not (p.mask & occupied) and not (used_pieces >> p.piece & 1):
                        valid.append(p)
                if options is None or len(valid) < len(options):
                    best, options = cell_id, valid
                    if not options:
                        return
            for placement in options or ():
                used_pieces |= 1 << placement.piece
                chosen.append(placement)
                search(occupied | placement.mask, chosen)
                chosen.pop()
                used_pieces ^= 1 << placement.piece
                if len(results) >= limit:
                    return
        search(0, [])
        return results


def render(board: Iterable[tuple[int, int]], solution: Iterable[Placement]) -> str:
    """Render a solution as an ASCII board; disconnected cells use dots."""
    labels = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    cells = set(board)
    placements = tuple(solution)
    if not cells:
        raise ValueError("board must contain at least one cell")
    if len(placements) > len(labels):
        raise ValueError("ASCII renderer supports at most 62 pieces")
    out = []
    for r in range(max(x for x, _ in cells) + 1):
        out.append("")
        row = []
        for c in range(max(y for _, y in cells) + 1):
            if (r, c) not in cells:
                row.append(" ")
            else:
                row.append("?")
                for i, placement in enumerate(solution):
                    if (r, c) in placement.cells:
                        row[-1] = labels[placement.piece]
                        break
        out[-1] = "".join(row).rstrip()
    return "\n".join(out)
