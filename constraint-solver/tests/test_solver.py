"""
Comprehensive test suite for the CSP Solver.
"""

import pytest
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from csp_solver.csp import CSP, Variable, Constraint
from csp_solver.ac3 import ac3, ac3_queue, revise
from csp_solver.backtrack import BacktrackingSolver
from csp_solver.solver import CSPSolver, SolveResult
from csp_solver.problems import (
    sudoku_csp,
    n_queens_csp,
    graph_coloring_csp,
    cryptarithm_csp,
    format_sudoku_solution,
    format_queens_solution,
    format_cryptarithm_solution,
)


# ─── CSP Data Structure Tests ────────────────────────────────────

class TestVariable:
    def test_creation(self):
        v = Variable("X", domain={1, 2, 3})
        assert v.name == "X"
        assert v.domain == {1, 2, 3}

    def test_empty_domain(self):
        v = Variable("Y")
        assert v.domain == set()

    def test_equality(self):
        v1 = Variable("X", domain={1, 2})
        v2 = Variable("X", domain={3, 4})
        assert v1 == v2  # same name

    def test_inequality(self):
        v1 = Variable("X", domain={1})
        v2 = Variable("Y", domain={1})
        assert v1 != v2


class TestConstraint:
    def test_binary(self):
        c = Constraint(("A", "B"), lambda a: a["A"] != a["B"])
        assert c.arity == 2
        assert c.is_binary()

    def test_ternary(self):
        c = Constraint(("A", "B", "C"), lambda a: True)
        assert c.arity == 3
        assert not c.is_binary()

    def test_duplicate_scope(self):
        with pytest.raises(ValueError):
            Constraint(("A", "A"), lambda a: True)


class TestCSP:
    def test_add_variable(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3}))
        assert "X" in csp.variables
        assert csp.get_domain("X") == {1, 2, 3}

    def test_add_duplicate_variable(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1}))
        with pytest.raises(ValueError):
            csp.add_variable(Variable("X", domain={2}))

    def test_add_constraint(self):
        csp = CSP()
        csp.add_variable(Variable("A", domain={1, 2}))
        csp.add_variable(Variable("B", domain={1, 2}))
        csp.add_constraint(Constraint(("A", "B"), lambda a: a["A"] != a["B"]))
        assert len(csp.constraints) == 1
        assert csp.get_neighbors("A") == {"B"}

    def test_unknown_variable_in_constraint(self):
        csp = CSP()
        csp.add_variable(Variable("A", domain={1}))
        with pytest.raises(ValueError):
            csp.add_constraint(Constraint(("A", "B"), lambda a: True))

    def test_is_consistent(self):
        csp = CSP()
        csp.add_variable(Variable("A", domain={1, 2}))
        csp.add_variable(Variable("B", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] != a["B"],
            pair_check=lambda x, y: x != y,
        ))
        assert csp.is_consistent("A", 1, {"B": 2})
        assert not csp.is_consistent("A", 1, {"B": 1})

    def test_copy_restore_domains(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3}))
        original = csp.copy_domains()
        csp.variables["X"].domain.discard(1)
        assert csp.get_domain("X") == {2, 3}
        csp.restore_domains(original)
        assert csp.get_domain("X") == {1, 2, 3}


# ─── AC-3 Tests ──────────────────────────────────────────────────

