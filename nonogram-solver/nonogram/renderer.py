"""
Renderers for nonogram boards.

Provides colored ASCII, HTML, and SVG output beyond the plain ``Board.render()``.
"""

from __future__ import annotations

from typing import List

from nonogram.board import Board, Cell


class Renderer:
    """Multiple output formats for nonogram boards."""

    # ANSI color codes
    _FILLED = "\033[48;5;235m"  # dark background
    _EMPTY = "\033[48;5;255m"   # light background
    _UNKNOWN = "\033[48;5;244m" # grey
    _RESET = "\033[0m"
    _BOLD = "\033[1m"

    @staticmethod
    def ansi(board: Board) -> str:
        """Colored ANSI terminal rendering with clues."""
        lines: List[str] = []

        # Calculate column clue display height.
        max_col_clue_len = max((len(c) for c in board.col_clues), default=1)
        max_row_clue_width = max(
            (len(" ".join(str(x) for x in clue)) for clue in board.row_clues),
            default=0,
        )

        # Column clues (vertical).
        for ci in range(max_col_clue_len):
            prefix = " " * max_row_clue_width + " "
            parts = []
            for c in range(board.width):
                if ci < len(board.col_clues[c]):
                    parts.append(str(board.col_clues[c][ci]))
                else:
                    parts.append(" ")
            lines.append(prefix + " ".join(parts))

        # Rows.
        for r in range(board.height):
            clue_str = " ".join(str(x) for x in board.row_clues[r])
            clue_str = clue_str.rjust(max_row_clue_width)
            row_parts = []
            for c in range(board.width):
                cell = board.grid[r][c]
                if cell is Cell.FILLED:
                    row_parts.append(f"{Renderer._FILLED}  {Renderer._RESET}")
                elif cell is Cell.EMPTY:
                    row_parts.append(f"{Renderer._EMPTY}  {Renderer._RESET}")
                else:
                    row_parts.append(f"{Renderer._UNKNOWN}  {Renderer._RESET}")
            lines.append(f"{clue_str} {''.join(row_parts)}")

        return "\n".join(lines)

    @staticmethod
    def html(board: Board, title: str = "Nonogram") -> str:
        """Render the board as a self-contained HTML page with clues."""
        max_col_clue_len = max((len(c) for c in board.col_clues), default=1)
        parts = [
            "<!DOCTYPE html>",
            '<html><head><meta charset="utf-8">',
            f"<title>{title}</title>",
            "<style>",
            "table { border-collapse: collapse; }",
            "td { width: 24px; height: 24px; text-align: center; "
            "border: 1px solid #ddd; font-family: monospace; font-size: 12px; }",
            ".filled { background: #333; }",
            ".empty { background: #fff; }",
            ".unknown { background: #ccc; }",
            ".clue { background: #f5f5f5; font-weight: bold; }",
            "</style></head><body>",
            f"<h2>{title}</h2>",
            "<table>",
        ]

        # Column clue rows.
        for ci in range(max_col_clue_len):
            parts.append("<tr>")
            # Empty corner cell.
            parts.append('<td class="clue"></td>')
            for c in range(board.width):
                val = board.col_clues[c][ci] if ci < len(board.col_clues[c]) else ""
                parts.append(f'<td class="clue">{val}</td>')
            parts.append("</tr>")

        # Board rows.
        for r in range(board.height):
            parts.append("<tr>")
            # Row clue cell.
            clue_str = " ".join(str(x) for x in board.row_clues[r])
            parts.append(f'<td class="clue">{clue_str}</td>')
            for c in range(board.width):
                cell = board.grid[r][c]
                cls = "filled" if cell is Cell.FILLED else (
                    "empty" if cell is Cell.EMPTY else "unknown"
                )
                parts.append(f'<td class="{cls}"></td>')
            parts.append("</tr>")

        parts.append("</table></body></html>")
        return "\n".join(parts)