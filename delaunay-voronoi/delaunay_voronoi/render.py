"""
Rendering utilities: SVG (vector) and PPM (raster) output.

SVG is the preferred format — crisp, human-readable, and viewable in any
browser.  PPM is provided for environments without XML tooling and as a
minimal raster fallback.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .geometry import Edge, Point, Triangle


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_svg(
    width: int = 800,
    height: int = 600,
    delaunay_triangles: Optional[List[Triangle]] = None,
    delaunay_edges: Optional[List[Edge]] = None,
    voronoi_edges: Optional[List[Edge]] = None,
    points: Optional[List[Point]] = None,
    hull: Optional[List[Point]] = None,
    background: str = "#0f0f17",
    delaunay_color: str = "#3a506b",
    voronoi_color: str = "#e0a458",
    point_color: str = "#5bc0be",
    hull_color: str = "#9bf6ff",
    point_radius: float = 3.0,
    show_points: bool = True,
    show_delaunay: bool = True,
    show_voronoi: bool = True,
) -> str:
    """Render a diagram to an SVG string.

    Coordinates are assumed to be in pixel space already. If your data is in a
    different range, pre-scale the points.
    """
    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{_esc(background)}"/>',
    ]

    if show_delaunay and delaunay_edges:
        for e in delaunay_edges:
            parts.append(
                f'<line x1="{e.a.x:.3f}" y1="{e.a.y:.3f}" x2="{e.b.x:.3f}" '
                f'y2="{e.b.y:.3f}" stroke="{_esc(delaunay_color)}" '
                f'stroke-width="0.6" opacity="0.5"/>'
            )

    if show_voronoi and voronoi_edges:
        for e in voronoi_edges:
            parts.append(
                f'<line x1="{e.a.x:.3f}" y1="{e.a.y:.3f}" x2="{e.b.x:.3f}" '
                f'y2="{e.b.y:.3f}" stroke="{_esc(voronoi_color)}" '
                f'stroke-width="1.0"/>'
            )

    if hull and len(hull) >= 2:
        path_pts = " ".join(f"{p.x:.3f},{p.y:.3f}" for p in hull)
        parts.append(
            f'<polygon points="{path_pts}" fill="none" '
            f'stroke="{_esc(hull_color)}" stroke-width="1.5"/>'
        )

    if show_points and points:
        for p in points:
            parts.append(
                f'<circle cx="{p.x:.3f}" cy="{p.y:.3f}" r="{point_radius}" '
                f'fill="{_esc(point_color)}"/>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def render_ppm(
    width: int,
    height: int,
    points: List[Point],
    voronoi_cells: Optional[dict] = None,
    background: Tuple[int, int, int] = (15, 15, 23),
    point_color: Tuple[int, int, int] = (91, 192, 190),
    cell_colors: Optional[List[Tuple[int, int, int]]] = None,
) -> bytes:
    """Render a flat-shaded Voronoi diagram to PPM (P6 binary) bytes.

    Each pixel is coloured according to the nearest site (a brute-force
    O(width*height*n) computation suitable for modest images / demos).
    """
    if not points:
        return b"P6\n%d %d\n255\n" % (width, height) + bytes(
            background for _ in range(width * height)
        )

    # Map cells to colours
    site_colors: dict = {}
    n = len(points)
    for i, p in enumerate(points):
        if cell_colors and i < len(cell_colors):
            site_colors[p] = cell_colors[i]
        else:
            # Deterministic pseudo-random colour
            r = (i * 47) % 256
            g = (i * 113) % 256
            b = (i * 197) % 256
            site_colors[p] = (r, g, b)

    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            best = None
            best_d = float("inf")
            for p in points:
                d = (p.x - x) ** 2 + (p.y - y) ** 2
                if d < best_d:
                    best_d = d
                    best = p
            color = site_colors[best]
            pixels.extend(color)

    # Draw points on top
    for p in points:
        px = int(p.x)
        py = int(p.y)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = px + dx, py + dy
                if 0 <= nx < width and 0 <= ny < height:
                    idx = (ny * width + nx) * 3
                    pixels[idx : idx + 3] = bytes(point_color)

    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    return header + bytes(pixels)