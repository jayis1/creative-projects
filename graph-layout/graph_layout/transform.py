"""Transform utilities: scale-to-fit, normalize, rotate, translate layouts."""

from __future__ import annotations

import math
from typing import Tuple

from .graph import Graph


def bounding_box(graph: Graph) -> Tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y). Returns (0,0,0,0) if no nodes."""
    xs = [n.x for n in graph.nodes.values() if n.x is not None]
    ys = [n.y for n in graph.nodes.values() if n.y is not None]
    if not xs or not ys:
        return 0.0, 0.0, 0.0, 0.0
    return min(xs), min(ys), max(xs), max(ys)


def scale_to_fit(graph: Graph, width: float, height: float,
                 margin: float = 20.0) -> Graph:
    """Scale and translate the graph to fit within (width, height) with margin."""
    minx, miny, maxx, maxy = bounding_box(graph)
    span_x = maxx - minx
    span_y = maxy - miny
    if span_x <= 0 and span_y <= 0:
        for n in graph.iter_nodes():
            n.x = width / 2
            n.y = height / 2
        return graph
    avail_w = max(1, width - 2 * margin)
    avail_h = max(1, height - 2 * margin)
    sx = avail_w / span_x if span_x > 0 else 1.0
    sy = avail_h / span_y if span_y > 0 else 1.0
    scale = min(sx, sy)
    tx = (width - span_x * scale) / 2 - minx * scale
    ty = (height - span_y * scale) / 2 - miny * scale
    for n in graph.iter_nodes():
        if n.x is not None:
            n.x = n.x * scale + tx
        if n.y is not None:
            n.y = n.y * scale + ty
    return graph


def normalize(graph: Graph) -> Graph:
    """Scale positions to unit square [0, 1] × [0, 1]."""
    return scale_to_fit(graph, 1.0, 1.0, margin=0.0)


def translate(graph: Graph, dx: float, dy: float) -> Graph:
    """Translate all nodes by (dx, dy)."""
    for n in graph.iter_nodes():
        if n.x is not None:
            n.x += dx
        if n.y is not None:
            n.y += dy
    return graph


def rotate(graph: Graph, angle_rad: float, cx: float = 0, cy: float = 0) -> Graph:
    """Rotate all node positions by ``angle_rad`` around (cx, cy)."""
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    for n in graph.iter_nodes():
        if n.x is None or n.y is None:
            continue
        dx = n.x - cx
        dy = n.y - cy
        n.x = cx + dx * cos_a - dy * sin_a
        n.y = cy + dx * sin_a + dy * cos_a
    return graph


def center_on_origin(graph: Graph) -> Graph:
    """Translate so the centroid of positions is at (0, 0)."""
    minx, miny, maxx, maxy = bounding_box(graph)
    cx = (minx + maxx) / 2
    cy = (miny + maxy) / 2
    return translate(graph, -cx, -cy)