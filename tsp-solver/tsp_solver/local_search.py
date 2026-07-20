"""Local search improvement heuristics for TSP."""

from __future__ import annotations

import random
from typing import List, Optional

from .instance import TSPInstance
from .tour import Tour


def two_opt(instance: TSPInstance, tour: Optional[Tour] = None, max_iter: int = 10000) -> Tour:
    """2-opt local search: reverse segments to eliminate crossing edges.

    Repeatedly find two edges (a,b) and (c,d) such that replacing them with
    (a,c) and (b,d) reduces total length, and perform the swap.

    Uses first-improvement: applies the first improving move found, then
    restarts the scan. Handles wrap-around edges via modular indexing.

    Parameters
    ----------
    instance : TSPInstance
    tour : Tour, optional
        Starting tour. If None, a nearest-neighbor tour is used.
    max_iter : int
        Maximum number of improvement iterations.
    """
    from .heuristics import nearest_neighbor

    if tour is None:
        tour = nearest_neighbor(instance)

    order = list(tour.order)
    n = len(order)
    matrix = instance.matrix
    improved = True
    iters = 0
    while improved and iters < max_iter:
        improved = False
        iters += 1
        # Iterate over all pairs of edges (i, i+1) and (j, j+1) where j > i.
        # Edge k is (order[k], order[(k+1) % n]). When j = n-1, the edge
        # (order[n-1], order[0]) is the wrap-around edge, handled naturally.
        for i in range(n):
            a = order[i]
            b = order[(i + 1) % n]
            for j in range(i + 2, n):
                # Skip adjacent edges (share a vertex)
                if (i + 1) % n == j:
                    continue
                c = order[j]
                d = order[(j + 1) % n]
                delta = (matrix[a, c] + matrix[b, d]) - (matrix[a, b] + matrix[c, d])
                if delta < -1e-12:
                    # Reverse the segment from (i+1) to j.
                    # Since i < j and j < n, (i+1) <= j, so this is a simple
                    # slice reversal with no wrapping.
                    order[(i + 1) % n : j + 1] = order[(i + 1) % n : j + 1][::-1]
                    improved = True
                    break
            if improved:
                break

    cost = instance.tour_length(order)
    return Tour(order, cost)


def three_opt(instance: TSPInstance, tour: Optional[Tour] = None, max_iter: int = 5000) -> Tour:
    """3-opt local search: try all 7 possible reconnections of 3 broken edges.

    This is much more expensive than 2-opt (O(n³) per pass) but finds better
    local optima. Uses first-improvement strategy.

    The 7 non-trivial 3-opt moves on edges (a,b), (c,d), (e,f) at positions
    i < j < k produce the following reconnections (where seg1 = order[i+1..j],
    seg2 = order[j+1..k]):

    1. a-c, b-d, e-f  → reverse seg1           (2-opt sub-case)
    2. a-b, c-e, d-f  → reverse seg2           (2-opt sub-case)
    3. a-c, d-f, e-b  → swap, seg2 then seg1^R
    4. a-d, c-f, e-b  → reverse both, swap
    5. a-e, d-b, c-f  → reverse seg2, swap
    6. a-d, b-e, c-f  → reverse seg2, seg1
    7. a-e, b-d, c-f  → reverse seg1, swap
    """
    from .heuristics import nearest_neighbor

    if tour is None:
        tour = nearest_neighbor(instance)

    order = list(tour.order)
    n = len(order)
    matrix = instance.matrix
    improved = True
    iters = 0
    while improved and iters < max_iter:
        improved = False
        iters += 1
        for i in range(n - 2):
            a, b = order[i], order[(i + 1) % n]
            for j in range(i + 2, n - 1):
                c, d = order[j], order[(j + 1) % n]
                for k in range(j + 2, n):
                    e, f = order[k], order[(k + 1) % n]
                    original = matrix[a, b] + matrix[c, d] + matrix[e, f]
                    seg1 = order[i + 1 : j + 1]  # cities b..c
                    seg2 = order[j + 1 : k + 1]  # cities d..e

                    # The 7 non-trivial 3-opt reconnections.
                    # Each tuple is (new_cost, replacement_for_seg1+seg2).
                    moves = [
                        # Case 1: reverse seg1 (2-opt on edge 1)
                        (matrix[a, c] + matrix[b, d] + matrix[e, f],
                         seg1[::-1] + seg2),
                        # Case 2: reverse seg2 (2-opt on edge 2)
                        (matrix[a, b] + matrix[c, e] + matrix[d, f],
                         seg1 + seg2[::-1]),
                        # Case 3: a-c, d-f, e-b → seg2 + seg1[::-1]
                        (matrix[a, c] + matrix[d, f] + matrix[e, b],
                         seg2 + seg1[::-1]),
                        # Case 4: a-d, c-f, e-b → seg2[::-1] + seg1[::-1]
                        (matrix[a, d] + matrix[c, f] + matrix[e, b],
                         seg2[::-1] + seg1[::-1]),
                        # Case 5: a-e, d-b, c-f → seg2[::-1] + seg1
                        (matrix[a, e] + matrix[d, b] + matrix[c, f],
                         seg2[::-1] + seg1),
                        # Case 6: a-d, b-e, c-f → seg2[::-1] + seg1
                        #  Wait — case 6 and 5 produce the same order but
                        #  different costs. Case 6: a→d, then d..e reversed
                        #  (seg2[::-1]), then e→b, then b..c (seg1), c→f.
                        #  So middle = seg2[::-1] + seg1, cost = a-d + e-b + c-f
                        (matrix[a, d] + matrix[b, e] + matrix[c, f],
                         seg2[::-1] + seg1),
                        # Case 7: a-e, b-d, c-f → seg1[::-1] + seg2
                        (matrix[a, e] + matrix[b, d] + matrix[c, f],
                         seg1[::-1] + seg2),
                    ]

                    best_delta = -1e-12
                    best_middle = None
                    for new_cost, middle in moves:
                        delta = new_cost - original
                        if delta < best_delta:
                            best_delta = delta
                            best_middle = middle

                    if best_middle is not None:
                        order[i + 1 : k + 1] = best_middle
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break

    cost = instance.tour_length(order)
    return Tour(order, cost)


