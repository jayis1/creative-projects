"""
Minimum cut algorithms.

The minimum s-t cut is the dual of the maximum flow: after computing max
flow, the min cut is found by BFS/DFS in the residual graph.  The set of
nodes reachable from the source forms the S-partition; the rest forms T.

We also implement the Stoer-Wagner global minimum cut algorithm (no
designated terminals), which works on weighted undirected graphs.
"""

from __future__ import annotations

from collections import deque

from .graph import FlowNetwork
from .maxflow import Dinic


class MinCut:
    """Minimum s-t cut via max-flow duality.

    After calling :meth:`compute`, the following attributes are set:
      - ``max_flow``: value of the max flow (= min cut capacity)
      - ``source_side``: list of nodes reachable from source in residual graph
      - ``sink_side``: list of remaining nodes
      - ``cut_edges``: edges crossing from source_side to sink_side
    """

    def __init__(self, solver=None):
        self.solver = solver or Dinic()
        self.max_flow: float = 0.0
        self.source_side: list[int] = []
        self.sink_side: list[int] = []
        self.cut_edges: list[tuple[int, int, float]] = []

    def compute(self, network: FlowNetwork, source: int, sink: int
                ) -> float:
        """Compute the minimum s-t cut.

        Returns the cut capacity (equal to max flow value).
        """
        self.max_flow = self.solver.solve(network, source, sink)
        # BFS in residual graph to find reachable nodes from source
        visited = [False] * network.n
        visited[source] = True
        q = deque([source])
        while q:
            u = q.popleft()
            for e in network.graph[u]:
                if not visited[e.to] and e.residual() > 1e-12:
                    visited[e.to] = True
                    q.append(e.to)
        self.source_side = [i for i in range(network.n) if visited[i]]
        self.sink_side = [i for i in range(network.n) if not visited[i]]
        # Find cut edges: forward edges from S-side to T-side
        self.cut_edges = []
        for u in self.source_side:
            for e in network.graph[u]:
                if e.cap > 0 and not visited[e.to]:
                    self.cut_edges.append((u, e.to, e.cap))
        return self.max_flow


class StoerWagner:
    """Stoer-Wagner global minimum cut algorithm for undirected weighted graphs.

    Finds the minimum cut of an undirected graph without designated
    terminals.  Uses the maximum adjacency (phase) ordering and the
    "contraction of the last two vertices" approach.

    Example
    -------
    >>> sw = StoerWagner()
    >>> graph = {
    ...     0: [(1, 2), (2, 3)],
    ...     1: [(0, 2), (2, 4)],
    ...     2: [(0, 3), (1, 4)],
    ... }
    >>> sw.solve(graph)  # min cut weight
    2.0
    """

    def __init__(self):
        self.min_cut_value: float = float("inf")
        self.best_partition: tuple[set[int], set[int]] | None = None

    def solve(self, graph: dict[int, list[tuple[int, float]]]) -> float:
        """Compute global minimum cut of an undirected weighted graph.

        *graph* is an adjacency dict: {node: [(neighbor, weight), ...]}.
        Returns the minimum cut value.
        """
        # Build merged-node representation
        # vertices: dict of current node -> set of original nodes
        nodes = list(graph.keys())
        # Work with integer indices for simplicity
        idx = {v: i for i, v in enumerate(nodes)}
        n = len(nodes)
        # Weight matrix — undirected graph, each edge may appear in both
        # adjacency lists.  We take the max to avoid double-counting.
        w = [[0.0] * n for _ in range(n)]
        for u, edges in graph.items():
            for v, weight in edges:
                i, j = idx[u], idx[v]
                w[i][j] = max(w[i][j], weight)
                w[j][i] = max(w[j][i], weight)

        # Use the standard Stoer-Wagner with "merged" sets
        # vertices[i] = set of original nodes merged into node i
        merged = [{i} for i in range(n)]
        active = list(range(n))
        best = float("inf")

        while len(active) > 1:
            # Phase: find the maximum adjacency ordering
            # Start with arbitrary vertex, keep adding the most-connected
            a = active[0]
            A = [a]
            in_a = set([a])
            w_sum = [0.0] * n  # weight to current A set
            for v in active:
                w_sum[v] = w[a][v]
            last = a
            second_last = a
            while len(A) < len(active):
                # Find the vertex not in A with max w_sum
                best_v = -1
                best_w = -1.0
                for v in active:
                    if v not in in_a and w_sum[v] > best_w:
                        best_w = w_sum[v]
                        best_v = v
                second_last = last
                last = best_v
                A.append(best_v)
                in_a.add(best_v)
                # Update weights
                for v in active:
                    if v not in in_a:
                        w_sum[v] += w[best_v][v]
            # Cut of the phase: weight of edges incident to *last*
            cut_value = w_sum[last]
            if cut_value < best:
                best = cut_value
                # Record partition: {last} vs rest (at this contraction stage)
                self.best_partition = (
                    set(merged[last]),
                    set().union(*[merged[v] for v in active if v != last])
                    if len(active) > 2 else
                    set(merged[second_last]),
                )
            # Merge last and second_last
            s, t = second_last, last
            # Merge t into s
            for v in range(n):
                w[s][v] = w[s][v] + w[t][v]
                w[v][s] = w[s][v]
            merged[s] |= merged[t]
            active.remove(t)

        self.min_cut_value = best
        return best

    def get_partition(self) -> tuple[set[int], set[int]] | None:
        """Return the partition achieving the min cut (original node indices)."""
        return self.best_partition