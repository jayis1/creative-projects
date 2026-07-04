"""
Rendering backends: ASCII art, PNG (pure stdlib), and SVG.

All renderers accept a :class:`~maze_solver.core.Maze` and an optional
solution path to highlight.
"""

from __future__ import annotations

import struct
import zlib
from typing import List, Optional, Set, Tuple

from .core import Cell, Direction, _ALL_DIRECTIONS


# --------------------------------------------------------------------------- #
# ASCII renderer
# --------------------------------------------------------------------------- #


def render_ascii(
    maze,
    solution: Optional[List[Tuple[int, int]]] = None,
    mark_start_end: bool = True,
) -> str:
    """Render the maze as an ASCII art string.

    Parameters
    ----------
    maze : Maze
        The maze to render.
    solution : list of (x, y), optional
        Solution path to highlight with ``·`` markers.
    mark_start_end : bool
        Mark start with ``S`` and end with ``E``.
    """
    sol_set: Set[Tuple[int, int]] = set(solution) if solution else set()
    grid_w = maze.width * 2 + 1
    grid_h = maze.height * 2 + 1
    grid: List[List[str]] = [
        [" " for _ in range(grid_w)] for _ in range(grid_h)
    ]

    for y in range(maze.height):
        for x in range(maze.width):
            cell = maze.cells[y][x]
            cx, cy = x * 2 + 1, y * 2 + 1
            # Walls
            if Direction.NORTH in cell.walls:
                grid[cy - 1][cx] = "-"
            if Direction.WEST in cell.walls:
                grid[cy][cx - 1] = "|"
            if Direction.SOUTH in cell.walls:
                grid[cy + 1][cx] = "-"
            if Direction.EAST in cell.walls:
                grid[cy][cx + 1] = "|"
            # Cell content
            coord = (x, y)
            if mark_start_end and coord == maze.start:
                grid[cy][cx] = "S"
            elif mark_start_end and coord == maze.end:
                grid[cy][cx] = "E"
            elif coord in sol_set:
                grid[cy][cx] = "·"

    # Fill all corner intersections.
    for y in range(0, grid_h, 2):
        for x in range(0, grid_w, 2):
            grid[y][x] = "+"

    # Draw solution path through passages (between cells).
    if solution and len(solution) > 1:
        for i in range(len(solution) - 1):
            x1, y1 = solution[i]
            x2, y2 = solution[i + 1]
            gx1, gy1 = x1 * 2 + 1, y1 * 2 + 1
            gx2, gy2 = x2 * 2 + 1, y2 * 2 + 1
            mid_x, mid_y = (gx1 + gx2) // 2, (gy1 + gy2) // 2
            if grid[mid_y][mid_x] in (" ", "|", "-"):
                grid[mid_y][mid_x] = "·"

    return "\n".join("".join(row) for row in grid)


def render_distance_map(
    maze,
    source: Optional[Tuple[int, int]] = None,
    max_width: int = 80,
) -> str:
    """Render a distance heatmap as ANSI-colored ASCII art.

    Cells are colored by distance from source using a grayscale
    gradient (ANSI 256-color codes 232–255).
    """
    dist = maze.distance_map(source)
    max_dist = max(d for row in dist for d in row if d >= 0)
    lines: List[str] = []
    for y in range(maze.height):
        line_parts: List[str] = []
        for x in range(maze.width):
            d = dist[y][x]
            if d < 0:
                line_parts.append("  ")
            elif max_dist == 0:
                line_parts.append("\033[38;5;21m██\033[0m")
            else:
                shade = 232 + int((d / max_dist) * 23)
                line_parts.append(f"\033[38;5;{shade}m██\033[0m")
        line = "".join(line_parts)
        if len(line) > max_width:
            line = line[:max_width] + "..."
        lines.append(line)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# PNG renderer (pure stdlib)
# --------------------------------------------------------------------------- #


def write_png(
    maze,
    path: str,
    cell_size: int = 10,
    wall_thickness: int = 2,
    solution: Optional[List[Tuple[int, int]]] = None,
) -> None:
    """Export the maze as a PNG file using only the standard library.

    Walls are drawn in black on a white background.  The start and end
    cells are marked with green and red respectively.  If a solution
    path is provided, it is drawn in blue.

    Parameters
    ----------
    maze : Maze
        The maze to export.
    path : str
        Output file path.
    cell_size : int
        Pixel size of each maze cell.
    wall_thickness : int
        Pixel thickness of walls.
    solution : list of (x, y), optional
        Solution path to draw in blue.
    """
    if cell_size < 2:
        raise ValueError("cell_size must be >= 2")
    if wall_thickness < 1:
        raise ValueError("wall_thickness must be >= 1")

    w = maze.width * cell_size + 1
    h = maze.height * cell_size + 1
    # RGB pixel buffer (3 bytes per pixel, row-major, top-to-bottom).
    pixels = bytearray([255, 255, 255] * (w * h))

    def set_pixel(px: int, py: int, r: int, g: int, b: int) -> None:
        if 0 <= px < w and 0 <= py < h:
            idx = (py * w + px) * 3
            pixels[idx] = r
            pixels[idx + 1] = g
            pixels[idx + 2] = b

    def fill_rect(x0: int, y0: int, x1: int, y1: int, r: int, g: int, b: int) -> None:
        for py in range(max(0, y0), min(h, y1)):
            for px in range(max(0, x0), min(w, x1)):
                set_pixel(px, py, r, g, b)

    # Draw walls in black.
    black = (0, 0, 0)
    for y in range(maze.height):
        for x in range(maze.width):
            cell = maze.cells[y][x]
            px0 = x * cell_size
            py0 = y * cell_size
            px1 = (x + 1) * cell_size
            py1 = (y + 1) * cell_size
            if Direction.NORTH in cell.walls:
                fill_rect(px0, py0, px1, py0 + wall_thickness, *black)
            if Direction.WEST in cell.walls:
                fill_rect(px0, py0, px0 + wall_thickness, py1, *black)
            if Direction.SOUTH in cell.walls:
                fill_rect(px0, py1 - wall_thickness, px1, py1 + 1, *black)
            if Direction.EAST in cell.walls:
                fill_rect(px1 - wall_thickness, py0, px1 + 1, py1, *black)

    # Draw solution path in blue if provided.
    if solution:
        blue = (50, 100, 255)
        for x, y in solution:
            fill_rect(
                x * cell_size + wall_thickness + 1,
                y * cell_size + wall_thickness + 1,
                (x + 1) * cell_size,
                (y + 1) * cell_size,
                *blue,
            )

    # Mark start (green) and end (red).
    sx, sy = maze.start
    fill_rect(
        sx * cell_size + wall_thickness + 1,
        sy * cell_size + wall_thickness + 1,
        (sx + 1) * cell_size,
        (sy + 1) * cell_size,
        0, 200, 0,
    )
    ex, ey = maze.end
    fill_rect(
        ex * cell_size + wall_thickness + 1,
        ey * cell_size + wall_thickness + 1,
        (ex + 1) * cell_size,
        (ey + 1) * cell_size,
        200, 0, 0,
    )

    _write_png_file(path, pixels, w, h)