class TestAC3:
    def test_simple_arc_consistency(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3}))
        csp.add_variable(Variable("Y", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        result = ac3(csp)
        assert result is True
        # X and Y have overlapping domains {1,2} but must differ
        # AC-3 alone won't reduce further since each value has support

    def test_ac3_reduces_domain(self):
        """Test that AC-3 reduces domains when possible."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1}))
        csp.add_variable(Variable("Y", domain={1, 2, 3}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        result = ac3(csp)
        assert result is True
        assert 1 not in csp.get_domain("Y")  # Y=1 conflicts with X=1

    def test_ac3_detects_inconsistency(self):
        """AC-3 detects when a domain is wiped out."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1}))
        csp.add_variable(Variable("Y", domain={1}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        result = ac3(csp)
        assert result is False  # X=1, Y must differ → Y has no values → inconsistency

    def test_revise_removes_values(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3}))
        csp.add_variable(Variable("Y", domain={2}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        removed = revise(csp, "X", "Y")
        assert removed == 1  # X=2 removed (conflicts with Y=2)
        assert 2 not in csp.get_domain("X")

    def test_ac3_queue(self):
        """Test targeted AC-3 from a specific arc queue."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1}))
        csp.add_variable(Variable("Y", domain={1, 2, 3}))
        csp.add_variable(Variable("Z", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        csp.add_constraint(Constraint(
            ("Y", "Z"),
            lambda a: a["Y"] != a["Z"],
            pair_check=lambda x, y: x != y,
        ))
        # Queue only the X→Y arc
        result = ac3_queue(csp, [("Y", "X")])
        assert result is True
        assert 1 not in csp.get_domain("Y")


# ─── Backtracking Solver Tests ────────────────────────────────────

class TestBacktrackingSolver:
    def test_simple_csp(self):
        """Solve A != B, A + B = 3 with domains {1,2}."""
        csp = CSP()
        csp.add_variable(Variable("A", domain={1, 2}))
        csp.add_variable(Variable("B", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] != a["B"],
            pair_check=lambda x, y: x != y,
        ))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] + a["B"] == 3,
        ))
        solver = BacktrackingSolver()
        result = solver.solve(csp)
        assert result is not None
        assert result["A"] + result["B"] == 3
        assert result["A"] != result["B"]

    def test_unsatisfiable(self):
        """A CSP with no solution."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1}))
        csp.add_variable(Variable("Y", domain={1}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        solver = BacktrackingSolver()
        result = solver.solve(csp)
        assert result is None

    def test_with_mrv(self):
        """MRV heuristic should prefer the most constrained variable."""
        csp = CSP()
        csp.add_variable(Variable("A", domain={1, 2, 3}))
        csp.add_variable(Variable("B", domain={1}))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] != a["B"],
            pair_check=lambda x, y: x != y,
        ))
        solver = BacktrackingSolver(use_mrv=True, use_mac=False)
        result = solver.solve(csp)
        assert result is not None
        assert result["A"] != result["B"]

    def test_with_mac(self):
        """MAC should find solution and prune effectively."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3}))
        csp.add_variable(Variable("Y", domain={1, 2, 3}))
        csp.add_variable(Variable("Z", domain={1, 2, 3}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        csp.add_constraint(Constraint(
            ("Y", "Z"),
            lambda a: a["Y"] != a["Z"],
            pair_check=lambda x, y: x != y,
        ))
        csp.add_constraint(Constraint(
            ("X", "Z"),
            lambda a: a["X"] != a["Z"],
            pair_check=lambda x, y: x != y,
        ))
        solver = BacktrackingSolver(use_mrv=True, use_mac=True)
        result = solver.solve(csp)
        assert result is not None
        assert result["X"] != result["Y"]
        assert result["Y"] != result["Z"]
        assert result["X"] != result["Z"]

    def test_with_forward_check(self):
        """Forward checking should work."""
        csp = CSP()
        csp.add_variable(Variable("A", domain={1, 2}))
        csp.add_variable(Variable("B", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] != a["B"],
            pair_check=lambda x, y: x != y,
        ))
        solver = BacktrackingSolver(use_forward_check=True)
        result = solver.solve(csp)
        assert result is not None
        assert result["A"] != result["B"]

    def test_timeout(self):
        """Test that timeout mechanism works."""
        # Large N-Queens might take long
        csp = n_queens_csp(20)
        solver = BacktrackingSolver(use_mrv=True, use_mac=True, timeout=0.001)
        result = solver.solve(csp)
        # May or may not solve, but should not hang
        assert isinstance(result, (dict, type(None)))

    def test_lcv_ordering(self):
        """LCV should order values to be least constraining."""
        csp = CSP()
        csp.add_variable(Variable("A", domain={1, 2, 3}))
        csp.add_variable(Variable("B", domain={1}))
        csp.add_variable(Variable("C", domain={1}))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] != a["B"],
            pair_check=lambda x, y: x != y,
        ))
        csp.add_constraint(Constraint(
            ("A", "C"),
            lambda a: a["A"] != a["C"],
            pair_check=lambda x, y: x != y,
        ))
        solver = BacktrackingSolver(use_lcv=True)
        result = solver.solve(csp)
        assert result is not None
        assert result["A"] != 1  # A must differ from both B=1 and C=1


# ─── High-Level Solver Tests ────────────────────────────────────

class TestCSPSolver:
    def test_basic(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2}))
        csp.add_variable(Variable("Y", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment is not None
        assert result.assignment["X"] != result.assignment["Y"]

    def test_unsatisfiable(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1}))
        csp.add_variable(Variable("Y", domain={1}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is False

    def test_solve_all(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2}))
        csp.add_variable(Variable("Y", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        solver = CSPSolver(use_mac=False, preprocess_ac3=False)
        solutions = solver.solve_all(csp, max_solutions=10)
        assert len(solutions) == 2
        # Verify all solutions are different
        sol_sets = {(s["X"], s["Y"]) for s in solutions}
        assert len(sol_sets) == 2


# ─── Sudoku Tests ────────────────────────────────────────────────

class TestSudoku:
    def test_easy_puzzle(self):
        """Easy puzzle should solve quickly."""
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
        csp = sudoku_csp(grid)
        solver = CSPSolver(use_mac=True, timeout=30)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment is not None

        # Verify solution satisfies original given values
        for i in range(9):
            for j in range(9):
                if grid[i][j] != 0:
                    assert result.assignment[f"R{i}C{j}"] == grid[i][j]

    def test_solution_valid(self):
        """Verify solution produces a valid Sudoku grid."""
        grid = [
            [0, 0, 3, 0, 2, 0, 6, 0, 0],
            [9, 0, 0, 3, 0, 5, 0, 0, 1],
            [0, 0, 1, 8, 0, 6, 4, 0, 0],
            [0, 0, 8, 1, 0, 2, 9, 0, 0],
            [7, 0, 0, 0, 0, 0, 0, 0, 8],
            [0, 0, 6, 7, 0, 8, 2, 0, 0],
            [0, 0, 2, 6, 0, 9, 5, 0, 0],
            [8, 0, 0, 2, 0, 3, 0, 0, 9],
            [0, 0, 5, 0, 1, 0, 3, 0, 0],
        ]
        csp = sudoku_csp(grid)
        solver = CSPSolver(use_mac=True, timeout=30)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

        # Check rows have all digits 1-9
        for i in range(9):
            row_vals = {result.assignment[f"R{i}C{j}"] for j in range(9)}
            assert row_vals == set(range(1, 10)), f"Row {i} invalid"

        # Check columns
        for j in range(9):
            col_vals = {result.assignment[f"R{i}C{j}"] for i in range(9)}
            assert col_vals == set(range(1, 10)), f"Column {j} invalid"

    def test_invalid_grid(self):
        """Invalid grid size should raise error."""
        with pytest.raises(ValueError):
            sudoku_csp([[1, 2], [3, 4]])  # 2x2 instead of 9x9


# ─── N-Queens Tests ──────────────────────────────────────────────

class TestNQueens:
    def test_4_queens(self):
        """4-Queens should have 2 solutions."""
        csp = n_queens_csp(4)
        solver = CSPSolver(use_mac=True)
        solutions = solver.solve_all(csp, max_solutions=10)
        assert len(solutions) == 2

    def test_8_queens(self):
        """8-Queens should find a valid solution."""
        csp = n_queens_csp(8)
        solver = CSPSolver(use_mac=True, timeout=30)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

        # Verify no two queens attack each other
        assignment = result.assignment
        for i in range(8):
            for j in range(i + 1, 8):
                qi = assignment[f"Q{i}"]
                qj = assignment[f"Q{j}"]
                assert qi != qj, f"Same column: Q{i}={qi}, Q{j}={qj}"
                assert abs(qi - qj) != abs(i - j), f"Same diagonal: Q{i}={qi}, Q{j}={qj}"

    def test_1_queen(self):
        """1-Queen should have 1 solution."""
        csp = n_queens_csp(1)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["Q0"] == 0

    def test_2_queens_unsatisfiable(self):
        """2-Queens has no solution."""
        csp = n_queens_csp(2)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is False

    def test_invalid_n(self):
        """n < 1 should raise error."""
        with pytest.raises(ValueError):
            n_queens_csp(0)


# ─── Graph Coloring Tests ────────────────────────────────────────

class TestGraphColoring:
    def test_australia_map(self):
        """Australia map should be 3-colorable."""
        edges = [
            ("WA", "NT"), ("WA", "SA"), ("NT", "SA"),
            ("NT", "Q"), ("SA", "Q"), ("SA", "NSW"),
            ("SA", "V"), ("Q", "NSW"), ("NSW", "V"),
        ]
        csp = graph_coloring_csp(edges, num_colors=3)
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

        # Verify no adjacent nodes share a color
        assignment = result.assignment
        for a, b in edges:
            assert assignment[a] != assignment[b], f"{a} and {b} share color {assignment[a]}"

    def test_2_coloring_triangle(self):
        """Triangle is not 2-colorable."""
        edges = [("A", "B"), ("B", "C"), ("A", "C")]
        csp = graph_coloring_csp(edges, num_colors=2)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is False

    def test_3_coloring_triangle(self):
        """Triangle is 3-colorable."""
        edges = [("A", "B"), ("B", "C"), ("A", "C")]
        csp = graph_coloring_csp(edges, num_colors=3)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is True

    def test_invalid_colors(self):
        """0 colors should raise error."""
        with pytest.raises(ValueError):
            graph_coloring_csp([("A", "B")], num_colors=0)


# ─── Cryptarithm Tests ───────────────────────────────────────────

class TestCryptarithm:
    def test_send_more_money(self):
        """Classic SEND + MORE = MONEY puzzle."""
        csp = cryptarithm_csp(["SEND", "MORE"], "MONEY")
        solver = CSPSolver(use_mac=True, timeout=60)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

        # Verify the solution
        a = result.assignment
        send = 1000 * a["S"] + 100 * a["E"] + 10 * a["N"] + a["D"]
        more = 1000 * a["M"] + 100 * a["O"] + 10 * a["R"] + a["E"]
        money = 10000 * a["M"] + 1000 * a["O"] + 100 * a["N"] + 10 * a["E"] + a["Y"]
        assert send + more == money
        assert a["S"] != 0
        assert a["M"] != 0

    def test_simple_cryptarithm(self):
        """Simple AB + C = DE (2-digit result)."""
        # Let's try a simpler one: I + BB = ILL
        # Actually let's do: A + B = C with single digits
        # That's too simple. Let's do: AB + C = DE
        # This means 10*A + B + C = 10*D + E
        csp = CSP()
        for letter in "ABCDE":
            if letter in ("A", "D"):
                csp.add_variable(Variable(letter, domain=set(range(1, 10))))
            else:
                csp.add_variable(Variable(letter, domain=set(range(10))))

        # All different
        letters = ["A", "B", "C", "D", "E"]
        for i in range(len(letters)):
            for j in range(i + 1, len(letters)):
                csp.add_constraint(Constraint(
                    (letters[i], letters[j]),
                    lambda a, li=letters[i], lj=letters[j]: a[li] != a[lj],
                    pair_check=lambda x, y: x != y,
                ))

        def check(a):
            ab = 10 * a["A"] + a["B"]
            c = a["C"]
            de = 10 * a["D"] + a["E"]
            return ab + c == de

        csp.add_constraint(Constraint(letters, check))

        solver = CSPSolver(use_mac=True, timeout=30)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        a = result.assignment
        assert 10 * a["A"] + a["B"] + a["C"] == 10 * a["D"] + a["E"]

    def test_too_many_letters(self):
        """More than 10 unique letters should raise error."""
        with pytest.raises(ValueError):
            cryptarithm_csp(
                ["ABCDEFGHIJK"],  # 11 letters
                "X",
            )


# ─── Formatting Tests ────────────────────────────────────────────

class TestFormatting:
    def test_sudoku_format(self):
        assignment = {}
        for i in range(9):
            for j in range(9):
                assignment[f"R{i}C{j}"] = (i * 3 + j // 3 + i // 3) % 9 + 1
        output = format_sudoku_solution(assignment)
        assert isinstance(output, str)
        assert len(output.split("\n")) == 9 + 2  # 9 rows + 2 separator lines

    def test_queens_format(self):
        assignment = {"Q0": 1, "Q1": 3, "Q2": 0, "Q3": 2}
        output = format_queens_solution(assignment, 4)
        assert "♛" in output

    def test_cryptarithm_format(self):
        assignment = {"S": 9, "E": 5, "N": 6, "D": 7, "M": 1, "O": 0, "R": 8, "Y": 2}
        output = format_cryptarithm_solution(assignment, ["SEND", "MORE"], "MONEY")
        assert "SEND" in output
        assert "9567" in output  # SEND value


# ─── Edge Case Tests ─────────────────────────────────────────────

class TestEdgeCases:
    def test_single_variable_no_constraints(self):
        """Single variable with domain should solve to any value."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={42}))
        solver = CSPSolver(use_mac=False)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["X"] == 42

    def test_single_variable_empty_domain(self):
        """Variable with empty domain should be unsatisfiable."""
        csp = CSP()
        csp.add_variable(Variable("X", domain=set()))
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is False

    def test_ternary_constraint(self):
        """Test an n-ary (3-variable) constraint."""
        csp = CSP()
        csp.add_variable(Variable("X", domain=set(range(10))))
        csp.add_variable(Variable("Y", domain=set(range(10))))
        csp.add_variable(Variable("Z", domain=set(range(10))))

        # X + Y + Z == 10
        csp.add_constraint(Constraint(
            ("X", "Y", "Z"),
            lambda a: a["X"] + a["Y"] + a["Z"] == 10,
        ))

        solver = CSPSolver(use_mac=False, preprocess_ac3=False)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        a = result.assignment
        assert a["X"] + a["Y"] + a["Z"] == 10

    def test_large_domain(self):
        """Test with large domain (stress test for LCV)."""
        csp = CSP()
        csp.add_variable(Variable("A", domain=set(range(100))))
        csp.add_variable(Variable("B", domain=set(range(100))))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] + a["B"] == 99,
        ))
        solver = CSPSolver(use_mac=False, use_lcv=True, timeout=10)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["A"] + result.assignment["B"] == 99

    def test_solver_stats(self):
        """Verify solver tracks statistics."""
        csp = n_queens_csp(6)
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.stats is not None
        assert result.stats.assignments_tried > 0

    def test_method_string(self):
        """Verify method description is populated."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2}))
        solver = CSPSolver(use_mac=True, use_mrv=True, use_lcv=True)
        result = solver.solve(csp)
        assert "MAC" in result.method
        assert "MRV" in result.method
        assert "LCV" in result.method


if __name__ == "__main__":
    pytest.main([__file__, "-v"])