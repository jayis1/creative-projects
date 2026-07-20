"""Advanced TSP algorithms: Savings (Clarke-Wright), Lin-Kernighan, Iterated Local Search.

This module provides more advanced construction and improvement algorithms
that go beyond the basic heuristics and local search in the core modules.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

from .instance import TSPInstance
from .tour import Tour


# ---------------------------------------------------------------------------
# Clarke-Wright Savings Algorithm
# ---------------------------------------------------------------------------

def savings(instance: TSPInstance) -> Tour:
    """Clarke-Wright savings construction heuristic.

    Starts with each city as its own subtour (a loop), then merges subtours
    in order of decreasing *savings*:

        s(i, j) = d(depot, i) + d(depot, j) - d(i, j)

    where the "depot" is city 0.  This is one of the best-known constructive
    heuristics for the TSP/VRP and typically produces tours competitive with
    nearest insertion while running in O(n² log n).

    Parameters
    ----------
    instance : TSPInstance
        A symmetric TSP instance.

    Returns
    -------
    Tour
        The constructed tour.
    """
    n = instance.n
    matrix = instance.matrix

    if n == 2:
        return Tour([0, 1], instance.tour_length([0, 1]))

    # Compute savings for all pairs (i, j), i, j > 0, i != j
    savings_list: List[Tuple[float, int, int]] = []
    for i in range(1, n):
        for j in range(i + 1, n):
            s = matrix[0, i] + matrix[0, j] - matrix[i, j]
            savings_list.append((s, i, j))
    # Sort by descending savings
    savings_list.sort(key=lambda x: -x[0])

    # Track, for each city, which subtour it belongs to and its endpoints.
    # We represent each subtour as a list.  city2route maps city -> route list.
    # Each route is a list of cities starting and ending at depot-adjacent
    # endpoints (we don't include the depot itself in the list, but the route
    # conceptually is depot - ... - depot).
    # For TSP we start with each city in its own "route" of just that city,
    # conceptually 0-i-0.  When merging two routes, we join endpoints i and j.

    # route_of[city] = the route list containing city
    route_of: List[Optional[List[int]]] = [[i] for i in range(n)]
    # endpoints: for each route, (left_end, right_end) — initially each is i.
    # We'll track whether a city is at an endpoint.
    is_endpoint = [True] * n

    for s, i, j in savings_list:
        ri = route_of[i]
        rj = route_of[j]
        if ri is None or rj is None:
            continue
        if ri is rj:
            continue  # Already in the same route

        # Both must be endpoints (the savings merge is only valid for endpoints)
        if not is_endpoint[i] or not is_endpoint[j]:
            continue

        # Merge: join i and j.  The new route connects the two routes by linking
        # their endpoints i and j, dropping the depot links.
        # ri ends at i (or starts at i), rj ends at j.
        # Ensure i is the last element of ri and j is the first/last of rj.
        if ri[-1] != i:
            ri.reverse()
        if rj[0] != j:
            rj.reverse()
        # Now ri[-1] == i, rj[0] == j
        merged = ri + rj
        # Update tracking
        for c in merged:
            route_of[c] = merged
        # The new endpoints are ri[0] and rj[-1]
        # Mark old endpoints as non-endpoint
        is_endpoint[i] = False
        is_endpoint[j] = False
        is_endpoint[ri[0]] = True  # but ri[0] might equal i if route was length 1
        # Actually after merge, endpoints are merged[0] and merged[-1]
        # Reset endpoints for all members and set only the two ends
        is_endpoint[merged[0]] = True
        is_endpoint[merged[-1]] = True

    # Find the final single route (the one containing city 0... but we didn't
    # include 0). Actually we built routes for cities 1..n-1.  There should be
    # one big route; add depot 0 at front.
    final_route: Optional[List[int]] = route_of[1]
    # In edge cases, not all merged — collect remaining.
    if final_route is None:
        final_route = [1]
    seen = set(final_route)
    for c in range(1, n):
        if c not in seen:
            final_route.append(c)
            seen.add(c)

    order = [0] + final_route
    cost = instance.tour_length(order)
    return Tour(order, cost)


# ---------------------------------------------------------------------------
# Double-bridge perturbation (used by Iterated Local Search)
# ---------------------------------------------------------------------------

def double_bridge(order: Sequence[int], rng: random.Random) -> List[int]:
    """Apply a *double-bridge* kick to *order* and return the new permutation.

    The double-bridge is a 4-opt perturbation that cannot be undone by 2-opt,
    making it ideal for iterated local search.  It cuts the tour at 4 points
    and reassembles the segments in a different order.
    """
    n = len(order)
    if n < 8:
        # Fall back to a random reversal for very small tours
        result = list(order)
        a, b = sorted(rng.sample(range(n), 2))
        result[a:b+1] = result[a:b+1][::-1]
        return result
    # Choose 4 cut points
    cuts = sorted(rng.sample(range(1, n), 4))
    s1, s2, s3, s4 = cuts
    # Segments: [0:s1], [s1:s2], [s2:s3], [s3:s4], [s4:]
    # Reassemble as: seg0, seg3, seg2, seg1, seg4  (a classic double-bridge)
    seg_a = list(order[0:s1])
    seg_b = list(order[s1:s2])
    seg_c = list(order[s2:s3])
    seg_d = list(order[s3:s4])
    seg_e = list(order[s4:])
    return seg_a + seg_d + seg_c + seg_b + seg_e


# ---------------------------------------------------------------------------
# Iterated Local Search
# ---------------------------------------------------------------------------

def iterated_local_search(
    instance: TSPInstance,
    tour: Optional[Tour] = None,
    *,
    max_iter: int = 1000,
    max_no_improve: int = 200,
    seed: Optional[int] = None,
    local_search: str = "two_opt",
) -> Tour:
    """Iterated Local Search (ILS) with 2-opt local search and double-bridge kicks.

    ILS repeatedly perturbs the best-known solution (via a double-bridge
    kick) and applies local search to escape local optima.  It is among the
    best simple metaheuristics for the TSP.

    Parameters
    ----------
    instance : TSPInstance
    tour : Tour, optional
        Starting tour (default: nearest-neighbor).
    max_iter : int
        Maximum number of ILS iterations.
    max_no_improve : int
        Stop after this many iterations without improvement.
    seed : int, optional
        RNG seed.
    local_search : str
        Local search to use: ``"two_opt"``, ``"three_opt"``, or ``"or_opt"``.
    """
    from .heuristics import nearest_neighbor
    from .local_search import two_opt, three_opt, or_opt

    rng = random.Random(seed)
    if tour is None:
        tour = nearest_neighbor(instance, start=rng.randint(0, instance.n - 1))

    # Initial local search
    refiners = {"two_opt": two_opt, "three_opt": three_opt, "or_opt": or_opt}
    if local_search not in refiners:
        raise ValueError(f"Unknown local_search {local_search!r}")
    refine_fn = refiners[local_search]

    best = refine_fn(instance, tour)
    current = best
    no_improve = 0

    for _ in range(max_iter):
        if no_improve >= max_no_improve:
            break
        # Perturb
        kicked_order = double_bridge(current.order, rng)
        kicked_tour = Tour(kicked_order, instance.tour_length(kicked_order))
        # Local search
        candidate = refine_fn(instance, kicked_tour)
        if candidate.length < best.length - 1e-10:
            best = candidate
            current = candidate
            no_improve = 0
        else:
            # Accept if not too much worse (random walk acceptance)
            if candidate.length < current.length + 1e-10:
                current = candidate
            no_improve += 1

    return best


# ---------------------------------------------------------------------------
# Lin-Kernighan (simplified)
# ---------------------------------------------------------------------------

def lin_kernighan(
    instance: TSPInstance,
    tour: Optional[Tour] = None,
    *,
    max_iter: int = 5000,
    max_depth: int = 5,
    seed: Optional[int] = None,
) -> Tour:
    """A simplified Lin-Kernighan heuristic.

    The full LK algorithm is complex; this implementation captures its essence:
    a variable-depth sequential edge-exchange that builds a sequence of 2-opt-
    like moves, gaining at each step, and stops when no further gain is
    possible.  It achieves near-optimal results on many instances.

    Parameters
    ----------
    instance : TSPInstance
    tour : Tour, optional
        Starting tour (default: nearest-neighbor).
    max_iter : int
        Maximum outer iterations.
    max_depth : int
        Maximum depth of the sequential exchange.
    seed : int, optional
        RNG seed (for tie-breaking).
    """
    from .heuristics import nearest_neighbor

    rng = random.Random(seed)
    if tour is None:
        tour = nearest_neighbor(instance, start=rng.randint(0, instance.n - 1))

    order = list(tour.order)
    n = len(order)
    matrix = instance.matrix

    def _gain(from_city: int, to_city: int, next_city: int) -> float:
        """Gain from replacing edge (from_city, to_city) with (from_city, next_city)."""
        return matrix[from_city, to_city] - matrix[from_city, next_city]

    improved = True
    iters = 0
    while improved and iters < max_iter:
        improved = False
        iters += 1
        # Try every city as the starting point of the sequence
        start_list = list(range(n))
        rng.shuffle(start_list)
        for t1 in start_list:
            if improved:
                break
            # t1-t2 is the first edge to break
            t2_idx = (order.index(t1) + 1) % n
            t2 = order[t2_idx]
            # Try to find a better edge from t1
            for t3 in range(n):
                if t3 == t1 or t3 == t2:
                    continue
                g1 = _gain(t1, t2, t3)
                if g1 <= 1e-10:
                    continue
                # t3-t4 is the next edge to break (t4 is next after t3 in tour)
                t3_idx = order.index(t3)
                # t4 is the neighbour of t3 in the tour (the one we'd reconnect)
                t4 = order[(t3_idx + 1) % n]
                # Check if closing the tour here (t4 -> t2) is beneficial
                # This is a 2-opt move: reverse segment from t2 to t3
                g2 = matrix[t3, t4] - matrix[t4, t2]  # gain from second exchange
                total_gain = g1 + g2
                if total_gain > 1e-10:
                    # Perform the 2-opt: reverse segment between t2_idx and t3_idx
                    i = order.index(t1)
                    j = order.index(t3)
                    # Ensure i < j in the segment sense
                    lo, hi = min(i, j), max(i, j)
                    # Standard 2-opt reversal (edges are (t1,t2) and (t3,t4))
                    if (i + 1) % n != j and (j + 1) % n != i:
                        if i < j:
                            order[i + 1:j + 1] = order[i + 1:j + 1][::-1]
                        else:
                            order[j + 1:i + 1] = order[j + 1:i + 1][::-1]
                        improved = True
                        break
            if improved:
                break

    cost = instance.tour_length(order)
    return Tour(order, cost)