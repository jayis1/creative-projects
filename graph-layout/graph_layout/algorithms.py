"""Graph algorithms: traversal, shortest paths, centrality, MST, community detection.

Pure-Python implementations of common graph algorithms that complement the
layout engine.  These are useful for analysis, filtering, and as building
blocks for more complex layouts.
"""

from __future__ import annotations

import heapq
import math
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from .graph import Graph


# --------------------------------------------------------------------- #
#  Traversal
# --------------------------------------------------------------------- #
def bfs(graph: Graph, start: str) -> List[str]:
    """Breadth-first traversal from *start*. Returns visited node ids in order."""
    if start not in graph:
        return []
    visited: Set[str] = {start}
    order: List[str] = []
    queue: deque = deque([start])
    while queue:
        cur = queue.popleft()
        order.append(cur)
        for nbr in sorted(graph.neighbors(cur)):
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)
    return order


def dfs(graph: Graph, start: str) -> List[str]:
    """Depth-first traversal from *start* (iterative). Returns visited node ids in order."""
    if start not in graph:
        return []
    visited: Set[str] = {start}
    order: List[str] = []
    stack: List[str] = [start]
    while stack:
        cur = stack.pop()
        order.append(cur)
        for nbr in sorted(graph.neighbors(cur), reverse=True):
            if nbr not in visited:
                visited.add(nbr)
                stack.append(nbr)
    return order


def dijkstra(graph: Graph, source: str) -> Dict[str, float]:
    """Shortest path distances from *source* using Dijkstra's algorithm.

    Edge weights are used as distances.  Returns a dict ``{node_id: distance}``.
    """
    if source not in graph:
        return {}
    dist: Dict[str, float] = {source: 0.0}
    pq: List[Tuple[float, str]] = [(0.0, source)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf):
            continue
        for nbr in graph.neighbors(u):
            edge = graph.get_edge(u, nbr)
            w = edge.weight if edge else 1.0
            nd = d + w
            if nd < dist.get(nbr, math.inf):
                dist[nbr] = nd
                heapq.heappush(pq, (nd, nbr))
    return dist


def all_pairs_shortest_paths(graph: Graph) -> Dict[str, Dict[str, float]]:
    """All-pairs shortest path distances using Dijkstra from every node."""
    return {nid: dijkstra(graph, nid) for nid in graph.nodes}


# --------------------------------------------------------------------- #
#  Centrality measures
# --------------------------------------------------------------------- #
def degree_centrality(graph: Graph) -> Dict[str, float]:
    """Degree centrality: ``degree(n) / (n-1)`` for each node."""
    n = graph.node_count
    if n <= 1:
        return {nid: 0.0 for nid in graph.nodes}
    return {nid: graph.degree(nid) / (n - 1) for nid in graph.nodes}


def closeness_centrality(graph: Graph) -> Dict[str, float]:
    """Closeness centrality: reciprocal of the sum of shortest path distances."""
    result: Dict[str, float] = {}
    n = graph.node_count
    for nid in graph.nodes:
        dist = dijkstra(graph, nid)
        total = sum(v for v in dist.values() if v < math.inf and v > 0)
        if total > 0:
            result[nid] = (len(dist) - 1) / total
        else:
            result[nid] = 0.0
    return result


