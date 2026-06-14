"""
Backtracking CSP Solver with heuristics.

Implements backtracking search with:
- MRV (Minimum Remaining Values) heuristic
- Degree heuristic (tiebreaker for MRV)
- LCV (Least Constraining Value) heuristic
- Forward checking
- MAC (Maintaining Arc Consistency)
- Constraint propagation during search
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from .csp import CSP, Assignment, Constraint
from .ac3 import ac3, ac3_queue


class SolverStats:
    """Track solver statistics during search.

    Collects metrics like assignments tried, backtracks,
    constraint checks, and timing information.
    """

    __slots__ = (
        "assignments_tried",
        "backtracks",
        "constraint_checks",
        "domain_prunes",
        "start_time",
        "end_time",
        "solution_found",
    )

    def __init__(self) -> None:
        self.assignments_tried: int = 0
        self.backtracks: int = 0
        self.constraint_checks: int = 0
        self.domain_prunes: int = 0
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.solution_found: bool = False

    @property
    def elapsed(self) -> float:
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    def __repr__(self) -> str:
        return (
            f"Stats(assignments={self.assignments_tried}, "
            f"backtracks={self.backtracks}, "
            f"checks={self.constraint_checks}, "
            f"prunes={self.domain_prunes}, "
            f"time={self.elapsed:.4f}s, "
            f"found={self.solution_found})"
        )

    def to_dict(self) -> Dict:
        """Convert stats to a dictionary for JSON serialization."""
        return {
            "assignments_tried": self.assignments_tried,
            "backtracks": self.backtracks,
            "constraint_checks": self.constraint_checks,
            "domain_prunes": self.domain_prunes,
            "elapsed_seconds": round(self.elapsed, 4),
            "solution_found": self.solution_found,
        }


# Type alias for the callback invoked on each step
ProgressCallback = Callable[[Assignment, SolverStats], None]


class BacktrackingSolver:
    """Backtracking search for CSPs with configurable heuristics.

    The solver supports multiple strategies that can be combined:

    - **MRV (Minimum Remaining Values)**: Selects the unassigned variable
      with the fewest legal values, causing earlier failures and more
      pruning.

    - **Degree Heuristic**: When MRV ties, picks the variable involved
      in the most constraints with unassigned variables.

    - **LCV (Least Constraining Value)**: Tries values that eliminate
      the fewest options for neighboring variables first.

    - **Forward Checking**: After assigning a value, removes inconsistent
      values from neighboring domains.

    - **MAC (Maintaining Arc Consistency)**: After assigning a value,
      runs AC-3 on affected arcs. This is stronger than forward checking
      because it propagates constraints transitively.

    Args:
        use_mrv: Use Minimum Remaining Values heuristic for variable selection.
        use_degree: Use degree heuristic as tiebreaker for MRV.
        use_lcv: Use Least Constraining Value heuristic for value ordering.
        use_forward_check: Use forward checking after each assignment.
        use_mac: Use Maintaining Arc Consistency after each assignment.
            (MAC subsumes forward checking; if both are True, MAC is used.)
        timeout: Maximum seconds to spend on search. None = no limit.
        progress_callback: Optional callback invoked after each assignment attempt.
    """

    def __init__(
        self,
        use_mrv: bool = True,
        use_degree: bool = True,
        use_lcv: bool = True,
        use_forward_check: bool = False,
        use_mac: bool = False,
        timeout: Optional[float] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        self.use_mrv = use_mrv
        self.use_degree = use_degree
        self.use_lcv = use_lcv
        self.use_forward_check = use_forward_check
        self.use_mac = use_mac
        self.timeout = timeout
        self.progress_callback = progress_callback
        self.stats = SolverStats()

    def solve(self, csp: CSP) -> Optional[Assignment]:
        """Solve the CSP and return a satisfying assignment, or None.

        Creates a deep copy of domains so the original CSP is not mutated.
        Runs initial constraint propagation if MAC is enabled.
        """
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
            self.stats.solution_found = result is not None
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
        """Recursive backtracking search.

        Selects an unassigned variable using heuristics, tries values
        in heuristic order, and propagates constraints after each
        assignment. Backtracks if a domain wipeout occurs.
        """
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

                # Invoke progress callback if provided
                if self.progress_callback:
                    self.progress_callback(dict(assignment), self.stats)

                # Save domains before propagation
                saved_domains = csp.copy_domains()

                # Prune domains based on assignment
                consistent = True
                if self.use_mac:
                    # MAC: enforce arc consistency from assigned variable
                    csp.variables[var].domain = {value}
                    arcs = [(neighbor, var) for neighbor in csp.get_neighbors(var)]
                    consistent = ac3_queue(csp, arcs)
                elif self.use_forward_check:
                    # Forward checking: prune domains of unassigned neighbors
                    consistent = self._forward_check(csp, var, value, assignment)

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
        """Select the next variable to assign using heuristics.

        Strategy:
        1. If MRV is enabled, pick the variable with the smallest domain.
        2. If degree heuristic is also enabled and there are ties,
           pick the variable with the most constraints on unassigned neighbors.
        3. Otherwise, pick the first unassigned variable in insertion order.
        """
        unassigned = [
            v for v in csp.variable_order() if v not in assignment
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

        # Default: first unassigned variable in insertion order
        return unassigned[0]

    def _order_domain_values(
        self, csp: CSP, var: str, assignment: Assignment
    ) -> List[int]:
        """Order domain values for the given variable.

        If LCV is enabled, values are sorted by how constraining they are
        (least constraining first). Otherwise, values are returned in
        sorted order for determinism.
        """
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
            if to_remove:
                domain -= to_remove
                self.stats.domain_prunes += len(to_remove)
            if not domain:
                return False  # Wipeout
        return True