def or_opt(instance: TSPInstance, tour: Optional[Tour] = None, max_iter: int = 10000) -> Tour:
    """Or-opt: move segments of length 1, 2, or 3 to a better position.

    For each segment of length *seg_len*, try removing it and reinserting it
    between every other pair of consecutive cities. If any reinsertion reduces
    the total tour length, apply the move immediately (first-improvement).
    """
    from .heuristics import nearest_neighbor

    if tour is None:
        tour = nearest_neighbor(instance)

    order = list(tour.order)
    n = len(order)
    matrix = instance.matrix
    improved = True
    iters = 0
    while improved and iters < max_iter:
        improved = False
        iters += 1
        for seg_len in (1, 2, 3):
            if seg_len > n - 1:
                continue
            for i in range(n):
                # Segment is order[i : i+seg_len]. We avoid wrap-around segments.
                if i + seg_len > n:
                    continue
                a_prev = order[(i - 1) % n]
                a = order[i]
                b = order[i + seg_len - 1]
                b_next = order[(i + seg_len) % n]
                # Cost change of removing segment: we remove edges (a_prev, a)
                # and (b, b_next), and add edge (a_prev, b_next) to close the gap.
                # The net cost change from this step is:
                #   add (a_prev, b_next) - remove (a_prev, a) - remove (b, b_next)
                #   = matrix[a_prev, b_next] - matrix[a_prev, a] - matrix[b, b_next]
                #   = -removed_cost  (where removed_cost is defined below)
                # BUG FIX: Previously the delta was computed as removed_cost + insert_cost,
                # but it should be -removed_cost + insert_cost. The removed_cost as
                # defined (matrix[a_prev,a] + matrix[b,b_next] - matrix[a_prev,b_next])
                # represents the cost of the edges being removed minus the new edge
                # being added. The savings from removal is -removed_cost (negated).
                removed_cost = matrix[a_prev, a] + matrix[b, b_next] - matrix[a_prev, b_next]
                seg = order[i : i + seg_len]
                seg_set = set(seg)
                # Try inserting between every pair (c, d) of consecutive cities.
                for j in range(n):
                    # Skip positions adjacent to or inside the removed segment.
                    if j == i or j == (i - 1) % n:
                        continue
                    c = order[j]
                    d = order[(j + 1) % n]
                    # Skip if c or d is inside the segment being moved
                    if c in seg_set or d in seg_set:
                        continue
                    # Cost of inserting segment between c and d:
                    # remove edge (c, d), add edges (c, a) and (b, d).
                    insert_cost = matrix[c, a] + matrix[b, d] - matrix[c, d]
                    # Total delta = savings from removal + cost of insertion.
                    # Savings from removal = -removed_cost (we add a_prev→b_next
                    # but remove a_prev→a and b→b_next).
                    delta = -removed_cost + insert_cost
                    if delta < -1e-12:
                        # Perform the move:
                        # 1. Remove the segment from the current order
                        new_order = order[:i] + order[i + seg_len:]
                        # 2. Find where j maps in new_order.
                        #    If j >= i+seg_len, it shifts left by seg_len.
                        #    If j < i, it stays the same.
                        if j >= i + seg_len:
                            insert_j = j - seg_len
                        else:
                            insert_j = j
                        # Insert segment after position insert_j (between
                        # new_order[insert_j] and new_order[insert_j+1]).
                        new_order = new_order[:insert_j + 1] + seg + new_order[insert_j + 1:]
                        order = new_order
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break

    cost = instance.tour_length(order)
    return Tour(order, cost)