"""Renderers: SVG, ASCII, and plain-text output for laid-out graphs."""

from __future__ import annotations

import html
import math
from typing import Optional, Tuple

from .graph import Graph


def _bounds(graph: Graph, default_w: float = 1000, default_h: float = 1000):
    xs = [n.x for n in graph.nodes.values() if n.x is not None]
    ys = [n.y for n in graph.nodes.values() if n.y is not None]
    if not xs or not ys:
        return 0, 0, default_w, default_h
    return min(xs), min(ys), max(xs), max(ys)


class SVGRenderer:
    """Render a positioned graph to an SVG string."""

    def __init__(self, width: int = 800, height: int = 600,
                 node_radius: float = 12, show_labels: bool = True,
                 bg: str = "white", edge_color: str = "#999",
                 node_color: str = "#4a90d9", text_color: str = "white") -> None:
        self.width = width
        self.height = height
        self.node_radius = node_radius
        self.show_labels = show_labels
        self.bg = bg
        self.edge_color = edge_color
        self.node_color = node_color
        self.text_color = text_color

    def render(self, graph: Graph) -> str:
        minx, miny, maxx, maxy = _bounds(graph, self.width, self.height)
        span_x = max(1, maxx - minx)
        span_y = max(1, maxy - miny)
        margin = 30
        scale = min((self.width - 2 * margin) / span_x,
                    (self.height - 2 * margin) / span_y)

        def tx(x: float) -> float:
            return margin + (x - minx) * scale

        def ty(y: float) -> float:
            return margin + (y - miny) * scale

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">',
            f'<rect width="{self.width}" height="{self.height}" fill="{self.bg}"/>',
        ]

        # edges
        for e in graph.edges:
            n1, n2 = graph.nodes.get(e.source), graph.nodes.get(e.target)
            if not n1 or not n2 or n1.x is None or n2.x is None:
                continue
            x1, y1 = tx(n1.x), ty(n1.y)
            x2, y2 = tx(n2.x), ty(n2.y)
            attrs = f'stroke="{self.edge_color}" stroke-width="1.5"'
            if e.directed:
                attrs += ' marker-end="url(#arrow)"'
            parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
                         f'x2="{x2:.1f}" y2="{y2:.1f}" {attrs}/>')

        # arrow marker
        parts.append(
            '<defs><marker id="arrow" markerWidth="10" markerHeight="10" '
            'refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
            f'<path d="M0,0 L0,6 L9,3 z" fill="{self.edge_color}"/>'
            '</marker></defs>'
        )

        # nodes
        for nid, node in graph.nodes.items():
            if node.x is None:
                continue
            cx, cy = tx(node.x), ty(node.y)
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" '
                         f'r="{self.node_radius}" fill="{self.node_color}"/>')
            if self.show_labels:
                label = html.escape(str(nid))
                parts.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" '
                             f'text-anchor="middle" font-size="10" '
                             f'fill="{self.text_color}">{label}</text>')

        parts.append('</svg>')
        return "\n".join(parts)

    def save(self, graph: Graph, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render(graph))


class ASCIIRenderer:
    """Render a positioned graph as an ASCII art grid."""

    def __init__(self, width: int = 70, height: int = 25) -> None:
        self.width = width
        self.height = height

    def render(self, graph: Graph) -> str:
        minx, miny, maxx, maxy = _bounds(graph, self.width, self.height)
        span_x = max(1, maxx - minx)
        span_y = max(1, maxy - miny)
        grid = [[" "] * self.width for _ in range(self.height)]

        def to_cell(x: float, y: float) -> Tuple[int, int]:
            cx = int((x - minx) / span_x * (self.width - 1))
            cy = int((y - miny) / span_y * (self.height - 1))
            return cx, cy

        # draw edges with Bresenham
        for e in graph.edges:
            n1, n2 = graph.nodes.get(e.source), graph.nodes.get(e.target)
            if not n1 or not n2 or n1.x is None or n2.x is None:
                continue
            x0, y0 = to_cell(n1.x, n1.y)
            x1, y1 = to_cell(n2.x, n2.y)
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx - dy
            while True:
                if 0 <= y0 < self.height and 0 <= x0 < self.width:
                    if grid[y0][x0] == " ":
                        grid[y0][x0] = "-" if abs(x1 - x0) > abs(y1 - y0) else "|"
                    elif grid[y0][x0] not in ("+",):
                        grid[y0][x0] = "+"
                if x0 == x1 and y0 == y1:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if e2 < dx:
                    err += dx
                    y0 += sy

        # draw nodes
        for nid, node in graph.nodes.items():
            if node.x is None:
                continue
            cx, cy = to_cell(node.x, node.y)
            if 0 <= cy < self.height and 0 <= cx < self.width:
                ch = nid[0] if nid else "*"
                grid[cy][cx] = ch.upper() if len(nid) == 1 else "o"

        return "\n".join("".join(row) for row in grid)

    def save(self, graph: Graph, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render(graph))


class TextRenderer:
    """Render a positioned graph as a plain-text node/edge list."""

    def render(self, graph: Graph) -> str:
        lines = [f"Graph: {graph.node_count} nodes, {graph.edge_count} edges"]
        lines.append("")
        lines.append("Nodes:")
        for nid, node in graph.nodes.items():
            pos = f"({node.x:.2f}, {node.y:.2f})" if node.x is not None else "(unpositioned)"
            lines.append(f"  {nid}: {pos}")
        lines.append("")
        lines.append("Edges:")
        for e in graph.edges:
            arrow = "->" if e.directed else "--"
            lines.append(f"  {e.source} {arrow} {e.target}  (w={e.weight})")
        return "\n".join(lines)

    def save(self, graph: Graph, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render(graph))