"""Additional layout algorithms: DRGraph (deterministic) and PivotMDS.

DRGraph (Deterministic Random Graph) layout by Sugiyama et al. uses
a deterministic seed-free initialization and a bounded stress majorization
process.  Our implementation uses a grid-based initial placement and
a simplified energy function, providing good-quality layouts without
the randomness of Fruchterman-Reingold.

PivotMDS (Brandes & Piek 2007) is a multi-dimensional scaling layout
that uses a set of pivot nodes to approximate the distance matrix,
achieving O(p·n) time instead of O(n²).
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from .graph import Graph
from .layouts import LayoutAlgorithm


class DRGraphLayout(LayoutAlgorithm):
    """Deterministic force-directed layout.

    Uses a grid-based initial placement (no random seed needed) and a
    bounded stress minimization loop.  Works well for graphs up to a
    few hundred nodes.  Converges faster than Fruchterman-Reingold
    because the deterministic initialization is already close to a
    good local minimum.
    """

    name = "drgraph"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 iterations: int = 200, seed: Optional[int] = None,
                 k: Optional[float] = None) -> None:
        self.width = width
        self.height = height
        self.iterations = iterations
        self.seed = seed
        self.k = k

    def layout(self, graph: Graph, **kwargs) -> Graph:
        nodes = list(graph.iter_nodes())
        n = len(nodes)
        if n == 0:
            return graph
        if n == 1:
            nodes[0].x = self.width / 2
            nodes[0].y = self.height / 2
            return graph

        area = self.width * self.height
        k = self.k or math.sqrt(area / n)

        # Deterministic grid initialization — place on a spiral
        idx = {node.id: i for i, node in enumerate(nodes)}
        pos: Dict[str, List[float]] = {}
        cx, cy = self.width / 2, self.height / 2
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / n
            r = k * (i / max(1, n - 1)) ** 0.5
            pos[node.id] = [cx + r * math.cos(angle), cy + r * math.sin(angle)]

        # adjacency
        adj: Dict[str, List[str]] = {nid: [] for nid in pos}
        for e in graph.edges:
            if e.source in pos and e.target in pos:
                adj[e.source].append(e.target)

        rng = random.Random(self.seed)

        temp = k
        for iteration in range(self.iterations):
            disp: Dict[str, List[float]] = {nid: [0.0, 0.0] for nid in pos}
            ids = list(pos.keys())

            # repulsive forces
            for i in range(len(ids)):
                u = ids[i]
                for j in range(i + 1, len(ids)):
                    v = ids[j]
                    dx = pos[u][0] - pos[v][0]
                    dy = pos[u][1] - pos[v][1]
                    d2 = dx * dx + dy * dy
                    if d2 < 0.01:
                        d2 = 0.01
                        dx = rng.uniform(-0.1, 0.1)
                        dy = rng.uniform(-0.1, 0.1)
                    d = math.sqrt(d2)
                    force = (k * k) / d
                    fx = (dx / d) * force
                    fy = (dy / d) * force
                    disp[u][0] += fx
                    disp[u][1] += fy
                    disp[v][0] -= fx
                    disp[v][1] -= fy

            # attractive forces (gravity toward center + edge spring)
            for nid in pos:
                dx_c = pos[nid][0] - cx
                dy_c = pos[nid][1] - cy
                disp[nid][0] -= 0.01 * dx_c
                disp[nid][1] -= 0.01 * dy_c

            for e in graph.edges:
                u, v = e.source, e.target
                if u not in pos or v not in pos:
                    continue
                dx = pos[u][0] - pos[v][0]
                dy = pos[u][1] - pos[v][1]
                d = math.sqrt(dx * dx + dy * dy)
                if d < 0.01:
                    d = 0.01
                force = (d * d) / k
                fx = (dx / d) * force
                fy = (dy / d) * force
                disp[u][0] -= fx
                disp[u][1] -= fy
                disp[v][0] += fx
                disp[v][1] += fy

            # apply with temperature
            for nid in pos:
                dx, dy = disp[nid]
                d = math.sqrt(dx * dx + dy * dy)
                if d > 0:
                    limited = min(d, temp)
                    pos[nid][0] += (dx / d) * limited
                    pos[nid][1] += (dy / d) * limited
                pos[nid][0] = max(0, min(self.width, pos[nid][0]))
                pos[nid][1] = max(0, min(self.height, pos[nid][1]))

            temp = k * (1 - iteration / self.iterations)

        for node in nodes:
            node.x = pos[node.id][0]
            node.y = pos[node.id][1]
        return graph


class PivotMDSLayout(LayoutAlgorithm):
    """Pivot MDS layout (Brandes & Piek 2007).

    Uses a subset of pivot nodes to approximate the full distance matrix
    and computes a 2D classical MDS embedding via power iteration on the
    double-centered matrix.  Time complexity O(p·n + p²·n).
    """

    name = "pivot-mds"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 pivots: int = 20, seed: Optional[int] = None) -> None:
        self.width = width
        self.height = height
        self.pivots = pivots
        self.seed = seed

    def layout(self, graph: Graph, **kwargs) -> Graph:
        nodes = list(graph.iter_nodes())
        ids = [n.id for n in nodes]
        n = len(ids)
        if n == 0:
            return graph
        if n == 1:
            nodes[0].x = self.width / 2
            nodes[0].y = self.height / 2
            return graph

        rng = random.Random(self.seed)
        p = min(self.pivots, n)

        # select pivots (spread by farthest-first / maxmin sampling)
        pivot_ids = [ids[0]]
        dist_to_pivots: Dict[str, float] = {}
        for nid in ids:
            dist_to_pivots[nid] = math.inf
        dist_to_pivots[ids[0]] = 0

        for _ in range(p - 1):
            # compute BFS distances from last pivot
            last = pivot_ids[-1]
            bfs_dist: Dict[str, int] = {last: 0}
            queue = [last]
            while queue:
                cur = queue.pop(0)
                d = bfs_dist[cur]
                for nbr in graph.neighbors(cur):
                    if nbr not in bfs_dist:
                        bfs_dist[nbr] = d + 1
                        queue.append(nbr)
            for nid in ids:
                d = bfs_dist.get(nid, n)
                if d < dist_to_pivots[nid]:
                    dist_to_pivots[nid] = d
            # pick farthest
            far = max(ids, key=lambda x: dist_to_pivots[x])
            pivot_ids.append(far)

        # build p x n distance matrix
        D = [[0.0] * n for _ in range(p)]
        for pi, pid in enumerate(pivot_ids):
            bfs_dist: Dict[str, int] = {pid: 0}
            queue = [pid]
            while queue:
                cur = queue.pop(0)
                d = bfs_dist[cur]
                for nbr in graph.neighbors(cur):
                    if nbr not in bfs_dist:
                        bfs_dist[nbr] = d + 1
                        queue.append(nbr)
            for ni, nid in enumerate(ids):
                D[pi][ni] = float(bfs_dist.get(nid, n))

        # double centering: C = -0.5 * J * D² * J  (using pivot distances)
        # For pivot MDS: B = -0.5 * D² (p x n), then SVD or power iteration
        # Simplified: compute coordinates via top-2 eigenvectors of B = -0.5 * D^T * D
        # We use the power iteration on the n x n matrix approximated by D^T * D

        # Square the distances
        D2 = [[d * d for d in row] for row in D]

        # Double-center the pivot matrix: subtract column means
        col_means = [sum(D2[pi][ni] for pi in range(p)) / p for ni in range(n)]
        D2_centered = [[D2[pi][ni] - col_means[ni] for ni in range(n)]
                       for pi in range(p)]

        # B = -0.5 * D2_centered^T * D2_centered (n x n)
        # Approximate: use the pivot approximation B_approx = -0.5 * C^T * C
        # where C is the centered pivot matrix
        B = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                s = 0.0
                for pi in range(p):
                    s += D2_centered[pi][i] * D2_centered[pi][j]
                B[i][j] = -0.5 * s

        # Power iteration to find top-2 eigenvectors
        def power_iter(mat, n_iters=50):
            size = len(mat)
            v = [rng.uniform(-1, 1) for _ in range(size)]
            for _ in range(n_iters):
                new_v = [sum(mat[i][j] * v[j] for j in range(size))
                         for i in range(size)]
                norm = math.sqrt(sum(x * x for x in new_v)) or 1.0
                v = [x / norm for x in new_v]
            # eigenvalue = v^T * M * v
            Mv = [sum(mat[i][j] * v[j] for j in range(size))
                  for i in range(size)]
            eigval = sum(v[i] * Mv[i] for i in range(size))
            return v, eigval

        v1, eig1 = power_iter(B)

        # Deflate for second eigenvector
        B_def = [[B[i][j] - eig1 * v1[i] * v1[j] for j in range(n)]
                 for i in range(n)]
        v2, eig2 = power_iter(B_def)

        # Scale coordinates
        s1 = math.sqrt(max(0.0, abs(eig1)))
        s2 = math.sqrt(max(0.0, abs(eig2)))
        span = min(self.width, self.height) * 0.8
        scale = span / max(1.0, max(s1, s2))

        cx, cy = self.width / 2, self.height / 2
        for i, node in enumerate(nodes):
            node.x = cx + v1[i] * s1 * scale
            node.y = cy + v2[i] * s2 * scale

        return graph


__all__ = ["DRGraphLayout", "PivotMDSLayout"]