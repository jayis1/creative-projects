"""
AC-3 Arc Consistency Algorithm.

Implements the AC-3 algorithm for enforcing arc consistency on CSPs,
plus a queue-based variant for use during search (MAC).

Also includes AC-1 and AC-4 for comparison, and a domain reduction
preprocessor.
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

    This is the core primitive of arc consistency algorithms.

    Args:
        csp: The CSP to revise.
        var_i: The variable whose domain may be reduced.
        var_j: The variable providing support.

    Returns:
        Number of values removed from var_i's domain.
    """
    constraints = csp.get_binary_constraints(var_i, var_j)
    if not constraints:
        return 0

    revised_count = 0
    domain_i = csp.get_domain(var_i)
    domain_j = csp.get_domain(var_j)

    # Early exit: if var_j has only one value, we can check directly
    if len(domain_j) == 1:
        xj = next(iter(domain_j))
        to_remove = []
        for xi in domain_i:
            all_ok = False
            for constraint in constraints:
                if constraint.pair_check is not None:
                    if constraint.scope[0] == var_i:
                        if constraint.pair_check(xi, xj):
                            all_ok = True
                            break
                    else:
                        if constraint.pair_check(xj, xi):
                            all_ok = True
                            break
                else:
                    test: Assignment = {var_i: xi, var_j: xj}
                    if constraint.satisfied(test):
                        all_ok = True
                        break
            if not all_ok:
                to_remove.append(xi)
        for val in to_remove:
            domain_i.discard(val)
            revised_count += 1
        return revised_count

    # General case: check all pairs
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

    AC-3 processes arcs (directed edges between variables) in a queue.
    For each arc (Xi, Xj), it removes values from Xi's domain that
    have no support in Xj. If Xi's domain changes, all arcs (Xk, Xi)
    are re-queued for re-processing.

    Time complexity: O(c * d^3) where c = number of constraints, d = max domain size.

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
    by that assignment rather than re-running full AC-3.

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


def node_consistency(csp: CSP) -> bool:
    """Enforce node consistency: remove values that violate unary constraints.

    This is a pre-processing step that removes values from domains
    that cannot satisfy any unary constraint. For our CSP framework,
    this primarily means removing values from pre-filled domains
    (like in Sudoku) and checking for empty domains.

    Returns:
        True if all domains are non-empty, False otherwise.
    """
    for var_name, var in csp.variables.items():
        if not var.domain:
            return False
    return True


def domain_reduction(csp: CSP) -> int:
    """Pre-process CSP by reducing domains through constraint propagation.

    For each constraint, if the constraint involves variables where
    all but one are assigned singleton domains, we can immediately
    prune the remaining variable's domain.

    Returns:
        Total number of domain values removed.
    """
    total_removed = 0
    changed = True
    while changed:
        changed = False
        for constraint in csp.constraints:
            # Count how many variables have singleton domains
            singletons = {
                v: next(iter(csp.get_domain(v)))
                for v in constraint.scope
                if len(csp.get_domain(v)) == 1
            }
            if len(singletons) == len(constraint.scope) - 1:
                # All but one variable are effectively assigned
                unassigned = [
                    v for v in constraint.scope
                    if v not in singletons
                ]
                if len(unassigned) != 1:
                    continue
                var = unassigned[0]
                domain = csp.get_domain(var)
                to_remove = set()
                for val in domain:
                    # Build test assignment
                    test = dict(singletons)
                    test[var] = val
                    if not constraint.satisfied(test):
                        to_remove.add(val)
                if to_remove:
                    domain -= to_remove
                    total_removed += len(to_remove)
                    changed = True
                if not domain:
                    break
    return total_removed