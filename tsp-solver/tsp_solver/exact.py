"""Exact TSP algorithms: Held-Karp dynamic programming and Branch & Bound."""

from __future__ import annotations

import itertools
import math
from typing import List, Optional

from .instance import TSPInstance
from .tour import Tour


def held_karp(instance: TSPInstance) -> Tour:
    """Solve TSP exactly via the Held-Karp dynamic programming algorithm.

    Complexity: O(n² 2ⁿ) time, O(n 2ⁿ) space. Only feasible for n ≤ ~20.

    Returns the optimal tour as a :class:`Tour`.
    """
    n = instance.n
    if n > 22:
        raise ValueError(f"Held-Karp is infeasible for n={n} (>22). Use a heuristic.")

    matrix = instance.matrix

    # dp[mask][j] = minimum cost path starting at 0, visiting all cities in
    # mask, ending at j.
    size = 1 << n
    INF = math.inf
    dp = [[INF] * n for _ in range(size)]
    parent = [[-1] * n for _ in range(size)]
    dp[1][0] = 0.0  # start at city 0, mask = {0}

    for mask in range(1, size):
        if not (mask & 1):
            continue  # city 0 must be in the set
        for j in range(n):
            if not (mask & (1 << j)):
                continue
            if dp[mask][j] == INF:
                continue
            # try extending to k
            for k in range(n):
                if mask & (1 << k):
                    continue
                new_mask = mask | (1 << k)
                new_cost = dp[mask][j] + matrix[j, k]
                if new_cost < dp[new_mask][k]:
                    dp[new_mask][k] = new_cost
                    parent[new_mask][k] = j

    # Close the tour: add edge from last city back to 0
    full = size - 1
    best_cost = INF
    best_last = -1
    for j in range(1, n):
        if dp[full][j] + matrix[j, 0] < best_cost:
            best_cost = dp[full][j] + matrix[j, 0]
            best_last = j

    # Reconstruct
    order: List[int] = []
    mask = full
    j = best_last
    while j != -1:
        order.append(j)
        prev = parent[mask][j]
        mask ^= (1 << j)
        j = prev
    order.reverse()
    # Ensure starts at 0
    if order[0] != 0:
        order = [0] + [c for c in order if c != 0]
    return Tour(order, best_cost)


def branch_and_bound(instance: TSPInstance) -> Tour:
    """Solve TSP exactly via branch-and-bound with a reduced-cost lower bound.

    Uses the 1-tree lower bound (MST + two cheapest edges from one vertex)
    and depth-first search. Feasible for n ≤ ~15-18 depending on the instance.
    """
    n = instance.n
    if n > 20:
        raise ValueError(f"Branch & bound infeasible for n={n} (>20).")
    matrix = instance.matrix

    # Initial upper bound via nearest neighbor
    upper = _nn_upper_bound(instance)

    # BUG FIX: Initialize best_order with the NN tour so that if the NN tour
    # is already optimal, B&B returns it instead of an empty list.
    # Previously, if no tour strictly improved on the upper bound (because
    # NN was already optimal), best_order would remain empty and the fallback
    # list(range(n)) would be returned, which is almost certainly suboptimal.
    best_order: List[int] = []
    best_cost = [upper]

    # Try to get the actual NN tour to use as initial best_order
    from .heuristics import nearest_neighbor
    nn_tour = nearest_neighbor(instance)
    if nn_tour.length <= upper:
        best_cost[0] = nn_tour.length
        best_order = list(nn_tour.order)

    # DFS with pruning
    visited = [False] * n
    visited[0] = True
    path = [0]

    def _lower_bound(cur_path: List[int]) -> float:
        """Compute a lower bound for completing the current partial tour.

        The bound is: (cost so far) + (minimum edge from current city to any
        unvisited city) + (minimum spanning tree of unvisited cities) +
        (minimum edge from any unvisited city back to city 0).

        This is a valid lower bound because any completion must include:
        - An edge from the current city to some unvisited city
        - A path through all unvisited cities (≥ MST cost)
        - An edge from some unvisited city back to the start
        """
        cur = cur_path[-1]
        unvisited = [j for j in range(n) if not visited[j]]
        if not unvisited:
            # All visited — just close the tour
            return sum(matrix[a, b] for a, b in zip(cur_path, cur_path[1:])) + matrix[cur, 0]

        # Cost of edges already traversed
        path_cost = sum(matrix[a, b] for a, b in zip(cur_path, cur_path[1:]))

        # Min edge from current to unvisited
        min_to_unvisited = min(matrix[cur, j] for j in unvisited)

        # Min edge from unvisited back to start (city 0)
        min_to_start = min(matrix[j, 0] for j in unvisited)

        # MST of unvisited cities (Prim's algorithm)
        if len(unvisited) <= 1:
            mst_cost = 0.0
        else:
            mst_cost = _mst_cost(matrix, unvisited)

        return path_cost + min_to_unvisited + mst_cost + min_to_start

    def _dfs(cur: int, cost: float, depth: int) -> None:
        nonlocal best_order
        if cost >= best_cost[0]:
            return
        if depth == n:
            total = cost + matrix[cur, 0]
            if total < best_cost[0]:
                best_cost[0] = total
                best_order = list(path)
            return
        lb = _lower_bound(path)
        if lb >= best_cost[0]:
            return
        # Visit unvisited cities in order of increasing distance
        candidates = sorted(
            ((matrix[cur, j], j) for j in range(n) if not visited[j]),
        )
        for dist, j in candidates:
            visited[j] = True
            path.append(j)
            _dfs(j, cost + dist, depth + 1)
            path.pop()
            visited[j] = False

    _dfs(0, 0.0, 1)
    if not best_order:
        # Fallback
        best_order = list(range(n))
        best_cost[0] = instance.tour_length(best_order)
    return Tour(best_order, best_cost[0])


def _mst_cost(matrix, vertices: List[int]) -> float:
    """Compute MST cost of the subgraph induced by *vertices* using Prim's."""
    if len(vertices) <= 1:
        return 0.0
    in_tree = {vertices[0]}
    total = 0.0
    while len(in_tree) < len(vertices):
        best_d = math.inf
        best_v = -1
        for u in in_tree:
            for v in vertices:
                if v not in in_tree and matrix[u, v] < best_d:
                    best_d = matrix[u, v]
                    best_v = v
        if best_v == -1:
            break
        in_tree.add(best_v)
        total += best_d
    return total


def _nn_upper_bound(instance: TSPInstance) -> float:
    """Compute an upper bound via nearest neighbor heuristic."""
    n = instance.n
    visited = [False] * n
    visited[0] = True
    cur = 0
    cost = 0.0
    for _ in range(n - 1):
        best_j = -1
        best_d = math.inf
        for j in range(n):
            if not visited[j] and instance.matrix[cur, j] < best_d:
                best_d = instance.matrix[cur, j]
                best_j = j
        visited[best_j] = True
        cost += best_d
        cur = best_j
    cost += instance.matrix[cur, 0]
    return cost