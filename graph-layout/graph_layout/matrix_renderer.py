"""Matrix renderer — produces an adjacency-matrix visualization as SVG.

The matrix renderer draws an n×n grid where cells are filled proportional
to edge weight.  Useful for visualizing graph structure independently of
any 2D layout.
"""

from __future__ import annotations

import html
from typing import Optional

from .graph import Graph


class MatrixRenderer:
    """Render a graph as an adjacency-matrix SVG heatmap.

    Args:
        cell_size: pixel size of each matrix cell.
        color: fill color for edges (hex or named color).
        bg: background color.
    """

    def __init__(self, cell_size: int = 20,
                 color: str = "#4a90d9",
                 bg: str = "white") -> None:
        self.cell_size = cell_size
        self.color = color
        self.bg = bg

    def render(self, graph: Graph) -> str:
        ids = list(graph.nodes)
        n = len(ids)
        if n == 0:
            return f'<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"/>'

        size = self.cell_size
        total = n * size
        margin = 40
        w = total + 2 * margin
        h = total + 2 * margin

        # build adjacency weight map
        weight_map = {}
        for e in graph.edges:
            weight_map[(e.source, e.target)] = e.weight
            if not e.directed:
                weight_map[(e.target, e.source)] = e.weight

        max_w = max((w for w in weight_map.values()), default=1.0)

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            f'<rect width="{w}" height="{h}" fill="{self.bg}"/>',
        ]

        # axis labels
        for i, nid in enumerate(ids):
            label = html.escape(str(nid)[:8])
            parts.append(f'<text x="{margin // 2}" '
                         f'y="{margin + i * size + size // 2 + 3}" '
                         f'font-size="8" text-anchor="end" '
                         f'fill="#666">{label}</text>')
            parts.append(f'<text x="{margin + i * size + size // 2}" '
                         f'y="{margin - 5}" font-size="8" '
                         f'text-anchor="middle" '
                         f'fill="#666">{label}</text>')

        # cells
        for i, ni in enumerate(ids):
            for j, nj in enumerate(ids):
                w_ij = weight_map.get((ni, nj), 0.0)
                if w_ij == 0:
                    continue
                alpha = min(1.0, w_ij / max_w) if max_w > 0 else 0
                x = margin + j * size
                y = margin + i * size
                # parse hex color for opacity overlay
                parts.append(
                    f'<rect x="{x}" y="{y}" '
                    f'width="{size - 1}" height="{size - 1}" '
                    f'fill="{self.color}" '
                    f'opacity="{alpha:.2f}"/>'
                )

        # grid border
        parts.append(f'<rect x="{margin - 1}" y="{margin - 1}" '
                     f'width="{total + 2}" height="{total + 2}" '
                     f'fill="none" stroke="#ccc" stroke-width="1"/>')

        parts.append('</svg>')
        return "\n".join(parts)

    def save(self, graph: Graph, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render(graph))


__all__ = ["MatrixRenderer"]