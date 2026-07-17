"""ASCII visualization helpers for orbits and ground tracks.

Produces terminal-friendly plots using only standard-library text
formatting — no matplotlib dependency.  Useful for quick CLI demos
and CI logs.
"""
from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import numpy as np

from .elements import StateVector


def ascii_orbit_xy(
    states: Sequence[StateVector],
    width: int = 60,
    height: int = 30,
    title: str = "Orbit (XY plane)",
) -> str:
    """Render an orbit's XY projection as an ASCII art plot.

    Parameters
    ----------
    states : sequence of StateVector
        Propagated states forming the orbit.
    width, height : int
        Character dimensions of the plot.
    title : str
        Title shown above the plot.

    Returns
    -------
    str
        Multi-line ASCII plot.
    """
    if not states:
        return title + "\n(no data)"

    xs = np.array([s.r[0] for s in states])
    ys = np.array([s.r[1] for s in states])
    xmin, xmax = float(xs.min()), float(xs.max())
    ymin, ymax = float(ys.min()), float(ys.max())
    # Pad ranges by 5%.
    dx = (xmax - xmin) * 0.05 or 1.0
    dy = (ymax - ymin) * 0.05 or 1.0
    xmin -= dx; xmax += dx
    ymin -= dy; ymax += dy

    grid = [[" "] * width for _ in range(height)]

    def to_cell(x: float, y: float) -> Tuple[int, int]:
        col = int((x - xmin) / (xmax - xmin) * (width - 1))
        row = int((1.0 - (y - ymin) / (ymax - ymin)) * (height - 1))
        return max(0, min(width - 1, col)), max(0, min(height - 1, row))

    # Draw axes if they fall inside the plot.
    if xmin <= 0 <= xmax:
        c, _ = to_cell(0, ymin)
        for r in range(height):
            grid[r][c] = "│" if grid[r][c] == " " else grid[r][c]
    if ymin <= 0 <= ymax:
        _, r = to_cell(xmin, 0)
        for c in range(width):
            grid[r][c] = "─" if grid[r][c] == " " else grid[r][c]

    # Draw orbit path.
    for x, y in zip(xs, ys):
        c, r = to_cell(float(x), float(y))
        if grid[r][c] in (" ", "│", "─"):
            grid[r][c] = "•"

    # Mark start and end.
    c0, r0 = to_cell(float(xs[0]), float(ys[0]))
    grid[r0][c0] = "S"
    cN, rN = to_cell(float(xs[-1]), float(ys[-1]))
    grid[rN][cN] = "E"

    lines = [title]
    for row in grid:
        lines.append("".join(row))
    lines.append(f"x: [{xmin/1000:.0f}, {xmax/1000:.0f}] km  "
                 f"y: [{ymin/1000:.0f}, {ymax/1000:.0f}] km  "
                 f"(S=start, E=end)")
    return "\n".join(lines)


def ascii_ground_track(
    points: Sequence[Tuple[float, float]],
    width: int = 72,
    height: int = 24,
    title: str = "Ground Track",
) -> str:
    """Render a ground track (lat/lon) as an ASCII world map outline.

    Latitude ranges [-90, 90]°, longitude [-180, 180]°.
    """
    grid = [[" "] * width for _ in range(height)]

    def to_cell(lat: float, lon: float) -> Tuple[int, int]:
        col = int((lon + 180.0) / 360.0 * (width - 1))
        row = int((90.0 - lat) / 180.0 * (height - 1))
        return max(0, min(width - 1, col)), max(0, min(height - 1, row))

    # Equator and prime meridian.
    _, eq_row = to_cell(0.0, -180.0)
    for c in range(width):
        grid[eq_row][c] = "·"
    pm_col, _ = to_cell(90.0, 0.0)
    for r in range(height):
        grid[r][pm_col] = "·"

    # Track.
    for lat, lon in points:
        c, r = to_cell(math.degrees(lat), math.degrees(lon))
        grid[r][c] = "*"

    lines = [title]
    for row in grid:
        lines.append("".join(row))
    lines.append("lat: [-90, 90]°  lon: [-180, 180]°  (* = sub-satellite point)")
    return "\n".join(lines)


def ascii_porkchop(
    data: Sequence[Tuple[float, float, float]],
    width: int = 50,
    height: int = 20,
    title: str = "Porkchop Plot (C3 = |v1|²)",
) -> str:
    """Render a porkchop plot (TOF vs C3) as ASCII art.

    ``data`` is a list of ``(tof, |v1|, |v2|)`` tuples from
    :func:`orbital.maneuvers.porkchop_data`.
    """
    if not data:
        return title + "\n(no data)"

    tofs = [d[0] for d in data]
    c3s = [d[1] ** 2 for d in data]
    tmin, tmax = min(tofs), max(tofs)
    cmin, cmax = min(c3s), max(c3s)
    if cmax == cmin:
        cmax = cmin + 1.0

    grid = [[" "] * width for _ in range(height)]
    for tof, c3 in zip(tofs, c3s):
        col = int((tof - tmin) / (tmax - tmin) * (width - 1))
        # Lower C3 → higher on the plot (better).
        row = int((1.0 - (c3 - cmin) / (cmax - cmin)) * (height - 1))
        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))
        # Use a density character.
        grid[row][col] = "█"

    lines = [title]
    for row in grid:
        lines.append("".join(row))
    lines.append(f"TOF: [{tmin:.0f}, {tmax:.0f}] s   "
                 f"C3: [{cmin:.0f}, {cmax:.0f}] km²/s²")
    return "\n".join(lines)