"""SVG rendering of curves and surfaces."""

from __future__ import annotations

from typing import Sequence, List

from .bspline import BSplineCurve
from .nurbs_curve import NURBSCurve
from .nurbs_surface import NURBSSurface
from .export import tessellate_curve, tessellate_surface


def curve_to_svg(
    curve: "BSplineCurve | NURBSCurve",
    samples: int = 100,
    width: int = 400,
    height: int = 400,
    stroke: str = "black",
    stroke_width: float = 2.0,
    show_control_polygon: bool = True,
) -> str:
    """Render a 2-D curve as an SVG string.

    The curve must be 2-D (x, y).  The view-box auto-fits to the data.
    """
    pts = tessellate_curve(curve, samples)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    # Include control polygon in bounds.
    cp = curve.control_points
    if show_control_polygon:
        for c in cp:
            x_min = min(x_min, c[0])
            x_max = max(x_max, c[0])
            y_min = min(y_min, c[1])
            y_max = max(y_max, c[1])

    margin = 20
    data_w = x_max - x_min or 1.0
    data_h = y_max - y_min or 1.0
    scale = min((width - 2 * margin) / data_w, (height - 2 * margin) / data_h)

    def tx(x: float) -> float:
        return margin + (x - x_min) * scale

    def ty(y: float) -> float:
        # Flip y for SVG.
        return height - margin - (y - y_min) * scale

    path_parts: List[str] = []
    for i, p in enumerate(pts):
        cmd = "M" if i == 0 else "L"
        path_parts.append(f"{cmd} {tx(p[0]):.2f} {ty(p[1]):.2f}")

    elements: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]

    if show_control_polygon:
        cp_parts: List[str] = []
        for i, c in enumerate(cp):
            cmd = "M" if i == 0 else "L"
            cp_parts.append(f"{cmd} {tx(c[0]):.2f} {ty(c[1]):.2f}")
        elements.append(
            f'<path d="{" ".join(cp_parts)}" fill="none" '
            f'stroke="#ccc" stroke-width="1" stroke-dasharray="4 2"/>'
        )
        for c in cp:
            elements.append(
                f'<circle cx="{tx(c[0]):.2f}" cy="{ty(c[1]):.2f}" r="3" fill="#aaa"/>'
            )

    elements.append(
        f'<path d="{" ".join(path_parts)}" fill="none" '
        f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )
    elements.append("</svg>")
    return "\n".join(elements)


def surface_to_svg_wireframe(
    surface: NURBSSurface,
    samples_u: int = 20,
    samples_v: int = 20,
    width: int = 400,
    height: int = 400,
) -> str:
    """Render a 3-D surface as a wireframe SVG (isometric projection)."""
    (u0, u1), (v0, v1) = surface.parameter_range
    # Sample grid.
    grid: List[List[List[float]]] = []
    for i in range(samples_u):
        row: List[List[float]] = []
        for j in range(samples_v):
            u = u0 + (i / (samples_u - 1)) * (u1 - u0)
            v = v0 + (j / (samples_v - 1)) * (v1 - v0)
            row.append(surface.evaluate(u, v))
        grid.append(row)

    # Isometric projection.
    def project(p: List[float]) -> List[float]:
        x, y, z = p[0], p[1], p[2]
        return [
            (x - y) * 0.866,
            (x + y) * 0.5 - z,
        ]

    pts2d = [[project(p) for p in row] for row in grid]
    xs = [p[0] for row in pts2d for p in row]
    ys = [p[1] for row in pts2d for p in row]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    margin = 20
    dw = x_max - x_min or 1.0
    dh = y_max - y_min or 1.0
    scale = min((width - 2 * margin) / dw, (height - 2 * margin) / dh)

    def tx(x: float) -> float:
        return margin + (x - x_min) * scale

    def ty(y: float) -> float:
        return height - margin - (y - y_min) * scale

    elements: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]

    # U-direction lines.
    for i in range(samples_u):
        parts = []
        for j in range(samples_v):
            p = pts2d[i][j]
            cmd = "M" if j == 0 else "L"
            parts.append(f"{cmd} {tx(p[0]):.2f} {ty(p[1]):.2f}")
        elements.append(
            f'<path d="{" ".join(parts)}" fill="none" stroke="blue" stroke-width="0.8" opacity="0.6"/>'
        )
    # V-direction lines.
    for j in range(samples_v):
        parts = []
        for i in range(samples_u):
            p = pts2d[i][j]
            cmd = "M" if i == 0 else "L"
            parts.append(f"{cmd} {tx(p[0]):.2f} {ty(p[1]):.2f}")
        elements.append(
            f'<path d="{" ".join(parts)}" fill="none" stroke="red" stroke-width="0.8" opacity="0.6"/>'
        )

    elements.append("</svg>")
    return "\n".join(elements)