def _write_png_file(path: str, pixels: bytearray, width: int, height: int) -> None:
    """Write an RGB pixel buffer to a PNG file using only the stdlib."""

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = make_chunk(b"IHDR", ihdr_data)
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter type: None
        raw.extend(pixels[y * stride:(y + 1) * stride])
    compressed = zlib.compress(bytes(raw), level=9)
    idat = make_chunk(b"IDAT", compressed)
    iend = make_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(signature)
        f.write(ihdr)
        f.write(idat)
        f.write(iend)


# --------------------------------------------------------------------------- #
# SVG renderer
# --------------------------------------------------------------------------- #


def write_svg(
    maze,
    path: str,
    cell_size: int = 20,
    wall_width: int = 2,
    solution: Optional[List[Tuple[int, int]]] = None,
) -> None:
    """Export the maze as an SVG (Scalable Vector Graphics) file.

    SVGs are resolution-independent and can be scaled to any size
    without quality loss — ideal for printing or web display.

    Parameters
    ----------
    maze : Maze
        The maze to export.
    path : str
        Output file path.
    cell_size : int
        Pixel size of each maze cell in the SVG coordinate system.
    wall_width : int
        Stroke width for walls.
    solution : list of (x, y), optional
        Solution path to draw as a colored polyline.
    """
    if cell_size < 2:
        raise ValueError("cell_size must be >= 2")

    w = maze.width * cell_size + wall_width
    h = maze.height * cell_size + wall_width
    lines: List[str] = []

    # SVG header.
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    )
    # White background.
    lines.append(f'<rect width="{w}" height="{h}" fill="white"/>')

    # Draw walls as SVG lines.
    for y in range(maze.height):
        for x in range(maze.width):
            cell = maze.cells[y][x]
            px = x * cell_size
            py = y * cell_size
            if Direction.NORTH in cell.walls:
                lines.append(
                    f'<line x1="{px}" y1="{py}" '
                    f'x2="{px + cell_size}" y2="{py}" '
                    f'stroke="black" stroke-width="{wall_width}"/>'
                )
            if Direction.WEST in cell.walls:
                lines.append(
                    f'<line x1="{px}" y1="{py}" '
                    f'x2="{px}" y2="{py + cell_size}" '
                    f'stroke="black" stroke-width="{wall_width}"/>'
                )
            # Only draw south/east walls for edge cells to avoid
            # duplicate lines (shared walls drawn from one side).
            if y == maze.height - 1 and Direction.SOUTH in cell.walls:
                lines.append(
                    f'<line x1="{px}" y1="{py + cell_size}" '
                    f'x2="{px + cell_size}" y2="{py + cell_size}" '
                    f'stroke="black" stroke-width="{wall_width}"/>'
                )
            if x == maze.width - 1 and Direction.EAST in cell.walls:
                lines.append(
                    f'<line x1="{px + cell_size}" y1="{py}" '
                    f'x2="{px + cell_size}" y2="{py + cell_size}" '
                    f'stroke="black" stroke-width="{wall_width}"/>'
                )

    # Draw solution path as a polyline.
    if solution and len(solution) > 1:
        points = " ".join(
            f"{x * cell_size + cell_size // 2},{y * cell_size + cell_size // 2}"
            for x, y in solution
        )
        lines.append(
            f'<polyline points="{points}" '
            f'fill="none" stroke="#3264FF" stroke-width="{max(1, wall_width)}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    # Mark start (green circle) and end (red circle).
    sx, sy = maze.start
    cx_s = sx * cell_size + cell_size // 2
    cy_s = sy * cell_size + cell_size // 2
    lines.append(
        f'<circle cx="{cx_s}" cy="{cy_s}" r="{cell_size // 3}" '
        f'fill="#00C800"/>'
    )
    ex, ey = maze.end
    cx_e = ex * cell_size + cell_size // 2
    cy_e = ey * cell_size + cell_size // 2
    lines.append(
        f'<circle cx="{cx_e}" cy="{cy_e}" r="{cell_size // 3}" '
        f'fill="#C80000"/>'
    )

    lines.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))