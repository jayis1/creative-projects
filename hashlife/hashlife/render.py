"""ASCII rendering of the Hashlife universe (or any set of live cells)."""

from __future__ import annotations

from typing import Iterable, Tuple


def render(cells: Iterable[Tuple[int, int]],
           x_range=None, y_range=None,
           alive: str = "O", dead: str = ".",
           ) -> str:
    """Render a region of the universe as an ASCII grid.

    Parameters
    ----------
    cells : iterable of (x, y)
        Live cell coordinates.  Accepts a set, list, generator, or the
        result of :meth:`Hashlife.get_live_cells`.
    x_range, y_range : (start, stop) tuples, optional
        The half-open range of coordinates to render.  If omitted, the
        bounding box of *cells* (with a 1-cell border) is used.
    alive, dead : str
        Characters used for live / dead cells.
    """
    cells = list(cells)
    if not cells:
        return dead
    if x_range is None:
        xs = [c[0] for c in cells]
        x_range = (min(xs) - 1, max(xs) + 2)
    if y_range is None:
        ys = [c[1] for c in cells]
        y_range = (min(ys) - 1, max(ys) + 2)

    x0, x1 = x_range
    y0, y1 = y_range
    width = x1 - x0
    if width <= 0:
        return dead

    cell_set = set(cells)
    lines = []
    for y in range(y0, y1):
        row = []
        for x in range(x0, x1):
            row.append(alive if (x, y) in cell_set else dead)
        lines.append("".join(row))
    return "\n".join(lines)