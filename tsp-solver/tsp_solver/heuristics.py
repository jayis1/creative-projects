"""Construction heuristics for TSP."""

from __future__ import annotations

import math
from typing import List, Optional

from .instance import TSPInstance
from .tour import Tour


def nearest_neighbor(instance: TSPInstance, start: int = 0) -> Tour:
    """Nearest-neighbor construction: always go to the closest unvisited city."""
    n = instance.n
    if not (0 <= start < n):
        raise IndexError(f"start={start} out of range [0,{n}).")
    visited = [False] * n
    visited[start] = True
    order = [start]
    cur = start
    cost = 0.0
    for _ in range(n - 1):
        best_j = -1
        best_d = math.inf
        for j in range(n):
            if not visited[j] and instance.matrix[cur, j] < best_d:
                best_d = instance.matrix[cur, j]
                best_j = j
        visited[best_j] = True
        order.append(best_j)
        cost += best_d
        cur = best_j
    cost += instance.matrix[cur, start]
    return Tour(order, cost)


def nearest_neighbor_multistart(
    instance: TSPInstance,
    *,
    seed: Optional[int] = None,
    starts: Optional[int] = None,
) -> Tour:
    """Multi-start nearest neighbor: try every city as starting point, keep best.

    Parameters
    ----------
    instance : TSPInstance
    seed : int, optional
        If provided, randomly sample *starts* starting cities instead of
        trying all n.
    starts : int, optional
        Number of starting cities to try. If None, tries all n (or 10 if
        seed is given).
    """
    import random

    n = instance.n
    if starts is None:
        starts = 10 if seed is not None else n
    starts = min(starts, n)

    if seed is not None:
        rng = random.Random(seed)
        start_cities = rng.sample(range(n), starts)
    else:
        start_cities = list(range(starts))

    best_tour: Optional[Tour] = None
    for s in start_cities:
        t = nearest_neighbor(instance, start=s)
        if best_tour is None or t.length < best_tour.length:
            best_tour = t
    return best_tour  # type: ignore[return-value]


def nearest_insertion(instance: TSPInstance) -> Tour:
    """Nearest-insertion construction heuristic.

    Start with a 2-city subtour, then repeatedly insert the city nearest to
    the tour into its best position.
    """
    n = instance.n
    # Start with cities 0 and nearest to 0
    j = min(range(1, n), key=lambda k: instance.matrix[0, k])
    tour = [0, j]
    tour_set = {0, j}

    while len(tour) < n:
        # Find unvisited city nearest to any tour city
        best_city = -1
        best_dist = math.inf
        for c in range(n):
            if c in tour_set:
                continue
            d = min(instance.matrix[c, t] for t in tour)
            if d < best_dist:
                best_dist = d
                best_city = c
        # Insert at best position
        best_pos = 0
        best_delta = math.inf
        for i in range(len(tour)):
            a, b = tour[i], tour[(i + 1) % len(tour)]
            delta = (
                instance.matrix[a, best_city]
                + instance.matrix[best_city, b]
                - instance.matrix[a, b]
            )
            if delta < best_delta:
                best_delta = delta
                best_pos = i + 1
        tour.insert(best_pos, best_city)
        tour_set.add(best_city)

    cost = instance.tour_length(tour)
    return Tour(tour, cost)


def farthest_insertion(instance: TSPInstance) -> Tour:
    """Farthest-insertion: insert the city farthest from the tour."""
    n = instance.n
    j = max(range(1, n), key=lambda k: instance.matrix[0, k])
    tour = [0, j]
    tour_set = {0, j}

    while len(tour) < n:
        # Find unvisited city farthest from any tour city
        best_city = -1
        best_dist = -1
        for c in range(n):
            if c in tour_set:
                continue
            d = min(instance.matrix[c, t] for t in tour)
            if d > best_dist:
                best_dist = d
                best_city = c
        # Insert at best position (least cost increase)
        best_pos = 0
        best_delta = math.inf
        for i in range(len(tour)):
            a, b = tour[i], tour[(i + 1) % len(tour)]
            delta = (
                instance.matrix[a, best_city]
                + instance.matrix[best_city, b]
                - instance.matrix[a, b]
            )
            if delta < best_delta:
                best_delta = delta
                best_pos = i + 1
        tour.insert(best_pos, best_city)
        tour_set.add(best_city)

    cost = instance.tour_length(tour)
    return Tour(tour, cost)


def greedy(instance: TSPInstance) -> Tour:
    """Greedy edge-selection heuristic (also called the 'multi-fragment' heuristic).

    Sort all edges by weight and add the shortest edge that doesn't create a
    degree-3 vertex or a sub-cycle, until the tour is complete.
    """
    n = instance.n
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            edges.append((instance.matrix[i, j], i, j))
    edges.sort()

    # Union-find for cycle detection
    parent = list(range(n))
    rank_ = [0] * n
    degree = [0] * n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if rank_[ra] < rank_[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank_[ra] == rank_[rb]:
            rank_[ra] += 1
        return True

    adj: List[List[int]] = [[] for _ in range(n)]
    edges_used = 0
    for d, i, j in edges:
        if degree[i] >= 2 or degree[j] >= 2:
            continue
        # Don't close a sub-cycle unless it's the final edge
        if find(i) == find(j) and edges_used != n - 1:
            continue
        if not union(i, j):
            # This is the last edge closing the full tour
            if edges_used == n - 1:
                pass
            else:
                continue
        adj[i].append(j)
        adj[j].append(i)
        degree[i] += 1
        degree[j] += 1
        edges_used += 1
        if edges_used == n:
            break

    # Reconstruct tour from adjacency
    order = [0]
    prev = -1
    cur = 0
    for _ in range(n - 1):
        nxt = [v for v in adj[cur] if v != prev][0]
        order.append(nxt)
        prev, cur = cur, nxt
    cost = instance.tour_length(order)
    return Tour(order, cost)