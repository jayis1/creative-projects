"""
AC-3 Arc Consistency Algorithm.

Implements the AC-3 algorithm for enforcing arc consistency on CSPs,
plus a queue-based variant for use during search (MAC).
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from .csp import CSP, Assignment, Domain


def revise(
    csp: CSP,
    var_i: str,
    var_j: str,
) -> int:
    """Revise the domain of var_i given constraints with var_j.

    Removes values from var_i's domain that have no supporting value
    in var_j's domain that satisfies all binary constraints between them.

    Returns:
        Number of values removed from var_i's domain.
    """
    constraints = csp.get_binary_constraints(var_i, var_j)
    if not constraints:
        return 0

    revised_count = 0
    domain_i = csp.get_domain(var_i)
    domain_j = csp.get_domain(var_j)

    # Collect values to remove (can't modify set during iteration)
    to_remove = []
    for xi in domain_i:
        # Check if there exists any xj in domain_j such that ALL
        # binary constraints between var_i and var_j are satisfied
        supported = False
        for xj in domain_j:
            all_ok = True
            for constraint in constraints:
                if constraint.pair_check is not None:
                    # Use optimized pair check
                    # Determine ordering: scope might be (i,j) or (j,i)
                    if constraint.scope[0] == var_i:
                        if not constraint.pair_check(xi, xj):
                            all_ok = False
                            break
                    else:
                        if not constraint.pair_check(xj, xi):
                            all_ok = False
                            break
                else:
                    # Fall back to full constraint check
                    test: Assignment = {var_i: xi, var_j: xj}
                    if not constraint.satisfied(test):
                        all_ok = False
                        break
            if all_ok:
                supported = True
                break
        if not supported:
            to_remove.append(xi)

    for val in to_remove:
        domain_i.discard(val)
        revised_count += 1

    return revised_count


def ac3(csp: CSP) -> bool:
    """Run AC-3 to enforce arc consistency on the entire CSP.

    Returns:
        True if arc consistency was achieved (no domain emptied),
        False if a domain wipeout occurred (CSP is unsolvable).
    """
    # Initialize queue with all arcs (both directions for each edge)
    queue: deque[Tuple[str, str]] = deque()
    for var_name in csp.variables:
        for neighbor in csp.get_neighbors(var_name):
            queue.append((var_name, neighbor))

    while queue:
        var_i, var_j = queue.popleft()
        removed = revise(csp, var_i, var_j)
        if removed > 0:
            if not csp.get_domain(var_i):
                # Domain wipeout — CSP is inconsistent
                return False
            # Re-queue arcs from var_i's neighbors (except var_j)
            for neighbor in csp.get_neighbors(var_i):
                if neighbor != var_j:
                    queue.append((neighbor, var_i))

    return True


def ac3_queue(
    csp: CSP,
    queue: List[Tuple[str, str]],
) -> bool:
    """Run AC-3 starting from a specific set of arcs.

    Used for MAC (Maintaining Arc Consistency) during search:
    after making an assignment, queue only the arcs affected
    by that assignment.

    Args:
        csp: The CSP to enforce consistency on.
        queue: Initial list of (var_i, var_j) arcs to process.

    Returns:
        True if arc consistency was achieved, False on wipeout.
    """
    arc_queue: deque[Tuple[str, str]] = deque(queue)

    while arc_queue:
        var_i, var_j = arc_queue.popleft()
        removed = revise(csp, var_i, var_j)
        if removed > 0:
            if not csp.get_domain(var_i):
                return False
            for neighbor in csp.get_neighbors(var_i):
                if neighbor != var_j:
                    arc_queue.append((neighbor, var_i))

    return True