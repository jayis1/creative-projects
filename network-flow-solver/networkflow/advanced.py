"""
Advanced max-flow algorithms and multi-source/multi-sink support.

  - BoykovKolmogorov: max-flow via two trees growing from source and sink.
    Excellent for graphs with low connectivity (vision / image segmentation).
  - MultiSourceSink: wrapper that adds a super-source and super-sink to
    handle multiple sources/sinks with individual supply/demand values.
  - CycleCanceling: min-cost flow via cycle cancellation (alternative to
    successive shortest paths).
"""

from __future__ import annotations

from collections import deque
from typing import Sequence

from .graph import FlowNetwork
from .maxflow import Dinic
from .mincost import MinCostMaxFlow


class BoykovKolmogorov:
    """Boykov-Kolmogorov max-flow algorithm.

    Uses two search trees — one rooted at the source (S-tree) and one at
    the sink (T-tree) — that grow simultaneously.  When an edge connecting
    the two trees is found, an augmenting path is established.  After
    augmentation, orphaned nodes are adopted.

    This algorithm has O(V²·E·|C|) worst-case but is empirically much faster
    on low-connectivity graphs common in computer vision.

    Attributes
    ----------
    iterations : int
        Number of augmenting paths found.
    """

    def __init__(self):
        self.iterations: int = 0

    def solve(self, network: FlowNetwork, source: int, sink: int) -> float | int:
        self.iterations = 0
        n = network.n
        max_iters = 100_000  # safety limit
        # TREE: 0=free, 1=S-tree, 2=T-tree
        tree = [0] * n
        tree[source] = 1
        tree[sink] = 2
        # parent: (parent_node, edge_index_in_parent_adjacency)
        parent: list[tuple[int, int] | None] = [None] * n
        # Active set: nodes whose edges haven't been fully explored
        active: set[int] = {source, sink}

        total = 0.0

        while self.iterations < max_iters:
            # Growth phase: find an augmenting path
            path = self._grow(network, source, sink, tree, parent, active)
            if path is None:
                break

            # Find bottleneck along the path
            bottleneck = self._bottleneck(network, path)
            if bottleneck <= 1e-12:
                break

            # Augment
            self._augment(network, path, bottleneck, tree, parent, active,
                          source, sink)
            total += bottleneck
            self.iterations += 1

            # Source and sink are always re-activated after augmentation
            active.add(source)
            active.add(sink)

            # Adoption phase: fix orphaned nodes
            self._adopt(network, tree, parent, active, source, sink)

        return total

    def _grow(self, net: FlowNetwork, source: int, sink: int,
              tree: list[int], parent: list,
              active: set[int]) -> list[tuple[int, int, int]] | None:
        """Growth phase: expand active nodes until trees meet.

        Returns a list of (u, edge_idx, v) tuples representing the augmenting
        path from source to sink, or None if no path exists.
        """
        while active:
            # Pick an active node (any order)
            u = next(iter(active))

            tu = tree[u]
            found_child = False

            for idx, e in enumerate(net.graph[u]):
                if tu == 1:
                    # S-tree: follow edges with residual > 0
                    if e.residual() <= 1e-12:
                        continue
                    if tree[e.to] == 0:
                        tree[e.to] = 1
                        parent[e.to] = (u, idx)
                        active.add(e.to)
                        found_child = True
                    elif tree[e.to] == 2:
                        # Trees meet! Path: source → u → e.to → sink
                        return self._build_path(net, u, idx, e.to,
                                                source, sink, parent)
                elif tu == 2:
                    # T-tree: grow backward — we need edges where the
                    # reverse edge (e.to → u) has residual > 0.
                    # The reverse edge is at net.graph[e.to][e.rev].
                    if e.rev < len(net.graph[e.to]):
                        rev_e = net.graph[e.to][e.rev]
                        if rev_e.residual() <= 1e-12:
                            continue
                    else:
                        continue
                    if tree[e.to] == 0:
                        tree[e.to] = 2
                        parent[e.to] = (u, idx)
                        active.add(e.to)
                        found_child = True
                    elif tree[e.to] == 1:
                        # Trees meet: S-tree node found from T-tree
                        # Path: source → e.to → u → sink
                        return self._build_path(net, e.to, e.rev, u,
                                                source, sink, parent)

            # Node u is done exploring — remove from active
            active.discard(u)

        return None

    def _build_path(self, net: FlowNetwork, s_node: int, s_edge: int,
                    t_node: int, source: int, sink: int,
                    parent: list) -> list[tuple[int, int, int]]:
        """Build the full s-t path from the meeting point.

        Returns list of (u, edge_idx, v) tuples representing edges along
        the path from source to sink.
        """
        # Path from source to s_node (S-tree: parent links point toward source)
        s_path: list[tuple[int, int, int]] = []
        cur = s_node
        while cur != source:
            p_node, p_edge = parent[cur]
            s_path.append((p_node, p_edge, cur))
            cur = p_node
        s_path.reverse()

        # The connecting edge: s_node → t_node via edge s_edge in s_node's list
        mid = (s_node, s_edge, t_node)

        # Path from t_node to sink (T-tree: parent links point toward sink)
        t_path: list[tuple[int, int, int]] = []
        cur = t_node
        while cur != sink:
            p_node, p_edge = parent[cur]
            # In T-tree, parent[cur] = (p_node, p_edge) means the edge
            # from cur's adjacency at index p_edge connects to p_node.
            # The actual flow edge is the reverse edge: net.graph[p_node][...]
            # But for augmentation, we need the edge that carries flow.
            # In T-tree, the path goes cur → p_node, and the edge in
            # cur's adjacency at p_edge is the reverse edge.
            t_path.append((cur, p_edge, p_node))
            cur = p_node

        return s_path + [mid] + t_path

    def _bottleneck(self, net: FlowNetwork,
                    path: list[tuple[int, int, int]]) -> float:
        """Find the minimum residual along the path."""
        bottleneck = float("inf")
        for u, ei, v in path:
            e = net.graph[u][ei]
            bottleneck = min(bottleneck, e.residual())
        return max(bottleneck, 0.0)

    def _augment(self, net: FlowNetwork,
                 path: list[tuple[int, int, int]], bottleneck: float,
                 tree: list[int], parent: list,
                 active: set[int],
                 source: int, sink: int) -> None:
        """Augment flow along path and mark saturated-edge endpoints as orphans."""
        orphans: list[int] = []

        for u, ei, v in path:
            e = net.graph[u][ei]
            e.flow += bottleneck
            net.graph[e.to][e.rev].flow -= bottleneck
            # If this edge is now saturated, the child in the tree becomes orphan
            if e.residual() <= 1e-12:
                # In S-tree, v is child of u; in T-tree, the structure differs
                if tree[u] == 1 and tree[v] == 1 and parent[v] is not None:
                    if parent[v][0] == u:
                        orphans.append(v)
                elif tree[v] == 2 and tree[u] == 2 and parent[u] is not None:
                    if parent[u][0] == v:
                        orphans.append(u)

        # Process orphans in adoption
        for node in orphans:
            parent[node] = None
            active.add(node)

    def _adopt(self, net: FlowNetwork, tree: list[int],
               parent: list, active: set[int],
               source: int, sink: int) -> None:
        """Adoption phase: find new parents for orphaned nodes.

        Orphans search their neighbors for a valid parent in the same tree.
        The candidate parent must be connected to the root (source for S-tree,
        sink for T-tree) without passing through the orphan — this prevents
        cycles.  If no valid parent is found, the node becomes free and its
        children become orphans.
        """
        orphans: deque[int] = deque()
        for i in range(len(parent)):
            if parent[i] is None and tree[i] != 0 and i != source and i != sink:
                orphans.append(i)

        while orphans:
            u = orphans.popleft()
            tu = tree[u]
            found_parent = False

            if tu == 1:
                # S-tree orphan: find a node v in S-tree such that
                # the edge v→u has residual > 0 and v is connected to source
                for idx, e in enumerate(net.graph[u]):
                    if e.rev < len(net.graph[e.to]):
                        rev_e = net.graph[e.to][e.rev]
                        if (rev_e.residual() > 1e-12
                                and tree[e.to] == 1
                                and parent[e.to] is not None
                                and e.to != u
                                and self._connected_to_root(
                                    e.to, source, parent, max_depth=net.n)):
                            parent[u] = (e.to, e.rev)
                            found_parent = True
                            break
            elif tu == 2:
                # T-tree orphan: find a node v in T-tree such that
                # the reverse edge v→u has residual > 0 and v connected to sink
                for idx, e in enumerate(net.graph[u]):
                    if e.rev < len(net.graph[e.to]):
                        rev_e = net.graph[e.to][e.rev]
                        if (rev_e.residual() > 1e-12
                                and tree[e.to] == 2
                                and parent[e.to] is not None
                                and e.to != u
                                and self._connected_to_root(
                                    e.to, sink, parent, max_depth=net.n)):
                            parent[u] = (e.to, idx)
                            found_parent = True
                            break

            if not found_parent:
                # Make children orphans, then free this node
                for idx, e in enumerate(net.graph[u]):
                    child = e.to
                    if tree[child] == tu and parent[child] is not None:
                        pc, pe = parent[child]
                        if pc == u:
                            parent[child] = None
                            orphans.append(child)
                tree[u] = 0
                parent[u] = None
                active.discard(u)

    @staticmethod
    def _connected_to_root(node: int, root: int,
                            parent: list, max_depth: int = 1000) -> bool:
        """Check if *node* can reach *root* via parent pointers (no cycle)."""
        visited = {node}
        cur = node
        for _ in range(max_depth):
            if cur == root:
                return True
            p = parent[cur]
            if p is None:
                return False
            cur = p[0]
            if cur in visited:
                return False  # cycle detected
            visited.add(cur)
        return False


