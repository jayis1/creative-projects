"""
Karnaugh map (K-map) renderer.

Renders a boolean function as a 2-D K-map with Gray-code ordering of rows and
columns.  Supports 2–5 variables (K-maps above 5 variables are hard to read and
not commonly used).

Layouts
-------
* 2 vars: 2 rows × 2 cols
* 3 vars: 2 rows × 4 cols
* 4 vars: 4 rows × 4 cols
* 5 vars: 4 rows × 8 cols (two 4×4 maps side by side for the 5th variable)
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .boolean import BooleanFunction, var_names


def gray_code(n: int) -> List[int]:
    """Return the n-bit Gray code sequence as a list of integers."""
    if n <= 0:
        return [0]
    result = [0, 1]
    for bit in range(1, n):
        result = result + [x | (1 << bit) for x in reversed(result)]
    return result


class KarnaughMap:
    """Render a boolean function as a K-map.

    Parameters
    ----------
    func : BooleanFunction
        The function to visualize.
    """

    def __init__(self, func: BooleanFunction) -> None:
        if func.n_vars < 2 or func.n_vars > 5:
            raise ValueError("K-map supports 2–5 variables")
        self.func = func
        self.n_vars = func.n_vars

    def render(self) -> str:
        """Render the K-map as an ASCII table."""
        n = self.n_vars
        # Split variables into row-vars and col-vars
        if n == 2:
            row_vars, col_vars = 1, 1
        elif n == 3:
            row_vars, col_vars = 1, 2
        elif n == 4:
            row_vars, col_vars = 2, 2
        else:  # 5
            row_vars, col_vars = 2, 3
        row_grays = gray_code(row_vars)
        col_grays = gray_code(col_vars)
        names = var_names(n)
        row_names = names[:row_vars]
        col_names = names[row_vars:row_vars + col_vars]
        # Build the grid
        lines: List[str] = []
        # Header
        col_header = " ".join(col_names) if col_names else ""
        if col_vars > 0:
            header = f"{'  '.join(row_names):>6} |"
            for cg in col_grays:
                header += f" {format(cg, f'0{col_vars}b'):>{col_vars}} "
            lines.append(header)
            lines.append("-" * len(header))
        else:
            header = f"{'  '.join(row_names):>6} | f"
            lines.append(header)
            lines.append("-" * len(header))
        # Rows
        for rg in row_grays:
            row_str = f"{format(rg, f'0{row_vars}b'):>6} |"
            for cg in col_grays:
                # compose the full minterm index
                minterm = (rg << col_vars) | cg
                if minterm in self.func.minterms:
                    sym = "1"
                elif minterm in self.func.dontcare:
                    sym = "-"
                else:
                    sym = "0"
                row_str += f" {sym:>{col_vars}} "
            lines.append(row_str)
        return "\n".join(lines)

    def render_with_coverage(self, cubes: Sequence[str]) -> str:
        """Render the K-map marking cells covered by the given cubes.

        Covered on-set cells are shown as ``[1]``, uncovered as `` 1``,
        don't-cares as `` -``, and off-set as `` 0``.
        """
        from .boolean import cube_covers
        n = self.n_vars
        if n == 2:
            row_vars, col_vars = 1, 1
        elif n == 3:
            row_vars, col_vars = 1, 2
        elif n == 4:
            row_vars, col_vars = 2, 2
        else:
            row_vars, col_vars = 2, 3
        row_grays = gray_code(row_vars)
        col_grays = gray_code(col_vars)
        names = var_names(n)
        row_names = names[:row_vars]
        col_names = names[row_vars:row_vars + col_vars]
        lines: List[str] = []
        if col_vars > 0:
            header = f"{'  '.join(row_names):>6} |"
            for cg in col_grays:
                header += f" {format(cg, f'0{col_vars}b'):>{col_vars + 2}} "
            lines.append(header)
            lines.append("-" * len(header))
        for rg in row_grays:
            row_str = f"{format(rg, f'0{row_vars}b'):>6} |"
            for cg in col_grays:
                minterm = (rg << col_vars) | cg
                if minterm in self.func.minterms:
                    covered = any(cube_covers(c, minterm) for c in cubes)
                    sym = "[1]" if covered else " 1 "
                elif minterm in self.func.dontcare:
                    sym = " - "
                else:
                    sym = " 0 "
                row_str += f" {sym:>{col_vars + 2}} "
            lines.append(row_str)
        return "\n".join(lines)