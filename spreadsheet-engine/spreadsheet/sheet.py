"""
Sheet — a 2D grid of cells with formulas, values, and dependency tracking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .cell import Cell, CellError, CellType, ErrorType, format_a1, parse_a1


class Sheet:
    """
    A spreadsheet sheet: a sparse 2D grid of Cell objects keyed by (row, col).

    Sheets belong to an Engine which manages multi-sheet references and
    recalculation.  Each sheet tracks:
      - cells: dict[(row,col)] -> Cell
      - name: sheet name
    """

    def __init__(self, name: str = "Sheet1", max_rows: int = 1048576, max_cols: int = 16384):
        self.name = name
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.cells: Dict[Tuple[int, int], Cell] = {}

    # ---- cell access ----

    def get_cell(self, row: int, col: int) -> Cell:
        """Return the Cell at (row, col), creating an empty one if needed."""
        if row < 0 or col < 0 or row >= self.max_rows or col >= self.max_cols:
            raise IndexError(f"Cell ({row}, {col}) out of bounds")
        key = (row, col)
        if key not in self.cells:
            self.cells[key] = Cell(row=row, col=col)
        return self.cells[key]

    def get(self, row: int, col: int) -> Any:
        """Get the computed value of a cell (None if empty)."""
        cell = self.cells.get((row, col))
        if cell is None or cell.is_empty():
            return None
        return cell.value

    def set(self, row: int, col: int, raw: str) -> None:
        """Set a cell's raw text.  Parsing/formula evaluation handled by Engine."""
        cell = self.get_cell(row, col)
        cell.raw = raw
        cell.deps.clear()
        cell.formula = None
        cell.value = None
        cell.type = CellType.EMPTY
        if raw == "":
            cell.clear()
            # remove from sparse dict to keep it truly sparse
            if (row, col) in self.cells:
                del self.cells[(row, col)]
            return
        # classify the cell
        stripped = raw.strip()
        if stripped.startswith("="):
            cell.type = CellType.FORMULA
        else:
            # try number
            try:
                cell.value = float(stripped)
                cell.type = CellType.NUMBER
            except ValueError:
                # try boolean
                low = stripped.lower()
                if low == "true":
                    cell.value = True
                    cell.type = CellType.BOOLEAN
                elif low == "false":
                    cell.value = False
                    cell.type = CellType.BOOLEAN
                else:
                    cell.value = stripped
                    cell.type = CellType.STRING

    def set_value(self, row: int, col: int, value: Any) -> None:
        """Set a cell directly with a Python value (not a formula string)."""
        cell = self.get_cell(row, col)
        cell.deps.clear()
        cell.formula = None
        if value is None:
            cell.clear()
            return
        cell.raw = str(value)
        if isinstance(value, bool):
            cell.value = value
            cell.type = CellType.BOOLEAN
            cell.raw = "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            cell.value = float(value)
            cell.type = CellType.NUMBER
        elif isinstance(value, str):
            cell.value = value
            cell.type = CellType.STRING
        elif isinstance(value, CellError):
            cell.value = value
            cell.type = CellType.ERROR
        else:
            cell.value = str(value)
            cell.type = CellType.STRING

    # ---- convenience via A1 notation ----

    def get_a1(self, ref: str) -> Any:
        row, col = parse_a1(ref)
        return self.get(row, col)

    def set_a1(self, ref: str, raw: str) -> None:
        row, col = parse_a1(ref)
        self.set(row, col, raw)

    # ---- iteration ----

    def non_empty_cells(self) -> List[Cell]:
        return [c for c in self.cells.values() if not c.is_empty()]

    def used_range(self) -> Tuple[int, int, int, int]:
        """Return (min_row, min_col, max_row, max_col) of used cells.
        Returns (0,0,0,0) if sheet is empty."""
        if not self.cells:
            return (0, 0, 0, 0)
        rows = [c.row for c in self.cells.values() if not c.is_empty()]
        cols = [c.col for c in self.cells.values() if not c.is_empty()]
        if not rows:
            return (0, 0, 0, 0)
        return (min(rows), min(cols), max(rows), max(cols))

    # ---- display ----

    def to_grid(self, max_rows: int = 20, max_cols: int = 10) -> str:
        """Render the used portion of the sheet as an ASCII grid."""
        if not self.cells:
            return "(empty sheet)"
        mr, mc, xr, xc = self.used_range()
        mr = max(0, mr)
        mc = max(0, mc)
        xr = min(xr, mr + max_rows - 1)
        xc = min(xc, mc + max_cols - 1)

        # column widths
        col_widths = {}
        for c in range(mc, xc + 1):
            w = len(format_a1(0, c))
            for r in range(mr, xr + 1):
                cell = self.cells.get((r, c))
                val = "" if cell is None or cell.is_empty() else _format_value(cell.value)
                w = max(w, len(val))
            col_widths[c] = min(w + 1, 16)

        # header row
        header = "    " + "".join(
            format_a1(0, c).rjust(col_widths[c]) for c in range(mc, xc + 1)
        )
        lines = [header]
        for r in range(mr, xr + 1):
            row_label = f"{r + 1:>3} "
            row_str = row_label + "".join(
                _format_value(self.get(r, c)).rjust(col_widths[c])
                if self.get(r, c) is not None
                else "".rjust(col_widths[c])
                for c in range(mc, xc + 1)
            )
            lines.append(row_str)
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"Sheet(name={self.name!r}, cells={len(self.cells)})"


def _format_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return f"{v:.6g}"
    if isinstance(v, CellError):
        return str(v)
    return str(v)