"""ASCII mesh preview — render a 3-D triangle mesh as a 2-D ASCII art image.

Projects the mesh vertices orthographically onto the XY plane (or a chosen
view axis), discretises into a character grid, and shades each cell by the
density of projected triangles.  This gives a quick visual preview without
any graphics dependencies.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from .mesh import Mesh


def render_ascii_preview(
    mesh: Mesh,
    width: int = 70,
    height: int = 24,
    view: str = "xy",
) -> str:
    """Render *mesh* as an ASCII art image.

    Parameters
    ----------
    width, height : int
        Dimensions of the character grid.
    view : str
        Projection plane: ``"xy"`` (front), ``"xz"`` (top), or ``"yz"`` (side).
    """
    if mesh.num_vertices == 0:
        return "(empty mesh)"

    # Determine bounding box in the chosen projection plane
    if view == "xy":
        axes = (0, 1)
    elif view == "xz":
        axes = (0, 2)
    elif view == "yz":
        axes = (1, 2)
    else:
        raise ValueError(f"unknown view {view!r}; use 'xy', 'xz', or 'yz'")

    ax, ay = axes
    xs = [v[ax] for v in mesh.vertices]
    ys = [v[ay] for v in mesh.vertices]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Guard against degenerate meshes
    x_span = x_max - x_min
    y_span = y_max - y_min
    if x_span < 1e-12:
        x_span = 1.0
    if y_span < 1e-12:
        y_span = 1.0

    # Accumulate a density grid
    grid = [[0.0] * width for _ in range(height)]

    # For each triangle, rasterise its projection into the grid
    for (ia, ib, ic) in mesh.faces:
        va = mesh.vertices[ia]
        vb = mesh.vertices[ib]
        vc = mesh.vertices[ic]
        # Project to 2D
        p0 = (va[ax], va[ay])
        p1 = (vb[ax], vb[ay])
        p2 = (vc[ax], vc[ay])
        _rasterize_triangle(p0, p1, p2, grid, width, height,
                            x_min, x_span, y_min, y_span)

    # Find max density for normalisation
    max_d = max(max(row) for row in grid) if grid else 0.0
    if max_d < 1e-12:
        max_d = 1.0

    # Shade characters: from sparse to dense
    # Use a gradient of ASCII characters
    shade = " .:-=+*#%@"
    # Note: grid[0] is the top row (y_max), so we iterate in reverse y order
    lines: List[str] = []
    for row_idx in range(height - 1, -1, -1):
        row = grid[row_idx]
        line = []
        for cell in row:
            t = min(cell / max_d, 1.0)
            idx = int(t * (len(shade) - 1))
            line.append(shade[idx])
        lines.append("".join(line))
    return "\n".join(lines)


def _rasterize_triangle(
    p0: Tuple[float, float], p1: Tuple[float, float], p2: Tuple[float, float],
    grid: List[List[float]], width: int, height: int,
    x_min: float, x_span: float, y_min: float, y_span: float,
) -> None:
    """Rasterise a 2-D triangle into the density grid."""
    # Convert to grid coordinates
    def to_grid(px, py):
        gx = int((px - x_min) / x_span * (width - 1))
        gy = int((py - y_min) / y_span * (height - 1))
        return max(0, min(width - 1, gx)), max(0, min(height - 1, gy))

    g0 = to_grid(*p0)
    g1 = to_grid(*p1)
    g2 = to_grid(*p2)

    # Bounding box of the triangle in grid space
    min_x = max(0, min(g0[0], g1[0], g2[0]))
    max_x = min(width - 1, max(g0[0], g1[0], g2[0]))
    min_y = max(0, min(g0[1], g1[1], g2[1]))
    max_y = min(height - 1, max(g0[1], g1[1], g2[1]))

    # Test each grid cell in the bounding box
    for gy in range(min_y, max_y + 1):
        for gx in range(min_x, max_x + 1):
            # Point-in-triangle test (barycentric)
            if _point_in_triangle(gx, gy, g0, g1, g2):
                grid[gy][gx] += 1.0


def _point_in_triangle(
    px: int, py: int,
    p0: Tuple[int, int], p1: Tuple[int, int], p2: Tuple[int, int],
) -> bool:
    """Barycentric point-in-triangle test."""
    d = (p1[1] - p2[1]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[1] - p2[1])
    if abs(d) < 1e-12:
        return False
    a = ((p1[1] - p2[1]) * (px - p2[0]) + (p2[0] - p1[0]) * (py - p2[1])) / d
    b = ((p2[1] - p0[1]) * (px - p2[0]) + (p0[0] - p2[0]) * (py - p2[1])) / d
    c = 1.0 - a - b
    return a >= 0 and b >= 0 and c >= 0