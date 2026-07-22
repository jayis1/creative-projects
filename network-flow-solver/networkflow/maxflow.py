"""
Maximum flow algorithms.

Implementations:
  - FordFulkerson: basic DFS-based augmenting path (integer capacities)
  - EdmondsKarp: BFS-based, O(V·E²) worst case
  - Dinic: level graph + blocking flow, O(V²·E)
  - PushRelabel: FIFO queue push-relabel with gap heuristic, O(V³)

All solvers operate on a FlowNetwork and return the max flow value.
They also leave the network's edges updated with flow values.
"""

from __future__ import annotations

from collections import deque
from typing import Protocol

from .graph import FlowNetwork


class MaxFlowSolver(Protocol):
    """Protocol for max-flow solver implementations."""

    def solve(self, network: FlowNetwork, source: int, sink: int) -> float | int:
        ...


class FordFulkerson:
    """DFS-based Ford-Fulkerson method.

    Works for integer (or exact-rational) capacities.  For floating-point
    capacities use :class:`EdmondsKarp` or :class:`Dinic` instead, because
    DFS augmenting paths can loop indefinitely with irrational capacities.
    """

    def __init__(self, max_iter: int = 100_000):
        self.max_iter = max_iter
        self.iterations = 0

    def solve(self, network: FlowNetwork, source: int, sink: int) -> float | int:
        self.iterations = 0
        total = 0
        n = network.n
        while self.iterations < self.max_iter:
            self.iterations += 1
            visited = [False] * n
            parent_node = [-1] * n
            parent_edge = [-1] * n
            bottleneck = self._dfs(network, source, sink, visited,
                                    parent_node, parent_edge, float("inf"))
            if bottleneck == 0:
                break
            # Augment along the path
            cur = sink
            while cur != source:
                u = parent_node[cur]
                ei = parent_edge[cur]
                e = network.graph[u][ei]
                e.flow += bottleneck
                network.graph[e.to][e.rev].flow -= bottleneck
                cur = u
            total += bottleneck
        return total

    def _dfs(self, net: FlowNetwork, u: int, target: int,
             visited: list[bool],
             parent_node: list[int], parent_edge: list[int],
             bottleneck: float) -> float:
        """Find one augmenting path via DFS.

        Fills *parent_node* / *parent_edge* so the caller can reconstruct
        the path.  Returns the bottleneck (0 if no path found).
        """
        visited[u] = True
        if u == target:
            return bottleneck
        for idx, e in enumerate(net.graph[u]):
            if not visited[e.to] and e.residual() > 0:
                parent_node[e.to] = u
                parent_edge[e.to] = idx
                result = self._dfs(net, e.to, target, visited,
                                   parent_node, parent_edge,
                                   min(bottleneck, e.residual()))
                if result > 0:
                    return result
        return 0


class EdmondsKarp:
    """BFS-based Ford-Fulkerson — O(V·E²) worst case.

    Works correctly with floating-point capacities.
    """

    def __init__(self):
        self.iterations = 0

    def solve(self, network: FlowNetwork, source: int, sink: int) -> float | int:
        self.iterations = 0
        total = 0.0
        n = network.n
        while True:
            self.iterations += 1
            # BFS for shortest augmenting path
            parent_edge: list[int] = [-1] * n   # edge index in parent's list
            parent_node: list[int] = [-1] * n
            visited = [False] * n
            visited[source] = True
            q = deque([source])
            while q and not visited[sink]:
                u = q.popleft()
                for idx, e in enumerate(network.graph[u]):
                    if not visited[e.to] and e.residual() > 1e-12:
                        visited[e.to] = True
                        parent_node[e.to] = u
                        parent_edge[e.to] = idx
                        q.append(e.to)
            if not visited[sink]:
                break
            # Find bottleneck along path
            bottleneck = float("inf")
            cur = sink
            while cur != source:
                ei = parent_edge[cur]
                u = parent_node[cur]
                r = network.graph[u][ei].residual()
                if r < bottleneck:
                    bottleneck = r
                cur = u
            # Augment
            cur = sink
            while cur != source:
                ei = parent_edge[cur]
                u = parent_node[cur]
                e = network.graph[u][ei]
                e.flow += bottleneck
                network.graph[e.to][e.rev].flow -= bottleneck
                cur = u
            total += bottleneck
        return total


