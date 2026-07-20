"""Approximation algorithms for metric TSP: MST-based and Christofides."""

from __future__ import annotations

import heapq
from typing import List, Set, Tuple

from .instance import TSPInstance
from .tour import Tour


def mst_approx(instance: TSPInstance) -> Tour:
    """MST-based 2-approximation for metric TSP.

    Build a minimum spanning tree, do a DFS preorder walk, and shortcut
    repeated cities (valid for metric distances via triangle inequality).
    """
    n = instance.n
    matrix = instance.matrix

    # Prim's MST
    in_tree = [False] * n
    in_tree[0] = True
    mst_adj: List[List[int]] = [[] for _ in range(n)]
    edges = []
    for j in range(1, n):
        heapq.heappush(edges, (matrix[0, j], 0, j))

    while edges:
        d, u, v = heapq.heappop(edges)
        if in_tree[v]:
            continue
        in_tree[v] = True
        mst_adj[u].append(v)
        mst_adj[v].append(u)
        for w in range(n):
            if not in_tree[w]:
                heapq.heappush(edges, (matrix[v, w], v, w))

    # DFS preorder
    visited = [False] * n
    walk: List[int] = []

    def dfs(u: int) -> None:
        visited[u] = True
        walk.append(u)
        for v in mst_adj[u]:
            if not visited[v]:
                dfs(v)

    dfs(0)
    # Shortcut: remove duplicates, keep first occurrence
    seen: Set[int] = set()
    order: List[int] = []
    for c in walk:
        if c not in seen:
            seen.add(c)
            order.append(c)
    cost = instance.tour_length(order)
    return Tour(order, cost)


def christofides(instance: TSPInstance) -> Tour:
    """Christofides' 1.5-approximation algorithm for metric TSP.

    Steps:
    1. Build MST.
    2. Find odd-degree vertices.
    3. Minimum-weight perfect matching on odd-degree vertices (greedy).
    4. Eulerian multigraph from MST + matching.
    5. Find Eulerian circuit and shortcut.
    """
    n = instance.n
    matrix = instance.matrix

    # 1. MST via Prim's
    in_tree = [False] * n
    in_tree[0] = True
    mst_adj: List[List[int]] = [[] for _ in range(n)]
    edges: List[Tuple[float, int, int]] = []
    for j in range(1, n):
        heapq.heappush(edges, (matrix[0, j], 0, j))

    while edges:
        d, u, v = heapq.heappop(edges)
        if in_tree[v]:
            continue
        in_tree[v] = True
        mst_adj[u].append(v)
        mst_adj[v].append(u)
        for w in range(n):
            if not in_tree[w]:
                heapq.heappush(edges, (matrix[v, w], v, w))

    # 2. Odd-degree vertices
    odd = [i for i in range(n) if len(mst_adj[i]) % 2 == 1]
    # Number of odd vertices is always even

    # 3. Minimum-weight perfect matching (greedy approximation)
    matching: List[Tuple[int, int]] = []
    if odd:
        # Greedy: sort pairs by distance
        pairs = []
        for idx, i in enumerate(odd):
            for j in odd[idx + 1:]:
                pairs.append((matrix[i, j], i, j))
        pairs.sort()
        matched: Set[int] = set()
        for d, i, j in pairs:
            if i not in matched and j not in matched:
                matching.append((i, j))
                matched.add(i)
                matched.add(j)

    # 4. Build Eulerian multigraph
    euler_adj: List[List[int]] = [list(adj) for adj in mst_adj]
    for i, j in matching:
        euler_adj[i].append(j)
        euler_adj[j].append(i)

    # 5. Find Eulerian circuit (Hierholzer's algorithm)
    euler_circuit: List[int] = []
    stack = [0]
    # Work with a mutable copy of adjacency and remove edges as used
    adj_copy = [list(lst) for lst in euler_adj]
    while stack:
        v = stack[-1]
        if adj_copy[v]:
            w = adj_copy[v].pop()
            # Remove reverse edge
            adj_copy[w].remove(v)
            stack.append(w)
        else:
            euler_circuit.append(stack.pop())
    euler_circuit.reverse()

    # 6. Shortcut
    seen: Set[int] = set()
    order: List[int] = []
    for c in euler_circuit:
        if c not in seen:
            seen.add(c)
            order.append(c)
    cost = instance.tour_length(order)
    return Tour(order, cost)