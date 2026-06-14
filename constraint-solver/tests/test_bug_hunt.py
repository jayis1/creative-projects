"""
Bug hunt tests for the constraint solver.
Tests that verify bugs exist before fixing and prove they're fixed after.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from csp_solver.csp import CSP, Variable, Constraint
from csp_solver.ac3 import ac3, ac3_queue, revise, domain_reduction
from csp_solver.backtrack import BacktrackingSolver
from csp_solver.solver import CSPSolver, compare_strategies
from csp_solver.problems import n_queens_csp


class TestBugSolveAllMutatesOriginalCSP:
    """Bug: solve_all adds blocking constraints to the original CSP,
    mutating it. Subsequent calls produce incorrect results."""

    def test_solve_all_does_not_mutate_original(self):
        """After solve_all, the original CSP should have the same
        number of constraints as before."""
        csp = n_queens_csp(4)
        orig_constraint_count = len(csp.constraints)
        solver = CSPSolver(use_mac=True)
        solutions = solver.solve_all(csp, max_solutions=5)
        # Verify solutions found
        assert len(solutions) == 2
        # BUG: This currently fails - CSP is mutated
        assert len(csp.constraints) == orig_constraint_count, (
            f"CSP was mutated: had {orig_constraint_count} constraints, "
            f"now has {len(csp.constraints)}"
        )

    def test_solve_all_twice_same_csp(self):
        """Calling solve_all twice on the same CSP should return
        the same results."""
        csp = n_queens_csp(4)
        solver = CSPSolver(use_mac=True)
        solutions1 = solver.solve_all(csp, max_solutions=10)
        solutions2 = solver.solve_all(csp, max_solutions=10)
        # Both calls should find the same number of solutions
        assert len(solutions1) == len(solutions2), (
            f"First call found {len(solutions1)}, second found {len(solutions2)}"
        )


class TestBugCompareStrategiesMutation:
    """Bug: compare_strategies uses dict.pop('name') which destroys
    the strategy dicts' 'name' key, making them unusable after."""

    def test_compare_strategies_returns_valid_results(self):
        """compare_strategies should return proper results with all fields."""
        csp = n_queens_csp(6)
        results = compare_strategies(csp, timeout=10)
        assert len(results) == 5
        for r in results:
            assert "strategy" in r
            assert "satisfiable" in r
            assert "method" in r
            # 'time' should be present (not None for satisfiable problems)
            if r["satisfiable"]:
                assert r["time"] is not None
                assert r["assignments"] is not None


class TestBugEmptyDomainDetection:
    """Bug: AC-3 doesn't detect empty domains that exist before AC-3 runs.
    An empty domain means the CSP is unsatisfiable, but ac3() returns True."""

    def test_preexisting_empty_domain_is_unsatisfiable(self):
        """If a variable has an empty domain, the CSP is unsatisfiable.
        ac3() should detect this or the solver should handle it."""
        csp = CSP()
        csp.add_variable(Variable("X", domain=set()))  # Empty domain!
        csp.add_variable(Variable("Y", domain={1}))
        # ac3() with no constraints returns True, but empty domain means
        # the CSP is unsatisfiable
        result = ac3(csp)
        # Currently returns True - this is a correctness issue
        # After fix, the solver should detect this
        solver = CSPSolver()
        solve_result = solver.solve(csp)
        assert solve_result.is_satisfiable is False, (
            "CSP with empty domain should be unsatisfiable"
        )


class TestBugUnaryConstraintNeighbors:
    """Unary constraints (arity 1) don't add neighbors. This means
    they won't be processed by AC-3 but should work in backtracking."""

    def test_unary_constraint_solving(self):
        """A CSP with only unary constraints should still be solvable."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3, 4, 5}))
        # X must be even
        csp.add_constraint(Constraint(
            ("X",),
            lambda a: a["X"] % 2 == 0,
        ))
        solver = CSPSolver(use_mac=False, preprocess_ac3=False)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["X"] % 2 == 0

    def test_unary_constraint_with_binary(self):
        """Unary + binary constraints together."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3, 4, 5}))
        csp.add_variable(Variable("Y", domain={1, 2, 3, 4, 5}))
        # X must be even
        csp.add_constraint(Constraint(
            ("X",),
            lambda a: a["X"] % 2 == 0,
        ))
        # X != Y
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["X"] % 2 == 0
        assert result.assignment["X"] != result.assignment["Y"]


class TestBugDomainReductionEdgeCase:
    """Test domain_reduction with edge cases."""

    def test_all_singletons_constraint(self):
        """When all variables in a constraint are singletons,
        domain_reduction shouldn't try to reduce anything."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={2}))
        csp.add_variable(Variable("Y", domain={3}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] + a["Y"] == 5,
        ))
        removed = domain_reduction(csp)
        # Both already singletons - nothing to remove
        assert removed == 0

    def test_domain_reduction_with_inconsistent_singletons(self):
        """If all singletons violate the constraint, domain_reduction
        should detect this (by reducing a domain to empty)."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1}))
        csp.add_variable(Variable("Y", domain={1, 2, 3}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        removed = domain_reduction(csp)
        assert removed >= 1  # Should remove Y=1
        assert 1 not in csp.get_domain("Y")


class TestBugLCVConsistency:
    """Test that LCV constraining_count handles all constraint types correctly."""

    def test_lcv_with_multiple_constraints(self):
        """LCV should correctly count constraints when a variable
        has multiple binary constraints with the same neighbor."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3}))
        csp.add_variable(Variable("Y", domain={1, 2, 3}))
        # Two constraints between X and Y
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: abs(a["X"] - a["Y"]) != 1,
        ))
        solver = BacktrackingSolver(use_lcv=True, use_mrv=True)
        result = solver.solve(csp)
        assert result is not None
        # Verify both constraints hold
        assert result["X"] != result["Y"]
        assert abs(result["X"] - result["Y"]) != 1


class TestBugOriginalCSPPreserved:
    """Verify that solving doesn't mutate the original CSP's domains."""

    def test_domains_preserved_after_solve(self):
        """After solving, original CSP domains should be unchanged."""
        csp = n_queens_csp(5)
        orig_domains = {name: set(var.domain) for name, var in csp.variables.items()}
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        for name in csp.variables:
            assert csp.get_domain(name) == orig_domains[name], (
                f"Domain of {name} was mutated"
            )


class TestBugMACWithPreFilledCells:
    """Test that MAC handles variables with singleton (pre-filled) domains correctly."""

    def test_sudoku_prefilled_preserved(self):
        """Pre-filled cells in Sudoku should retain their values."""
        grid = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ]
        from csp_solver.problems import sudoku_csp
        csp = sudoku_csp(grid)
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        # Verify pre-filled values are preserved
        for i in range(9):
            for j in range(9):
                if grid[i][j] != 0:
                    assert result.assignment[f"R{i}C{j}"] == grid[i][j]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])