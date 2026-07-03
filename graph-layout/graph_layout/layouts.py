"""Graph layout algorithms.

All layout algorithms take a :class:`Graph` and assign ``(x, y)`` positions
to each node.  They are pure Python (stdlib only) and use only ``math`` and
``random``.

Algorithms implemented
-----------------------
- FruchtermanReingold: force-directed with repulsive & attractive forces
- KamadaKawai: stress minimization via Newton-Raphson on each node
- StressMajorization: iterative majorization (SMOF)
- SugiyamaLayout: hierarchical layered layout for DAGs
- TreeLayout: recursive subtree positioning
- CircularLayout: nodes evenly spaced on a circle
- RadialLayout: BFS-rooted radial tree layout
- GridLayout: regular grid arrangement
- RandomLayout: uniform random positions
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from .graph import Graph, Node, Number

__all__ = [
    "FruchtermanReingold", "KamadaKawai", "StressMajorization",
    "SugiyamaLayout", "TreeLayout", "CircularLayout", "RadialLayout",
    "GridLayout", "RandomLayout",
]


class LayoutAlgorithm:
    """Base class. Subclasses implement :meth:`layout`."""

    name = "base"

    def layout(self, graph: Graph, **kwargs) -> Graph:
        raise NotImplementedError

    def __call__(self, graph: Graph, **kwargs) -> Graph:
        return self.layout(graph, **kwargs)


# ======================================================================
#  Random
# ======================================================================
class RandomLayout(LayoutAlgorithm):
    """Uniformly random positions in a square of side ``width``."""

    name = "random"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 seed: Optional[int] = None) -> None:
        self.width = width
        self.height = height
        self.seed = seed

    def layout(self, graph: Graph, **kwargs) -> Graph:
        rng = random.Random(self.seed)
        for node in graph.iter_nodes():
            node.x = rng.uniform(0, self.width)
            node.y = rng.uniform(0, self.height)
        return graph


# ======================================================================
#  Grid
# ======================================================================
class GridLayout(LayoutAlgorithm):
    """Arrange nodes in a regular grid."""

    name = "grid"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 spacing: Optional[float] = None) -> None:
        self.width = width
        self.height = height
        self.spacing = spacing

    def layout(self, graph: Graph, **kwargs) -> Graph:
        n = graph.node_count
        if n == 0:
            return graph
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        sp = self.spacing or min(self.width / max(cols, 1),
                                 self.height / max(rows, 1))
        ox = (self.width - (cols - 1) * sp) / 2
        oy = (self.height - (rows - 1) * sp) / 2
        for i, node in enumerate(graph.iter_nodes()):
            r, c = divmod(i, cols)
            node.x = ox + c * sp
            node.y = oy + r * sp
        return graph


# ======================================================================
#  Circular
# ======================================================================
class CircularLayout(LayoutAlgorithm):
    """Place nodes evenly on a circle."""

    name = "circular"

    def __init__(self, width: float = 1000.0, height: float = 1000.0) -> None:
        self.width = width
        self.height = height

    def layout(self, graph: Graph, **kwargs) -> Graph:
        n = graph.node_count
        if n == 0:
            return graph
        cx, cy = self.width / 2, self.height / 2
        radius = min(self.width, self.height) / 2 * 0.9
        for i, node in enumerate(graph.iter_nodes()):
            angle = 2 * math.pi * i / n
            node.x = cx + radius * math.cos(angle)
            node.y = cy + radius * math.sin(angle)
        return graph


# ======================================================================
#  Fruchterman–Reingold
# ======================================================================
class FruchtermanReingold(LayoutAlgorithm):
    """Force-directed layout (Fruchterman & Reingold 1991).

    Attractive forces pull connected nodes together; repulsive forces push
    all pairs apart.  An optimal distance *k* is derived from the area and
    node count.  Positions are cooled over iterations.
    """

    name = "fruchterman-reingold"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 iterations: int = 300, seed: Optional[int] = None,
                 cooling: str = "linear", k: Optional[float] = None) -> None:
        self.width = width
        self.height = height
        self.iterations = iterations
        self.seed = seed
        self.cooling = cooling
        self.k = k

    def layout(self, graph: Graph, **kwargs) -> Graph:
        nodes = list(graph.iter_nodes())
        n = len(nodes)
        if n == 0:
            return graph

        area = self.width * self.height
        k = self.k or math.sqrt(area / n)
        rng = random.Random(self.seed)

        # initial random positions
        pos: Dict[str, List[float]] = {}
        for node in nodes:
            pos[node.id] = [rng.uniform(0, self.width), rng.uniform(0, self.height)]

        # adjacency for O(E) attraction
        adj: Dict[str, List[str]] = {nid: [] for nid in pos}
        for e in graph.edges:
            adj[e.source].append(e.target)

        temp = self.width / 10.0
        temp_init = temp

        for iteration in range(self.iterations):
            disp: Dict[str, List[float]] = {nid: [0.0, 0.0] for nid in pos}

            # repulsive forces (all pairs)
            ids = list(pos.keys())
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

            # attractive forces (edges)
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

            # apply displacements with temperature cap
            for nid in pos:
                dx, dy = disp[nid]
                d = math.sqrt(dx * dx + dy * dy)
                if d > 0:
                    limited = min(d, temp)
                    pos[nid][0] += (dx / d) * limited
                    pos[nid][1] += (dy / d) * limited
                # keep within frame
                pos[nid][0] = max(0, min(self.width, pos[nid][0]))
                pos[nid][1] = max(0, min(self.height, pos[nid][1]))

            # cooling
            if self.cooling == "linear":
                temp = temp_init * (1 - iteration / self.iterations)
            elif self.cooling == "exponential":
                temp = temp_init * (0.95 ** iteration)
            else:
                temp = temp_init * (1 - iteration / self.iterations)

        for node in nodes:
            node.x = pos[node.id][0]
            node.y = pos[node.id][1]
        return graph


# ======================================================================
#  Kamada–Kawai
# ======================================================================
class KamadaKawai(LayoutAlgorithm):
    """Kamada–Kawai stress-minimization layout.

    Uses graph-theoretic distances as target lengths and minimises the
    stress function via Newton-Raphson on a single node at a time (the one
    with the largest partial derivative).
    """

    name = "kamada-kawai"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 iterations: int = 200, seed: Optional[int] = None,
                 k: Optional[float] = None, eps: float = 1e-4) -> None:
        self.width = width
        self.height = height
        self.iterations = iterations
        self.seed = seed
        self.k = k
        self.eps = eps

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

        # graph-theoretic distances
        dist = graph.shortest_path_lengths()
        # target spring lengths L_ij, spring strength K_ij
        L = self.width / max(2, n)  # diameter scale
        idx = {nid: i for i, nid in enumerate(ids)}
        # build matrices
        kmat = [[0.0] * n for _ in range(n)]
        lmat = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                dij = dist.get((ids[i], ids[j]), dist.get((ids[j], ids[i]), n))
                if dij == 0:
                    dij = n  # disconnected — large target
                lmat[i][j] = L * dij
                kmat[i][j] = 1.0 / (dij * dij)

        rng = random.Random(self.seed)
        pos = [[rng.uniform(0, self.width), rng.uniform(0, self.height)] for _ in range(n)]

        def stress():
            s = 0.0
            for i in range(n):
                for j in range(i + 1, n):
                    dx = pos[i][0] - pos[j][0]
                    dy = pos[i][1] - pos[j][1]
                    d = math.sqrt(dx * dx + dy * dy)
                    diff = d - lmat[i][j]
                    s += kmat[i][j] * diff * diff
            return s

        # Newton-Raphson on single node (the one with max delta)
        for _ in range(self.iterations):
            # find node with largest partial derivative
            best = -1
            best_delta = 0.0
            deltas = [0.0] * n
            for m in range(n):
                dx_dm = 0.0
                dy_dm = 0.0
                for i in range(n):
                    if i == m:
                        continue
                    dx = pos[m][0] - pos[i][0]
                    dy = pos[m][1] - pos[i][1]
                    d = math.sqrt(dx * dx + dy * dy)
                    if d < 1e-10:
                        d = 1e-10
                    inv_d = 1.0 / d
                    kmi = kmat[m][i]
                    lmi = lmat[m][i]
                    common = kmi * (1.0 - lmi * inv_d)
                    dx_dm += common * dx
                    dy_dm += common * dy
                delta = math.sqrt(dx_dm * dx_dm + dy_dm * dy_dm)
                deltas[m] = delta
                if delta > best_delta:
                    best_delta = delta
                    best = m

            if best_delta < self.eps:
                break

            # Newton iterations on node `best`
            for _inner in range(100):
                m = best
                dE_dx = dE_dy = 0.0
                d2E_dx2 = d2E_dy2 = d2E_dxdy = 0.0
                for i in range(n):
                    if i == m:
                        continue
                    dx = pos[m][0] - pos[i][0]
                    dy = pos[m][1] - pos[i][1]
                    d = math.sqrt(dx * dx + dy * dy)
                    if d < 1e-10:
                        d = 1e-10
                    inv_d = 1.0 / d
                    kmi = kmat[m][i]
                    lmi = lmat[m][i]
                    common = kmi * (1.0 - lmi * inv_d)
                    dE_dx += common * dx
                    dE_dy += common * dy
                    inv_d3 = inv_d ** 3
                    # Correct Hessian of the KK stress function:
                    # ∂²E/∂x_m² = Σ k_{mi}(1 - l_{mi}/d + l_{mi}·dx²/d³)
                    # ∂²E/∂y_m² = Σ k_{mi}(1 - l_{mi}/d + l_{mi}·dy²/d³)
                    # ∂²E/∂x∂y  = Σ k_{mi}·l_{mi}·dx·dy/d³
                    d2E_dx2 += kmi * (1 - lmi * inv_d + lmi * dx * dx * inv_d3)
                    d2E_dy2 += kmi * (1 - lmi * inv_d + lmi * dy * dy * inv_d3)
                    d2E_dxdy += kmi * lmi * dx * dy * inv_d3

                # Solve H·Δ = -g  →  Δ = -H⁻¹·g,  then pos -= Δ  (i.e. pos -= H⁻¹·g)
                det = d2E_dx2 * d2E_dy2 - d2E_dxdy * d2E_dxdy
                if abs(det) < 1e-12:
                    break
                # H⁻¹·g components (inverse of [[a,b],[b,c]] is (1/det)·[[c,-b],[-b,a]])
                dx = (d2E_dy2 * dE_dx - d2E_dxdy * dE_dy) / det
                dy = (d2E_dx2 * dE_dy - d2E_dxdy * dE_dx) / det
                pos[m][0] -= dx
                pos[m][1] -= dy
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    break

        for i, node in enumerate(nodes):
            node.x = pos[i][0]
            node.y = pos[i][1]
        return graph


# ======================================================================
#  Stress Majorization
# ======================================================================
class StressMajorization(LayoutAlgorithm):
    """Stress majorization layout (Gansner et al. 2004).

    Iteratively minimises a convex majorization of the stress function
    using the Gansner–Koren–North formulation.  Works on the full weight
    matrix so it is O(n²) per iteration but converges smoothly.
    """

    name = "stress-majorization"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 iterations: int = 200, seed: Optional[int] = None,
                 tol: float = 1e-4) -> None:
        self.width = width
        self.height = height
        self.iterations = iterations
        self.seed = seed
        self.tol = tol

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

        dist = graph.shortest_path_lengths()
        L0 = self.width / max(2, n)
        # weights
        W = [[0.0] * n for _ in range(n)]
        d = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                dij = dist.get((ids[i], ids[j]), dist.get((ids[j], ids[i]), n))
                if dij == 0:
                    dij = n
                d[i][j] = L0 * dij
                W[i][j] = 1.0 / (dij * dij)

        rng = random.Random(self.seed)
        z = [[rng.uniform(0, self.width), rng.uniform(0, self.height)] for _ in range(n)]

        def stress(pos):
            s = 0.0
            for i in range(n):
                for j in range(i + 1, n):
                    dx = pos[i][0] - pos[j][0]
                    dy = pos[i][1] - pos[j][1]
                    dist_ij = math.sqrt(dx * dx + dy * dy)
                    if dist_ij < 1e-10:
                        continue
                    diff = dist_ij - d[i][j]
                    s += W[i][j] * diff * diff
            return s

        prev_stress = float("inf")
        for _ in range(self.iterations):
            new = [[0.0, 0.0] for _ in range(n)]
            for i in range(n):
                sx, sy = 0.0, 0.0
                sw = 0.0
                for j in range(n):
                    if i == j:
                        continue
                    dx = z[i][0] - z[j][0]
                    dy = z[i][1] - z[j][1]
                    dist_ij = math.sqrt(dx * dx + dy * dy)
                    if dist_ij < 1e-10:
                        dist_ij = 1e-10
                    w = W[i][j]
                    sx += w * (z[j][0] + d[i][j] * dx / dist_ij)
                    sy += w * (z[j][1] + d[i][j] * dy / dist_ij)
                    sw += w
                if sw > 0:
                    new[i][0] = sx / sw
                    new[i][1] = sy / sw
                else:
                    new[i][0] = z[i][0]
                    new[i][1] = z[i][1]

            cur = stress(new)
            if abs(prev_stress - cur) < self.tol:
                z = new
                break
            prev_stress = cur
            z = new

        for i, node in enumerate(nodes):
            node.x = z[i][0]
            node.y = z[i][1]
        return graph


# ======================================================================
#  Tree layout (tidy / Walker-style)
# ======================================================================
class TreeLayout(LayoutAlgorithm):
    """Recursive tidy tree layout.

    Computes subtree widths bottom-up, then places children with equal
    spacing.  Works for any tree (or forest).  Non-tree edges are ignored.
    """

    name = "tree"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 root: Optional[str] = None, orientation: str = "top-down",
                 node_spacing: float = 40.0, level_spacing: float = 80.0) -> None:
        self.width = width
        self.height = height
        self.root = root
        self.orientation = orientation
        self.node_spacing = node_spacing
        self.level_spacing = level_spacing

    def layout(self, graph: Graph, **kwargs) -> Graph:
        if graph.node_count == 0:
            return graph

        # Build children mapping (undirected → treat as tree; pick root)
        adj = graph.neighbor_list()
        visited: set = set()
        # determine roots
        if self.root and self.root in adj:
            roots = [self.root]
        else:
            # find nodes with degree 1 or 0 (likely leaves); pick node with
            # minimum degree as a heuristic root, or node '0' if present
            deg = {nid: len(nbrs) for nid, nbrs in adj.items()}
            if not deg:
                return graph
            roots = [min(deg, key=lambda k: deg[k])]

        # BFS to build parent→children with visited set
        children: Dict[str, List[str]] = {nid: [] for nid in adj}
        parent: Dict[str, Optional[str]] = {nid: None for nid in adj}
        for r in roots:
            if r in visited:
                continue
            stack = [r]
            visited.add(r)
            while stack:
                cur = stack.pop(0)
                for nbr in adj[cur]:
                    if nbr in visited:
                        continue
                    visited.add(nbr)
                    children[cur].append(nbr)
                    parent[nbr] = cur
                    stack.append(nbr)
        # add any unvisited nodes as additional roots
        for nid in adj:
            if nid not in visited:
                roots.append(nid)
                visited.add(nid)

        # subtree width calculation
        widths: Dict[str, float] = {}
        leaf_count: Dict[str, int] = {}

        def compute_width(nid: str) -> float:
            ch = children[nid]
            if not ch:
                widths[nid] = self.node_spacing
                leaf_count[nid] = 1
                return widths[nid]
            total = 0.0
            leaves = 0
            for c in ch:
                total += compute_width(c)
                leaves += leaf_count[c]
            widths[nid] = max(total, self.node_spacing)
            leaf_count[nid] = leaves
            return widths[nid]

        for r in roots:
            compute_width(r)

        # assign positions
        positions: Dict[str, Tuple[float, float]] = {}

        def assign(nid: str, x_center: float, depth: int) -> None:
            ch = children[nid]
            if self.orientation == "top-down":
                positions[nid] = (x_center, depth * self.level_spacing)
            elif self.orientation == "left-right":
                positions[nid] = (depth * self.level_spacing, x_center)
            if not ch:
                return
            total = sum(widths[c] for c in ch)
            x = x_center - total / 2
            for c in ch:
                w = widths[c]
                assign(c, x + w / 2, depth + 1)
                x += w

        for r in roots:
            assign(r, self.width / 2, 0)

        # center / fit
        xs = [p[0] for p in positions.values()]
        ys = [p[1] for p in positions.values()]
        if xs and ys:
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)
            sx = (self.width - 40) / max(1, (maxx - minx)) if maxx > minx else 1
            sy = (self.height - 40) / max(1, (maxy - miny)) if maxy > miny else 1
            scale = min(1.0, min(sx, sy)) if (maxx > minx or maxy > miny) else 1.0
            tx = (self.width - (maxx - minx) * scale) / 2 - minx * scale
            ty = (self.height - (maxy - miny) * scale) / 2 - miny * scale
            for nid, (x, y) in positions.items():
                positions[nid] = (x * scale + tx, y * scale + ty)

        for nid, (x, y) in positions.items():
            if nid in graph.nodes:
                graph.nodes[nid].x = x
                graph.nodes[nid].y = y
        return graph


# ======================================================================
#  Radial layout
# ======================================================================
class RadialLayout(LayoutAlgorithm):
    """Radial tree layout: BFS from a root, each depth on a ring."""

    name = "radial"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 root: Optional[str] = None, seed: Optional[int] = None) -> None:
        self.width = width
        self.height = height
        self.root = root
        self.seed = seed

    def layout(self, graph: Graph, **kwargs) -> Graph:
        if graph.node_count == 0:
            return graph
        adj = graph.neighbor_list()
        cx, cy = self.width / 2, self.height / 2
        if self.root and self.root in adj:
            root = self.root
        else:
            root = next(iter(adj))
        # BFS
        from collections import deque
        depths: Dict[str, int] = {root: 0}
        parents: Dict[str, Optional[str]] = {root: None}
        queue = deque([root])
        while queue:
            cur = queue.popleft()
            for nbr in adj[cur]:
                if nbr not in depths:
                    depths[nbr] = depths[cur] + 1
                    parents[nbr] = cur
                    queue.append(nbr)
        max_depth = max(depths.values()) if depths else 1
        radius_step = min(self.width, self.height) / 2 / max(1, max_depth + 1)
        # assign angular slices
        # group by depth, order children around their parent's angle
        angle_span: Dict[str, Tuple[float, float]] = {root: (0, 2 * math.pi)}
        positions: Dict[str, Tuple[float, float]] = {root: (cx, cy)}
        # BFS order to assign angles
        by_depth: Dict[int, List[str]] = {}
        for nid, d in depths.items():
            by_depth.setdefault(d, []).append(nid)
        rng = random.Random(self.seed)
        for d in range(1, max_depth + 1):
            for nid in by_depth.get(d, []):
                parent = parents[nid]
                if parent is None:
                    continue
                p_angle_start, p_angle_end = angle_span[parent]
                siblings = [c for c in by_depth.get(d, []) if parents.get(c) == parent]
                if nid not in siblings:
                    siblings = [nid]
                idx = siblings.index(nid)
                seg = (p_angle_end - p_angle_start) / max(1, len(siblings))
                a_start = p_angle_start + idx * seg
                a_end = a_start + seg
                angle_span[nid] = (a_start, a_end)
                a_mid = (a_start + a_end) / 2
                r = d * radius_step
                positions[nid] = (cx + r * math.cos(a_mid),
                                   cy + r * math.sin(a_mid))
        for nid, (x, y) in positions.items():
            if nid in graph.nodes:
                graph.nodes[nid].x = x
                graph.nodes[nid].y = y
        return graph


# ======================================================================
#  Sugiyama hierarchical layout
# ======================================================================
class SugiyamaLayout(LayoutAlgorithm):
    """Sugiyama-style hierarchical layout for directed acyclic graphs.

    Four steps: (1) cycle removal, (2) layer assignment (longest path),
    (3) crossing reduction (median heuristic), (4) coordinate assignment.
    """

    name = "sugiyama"

    def __init__(self, width: float = 1000.0, height: float = 1000.0,
                 node_spacing: float = 60.0, level_spacing: float = 80.0) -> None:
        self.width = width
        self.height = height
        self.node_spacing = node_spacing
        self.level_spacing = level_spacing

    def layout(self, graph: Graph, **kwargs) -> Graph:
        if graph.node_count == 0:
            return graph
        adj = graph.neighbor_list()
        # Build directed adjacency from edge directions (or undirected → both)
        succ: Dict[str, List[str]] = {nid: [] for nid in adj}
        pred: Dict[str, List[str]] = {nid: [] for nid in adj}
        for e in graph.edges:
            succ[e.source].append(e.target)
            pred[e.target].append(e.source)

        # 1. Cycle removal: greedy heuristic — remove back edges via DFS
        # (we just ignore edges that point backward in a DFS post-order)
        order: List[str] = []
        visited: set = set()
        temp: set = set()

        def dfs(u: str) -> None:
            if u in visited:
                return
            if u in temp:
                return  # cycle — skip
            temp.add(u)
            for v in list(succ[u]):
                if v not in visited:
                    dfs(v)
            temp.discard(u)
            visited.add(u)
            order.append(u)

        for nid in adj:
            dfs(nid)
        # order is reverse topological (post-order)
        topo = list(reversed(order))

        # 2. Layer assignment (longest path)
        layer: Dict[str, int] = {}
        for nid in topo:
            if not pred[nid] or all(p not in layer for p in pred[nid]):
                layer[nid] = 0
            else:
                layer[nid] = max((layer[p] for p in pred[nid] if p in layer),
                                 default=-1) + 1
        max_layer = max(layer.values()) if layer else 0
        # group
        layers: Dict[int, List[str]] = {}
        for nid, l in layer.items():
            layers.setdefault(l, []).append(nid)

        # 3. Crossing reduction — median heuristic (a few sweeps)
        for _ in range(24):
            # top-down: reorder each layer by median of pred positions
            for l in range(1, max_layer + 1):
                above = layers.get(l - 1, [])
                pos_above = {nid: i for i, nid in enumerate(above)}
                medians = []
                for nid in layers[l]:
                    ps = [pos_above[p] for p in pred[nid] if p in pos_above]
                    if ps:
                        m = sorted(ps)[len(ps) // 2]
                    else:
                        m = 0
                    medians.append((m, nid))
                medians.sort(key=lambda t: t[0])
                layers[l] = [t[1] for t in medians]
            # bottom-up
            for l in range(max_layer - 1, -1, -1):
                below = layers.get(l + 1, [])
                pos_below = {nid: i for i, nid in enumerate(below)}
                medians = []
                for nid in layers[l]:
                    cs = [pos_below[c] for c in succ[nid] if c in pos_below]
                    if cs:
                        m = sorted(cs)[len(cs) // 2]
                    else:
                        m = 0
                    medians.append((m, nid))
                medians.sort(key=lambda t: t[0])
                layers[l] = [t[1] for t in medians]

        # 4. Coordinate assignment
        positions: Dict[str, Tuple[float, float]] = {}
        for l, nodes_in_layer in layers.items():
            for i, nid in enumerate(nodes_in_layer):
                x = i * self.node_spacing
                y = l * self.level_spacing
                positions[nid] = (x, y)

        # center the layout
        if positions:
            xs = [p[0] for p in positions.values()]
            ys = [p[1] for p in positions.values()]
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)
            tx = (self.width - (maxx - minx)) / 2 - minx
            ty = (self.height - (maxy - miny)) / 2 - miny
            for nid, (x, y) in positions.items():
                if nid in graph.nodes:
                    graph.nodes[nid].x = x + tx
                    graph.nodes[nid].y = y + ty
        return graph