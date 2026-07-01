"""
Nonogram file I/O — load and save puzzles in multiple formats.

Supported formats:
  - JSON  (native, with optional grid state)
  - NON   (compact text format used by many nonogram collections)
  - PNG   (render the solution/filled board as an image using stdlib only)
"""

from __future__ import annotations

import json
import zlib
import struct
from pathlib import Path
from typing import List, Optional

from nonogram.board import Board, Cell


class PuzzleIO:
    """Read and write nonogram puzzles in various formats."""

    # ------------------------------------------------------------------ #
    # JSON
    # ------------------------------------------------------------------ #
    @staticmethod
    def load_json(path: str) -> Board:
        data = json.loads(Path(path).read_text())
        return Board.from_dict(data)

    @staticmethod
    def save_json(board: Board, path: str, include_grid: bool = True) -> None:
        d: dict = {"row_clues": board.row_clues, "col_clues": board.col_clues}
        if include_grid:
            d["grid"] = [[c.value for c in row] for row in board.grid]
        Path(path).write_text(json.dumps(d, indent=2))

    # ------------------------------------------------------------------ #
    # NON format (compact text)
    # ------------------------------------------------------------------ #
    #  First line:  width height
    #  Next height lines: row clues (space-separated, '0' for empty row)
    #  Next width  lines: col clues (space-separated, '0' for empty col)
    @staticmethod
    def load_non(path: str) -> Board:
        lines = Path(path).read_text().strip().split("\n")
        if len(lines) < 2:
            raise ValueError("NON file too short")
        w, h = (int(x) for x in lines[0].split())
        # Validate we have enough lines: 1 header + h row clues + w col clues
        expected_lines = 1 + h + w
        if len(lines) < expected_lines:
            raise ValueError(
                f"NON file has {len(lines)} lines but needs "
                f"{expected_lines} (1 + {h} rows + {w} cols)"
            )
        idx = 1
        row_clues: List[List[int]] = []
        for _ in range(h):
            parts = [int(x) for x in lines[idx].split()]
            row_clues.append([x for x in parts if x > 0])
            idx += 1
        col_clues: List[List[int]] = []
        for _ in range(w):
            parts = [int(x) for x in lines[idx].split()]
            col_clues.append([x for x in parts if x > 0])
            idx += 1
        return Board(row_clues, col_clues)

    @staticmethod
    def save_non(board: Board, path: str) -> None:
        lines: List[str] = [f"{board.width} {board.height}"]
        for clue in board.row_clues:
            lines.append(" ".join(str(x) for x in clue) if clue else "0")
        for clue in board.col_clues:
            lines.append(" ".join(str(x) for x in clue) if clue else "0")
        Path(path).write_text("\n".join(lines) + "\n")

    # ------------------------------------------------------------------ #
    # PNG export (pure stdlib — minimal valid PNG)
    # ------------------------------------------------------------------ #
    @staticmethod
    def save_png(board: Board, path: str, cell_size: int = 20,
                 unknown_color=(200, 200, 200),
                 empty_color=(255, 255, 255),
                 filled_color=(40, 40, 40)) -> None:
        """Render the board as a PNG image using only the standard library."""
        w, h = board.width, board.height
        img_w = w * cell_size
        img_h = h * cell_size

        # Build raw pixel data (RGB) — one filter byte per image row.
        raw = bytearray()
        for r in range(h):
            for sub in range(cell_size):
                raw.append(0)  # filter byte (0 = None)
                for c in range(w):
                    cell = board.grid[r][c]
                    if cell is Cell.FILLED:
                        color = filled_color
                    elif cell is Cell.EMPTY:
                        color = empty_color
                    else:
                        color = unknown_color
                    raw.extend(bytes(color) * cell_size)

        compressed = zlib.compress(bytes(raw))

        def _chunk(chunk_type: bytes, data: bytes) -> bytes:
            c = chunk_type + data
            crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return struct.pack(">I", len(data)) + c + crc

        # PNG signature
        png = b"\x89PNG\r\n\x1a\n"
        # IHDR
        ihdr = struct.pack(">IIBBBBB", img_w, img_h, 8, 2, 0, 0, 0)  # 8-bit RGB
        png += _chunk(b"IHDR", ihdr)
        # IDAT
        png += _chunk(b"IDAT", compressed)
        # IEND
        png += _chunk(b"IEND", b"")

        Path(path).write_bytes(png)

    # ------------------------------------------------------------------ #
    # SVG export
    # ------------------------------------------------------------------ #
    @staticmethod
    def save_svg(board: Board, path: str, cell_size: int = 20) -> None:
        """Render the board as an SVG file."""
        w, h = board.width, board.height
        total_w = w * cell_size
        total_h = h * cell_size
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{total_w}" height="{total_h}" '
            f'viewBox="0 0 {total_w} {total_h}">'
        ]
        parts.append(f'<rect width="{total_w}" height="{total_h}" fill="white"/>')
        for r in range(h):
            for c in range(w):
                cell = board.grid[r][c]
                x = c * cell_size
                y = r * cell_size
                if cell is Cell.FILLED:
                    parts.append(
                        f'<rect x="{x}" y="{y}" width="{cell_size}" '
                        f'height="{cell_size}" fill="#333"/>'
                    )
                elif cell is Cell.UNKNOWN:
                    parts.append(
                        f'<rect x="{x}" y="{y}" width="{cell_size}" '
                        f'height="{cell_size}" fill="#ccc"/>'
                    )
        # Grid lines.
        for i in range(w + 1):
            x = i * cell_size
            parts.append(
                f'<line x1="{x}" y1="0" x2="{x}" y2="{total_h}" '
                f'stroke="#999" stroke-width="0.5"/>'
            )
        for i in range(h + 1):
            y = i * cell_size
            parts.append(
                f'<line x1="0" y1="{y}" x2="{total_w}" y2="{y}" '
                f'stroke="#999" stroke-width="0.5"/>'
            )
        parts.append("</svg>")
        Path(path).write_text("\n".join(parts))