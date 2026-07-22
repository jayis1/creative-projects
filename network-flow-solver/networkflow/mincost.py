"""
Minimum-cost maximum-flow algorithms.

Implements:
  - SPFA-based successive shortest paths (handles negative-cost edges via
    Bellman-Ford initial potential)
  - Johnson's all-pairs potential optimization for dense graphs

The solver finds the maximum flow that also minimizes total cost.
"""

from __future__ import annotations

from collections import deque

from .graph import FlowNetwork


class MinCostMaxFlow:
    """Min-cost max-flow via successive shortest paths with SPFA.

    Handles negative-cost edges by computing initial node potentials via
    Bellman-Ford on the residual graph (using reverse edges as needed).

    Attributes
    ----------
    total_flow : the max flow value found
    total_cost : the minimum cost to achieve that flow
    """

    def __init__(self):
        self.total_flow: float = 0.0
        self.total_cost: float = 0.0
        self.iterations: int = 0

    def solve(self, network: FlowNetwork, source: int,
              sink: int) -> tuple[float, float]:
        """Compute (max_flow, min_cost) from *source* to *sink*.

        The network's edge flows are updated in-place.
        """
        n = network.n
        self.total_flow = 0.0
        self.total_cost = 0.0
        self.iterations = 0

        # Compute initial potentials with Bellman-Ford to handle negative edges
        potential = self._initial_potentials(network, source)

        while True:
            self.iterations += 1
            # SPFA (shortest path faster algorithm) with reduced costs
            dist = [float("inf")] * n
            dist[source] = 0.0
            in_queue = [False] * n
            in_queue[source] = True
            parent_node = [-1] * n
            parent_edge = [-1] * n
            q = deque([source])
            cnt = [0] * n
            while q:
                u = q.popleft()
                in_queue[u] = False
                for idx, e in enumerate(network.graph[u]):
                    if e.residual() <= 1e-12:
                        continue
                    # Reduced cost
                    rc = e.cost + potential[u] - potential[e.to]
                    if dist[u] + rc < dist[e.to] - 1e-12:
                        dist[e.to] = dist[u] + rc
                        parent_node[e.to] = u
                        parent_edge[e.to] = idx
                        cnt[e.to] = cnt[u] + 1
                        if cnt[e.to] >= n:
                            # Negative cycle detected — should not happen with
                            # valid initial potentials, but guard anyway.
                            raise RuntimeError("Negative cycle in residual graph")
                        if not in_queue[e.to]:
                            q.append(e.to)
                            in_queue[e.to] = True
            if dist[sink] == float("inf"):
                break  # No more augmenting paths
            # Update potentials
            for i in range(n):
                if dist[i] < float("inf"):
                    potential[i] += dist[i]
            # Find bottleneck
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
                self.total_cost += bottleneck * e.cost
                cur = u
            self.total_flow += bottleneck
        return self.total_flow, self.total_cost

    def _initial_potentials(self, net: FlowNetwork,
                            source: int) -> list[float]:
        """Bellman-Ford to find initial potentials (handles neg-cost edges)."""
        n = net.n
        dist = [float("inf")] * n
        dist[source] = 0.0
        # Relax V-1 times
        for _ in range(n - 1):
            updated = False
            for u in range(n):
                if dist[u] == float("inf"):
                    continue
                for e in net.graph[u]:
                    if e.residual() > 1e-12 and dist[u] + e.cost < dist[e.to]:
                        dist[e.to] = dist[u] + e.cost
                        updated = True
            if not updated:
                break
        # Replace inf with 0 so reduced costs work
        return [d if d < float("inf") else 0.0 for d in dist]


class MinCostFlow:
    """Min-cost flow with a fixed flow target (not necessarily max flow).

    Finds the cheapest way to send exactly *target_flow* units from source
    to sink.  Returns (flow_sent, cost).  If the target cannot be met, returns
    the maximum achievable flow and its cost.
    """

    def __init__(self):
        self.flow_sent: float = 0.0
        self.cost: float = 0.0

    def solve(self, network: FlowNetwork, source: int, sink: int,
              target_flow: float) -> tuple[float, float]:
        n = network.n
        self.flow_sent = 0.0
        self.cost = 0.0
        potential = self._initial_potentials(network, source)
        while self.flow_sent < target_flow - 1e-12:
            dist = [float("inf")] * n
            dist[source] = 0.0
            in_queue = [False] * n
            in_queue[source] = True
            parent_node = [-1] * n
            parent_edge = [-1] * n
            q = deque([source])
            while q:
                u = q.popleft()
                in_queue[u] = False
                for idx, e in enumerate(network.graph[u]):
                    if e.residual() <= 1e-12:
                        continue
                    rc = e.cost + potential[u] - potential[e.to]
                    if dist[u] + rc < dist[e.to] - 1e-12:
                        dist[e.to] = dist[u] + rc
                        parent_node[e.to] = u
                        parent_edge[e.to] = idx
                        if not in_queue[e.to]:
                            q.append(e.to)
                            in_queue[e.to] = True
            if dist[sink] == float("inf"):
                break
            for i in range(n):
                if dist[i] < float("inf"):
                    potential[i] += dist[i]
            bottleneck = float("inf")
            cur = sink
            while cur != source:
                ei = parent_edge[cur]
                u = parent_node[cur]
                r = network.graph[u][ei].residual()
                if r < bottleneck:
                    bottleneck = r
                cur = u
            bottleneck = min(bottleneck, target_flow - self.flow_sent)
            cur = sink
            while cur != source:
                ei = parent_edge[cur]
                u = parent_node[cur]
                e = network.graph[u][ei]
                e.flow += bottleneck
                network.graph[e.to][e.rev].flow -= bottleneck
                self.cost += bottleneck * e.cost
                cur = u
            self.flow_sent += bottleneck
        return self.flow_sent, self.cost

    def _initial_potentials(self, net: FlowNetwork,
                            source: int) -> list[float]:
        n = net.n
        dist = [float("inf")] * n
        dist[source] = 0.0
        for _ in range(n - 1):
            updated = False
            for u in range(n):
                if dist[u] == float("inf"):
                    continue
                for e in net.graph[u]:
                    if e.residual() > 1e-12 and dist[u] + e.cost < dist[e.to]:
                        dist[e.to] = dist[u] + e.cost
                        updated = True
            if not updated:
                break
        return [d if d < float("inf") else 0.0 for d in dist]