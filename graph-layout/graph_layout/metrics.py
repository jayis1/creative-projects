"""Layout quality metrics.

Quantitative measures of how "good" a layout is, independent of aesthetics.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from .graph import Graph


class LayoutMetrics:
    """Compute quality metrics for a positioned graph."""

    @staticmethod
    def edge_length_variance(graph: Graph) -> float:
        """Variance of edge lengths (lower = more uniform)."""
        lengths = []
        for e in graph.edges:
            n1, n2 = graph.nodes[e.source], graph.nodes[e.target]
            if n1.x is None or n2.x is None:
                continue
            lengths.append(math.hypot(n1.x - n2.x, n1.y - n2.y))
        if not lengths:
            return 0.0
        mean = sum(lengths) / len(lengths)
        return sum((l - mean) ** 2 for l in lengths) / len(lengths)

    @staticmethod
    def crossing_count(graph: Graph) -> int:
        """Count the number of edge crossings (O(E²) brute force)."""
        edges = graph.edges
        count = 0

        def seg_cross(p1, p2, p3, p4):
            """Do segments p1p2 and p3p4 properly cross?"""
            def ccw(a, b, c):
                return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            d1 = ccw(p3, p4, p1)
            d2 = ccw(p3, p4, p2)
            d3 = ccw(p1, p2, p3)
            d4 = ccw(p1, p2, p4)
            if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
               ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
                return True
            # collinear overlaps — skip for simplicity
            return False

        pts = {}
        for nid, node in graph.nodes.items():
            if node.x is not None:
                pts[nid] = (node.x, node.y)

        for i in range(len(edges)):
            e1 = edges[i]
            if e1.source not in pts or e1.target not in pts:
                continue
            for j in range(i + 1, len(edges)):
                e2 = edges[j]
                if e2.source not in pts or e2.target not in pts:
                    continue
                # skip shared endpoints
                if e1.source in (e2.source, e2.target) or \
                   e1.target in (e2.source, e2.target):
                    continue
                if seg_cross(pts[e1.source], pts[e1.target],
                             pts[e2.source], pts[e2.target]):
                    count += 1
        return count

    @staticmethod
    def angular_resolution(graph: Graph) -> float:
        """Minimum angle between adjacent edges at any node (radians).

        Higher is better (closer to 2π/deg).
        """
        min_angle = float("inf")
        for nid, node in graph.nodes.items():
            if node.x is None:
                continue
            nbrs = graph.neighbors(nid)
            if len(nbrs) < 2:
                continue
            angles = []
            for nb in nbrs:
                other = graph.nodes.get(nb)
                if other is None or other.x is None:
                    continue
                angles.append(math.atan2(other.y - node.y, other.x - node.x))
            angles.sort()
            for i in range(len(angles)):
                diff = angles[(i + 1) % len(angles)] - angles[i]
                if diff < 0:
                    diff += 2 * math.pi
                if diff < min_angle:
                    min_angle = diff
        return min_angle if min_angle != float("inf") else 2 * math.pi

    @staticmethod
    def aspect_ratio(graph: Graph) -> float:
        """Ratio of width to height of the bounding box."""
        xs = [n.x for n in graph.nodes.values() if n.x is not None]
        ys = [n.y for n in graph.nodes.values() if n.y is not None]
        if not xs or not ys:
            return 1.0
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        if h == 0:
            return float("inf") if w > 0 else 1.0
        return w / h

    @staticmethod
    def stress(graph: Graph) -> float:
        """Stress value comparing realized Euclidean distances to graph distances."""
        dists = graph.shortest_path_lengths()
        total = 0.0
        count = 0
        ids = list(graph.nodes)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                d_graph = dists.get((ids[i], ids[j]), dists.get((ids[j], ids[i])))
                if d_graph is None or d_graph == 0:
                    continue
                n1, n2 = graph.nodes[ids[i]], graph.nodes[ids[j]]
                if n1.x is None or n2.x is None:
                    continue
                d_real = math.hypot(n1.x - n2.x, n1.y - n2.y)
                if d_graph == 0:
                    continue
                total += ((d_real - d_graph) / d_graph) ** 2
                count += 1
        return total / count if count else 0.0

    @staticmethod
    def node_overlap(graph: Graph, threshold: float = 1.0) -> int:
        """Count pairs of nodes closer than ``threshold`` (overlapping)."""
        nodes = [n for n in graph.nodes.values() if n.x is not None]
        count = 0
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                d = math.hypot(nodes[i].x - nodes[j].x,
                               nodes[i].y - nodes[j].y)
                if d < threshold:
                    count += 1
        return count

    @staticmethod
    def all_metrics(graph: Graph) -> Dict[str, float]:
        """Return a dict of all metrics."""
        return {
            "edge_length_variance": LayoutMetrics.edge_length_variance(graph),
            "crossing_count": float(LayoutMetrics.crossing_count(graph)),
            "angular_resolution": LayoutMetrics.angular_resolution(graph),
            "aspect_ratio": LayoutMetrics.aspect_ratio(graph),
            "stress": LayoutMetrics.stress(graph),
            "node_overlap": float(LayoutMetrics.node_overlap(graph)),
        }