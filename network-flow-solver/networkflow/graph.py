"""
Graph data structures for network flow algorithms.

Provides FlowNetwork (residual graph) and FlowEdge with support for
parallel edges, capacities, and costs for min-cost flow problems.
"""

from __future__ import annotations

import json
from typing import Any, Iterator


class FlowEdge:
    """A directed edge in a flow network with capacity and optional cost.

    Each edge stores its current flow and maintains a back-reference to its
    reverse (residual) counterpart so that residual graph updates are O(1).
    """

    __slots__ = ("to", "cap", "cost", "flow", "rev")

    def __init__(self, to: int, cap: float | int, cost: float = 0.0, rev: int = 0):
        self.to: int = to
        self.cap: float | int = cap
        self.cost: float = cost
        self.flow: float | int = 0
        self.rev: int = rev

    def residual(self) -> float | int:
        """Remaining (residual) capacity on this edge."""
        return self.cap - self.flow

    def __repr__(self) -> str:
        return (
            f"FlowEdge(to={self.to}, cap={self.cap}, cost={self.cost}, "
            f"flow={self.flow})"
        )


class FlowNetwork:
    """A directed flow network with integer/float capacities and optional costs.

    Internally represented as an adjacency list of ``FlowEdge`` objects.
    Adding an edge automatically creates a zero-capacity reverse edge so the
    data structure doubles as its own residual graph.

    Example
    -------
    >>> net = FlowNetwork(4)
    >>> net.add_edge(0, 1, 10)
    >>> net.add_edge(1, 2, 5)
    >>> net.add_edge(2, 3, 10)
    >>> net.add_edge(0, 3, 5)
    >>> net.edge_count()
    4
    """

    def __init__(self, n: int):
        if n < 0:
            raise ValueError(f"Number of nodes must be non-negative, got {n}")
        self.n: int = n
        self.graph: list[list[FlowEdge]] = [[] for _ in range(n)]

    # -- construction ---------------------------------------------------

    def add_edge(self, u: int, v: int, cap: float | int,
                 cost: float = 0.0, bidirectional: bool = False) -> int:
        """Add a directed edge *u → v* with given capacity (and optional cost).

        If *bidirectional* is True the reverse edge also gets *cap* (instead of
        zero), which is useful for undirected max-flow problems.

        Returns the index of the forward edge in ``graph[u]``.
        """
        self._validate_node(u)
        self._validate_node(v)
        if u == v:
            raise ValueError(f"Self-loop not allowed: {u} -> {u}")
        if cap < 0:
            raise ValueError(f"Negative capacity {cap} on edge {u} -> {v}")

        rev_cap = cap if bidirectional else 0
        fwd = FlowEdge(v, cap, cost, len(self.graph[v]))
        rev = FlowEdge(u, rev_cap, -cost, len(self.graph[u]))
        self.graph[u].append(fwd)
        self.graph[v].append(rev)
        return len(self.graph[u]) - 1

    def add_node(self) -> int:
        """Add a new isolated node and return its index."""
        self.n += 1
        self.graph.append([])
        return self.n - 1

    # -- accessors ------------------------------------------------------

    def edges_from(self, u: int) -> list[FlowEdge]:
        """Return all edges (including residual) leaving node *u*."""
        self._validate_node(u)
        return self.graph[u]

    def edge_count(self) -> int:
        """Number of *forward* edges (excluding auto-created residual edges)."""
        # Each add_edge creates exactly one forward edge and one reverse.
        return sum(len(adj) for adj in self.graph) // 2

    def node_count(self) -> int:
        return self.n

    def neighbors(self, u: int) -> Iterator[int]:
        """Yield target nodes of forward edges (positive capacity) from *u*."""
        self._validate_node(u)
        for e in self.graph[u]:
            if e.cap > 0:
                yield e.to

    def out_edges(self, u: int) -> Iterator[tuple[int, FlowEdge]]:
        """Yield (index, edge) pairs for all forward edges from *u*."""
        self._validate_node(u)
        for idx, e in enumerate(self.graph[u]):
            if e.cap > 0:
                yield idx, e

    # -- I/O ------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (for JSON)."""
        edges = []
        for u in range(self.n):
            for e in self.graph[u]:
                if e.cap > 0:  # forward edges only
                    edges.append({
                        "from": u, "to": e.to, "cap": e.cap,
                        "cost": e.cost, "flow": e.flow,
                    })
        return {"n": self.n, "edges": edges}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FlowNetwork":
        """Reconstruct a FlowNetwork from a serialized dict."""
        net = cls(d["n"])
        for e in d["edges"]:
            idx = net.add_edge(e["from"], e["to"], e["cap"], e.get("cost", 0.0))
            # restore flow on the forward edge and its reverse
            net.graph[e["from"]][idx].flow = e.get("flow", 0)
        return net

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, s: str) -> "FlowNetwork":
        return cls.from_dict(json.loads(s))

    def copy(self) -> "FlowNetwork":
        """Deep copy of this network (including flow values)."""
        return FlowNetwork.from_dict(self.to_dict())

    def reset_flows(self) -> None:
        """Set all edge flows back to zero."""
        for u in range(self.n):
            for e in self.graph[u]:
                e.flow = 0

    # -- validation -----------------------------------------------------

    def _validate_node(self, u: int) -> None:
        if not (0 <= u < self.n):
            raise IndexError(f"Node {u} out of range [0, {self.n})")

    def validate_flow(self, source: int, sink: int) -> float | int:
        """Check flow conservation and return total flow value.

        Raises ``ValueError`` if conservation is violated.
        """
        self._validate_node(source)
        self._validate_node(sink)
        excess = [0.0] * self.n
        for u in range(self.n):
            for e in self.graph[u]:
                if e.cap > 0:  # forward edge
                    excess[u] -= e.flow
                    excess[e.to] += e.flow
        for i in range(self.n):
            if i == source or i == sink:
                continue
            if abs(excess[i]) > 1e-9:
                raise ValueError(f"Flow conservation violated at node {i}: excess={excess[i]}")
        if abs(excess[source] + excess[sink]) > 1e-9:
            raise ValueError("Source outflow does not equal sink inflow")
        return excess[sink]

    def __repr__(self) -> str:
        return f"FlowNetwork(n={self.n}, edges={self.edge_count()})"