class Dinic:
    """Dinic's algorithm with level graphs and blocking flows — O(V²·E).

    Uses BFS to build level graphs and DFS to find blocking flows.
    Supports scaling for large networks via the ``scaling`` threshold.
    """

    def __init__(self):
        self.iterations = 0
        self.level: list[int] = []
        self.ptr: list[int] = []

    def solve(self, network: FlowNetwork, source: int, sink: int) -> float | int:
        self.iterations = 0
        n = network.n
        self.level = [0] * n
        self.ptr = [0] * n
        total = 0.0
        while self._bfs(network, source, sink):
            self.ptr = [0] * n
            while True:
                pushed = self._dfs(network, source, sink, float("inf"))
                if pushed < 1e-12:
                    break
                total += pushed
                self.iterations += 1
        return total

    def _bfs(self, net: FlowNetwork, s: int, t: int) -> bool:
        n = net.n
        self.level = [-1] * n
        self.level[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for e in net.graph[u]:
                if self.level[e.to] < 0 and e.residual() > 1e-12:
                    self.level[e.to] = self.level[u] + 1
                    q.append(e.to)
        return self.level[t] >= 0

    def _dfs(self, net: FlowNetwork, u: int, sink: int,
             bottleneck: float) -> float:
        if u == sink:
            return bottleneck
        while self.ptr[u] < len(net.graph[u]):
            e = net.graph[u][self.ptr[u]]
            if self.level[e.to] == self.level[u] + 1 and e.residual() > 1e-12:
                pushed = self._dfs(net, e.to, sink, min(bottleneck, e.residual()))
                if pushed > 1e-12:
                    e.flow += pushed
                    net.graph[e.to][e.rev].flow -= pushed
                    return pushed
            self.ptr[u] += 1
        return 0.0


class PushRelabel:
    """FIFO push-relabel with gap heuristic — O(V³).

    Maintains a height function and pushes excess flow downhill, relabeling
    vertices when no admissible outgoing edge exists.  The gap heuristic
    detects disconnected level sets to accelerate termination.
    """

    def __init__(self):
        self.relabels = 0
        self.pushes = 0

    def solve(self, network: FlowNetwork, source: int, sink: int) -> float | int:
        n = network.n
        height = [0] * n
        excess = [0.0] * n
        # count of nodes at each height (for gap heuristic)
        count = [0] * (2 * n + 1)
        height[source] = n
        count[0] = n - 1
        count[n] = 1

        # Preflow from source
        for e in network.graph[source]:
            if e.cap > 0:
                e.flow = e.cap
                network.graph[e.to][e.rev].flow = -e.cap
                excess[e.to] += e.cap
                excess[source] -= e.cap
                self.pushes += 1

        # FIFO queue
        q = deque()
        in_queue = [False] * n
        for e in network.graph[source]:
            if e.cap > 0 and e.to != sink:
                if not in_queue[e.to]:
                    q.append(e.to)
                    in_queue[e.to] = True

        while q:
            u = q.popleft()
            in_queue[u] = False
            # Discharge u
            while excess[u] > 1e-12:
                pushed_any = False
                for idx, e in enumerate(network.graph[u]):
                    if e.residual() > 1e-12 and height[u] == height[e.to] + 1:
                        # Push
                        amt = min(excess[u], e.residual())
                        if amt <= 0:
                            continue
                        e.flow += amt
                        network.graph[e.to][e.rev].flow -= amt
                        excess[u] -= amt
                        excess[e.to] += amt
                        self.pushes += 1
                        pushed_any = True
                        if e.to != source and e.to != sink and not in_queue[e.to]:
                            q.append(e.to)
                            in_queue[e.to] = True
                        if excess[u] <= 1e-12:
                            break
                if excess[u] > 1e-12:
                    # Relabel
                    old_h = height[u]
                    new_h = float("inf")
                    for e in network.graph[u]:
                        if e.residual() > 1e-12:
                            new_h = min(new_h, height[e.to])
                    if new_h == float("inf"):
                        # No outgoing residual — stuck, set high
                        height[u] = 2 * n + 1
                    else:
                        height[u] = int(new_h) + 1
                    self.relabels += 1
                    # Gap heuristic
                    if old_h < 2 * n + 1:
                        count[old_h] -= 1
                        if count[old_h] == 0 and old_h < n:
                            for v in range(n):
                                if v != source and v != sink and height[v] >= old_h and height[v] < n:
                                    count[height[v]] -= 1
                                    height[v] = n + 1
                                    count[n + 1] += 1
                        count[height[u]] += 1

        return excess[sink]