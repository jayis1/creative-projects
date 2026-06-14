"""
Backtracking CSP Solver with heuristics.

Implements backtracking search with:
- MRV (Minimum Remaining Values) heuristic
- Degree heuristic (tiebreaker for MRV)
- LCV (Least Constraining Value) heuristic
- Forward checking
- MAC (Maintaining Arc Consistency)
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Set, Tuple

from .csp import CSP, Assignment, Constraint
from .ac3 import ac3, ac3_queue


class SolverStats:
    """Track solver statistics during search."""

    __slots__ = (
        "assignments_tried",
        "backtracks",
        "constraint_checks",
        "start_time",
        "end_time",
    )

    def __init__(self) -> None:
        self.assignments_tried: int = 0
        self.backtracks: int = 0
        self.constraint_checks: int = 0
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    @property
    def elapsed(self) -> float:
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    def __repr__(self) -> str:
        return (
            f"Stats(assignments={self.assignments_tried}, "
            f"backtracks={self.backtracks}, "
            f"checks={self.constraint_checks}, "
            f"time={self.elapsed:.4f}s)"
        )


class BacktrackingSolver:
    """Backtracking search for CSPs with configurable heuristics.

    Args:
        use_mrv: Use Minimum Remaining Values heuristic for variable selection.
        use_degree: Use degree heuristic as tiebreaker for MRV.
        use_lcv: Use Least Constraining Value heuristic for value ordering.
        use_forward_check: Use forward checking after each assignment.
        use_mac: Use Maintaining Arc Consistency after each assignment.
            (MAC subsumes forward checking; if both are True, MAC is used.)
        timeout: Maximum seconds to spend on search. None = no limit.
    """

    def __init__(
        self,
        use_mrv: bool = True,
        use_degree: bool = True,
        use_lcv: bool = True,
        use_forward_check: bool = False,
        use_mac: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        self.use_mrv = use_mrv
        self.use_degree = use_degree
        self.use_lcv = use_lcv
        self.use_forward_check = use_forward_check
        self.use_mac = use_mac
        self.timeout = timeout
        self.stats = SolverStats()

    def solve(self, csp: CSP) -> Optional[Assignment]:
        """Solve the CSP and return a satisfying assignment, or None."""
        # Make a working copy of domains so we don't mutate the original
        original_domains = csp.copy_domains()
        self.stats = SolverStats()
        self.stats.start_time = time.time()

        try:
            # Initial constraint propagation
            if self.use_mac:
                if not ac3(csp):
                    return None
            elif self.use_forward_check:
                # Pre-process with AC-3 for better pruning
                ac3(csp)

            result = self._backtrack(csp, {})
            return result
        finally:
            self.stats.end_time = time.time()
            # Restore original domains
            csp.restore_domains(original_domains)

    def _backtrack(
        self,
        csp: CSP,
        assignment: Assignment,
    ) -> Optional[Assignment]:
        """Recursive backtracking search."""
        # Timeout check
        if self.timeout and time.time() - self.stats.start_time > self.timeout:
            return None

        # All variables assigned?
        if len(assignment) == len(csp.variables):
            return dict(assignment)

        # Select unassigned variable
        var = self._select_unassigned_variable(csp, assignment)

        # Order domain values
        for value in self._order_domain_values(csp, var, assignment):
            self.stats.assignments_tried += 1

            if csp.is_consistent(var, value, assignment):
                assignment[var] = value

                # Save domains before propagation
                saved_domains = csp.copy_domains()

                # Prune domains based on assignment
                if self.use_mac:
                    # MAC: enforce arc consistency
                    csp.variables[var].domain = {value}
                    # Queue arcs from neighbors of var to var
                    arcs = [(neighbor, var) for neighbor in csp.get_neighbors(var)]
                    consistent = ac3_queue(csp, arcs)
                elif self.use_forward_check:
                    # Forward checking: prune domains of unassigned neighbors
                    consistent = self._forward_check(csp, var, value, assignment)
                else:
                    consistent = True

                if consistent:
                    result = self._backtrack(csp, assignment)
                    if result is not None:
                        return result

                # Undo assignment and restore domains
                del assignment[var]
                csp.restore_domains(saved_domains)
                self.stats.backtracks += 1
            else:
                self.stats.constraint_checks += 1

        return None

    def _select_unassigned_variable(
        self, csp: CSP, assignment: Assignment
    ) -> str:
        """Select the next variable to assign using heuristics."""
        unassigned = [
            v for v in csp.variables if v not in assignment
        ]

        if not unassigned:
            raise ValueError("No unassigned variables left")

        if self.use_mrv:
            # Minimum Remaining Values: pick variable with smallest domain
            min_domain_size = min(
                len(csp.get_domain(v)) for v in unassigned
            )
            candidates = [
                v for v in unassigned
                if len(csp.get_domain(v)) == min_domain_size
            ]
            if self.use_degree and len(candidates) > 1:
                # Degree heuristic: pick variable involved in most constraints
                # with unassigned variables (tiebreaker)
                def degree(var: str) -> int:
                    return sum(
                        1 for n in csp.get_neighbors(var)
                        if n not in assignment
                    )
                return max(candidates, key=degree)
            return candidates[0]

        # Default: first unassigned variable
        return unassigned[0]

    def _order_domain_values(
        self, csp: CSP, var: str, assignment: Assignment
    ) -> List[int]:
        """Order domain values for the given variable."""
        domain = csp.get_domain(var)
        values = sorted(domain)  # deterministic order as baseline

        if self.use_lcv:
            # Least Constraining Value: prefer values that rule out
            # the fewest choices for neighbors
            def constraining_count(val: int) -> int:
                total = 0
                for neighbor in csp.get_neighbors(var):
                    if neighbor not in assignment:
                        for neighbor_val in csp.get_domain(neighbor):
                            test: Assignment = {var: val, neighbor: neighbor_val}
                            for constraint in csp.get_binary_constraints(var, neighbor):
                                if not constraint.satisfied(test):
                                    total += 1
                                    break
                return total

            values.sort(key=constraining_count)

        return values

    def _forward_check(
        self,
        csp: CSP,
        var: str,
        value: int,
        assignment: Assignment,
    ) -> bool:
        """Forward checking: prune domains of unassigned neighbors.

        After assigning var=value, remove inconsistent values from
        neighboring variables' domains.

        Returns:
            True if all domains are non-empty, False if wipeout occurred.
        """
        for neighbor in csp.get_neighbors(var):
            if neighbor in assignment:
                continue
            domain = csp.get_domain(neighbor)
            to_remove = set()
            for neighbor_val in domain:
                test: Assignment = {var: value, neighbor: neighbor_val}
                for constraint in csp.get_binary_constraints(var, neighbor):
                    if not constraint.satisfied(test):
                        to_remove.add(neighbor_val)
                        break
            domain -= to_remove
            if not domain:
                return False  # Wipeout
        return True