class MultiSourceSink:
    """Wrapper for multi-source / multi-sink max-flow.

    Adds a super-source connected to all real sources and a super-sink
    connected from all real sinks, then solves max-flow on the augmented
    network.

    Example
    -------
    >>> net = FlowNetwork(5)
    >>> net.add_edge(0, 2, 10)
    >>> net.add_edge(1, 2, 5)
    >>> net.add_edge(2, 3, 8)
    >>> net.add_edge(2, 4, 7)
    >>> ms = MultiSourceSink()
    >>> flow, augmented = ms.solve(net, sources=[0, 1], sinks=[3, 4],
    ...                            source_caps=[10, 5], sink_caps=[8, 7])
    >>> print(flow)
    """

    def __init__(self, solver=None):
        self.solver = solver or Dinic()

    def solve(self, network: FlowNetwork,
              sources: Sequence[int],
              sinks: Sequence[int],
              source_caps: Sequence[float | int] | None = None,
              sink_caps: Sequence[float | int] | None = None,
              ) -> tuple[float, FlowNetwork]:
        """Compute max-flow with multiple sources and sinks.

        Parameters
        ----------
        network : FlowNetwork
            The base network.
        sources : list of int
            Node indices acting as sources.
        sinks : list of int
            Node indices acting as sinks.
        source_caps : list, optional
            Supply capacity for each source.  If None, unlimited.
        sink_caps : list, optional
            Demand capacity for each sink.  If None, unlimited.

        Returns
        -------
        (flow_value, augmented_network)
            The max flow value and the augmented network (with super-source
            and super-sink added).
        """
        if not sources:
            raise ValueError("At least one source required")
        if not sinks:
            raise ValueError("At least one sink required")
        if source_caps and len(source_caps) != len(sources):
            raise ValueError("source_caps length must match sources")
        if sink_caps and len(sink_caps) != len(sinks):
            raise ValueError("sink_caps length must match sinks")

        n = network.n
        # Create augmented network by copying and adding 2 nodes
        aug = network.copy()
        super_source = aug.add_node()  # node n
        super_sink = aug.add_node()    # node n+1

        INF = float("inf")
        for i, s in enumerate(sources):
            cap = source_caps[i] if source_caps else INF
            if cap != INF:
                aug.add_edge(super_source, s, cap)
            else:
                aug.add_edge(super_source, s, 10**15)  # large finite

        for i, t in enumerate(sinks):
            cap = sink_caps[i] if sink_caps else INF
            if cap != INF:
                aug.add_edge(t, super_sink, cap)
            else:
                aug.add_edge(t, super_sink, 10**15)

        flow = self.solver.solve(aug, super_source, super_sink)
        return flow, aug


