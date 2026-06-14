"""
High-level solver interface combining AC-3 preprocessing and backtracking.

Provides a clean API: create a CSP, call solve(), get a SolveResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .csp import CSP, Assignment, Constraint
from .backtrack import BacktrackingSolver
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
    stats: Optional[object] = None
    method: str = ""


class CSPSolver:
    """High-level CSP solver.

    Configurable with various heuristics and strategies.

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

        Returns a SolveResult with the assignment (if found) and metadata.
        """
        # Make a copy so we don't mutate the original CSP
        import copy

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
        method_str = "+".join(method_parts)

        if result is not None:
            return SolveResult(
                assignment=result,
                is_satisfiable=True,
                stats=bt.stats,
                method=method_str,
            )
        else:
            # Could be unsatisfiable or timed out
            return SolveResult(
                assignment=None,
                is_satisfiable=False,
                stats=bt.stats,
                method=method_str,
            )

    def solve_all(self, csp: CSP, max_solutions: int = 10) -> List[Assignment]:
        """Find multiple solutions to a CSP.

        Uses iterative solving with solution blocking.
        """
        solutions: List[Assignment] = []
        import copy

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
                    return not all(assignment.get(n) == v for n, v in zip(names, vals))
                return blocker

            csp.add_constraint(
                Constraint(
                    list(csp.variables.keys()),
                    make_blocker(var_names, values),
                )
            )

        return solutions