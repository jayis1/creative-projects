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
        for i in range(n - 1):
            a = order[i]
            b = order[i + 1]
            for j in range(i + 2, n - 1):
                c = order[j]
                d = order[j + 1]
                delta = (matrix[a, c] + matrix[b, d]) - (matrix[a, b] + matrix[c, d])
                if delta < -1e-12:
                    # Reverse segment [i+1 .. j]
                    order[i + 1 : j + 1] = order[i + 1 : j + 1][::-1]
                    improved = True
        # also try the wrap-around edges
        a = order[-1]
        b = order[0]
        for j in range(1, n - 2):
            c = order[j]
            d = order[j + 1]
            delta = (matrix[a, c] + matrix[b, d]) - (matrix[a, b] + matrix[c, d])
            if delta < -1e-12:
                order[j + 1 :] = order[j + 1 :][::-1]
                # rotate so 0 stays at start
                idx0 = order.index(order[0])
                order = order[idx0:] + order[:idx0]
                improved = True

    cost = instance.tour_length(order)
    return Tour(order, cost)


def three_opt(instance: TSPInstance, tour: Optional[Tour] = None, max_iter: int = 5000) -> Tour:
    """3-opt local search: try all 7 possible reconnections of 3 broken edges.

    This is much more expensive than 2-opt (O(n³) per pass) but finds better
    local optima.
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
            for j in range(i + 2, n - 1):
                for k in range(j + 2, n):
                    best_delta = 0.0
                    best_case = -1
                    a, b = order[i], order[i + 1]
                    c, d = order[j], order[j + 1]
                    e, f = order[k], order[(k + 1) % n]
                    original = matrix[a, b] + matrix[c, d] + matrix[e, f]
                    # Case 1: swap (a,b)&(c,d) -> (a,c)&(b,d), keep (e,f)
                    new1 = matrix[a, c] + matrix[b, d] + matrix[e, f]
                    # Case 2: swap (c,d)&(e,f) -> (c,e)&(d,f), keep (a,b)
                    new2 = matrix[a, b] + matrix[c, e] + matrix[d, f]
                    # Case 3: swap (a,b)&(e,f) -> (a,e)&(b,f), keep (c,d)
                    new3 = matrix[a, e] + matrix[b, f] + matrix[c, d]
                    # Case 4: reverse segment (i+1..j) and (j+1..k)
                    new4 = matrix[a, d] + matrix[c, f] + matrix[e, b]
                    # Case 5: reverse (i+1..j) only with 3-opt reconnection
                    new5 = matrix[a, c] + matrix[b, e] + matrix[d, f]
                    # Case 6: reverse (j+1..k) only
                    new6 = matrix[a, e] + matrix[d, b] + matrix[c, f]
                    # Case 7: swap both segments
                    new7 = matrix[a, d] + matrix[e, b] + matrix[c, f]
                    for case_idx, new_d in enumerate(
                        [new1, new2, new3, new4, new5, new6, new7], start=1
                    ):
                        delta = new_d - original
                        if delta < best_delta - 1e-12:
                            best_delta = delta
                            best_case = case_idx
                    if best_case == -1:
                        continue
                    # Apply
                    seg1 = order[i + 1 : j + 1]
                    seg2 = order[j + 1 : k + 1]
                    if best_case == 1:
                        order[i + 1 : k + 1] = seg1[::-1] + seg2
                    elif best_case == 2:
                        order[i + 1 : k + 1] = seg1 + seg2[::-1]
                    elif best_case == 3:
                        order[i + 1 : k + 1] = seg2 + seg1
                    elif best_case == 4:
                        order[i + 1 : k + 1] = seg1[::-1] + seg2[::-1]
                    elif best_case == 5:
                        order[i + 1 : k + 1] = seg1[::-1] + seg2[::-1]
                        # Actually case 5: (a,c)(b,e)(d,f)
                        order[i + 1 : k + 1] = seg2 + seg1[::-1]
                    elif best_case == 6:
                        order[i + 1 : k + 1] = seg1 + seg2[::-1]
                        order[i + 1 : k + 1] = seg2[::-1] + seg1
                    elif best_case == 7:
                        order[i + 1 : k + 1] = seg2[::-1] + seg1[::-1]
                    improved = True

    cost = instance.tour_length(order)
    return Tour(order, cost)


def or_opt(instance: TSPInstance, tour: Optional[Tour] = None, max_iter: int = 10000) -> Tour:
    """Or-opt: move segments of length 1, 2, or 3 to a better position."""
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
            for i in range(n):
                if i + seg_len > n:
                    continue
                a_prev = order[(i - 1) % n]
                a = order[i]
                b = order[i + seg_len - 1]
                b_next = order[(i + seg_len) % n]
                removed_cost = matrix[a_prev, a] + matrix[b, b_next] - matrix[a_prev, b_next]
                seg = order[i : i + seg_len]
                # Try inserting at each other position
                for j in range(n):
                    if j == i or j == i - 1:
                        continue
                    if j < i:
                        # Need to be careful about index shifts; skip for simplicity
                        # Actually we can handle it: insert before j
                        pass
                    c = order[(j) % n]
                    d = order[(j + 1) % n]
                    if c == a or d == a:
                        continue
                    insert_cost = (
                        matrix[c, a] + matrix[b, d] - matrix[c, d]
                    )
                    delta = insert_cost + removed_cost
                    if delta < -1e-12:
                        # Perform the move
                        new_order = order[:i] + order[i + seg_len:]
                        # Adjust j index after removal
                        if j > i:
                            insert_at = j - seg_len + 1
                        else:
                            insert_at = j + 1
                        new_order = new_order[:insert_at] + seg + new_order[insert_at:]
                        order = new_order
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break

    cost = instance.tour_length(order)
    return Tour(order, cost)