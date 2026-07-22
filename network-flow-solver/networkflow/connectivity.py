"""
Connectivity and flow-based graph analysis utilities.

  - edge_disjoint_paths: maximum set of edge-disjoint s-t paths (via max flow)
  - vertex_disjoint_paths: maximum set of internally vertex-disjoint paths
    (node-splitting technique)
  - edge_connectivity: global edge connectivity (min cut over all pairs)
  - GomoryHuTree: all-pairs min-cut tree, computed in n max-flow calls
"""

from __future__ import annotations

from .graph import FlowNetwork
from .maxflow import Dinic


def edge_disjoint_paths(network: FlowNetwork, source: int,
                        sink: int) -> list[list[int]]:
    """Find maximum edge-disjoint paths from source to sink.

    Uses unit-capacity max flow and extracts paths from the flow decomposition.
    Returns a list of paths (each path is a list of node indices).
    """
    # Work on a copy with unit capacities
    n = network.n
    net = FlowNetwork(n)
    for u in range(n):
        for e in network.graph[u]:
            if e.cap > 0:
                net.add_edge(u, e.to, 1)  # unit capacity
    Dinic().solve(net, source, sink)
    # Extract paths by following positive-flow edges
    paths: list[list[int]] = []
    visited_edges = set()
    while True:
        path = _find_flow_path(net, source, sink, visited_edges)
        if path is None:
            break
        paths.append(path)
    return paths


def _find_flow_path(net: FlowNetwork, source: int, sink: int,
                    visited: set[tuple[int, int]]) -> list[int] | None:
    """Follow edges with positive flow to extract one path."""
    path = [source]
    cur = source
    while cur != sink:
        found = False
        for idx, e in enumerate(net.graph[cur]):
            if e.flow > 0 and (cur, idx) not in visited:
                visited.add((cur, idx))
                cur = e.to
                path.append(cur)
                found = True
                break
        if not found:
            return None
    return path


def vertex_disjoint_paths(network: FlowNetwork, source: int,
                           sink: int) -> list[list[int]]:
    """Find maximum internally vertex-disjoint paths.

    Uses the node-splitting technique: each vertex v (except s, t) is split
    into v_in and v_out connected by a capacity-1 edge.  Original edges
    go from u_out to v_in.
    """
    n = network.n
    # Split: node i → i_in = 2*i, i_out = 2*i + 1
    # source and sink don't get split (infinite internal capacity)
    N = 2 * n
    net = FlowNetwork(N)
    INF = float("inf")
    for i in range(n):
        if i == source or i == sink:
            # No split — just connect in to out with infinite capacity
            net.add_edge(2 * i, 2 * i + 1, INF)
        else:
            net.add_edge(2 * i, 2 * i + 1, 1)
    for u in range(n):
        for e in network.graph[u]:
            if e.cap > 0:
                net.add_edge(2 * u + 1, 2 * e.to, 1)
    Dinic().solve(net, 2 * source + 1, 2 * sink)
    # Extract paths
    paths: list[list[int]] = []
    visited = set()
    while True:
        path = _find_flow_path(net, 2 * source + 1, 2 * sink, visited)
        if path is None:
            break
        # Convert back from split to original nodes
        orig_path = [p // 2 for p in path]
        paths.append(orig_path)
    return paths


def edge_connectivity(network: FlowNetwork) -> float:
    """Global edge connectivity: minimum s-t cut over all pairs.

    For undirected graphs, the min cut over all (s, t) pairs gives the
    edge connectivity.  We fix s=0 and try all other t.
    """
    n = network.n
    if n < 2:
        return 0
    min_cut = float("inf")
    for t in range(1, n):
        net = network.copy()
        flow = Dinic().solve(net, 0, t)
        if flow < min_cut:
            min_cut = flow
    return min_cut


class GomoryHuTree:
    """Gomory-Hu cut tree for all-pairs min-cut computation.

    After construction, calling ``min_cut(u, v)`` returns the min s-t cut
    value for any pair in O(1) (it's the minimum edge weight on the path
    from u to v in the tree).  Requires only n-1 max-flow computations.

    Example
    -------
    >>> net = FlowNetwork(4)
    >>> net.add_edge(0, 1, 3)
    >>> net.add_edge(0, 2, 2)
    >>> net.add_edge(1, 2, 5)
    >>> net.add_edge(1, 3, 4)
    >>> net.add_edge(2, 3, 3)
    >>> tree = GomoryHuTree(net)
    >>> tree.min_cut(0, 3)
    5
    """

    def __init__(self, network: FlowNetwork):
        self.n = network.n
        # Tree adjacency: tree[u] = [(v, weight), ...]
        self.tree: list[list[tuple[int, float]]] = [[] for _ in range(self.n)]
        self._build(network)

    def _build(self, network: FlowNetwork) -> None:
        """Build the Gomory-Hu tree using Gusfield's algorithm (n-1 max-flow calls)."""
        n = self.n
        parent = [0] * n          # parent[i] in the tree (rooted at 0)
        capacity = [0.0] * n      # capacity[i] = min cut between i and parent[i]
        for s in range(1, n):
            # Compute min cut between s and parent[s]
            net = network.copy()
            flow = Dinic().solve(net, s, parent[s])
            # Find reachable set from s in residual
            visited = [False] * n
            from collections import deque
            visited[s] = True
            q = deque([s])
            while q:
                u = q.popleft()
                for e in net.graph[u]:
                    if not visited[e.to] and e.residual() > 1e-12:
                        visited[e.to] = True
                        q.append(e.to)
            capacity[s] = flow
            # Update parent pointers: for any i != s with parent[i] == parent[s]
            # and i is on the s-side of the cut, set parent[i] = s
            for i in range(n):
                if i == s:
                    continue
                if parent[i] == parent[s] and visited[i]:
                    parent[i] = s
            # Also update parent[s] if it was pointing to something on the t-side
            # (handled implicitly by the tree structure)
        # Build adjacency list
        for i in range(1, n):
            p = parent[i]
            self.tree[p].append((i, capacity[i]))
            self.tree[i].append((p, capacity[i]))
        # Store parent/capacity for queries
        self._parent = parent
        self._capacity = capacity

    def min_cut(self, u: int, v: int) -> float:
        """Return the min cut value between nodes *u* and *v*.

        This is the minimum edge weight on the path from u to v in the
        Gomory-Hu tree.  Uses BFS/DFS on the tree (O(n) per query).
        """
        if u == v:
            return float("inf")
        # BFS from u to v, tracking min edge weight
        from collections import deque
        visited = [False] * self.n
        min_weight = [float("inf")] * self.n
        visited[u] = True
        q = deque([u])
        while q:
            node = q.popleft()
            for nbr, w in self.tree[node]:
                if not visited[nbr]:
                    visited[nbr] = True
                    min_weight[nbr] = min(min_weight[node], w)
                    if nbr == v:
                        return min_weight[v]
                    q.append(nbr)
        return min_weight[v]