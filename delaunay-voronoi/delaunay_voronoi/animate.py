"""
Animated SVG rendering for Lloyd relaxation sequences.

Produces a self-contained SVG file with ``<animate>`` elements that
cross-fade between successive relaxation steps — viewable in any
modern browser without JavaScript.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .geometry import Edge, Point
from .render import _esc


def render_animated_svg(
    frames: List[List[Point]],
    width: int = 800,
    height: int = 600,
    delaunay_edges_per_frame: Optional[List[List[Edge]]] = None,
    voronoi_edges_per_frame: Optional[List[List[Edge]]] = None,
    frame_duration_ms: int = 800,
    background: str = "#0f0f17",
    point_color: str = "#5bc0be",
    delaunay_color: str = "#3a506b",
    voronoi_color: str = "#e0a458",
    point_radius: float = 4.0,
) -> str:
    """Render an animated SVG showing Lloyd relaxation frames.

    Each frame's point set fades in while the previous fades out, creating
    a smooth transition.  All frames share a single timeline.
    """
    n_frames = len(frames)
    if n_frames == 0:
        return f'<svg width="{width}" height="{height}"></svg>'

    total_duration = n_frames * frame_duration_ms
    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{_esc(background)}"/>',
        f'<style>@keyframes f{{0%,100%{{opacity:0}}'
        f'{100.0 / (2 * n_frames):.1f}%,{100.0 - 100.0 / (2 * n_frames):.1f}%{{opacity:1}}}}'
        f'.frame{{animation:f {total_duration}ms infinite;opacity:0}}'
        f'</style>',
    ]

    for i, pts in enumerate(frames):
        delay = i * frame_duration_ms
        parts.append(f'<g class="frame" style="animation-delay:{delay}ms">')
        if delaunay_edges_per_frame and i < len(delaunay_edges_per_frame):
            for e in delaunay_edges_per_frame[i]:
                parts.append(
                    f'<line x1="{e.a.x:.3f}" y1="{e.a.y:.3f}" '
                    f'x2="{e.b.x:.3f}" y2="{e.b.y:.3f}" '
                    f'stroke="{_esc(delaunay_color)}" stroke-width="0.5" '
                    f'opacity="0.4"/>'
                )
        if voronoi_edges_per_frame and i < len(voronoi_edges_per_frame):
            for e in voronoi_edges_per_frame[i]:
                parts.append(
                    f'<line x1="{e.a.x:.3f}" y1="{e.a.y:.3f}" '
                    f'x2="{e.b.x:.3f}" y2="{e.b.y:.3f}" '
                    f'stroke="{_esc(voronoi_color)}" stroke-width="0.8"/>'
                )
        for p in pts:
            parts.append(
                f'<circle cx="{p.x:.3f}" cy="{p.y:.3f}" r="{point_radius}" '
                f'fill="{_esc(point_color)}"/>'
            )
        parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)


def render_lloyd_animation(
    points: List[Point],
    iterations: int = 10,
    width: int = 800,
    height: int = 600,
    frame_duration_ms: int = 600,
    seed: Optional[int] = None,
) -> str:
    """Convenience: run Lloyd relaxation and return an animated SVG."""
    from .delaunay import DelaunayTriangulation
    from .voronoi import VoronoiDiagram
    from .lloyd import lloyd_relaxation

    box = (Point(0, 0), Point(width, height))
    frames: List[List[Point]] = [list(points)]
    delaunay_edges: List[List[Edge]] = []
    voronoi_edges: List[List[Edge]] = []

    current = list(points)
    dt = DelaunayTriangulation.from_points(current)
    vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
    delaunay_edges.append(dt.edges())
    voronoi_edges.append(vd.edges)

    for _ in range(iterations):
        current = lloyd_relaxation(current, iterations=1, clip_box=box, seed=seed)
        frames.append(list(current))
        dt = DelaunayTriangulation.from_points(current)
        vd = VoronoiDiagram.from_delaunay(dt, clip_box=box)
        delaunay_edges.append(dt.edges())
        voronoi_edges.append(vd.edges)

    return render_animated_svg(
        frames=frames,
        width=width,
        height=height,
        delaunay_edges_per_frame=delaunay_edges,
        voronoi_edges_per_frame=voronoi_edges,
        frame_duration_ms=frame_duration_ms,
    )