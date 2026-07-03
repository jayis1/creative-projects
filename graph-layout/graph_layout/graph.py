"""Core graph data structure for layout algorithms.

Provides an undirected or directed graph with weighted edges, node attributes,
and adjacency operations used by all layout algorithms.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterator, Optional, Union, Dict, List, Tuple, Set

Number = Union[int, float]


@dataclass
class Node:
    """A graph node with optional position and attributes.

    Attributes:
        id: unique identifier.
        x, y: 2D coordinates (None until a layout assigns them).
        width, height: bounding box for node size (used by some layouts).
        attributes: arbitrary metadata.
    """

    id: str
    x: Optional[float] = None
    y: Optional[float] = None
    width: float = 1.0
    height: float = 1.0
    attributes: Dict[str, object] = field(default_factory=dict)

    def pos(self) -> Optional[Tuple[float, float]]:
        if self.x is None or self.y is None:
            return None
        return (self.x, self.y)

    def distance_to(self, other: "Node") -> float:
        if self.x is None or self.y is None or other.x is None or other.y is None:
            raise ValueError("Both nodes must have positions")
        return math.hypot(self.x - other.x, self.y - other.y)

    def __repr__(self) -> str:
        return f"Node({self.id!r}, x={self.x}, y={self.y})"


@dataclass
class Edge:
    """A weighted edge between two node ids.

    Attributes:
        source: source node id.
        target: target node id.
        weight: edge weight (default 1.0).
        directed: whether the edge is directed.
        attributes: arbitrary metadata.
    """

    source: str
    target: str
    weight: float = 1.0
    directed: bool = False
    attributes: Dict[str, object] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Edge({self.source!r} -> {self.target!r}, w={self.weight})"


class Graph:
    """A graph supporting directed/undirected edges, weights, and attributes.

    Args:
        directed: if True, edges are treated as directed.

    Example::

        g = Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B", weight=2.0)
    """

    def __init__(self, directed: bool = False) -> None:
        self.directed = directed
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        self._adj: Dict[str, Set[str]] = {}
        self._edge_map: Dict[Tuple[str, str], Edge] = {}

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def add_node(self, node_id: str, **attrs) -> Node:
        """Add a node, returning it. Updates attributes if already present."""
        if node_id not in self._nodes:
            self._nodes[node_id] = Node(id=node_id)
            self._adj[node_id] = set()
        if attrs:
            self._nodes[node_id].attributes.update(attrs)
        return self._nodes[node_id]

    def add_edge(self, source: str, target: str, weight: float = 1.0,
                 directed: Optional[bool] = None, **attrs) -> Edge:
        """Add an edge. Auto-creates missing nodes."""
        self.add_node(source)
        self.add_node(target)
        d = self.directed if directed is None else directed
        edge = Edge(source=source, target=target, weight=weight, directed=d,
                    attributes=attrs)
        self._edges.append(edge)
        self._adj[source].add(target)
        self._adj[target].add(source)
        key = (source, target) if d else (frozenset({source, target}), Edge)
        # store canonical for undirected lookup both directions
        if not d:
            self._edge_map[(source, target)] = edge
            self._edge_map[(target, source)] = edge
        else:
            self._edge_map[(source, target)] = edge
        return edge

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all incident edges."""
        if node_id not in self._nodes:
            return
        del self._nodes[node_id]
        neighbors = self._adj.pop(node_id, set())
        for n in neighbors:
            self._adj[n].discard(node_id)
        self._edges = [e for e in self._edges
                       if e.source != node_id and e.target != node_id]
        to_del = [k for k in self._edge_map
                  if k[0] == node_id or k[1] == node_id]
        for k in to_del:
            del self._edge_map[k]

    def remove_edge(self, source: str, target: str) -> None:
        """Remove a single edge (undirected removes either direction)."""
        self._edges = [e for e in self._edges
                       if not ((e.source == source and e.target == target)
                               or (not e.directed and e.source == target and e.target == source))]
        self._adj[source].discard(target)
        self._adj[target].discard(source)
        self._edge_map.pop((source, target), None)
        self._edge_map.pop((target, source), None)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def nodes(self) -> Dict[str, Node]:
        return self._nodes

    @property
    def edges(self) -> List[Edge]:
        return self._edges

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def has_edge(self, a: str, b: str) -> bool:
        return b in self._adj.get(a, set())

    def get_node(self, node_id: str) -> Node:
        if node_id not in self._nodes:
            raise KeyError(f"Node {node_id!r} not found")
        return self._nodes[node_id]

    def get_edge(self, a: str, b: str) -> Optional[Edge]:
        return self._edge_map.get((a, b))

    def neighbors(self, node_id: str) -> Set[str]:
        return self._adj.get(node_id, set()).copy()

    def degree(self, node_id: str) -> int:
        return len(self._adj.get(node_id, set()))

    def neighbor_list(self) -> Dict[str, List[str]]:
        return {n: sorted(s) for n, s in self._adj.items()}

    def __len__(self) -> int:
        return self.node_count

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def __iter__(self) -> Iterator[str]:
        return iter(self._nodes)

    def iter_nodes(self) -> Iterator[Node]:
        return iter(self._nodes.values())

    def iter_edges(self) -> Iterator[Edge]:
        return iter(self._edges)

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------
    def is_connected(self) -> bool:
        """Check if the underlying undirected graph is connected."""
        if not self._nodes:
            return True
        start = next(iter(self._nodes))
        visited = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            stack.extend(self._adj.get(n, set()) - visited)
        return len(visited) == len(self._nodes)

    def connected_components(self) -> List[List[str]]:
        """Return list of connected components (node id lists)."""
        visited: Set[str] = set()
        components: List[List[str]] = []
        for n in self._nodes:
            if n in visited:
                continue
            comp: List[str] = []
            stack = [n]
            while stack:
                m = stack.pop()
                if m in visited:
                    continue
                visited.add(m)
                comp.append(m)
                stack.extend(self._adj.get(m, set()) - visited)
            components.append(comp)
        return components

    def shortest_path_lengths(self) -> Dict[Tuple[str, str], int]:
        """All-pairs shortest path lengths via BFS (unweighted).

        Returns dict mapping (src, dst) -> number of edges.
        """
        dists: Dict[Tuple[str, str], int] = {}
        for src in self._nodes:
            dist: Dict[str, int] = {src: 0}
            queue = [src]
            while queue:
                cur = queue.pop(0)
                d = dist[cur]
                for nbr in self._adj.get(cur, set()):
                    if nbr not in dist:
                        dist[nbr] = d + 1
                        queue.append(nbr)
            for dst, d in dist.items():
                dists[(src, dst)] = d
        return dists

    def copy(self) -> "Graph":
        g = Graph(directed=self.directed)
        for nid, node in self._nodes.items():
            g.add_node(nid, **node.attributes)
            g._nodes[nid].x = node.x
            g._nodes[nid].y = node.y
            g._nodes[nid].width = node.width
            g._nodes[nid].height = node.height
        for e in self._edges:
            g.add_edge(e.source, e.target, e.weight, e.directed, **e.attributes)
        return g

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------
    @classmethod
    def from_edge_list(cls, edges: List[Tuple[str, str]],
                       directed: bool = False) -> "Graph":
        g = cls(directed=directed)
        for s, t in edges:
            g.add_edge(s, t)
        return g

    @classmethod
    def complete_graph(cls, n: int) -> "Graph":
        g = cls()
        for i in range(n):
            g.add_node(str(i))
        for i in range(n):
            for j in range(i + 1, n):
                g.add_edge(str(i), str(j))
        return g

    @classmethod
    def grid_graph(cls, rows: int, cols: int) -> "Graph":
        """A rows×cols grid graph."""
        g = cls()
        for r in range(rows):
            for c in range(cols):
                nid = f"n_{r}_{c}"
                g.add_node(nid)
                if c > 0:
                    g.add_edge(nid, f"n_{r}_{c-1}")
                if r > 0:
                    g.add_edge(nid, f"n_{r-1}_{c}")
        return g

    @classmethod
    def tree_graph(cls, branching: int, depth: int) -> "Graph":
        """A balanced tree of given branching factor and depth."""
        g = cls()
        nodes_at_depth: List[str] = []
        # root
        root = "0"
        g.add_node(root)
        nodes_at_depth = [root]
        for d in range(1, depth + 1):
            next_level: List[str] = []
            for idx, parent in enumerate(nodes_at_depth):
                for b in range(branching):
                    child = f"{parent}.{b}"
                    g.add_node(child)
                    g.add_edge(parent, child)
                    next_level.append(child)
            nodes_at_depth = next_level
        return g

    def __repr__(self) -> str:
        return f"Graph(nodes={self.node_count}, edges={self.edge_count}, directed={self.directed})"