def betweenness_centrality(graph: Graph) -> Dict[str, float]:
    """Betweenness centrality via Brandes' algorithm (O(VE))."""
    nodes = list(graph.nodes)
    cb: Dict[str, float] = {n: 0.0 for n in nodes}

    for s in nodes:
        # single-source shortest paths (BFS for unweighted)
        S: List[str] = []
        P: Dict[str, List[str]] = {w: [] for w in nodes}
        sigma: Dict[str, float] = {w: 0.0 for w in nodes}
        sigma[s] = 1.0
        d: Dict[str, int] = {w: -1 for w in nodes}
        d[s] = 0
        Q: deque = deque([s])
        while Q:
            v = Q.popleft()
            S.append(v)
            for w in graph.neighbors(v):
                if d[w] < 0:
                    Q.append(w)
                    d[w] = d[v] + 1
                if d[w] == d[v] + 1:
                    sigma[w] += sigma[v]
                    P[w].append(v)
        delta: Dict[str, float] = {w: 0.0 for w in nodes}
        while S:
            w = S.pop()
            for v in P[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                cb[w] += delta[w]

    # normalize for undirected
    if not graph.directed:
        for n in cb:
            cb[n] /= 2.0
    return cb


# --------------------------------------------------------------------- #
#  Minimum Spanning Tree (Prim's)
# --------------------------------------------------------------------- #
def minimum_spanning_tree(graph: Graph) -> List[Tuple[str, str, float]]:
    """Prim's algorithm. Returns list of ``(u, v, weight)`` edges in the MST."""
    if graph.node_count == 0:
        return []
    start = next(iter(graph.nodes))
    visited: Set[str] = {start}
    edges_in_mst: List[Tuple[str, str, float]] = []
    pq: List[Tuple[float, str, str]] = []
    for nbr in graph.neighbors(start):
        edge = graph.get_edge(start, nbr)
        w = edge.weight if edge else 1.0
        heapq.heappush(pq, (w, start, nbr))
    while pq and len(visited) < graph.node_count:
        w, u, v = heapq.heappop(pq)
        if v in visited:
            continue
        visited.add(v)
        edges_in_mst.append((u, v, w))
        for nbr in graph.neighbors(v):
            if nbr not in visited:
                edge = graph.get_edge(v, nbr)
                ew = edge.weight if edge else 1.0
                heapq.heappush(pq, (ew, v, nbr))
    return edges_in_mst


# --------------------------------------------------------------------- #
#  Cycle detection
# --------------------------------------------------------------------- #
def has_cycle(graph: Graph) -> bool:
    """Detect whether the (undirected) graph contains a cycle."""
    visited: Set[str] = set()
    for start in graph.nodes:
        if start in visited:
            continue
        parent: Dict[str, Optional[str]] = {start: None}
        queue: deque = deque([start])
        visited.add(start)
        while queue:
            u = queue.popleft()
            for v in graph.neighbors(u):
                if v not in visited:
                    visited.add(v)
                    parent[v] = u
                    queue.append(v)
                elif parent.get(u) != v:
                    return True
    return False


def topological_sort(graph: Graph) -> List[str]:
    """Kahn's algorithm for topological ordering of a DAG.

    Raises ValueError if the graph contains a cycle.
    """
    in_degree: Dict[str, int] = {n: 0 for n in graph.nodes}
    for e in graph.edges:
        in_degree[e.target] = in_degree.get(e.target, 0) + 1
    queue: deque = deque([n for n in graph.nodes if in_degree[n] == 0])
    order: List[str] = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in sorted(graph.neighbors(u)):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
    if len(order) != graph.node_count:
        raise ValueError("Graph contains a cycle — cannot topologically sort")
    return order


# --------------------------------------------------------------------- #
#  Community detection (label propagation)
# --------------------------------------------------------------------- #
def label_propagation(graph: Graph, max_iter: int = 100,
                      seed: Optional[int] = None) -> Dict[str, int]:
    """Label-propagation community detection (Raghavan et al. 2007).

    Returns a mapping ``{node_id: community_id}``.
    """
    import random
    rng = random.Random(seed)
    labels: Dict[str, int] = {n: i for i, n in enumerate(graph.nodes)}
    node_list = list(graph.nodes)
    for _ in range(max_iter):
        rng.shuffle(node_list)
        changed = False
        for nid in node_list:
            nbrs = graph.neighbors(nid)
            if not nbrs:
                continue
            # count label frequencies among neighbors
            counts: Dict[int, int] = {}
            for nb in nbrs:
                lbl = labels[nb]
                counts[lbl] = counts.get(lbl, 0) + 1
            # pick max-count label (ties broken randomly)
            max_count = max(counts.values())
            best = [l for l, c in counts.items() if c == max_count]
            new_label = rng.choice(best) if len(best) > 1 else best[0]
            if new_label != labels[nid]:
                labels[nid] = new_label
                changed = True
        if not changed:
            break
    # relabel communities to 0..k-1
    unique = sorted(set(labels.values()))
    remap = {old: i for i, old in enumerate(unique)}
    return {n: remap[l] for n, l in labels.items()}


__all__ = [
    "bfs", "dfs", "dijkstra", "all_pairs_shortest_paths",
    "degree_centrality", "closeness_centrality", "betweenness_centrality",
    "minimum_spanning_tree", "has_cycle", "topological_sort",
    "label_propagation",
]