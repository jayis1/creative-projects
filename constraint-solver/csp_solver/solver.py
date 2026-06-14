"""
High-level solver interface combining AC-3 preprocessing and backtracking.

Provides a clean API: create a CSP, call solve(), get a SolveResult.
Also supports finding all solutions and comparing different strategies.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .csp import CSP, Assignment, Constraint
from .backtrack import BacktrackingSolver, SolverStats
from .ac3 import ac3


@dataclass
class SolveResult:
    """Result of solving a CSP.

    Attributes:
        assignment: The satisfying assignment (None if unsolvable).
        is_satisfiable: Whether a solution was found.
        stats: Solver statistics (from the backtracking solver).
        method: Description of the solving method used.
    """

    assignment: Optional[Assignment] = None
    is_satisfiable: Optional[bool] = None
    stats: Optional[SolverStats] = None
    method: str = ""

    def __bool__(self) -> bool:
        """Truth value: True if satisfiable."""
        return self.is_satisfiable is True


class CSPSolver:
    """High-level CSP solver with configurable strategies.

    The solver pipeline:
    1. Optionally run full AC-3 for preprocessing
    2. Run backtracking search with selected heuristics
    3. Return a SolveResult with assignment and statistics

    Args:
        use_mrv: Use Minimum Remaining Values heuristic.
        use_degree: Use degree heuristic as tiebreaker.
        use_lcv: Use Least Constraining Value heuristic.
        use_forward_check: Enable forward checking.
        use_mac: Enable MAC (Maintaining Arc Consistency).
        preprocess_ac3: Run full AC-3 before starting search.
        timeout: Maximum solve time in seconds.
    """

    def __init__(
        self,
        use_mrv: bool = True,
        use_degree: bool = True,
        use_lcv: bool = True,
        use_forward_check: bool = False,
        use_mac: bool = True,
        preprocess_ac3: bool = True,
        timeout: Optional[float] = None,
    ) -> None:
        self.use_mrv = use_mrv
        self.use_degree = use_degree
        self.use_lcv = use_lcv
        self.use_forward_check = use_forward_check
        self.use_mac = use_mac
        self.preprocess_ac3 = preprocess_ac3
        self.timeout = timeout

    def solve(self, csp: CSP) -> SolveResult:
        """Solve the CSP.

        Makes a deep copy so the original CSP is not mutated.
        Returns a SolveResult with the assignment (if found) and metadata.
        """
        # Make a copy so we don't mutate the original CSP
        csp_copy = copy.deepcopy(csp)

        # Preprocessing
        if self.preprocess_ac3:
            consistent = ac3(csp_copy)
            if not consistent:
                return SolveResult(
                    assignment=None,
                    is_satisfiable=False,
                    method="AC-3 preprocessing detected inconsistency",
                )

        # Solve with backtracking
        bt = BacktrackingSolver(
            use_mrv=self.use_mrv,
            use_degree=self.use_degree,
            use_lcv=self.use_lcv,
            use_forward_check=self.use_forward_check,
            use_mac=self.use_mac,
            timeout=self.timeout,
        )
        result = bt.solve(csp_copy)

        method_str = self._method_string()

        if result is not None:
            return SolveResult(
                assignment=result,
                is_satisfiable=True,
                stats=bt.stats,
                method=method_str,
            )
        else:
            # Could be unsatisfiable or timed out
            stats = bt.stats
            timed_out = (
                self.timeout is not None
                and stats is not None
                and stats.elapsed >= self.timeout * 0.9
            )
            return SolveResult(
                assignment=None,
                is_satisfiable=False if not timed_out else None,
                stats=stats,
                method=method_str,
            )

    def solve_all(self, csp: CSP, max_solutions: int = 10) -> List[Assignment]:
        """Find multiple solutions to a CSP.

        Uses iterative solving with solution blocking. After each solution
        is found, a constraint is added to prevent finding the same
        solution again, and search continues.

        Args:
            csp: The CSP to solve.
            max_solutions: Maximum number of solutions to find.

        Returns:
            List of satisfying assignments.
        """
        solutions: List[Assignment] = []

        for _ in range(max_solutions):
            csp_copy = copy.deepcopy(csp)
            if self.preprocess_ac3:
                if not ac3(csp_copy):
                    break

            bt = BacktrackingSolver(
                use_mrv=self.use_mrv,
                use_degree=self.use_degree,
                use_lcv=self.use_lcv,
                use_forward_check=self.use_forward_check,
                use_mac=self.use_mac,
                timeout=self.timeout,
            )
            result = bt.solve(csp_copy)
            if result is None:
                break

            solutions.append(result)

            # Add constraint to block this solution
            var_names = sorted(result.keys())
            values = tuple(result[v] for v in var_names)

            def make_blocker(names, vals):
                def blocker(assignment):
                    return not all(
                        assignment.get(n) == v for n, v in zip(names, vals)
                    )
                return blocker

            csp.add_constraint(
                Constraint(
                    list(csp.variables.keys()),
                    make_blocker(var_names, values),
                )
            )

        return solutions

    def _method_string(self) -> str:
        """Build a description string for the solving method."""
        method_parts = []
        if self.preprocess_ac3:
            method_parts.append("AC-3")
        if self.use_mac:
            method_parts.append("MAC")
        elif self.use_forward_check:
            method_parts.append("FC")
        else:
            method_parts.append("BT")
        if self.use_mrv:
            method_parts.append("MRV")
        if self.use_degree:
            method_parts.append("DEG")
        if self.use_lcv:
            method_parts.append("LCV")
        return "+".join(method_parts)


def compare_strategies(csp: CSP, timeout: Optional[float] = 30.0) -> List[Dict]:
    """Compare different solving strategies on a CSP.

    Tests multiple combinations of heuristics and reports timing
    and statistics for each.

    Args:
        csp: The CSP to solve.
        timeout: Maximum time per strategy.

    Returns:
        List of dicts with strategy name, time, assignments, and backtracks.
    """
    strategies = [
        {"name": "BT (no heuristics)", "use_mrv": False, "use_degree": False,
         "use_lcv": False, "use_forward_check": False, "use_mac": False,
         "preprocess_ac3": False},
        {"name": "BT+MRV", "use_mrv": True, "use_degree": False,
         "use_lcv": False, "use_forward_check": False, "use_mac": False,
         "preprocess_ac3": False},
        {"name": "BT+MRV+LCV", "use_mrv": True, "use_degree": True,
         "use_lcv": True, "use_forward_check": False, "use_mac": False,
         "preprocess_ac3": False},
        {"name": "FC+MRV+LCV", "use_mrv": True, "use_degree": True,
         "use_lcv": True, "use_forward_check": True, "use_mac": False,
         "preprocess_ac3": True},
        {"name": "MAC+MRV+LCV (full)", "use_mrv": True, "use_degree": True,
         "use_lcv": True, "use_forward_check": False, "use_mac": True,
         "preprocess_ac3": True},
    ]

    results = []
    for strat in strategies:
        name = strat.pop("name")
        solver = CSPSolver(**strat, timeout=timeout)
        result = solver.solve(csp)
        entry = {
            "strategy": name,
            "satisfiable": result.is_satisfiable,
            "method": result.method,
        }
        if result.stats:
            entry["time"] = round(result.stats.elapsed, 4),
            entry["assignments"] = result.stats.assignments_tried,
            entry["backtracks"] = result.stats.backtracks,
        else:
            entry["time"] = None
            entry["assignments"] = None
            entry["backtracks"] = None
        results.append(entry)

    return results