class CycleCanceling:
    """Min-cost flow via cycle cancellation.

    After finding a max-flow (using any max-flow algorithm), this method
    repeatedly finds negative-cost cycles in the residual graph and
    augments along them to reduce total cost while maintaining the flow
    value.

    Uses SPFA-based negative cycle detection.

    Attributes
    ----------
    total_flow : float
    total_cost : float
    """

    def __init__(self, max_flow_solver=None):
        self.max_flow_solver = max_flow_solver or Dinic()
        self.total_flow: float = 0.0
        self.total_cost: float = 0.0
        self.iterations: int = 0

    def solve(self, network: FlowNetwork, source: int,
              sink: int) -> tuple[float, float]:
        """Compute min-cost max-flow via cycle cancellation.

        Returns (flow, cost).
        """
        # Step 1: Find max flow
        self.total_flow = self.max_flow_solver.solve(network, source, sink)

        # Step 2: Compute initial cost
        self.total_cost = 0.0
        for u in range(network.n):
            for e in network.graph[u]:
                if e.cap > 0 and e.flow > 0:
                    self.total_cost += e.flow * e.cost

        # Step 3: Cancel negative cycles
        n = network.n
        while True:
            self.iterations += 1
            # SPFA to detect negative cycles
            dist = [0.0] * n
            in_queue = [False] * n
            cnt = [0] * n
            parent_node = [-1] * n
            parent_edge = [-1] * n
            q = deque(range(n))
            for i in range(n):
                in_queue[i] = True

            negative_cycle = None
            while q:
                u = q.popleft()
                in_queue[u] = False
                for idx, e in enumerate(network.graph[u]):
                    if e.residual() <= 1e-12:
                        continue
                    if dist[u] + e.cost < dist[e.to] - 1e-12:
                        dist[e.to] = dist[u] + e.cost
                        parent_node[e.to] = u
                        parent_edge[e.to] = idx
                        cnt[e.to] = cnt[u] + 1
                        if cnt[e.to] >= n:
                            # Found a negative cycle — trace it
                            negative_cycle = self._trace_cycle(
                                e.to, parent_node, parent_edge, n)
                            break
                        if not in_queue[e.to]:
                            q.append(e.to)
                            in_queue[e.to] = True
                if negative_cycle:
                    break

            if not negative_cycle:
                break

            # Find bottleneck along the cycle
            bottleneck = float("inf")
            for u, ei in negative_cycle:
                e = network.graph[u][ei]
                bottleneck = min(bottleneck, e.residual())

            # Augment along the cycle
            cost_delta = 0.0
            for u, ei in negative_cycle:
                e = network.graph[u][ei]
                e.flow += bottleneck
                network.graph[e.to][e.rev].flow -= bottleneck
                cost_delta += bottleneck * e.cost

            self.total_cost += cost_delta

        return self.total_flow, self.total_cost

    def _trace_cycle(self, start: int, parent_node: list[int],
                     parent_edge: list[int], n: int) -> list[tuple[int, int]]:
        """Trace the negative cycle from the detected node."""
        # Walk back n steps to get inside the cycle
        cur = start
        for _ in range(n + 1):
            cur = parent_node[cur]
        # Now trace the full cycle
        cycle_start = cur
        cycle: list[tuple[int, int]] = []
        cur = cycle_start
        while True:
            ei = parent_edge[cur]
            pu = parent_node[cur]
            cycle.append((pu, ei))
            cur = pu
            if cur == cycle_start:
                break
        return cycle