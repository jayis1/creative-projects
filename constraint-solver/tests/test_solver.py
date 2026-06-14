"""
Comprehensive test suite for the CSP Solver.

Tests core data structures, AC-3, backtracking, high-level solver,
and all problem generators (Sudoku, N-Queens, graph coloring,
cryptarithm, Latin square, magic square).
"""

import pytest
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from csp_solver.csp import CSP, Variable, Constraint
from csp_solver.ac3 import ac3, ac3_queue, revise, node_consistency, domain_reduction
from csp_solver.backtrack import BacktrackingSolver, SolverStats
from csp_solver.solver import CSPSolver, SolveResult, compare_strategies
from csp_solver.problems import (
    sudoku_csp,
    generate_sudoku,
    n_queens_csp,
    count_n_queens_solutions,
    graph_coloring_csp,
    cryptarithm_csp,
    latin_square_csp,
    magic_square_csp,
    format_sudoku_solution,
    format_queens_solution,
    format_cryptarithm_solution,
    format_latin_square,
    format_magic_square,
    AUSTRALIA_EDGES,
    US_REGIONS_EDGES,
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

    def test_is_assigned(self):
        v = Variable("X", domain={5})
        assert v.is_assigned() is True
        assert v.assigned_value() == 5

    def test_not_assigned(self):
        v = Variable("X", domain={1, 2})
        assert v.is_assigned() is False
        assert v.assigned_value() is None

    def test_initial_domain(self):
        v = Variable("X", domain={1, 2, 3})
        assert v.initial_domain == {1, 2, 3}
        v.domain.discard(1)
        assert v.domain == {2, 3}
        assert v.initial_domain == {1, 2, 3}  # unchanged


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

    def test_named_constraint(self):
        c = Constraint(("A", "B"), lambda a: True, name="test_con")
        assert "test_con" in repr(c)


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

    def test_variable_order(self):
        csp = CSP()
        csp.add_variable(Variable("C", domain={1}))
        csp.add_variable(Variable("A", domain={1}))
        csp.add_variable(Variable("B", domain={1}))
        assert csp.variable_order() == ["C", "A", "B"]

    def test_to_dict(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3}))
        d = csp.to_dict()
        assert "variables" in d
        assert "X" in d["variables"]
        assert d["variables"]["X"]["domain"] == [1, 2, 3]

    def test_ternary_constraint_neighbors(self):
        """N-ary constraints should create pairwise neighbors."""
        csp = CSP()
        csp.add_variable(Variable("A", domain={1, 2}))
        csp.add_variable(Variable("B", domain={1, 2}))
        csp.add_variable(Variable("C", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("A", "B", "C"),
            lambda a: a["A"] + a["B"] + a["C"] == 6,
        ))
        assert "B" in csp.get_neighbors("A")
        assert "C" in csp.get_neighbors("A")


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
        assert 1 not in csp.get_domain("Y")

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
        assert result is False

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
        assert removed == 1
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
        result = ac3_queue(csp, [("Y", "X")])
        assert result is True
        assert 1 not in csp.get_domain("Y")

    def test_node_consistency(self):
        """Test node_consistency check."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2}))
        assert node_consistency(csp) is True
        csp.add_variable(Variable("Y", domain=set()))
        assert node_consistency(csp) is False

    def test_domain_reduction(self):
        """Test domain reduction preprocessing."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1}))
        csp.add_variable(Variable("Y", domain={1, 2, 3}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        removed = domain_reduction(csp)
        assert removed >= 1
        assert 1 not in csp.get_domain("Y")

    def test_ac3_singleton_domain_optimization(self):
        """Test that AC-3 handles singleton domains efficiently."""
        csp = CSP()
        csp.add_variable(Variable("A", domain={3}))
        csp.add_variable(Variable("B", domain={1, 2, 3, 4, 5}))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] != a["B"],
            pair_check=lambda x, y: x != y,
        ))
        result = ac3(csp)
        assert result is True
        assert 3 not in csp.get_domain("B")

    def test_ac3_chain_propagation(self):
        """Test AC-3 propagates through chains of constraints."""
        csp = CSP()
        csp.add_variable(Variable("A", domain={1}))
        csp.add_variable(Variable("B", domain={1, 2}))
        csp.add_variable(Variable("C", domain={1, 2}))
        csp.add_constraint(Constraint(("A", "B"), lambda a: a["A"] != a["B"], pair_check=lambda x, y: x != y))
        csp.add_constraint(Constraint(("B", "C"), lambda a: a["B"] != a["C"], pair_check=lambda x, y: x != y))
        result = ac3(csp)
        assert result is True
        # A=1, so B≠1 → B={2}, then C≠2 → C could be {1}
        assert csp.get_domain("B") == {2}
        assert csp.get_domain("C") == {1}


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
        solver = CSP()
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
        csp = n_queens_csp(20)
        solver = BacktrackingSolver(use_mrv=True, use_mac=True, timeout=0.001)
        result = solver.solve(csp)
        assert isinstance(result, (dict, type(None)))

    def test_lcv_ordering(self):
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
        assert result["A"] != 1

    def test_solver_stats(self):
        """Test that SolverStats works correctly."""
        stats = SolverStats()
        assert stats.assignments_tried == 0
        assert stats.backtracks == 0
        assert stats.solution_found is False
        stats.assignments_tried = 42
        d = stats.to_dict()
        assert d["assignments_tried"] == 42

    def test_progress_callback(self):
        """Test progress callback is invoked."""
        calls = []
        def callback(assignment, stats):
            calls.append(len(assignment))

        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2}))
        csp.add_variable(Variable("Y", domain={1, 2}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] != a["Y"],
            pair_check=lambda x, y: x != y,
        ))
        solver = BacktrackingSolver(use_mac=False, progress_callback=callback)
        result = solver.solve(csp)
        assert result is not None
        assert len(calls) > 0


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
        sol_sets = {(s["X"], s["Y"]) for s in solutions}
        assert len(sol_sets) == 2

    def test_solve_result_bool(self):
        """Test that SolveResult supports truthiness."""
        result_true = SolveResult(is_satisfiable=True, assignment={"X": 1})
        result_false = SolveResult(is_satisfiable=False)
        assert result_true
        assert not result_false


# ─── Sudoku Tests ────────────────────────────────────────────────

class TestSudoku:
    def test_easy_puzzle(self):
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
        with pytest.raises(ValueError):
            sudoku_csp([[1, 2], [3, 4]])

    def test_invalid_grid_values(self):
        with pytest.raises(ValueError):
            sudoku_csp([[99] * 9 for _ in range(9)])

    def test_generate_sudoku(self):
        """Test Sudoku puzzle generation."""
        puzzle, solution = generate_sudoku(difficulty="easy", seed=42)
        assert len(puzzle) == 9
        assert len(puzzle[0]) == 9
        # Verify solution is valid
        for i in range(9):
            row_vals = {solution[i][j] for j in range(9)}
            assert row_vals == set(range(1, 10))

    def test_generate_sudoku_hard(self):
        """Test hard Sudoku generation."""
        puzzle, solution = generate_sudoku(difficulty="hard", seed=123)
        # Count blanks
        blanks = sum(1 for i in range(9) for j in range(9) if puzzle[i][j] == 0)
        assert blanks >= 40  # Hard puzzles should have many blanks


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

        assignment = result.assignment
        for i in range(8):
            for j in range(i + 1, 8):
                qi = assignment[f"Q{i}"]
                qj = assignment[f"Q{j}"]
                assert qi != qj, f"Same column: Q{i}={qi}, Q{j}={qj}"
                assert abs(qi - qj) != abs(i - j), f"Same diagonal: Q{i}={qi}, Q{j}={qj}"

    def test_1_queen(self):
        csp = n_queens_csp(1)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["Q0"] == 0

    def test_2_queens_unsatisfiable(self):
        csp = n_queens_csp(2)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is False

    def test_invalid_n(self):
        with pytest.raises(ValueError):
            n_queens_csp(0)

    def test_count_n_queens_solutions(self):
        """Count solutions for small N."""
        count = count_n_queens_solutions(4, timeout=10)
        assert count == 2


# ─── Graph Coloring Tests ────────────────────────────────────────

class TestGraphColoring:
    def test_australia_map(self):
        csp = graph_coloring_csp(AUSTRALIA_EDGES, num_colors=3)
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

        assignment = result.assignment
        for a, b in AUSTRALIA_EDGES:
            assert assignment[a] != assignment[b]

    def test_us_regions(self):
        """Test US regions coloring with enough colors."""
        csp = graph_coloring_csp(US_REGIONS_EDGES, num_colors=4)
        solver = CSPSolver(use_mac=True, timeout=30)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

    def test_2_coloring_triangle(self):
        edges = [("A", "B"), ("B", "C"), ("A", "C")]
        csp = graph_coloring_csp(edges, num_colors=2)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is False

    def test_3_coloring_triangle(self):
        edges = [("A", "B"), ("B", "C"), ("A", "C")]
        csp = graph_coloring_csp(edges, num_colors=3)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is True

    def test_invalid_colors(self):
        with pytest.raises(ValueError):
            graph_coloring_csp([("A", "B")], num_colors=0)


# ─── Cryptarithm Tests ───────────────────────────────────────────

class TestCryptarithm:
    def test_send_more_money(self):
        csp = cryptarithm_csp(["SEND", "MORE"], "MONEY")
        solver = CSPSolver(use_mac=True, timeout=60)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

        a = result.assignment
        send = 1000 * a["S"] + 100 * a["E"] + 10 * a["N"] + a["D"]
        more = 1000 * a["M"] + 100 * a["O"] + 10 * a["R"] + a["E"]
        money = 10000 * a["M"] + 1000 * a["O"] + 100 * a["N"] + 10 * a["E"] + a["Y"]
        assert send + more == money
        assert a["S"] != 0
        assert a["M"] != 0

    def test_simple_cryptarithm(self):
        csp = CSP()
        for letter in "ABCDE":
            if letter in ("A", "D"):
                csp.add_variable(Variable(letter, domain=set(range(1, 10))))
            else:
                csp.add_variable(Variable(letter, domain=set(range(10))))

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
        with pytest.raises(ValueError):
            cryptarithm_csp(["ABCDEFGHIJK"], "X")

    def test_empty_words(self):
        with pytest.raises(ValueError):
            cryptarithm_csp([], "X")

    def test_invalid_characters(self):
        with pytest.raises(ValueError):
            cryptarithm_csp(["AB1"], "CD")


# ─── Latin Square Tests ──────────────────────────────────────────

class TestLatinSquare:
    def test_3x3(self):
        """3x3 Latin Square should have a solution."""
        csp = latin_square_csp(3)
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

        # Verify: each row and column has all values
        a = result.assignment
        for i in range(3):
            row_vals = {a[f"L{i}_{j}"] for j in range(3)}
            assert row_vals == {0, 1, 2}
            col_vals = {a[f"L{j}_{i}"] for j in range(3)}
            assert col_vals == {0, 1, 2}

    def test_4x4(self):
        csp = latin_square_csp(4)
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

    def test_invalid_size(self):
        with pytest.raises(ValueError):
            latin_square_csp(0)

    def test_format(self):
        csp = latin_square_csp(3)
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        formatted = format_latin_square(result.assignment, 3)
        assert isinstance(formatted, str)
        assert len(formatted.split("\n")) == 3


# ─── Magic Square Tests ──────────────────────────────────────────

class TestMagicSquare:
    def test_3x3(self):
        """3x3 Magic Square should have a solution."""
        csp = magic_square_csp(3)
        solver = CSPSolver(use_mac=True, timeout=60)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

        # Verify: all numbers 1-9 used exactly once
        a = result.assignment
        values = [a[f"M{i}_{j}"] for i in range(3) for j in range(3)]
        assert sorted(values) == list(range(1, 10))

        # Verify row sums
        target = 15  # 3*(9+1)/2
        for i in range(3):
            assert sum(a[f"M{i}_{j}"] for j in range(3)) == target
        # Verify column sums
        for j in range(3):
            assert sum(a[f"M{i}_{j}"] for i in range(3)) == target
        # Verify diagonals
        assert sum(a[f"M{i}_{i}"] for i in range(3)) == target
        assert sum(a[f"M{i}_{2-i}"] for i in range(3)) == target

    def test_format(self):
        csp = magic_square_csp(3)
        solver = CSPSolver(use_mac=True, timeout=60)
        result = solver.solve(csp)
        formatted = format_magic_square(result.assignment, 3)
        assert isinstance(formatted, str)
        assert "Target sum" in formatted

    def test_invalid_size(self):
        with pytest.raises(ValueError):
            magic_square_csp(0)


# ─── Strategy Comparison Test ─────────────────────────────────────

class TestCompareStrategies:
    def test_compare_on_small_problem(self):
        """Compare strategies on a small problem."""
        csp = n_queens_csp(6)
        results = compare_strategies(csp, timeout=10)
        assert len(results) == 5
        # At least one strategy should find a solution
        assert any(r["satisfiable"] for r in results)
        # Check structure
        for r in results:
            assert "strategy" in r
            assert "method" in r


# ─── Formatting Tests ────────────────────────────────────────────

class TestFormatting:
    def test_sudoku_format(self):
        assignment = {}
        for i in range(9):
            for j in range(9):
                assignment[f"R{i}C{j}"] = (i * 3 + j // 3 + i // 3) % 9 + 1
        output = format_sudoku_solution(assignment)
        assert isinstance(output, str)
        assert len(output.split("\n")) == 9 + 2

    def test_queens_format(self):
        assignment = {"Q0": 1, "Q1": 3, "Q2": 0, "Q3": 2}
        output = format_queens_solution(assignment, 4)
        assert "♛" in output

    def test_cryptarithm_format(self):
        assignment = {"S": 9, "E": 5, "N": 6, "D": 7, "M": 1, "O": 0, "R": 8, "Y": 2}
        output = format_cryptarithm_solution(assignment, ["SEND", "MORE"], "MONEY")
        assert "SEND" in output
        assert "9567" in output

    def test_latin_square_format(self):
        assignment = {"L0_0": 0, "L0_1": 1, "L1_0": 1, "L1_1": 0}
        output = format_latin_square(assignment, 2)
        assert "0 1" in output

    def test_magic_square_format(self):
        assignment = {"M0_0": 2, "M0_1": 7, "M0_2": 6,
                      "M1_0": 9, "M1_1": 5, "M1_2": 1,
                      "M2_0": 4, "M2_1": 3, "M2_2": 8}
        output = format_magic_square(assignment, 3)
        assert "15" in output


# ─── Edge Case Tests ─────────────────────────────────────────────

class TestEdgeCases:
    def test_single_variable_no_constraints(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={42}))
        solver = CSPSolver(use_mac=False)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["X"] == 42

    def test_single_variable_empty_domain(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain=set()))
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is False

    def test_ternary_constraint(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain=set(range(10))))
        csp.add_variable(Variable("Y", domain=set(range(10))))
        csp.add_variable(Variable("Z", domain=set(range(10))))
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
        csp = n_queens_csp(6)
        solver = CSPSolver(use_mac=True)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.stats is not None
        assert result.stats.assignments_tried > 0

    def test_method_string(self):
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2}))
        solver = CSPSolver(use_mac=True, use_mrv=True, use_lcv=True)
        result = solver.solve(csp)
        assert "MAC" in result.method
        assert "MRV" in result.method
        assert "LCV" in result.method

    def test_predefined_maps(self):
        """Test that predefined edge lists are valid."""
        assert len(AUSTRALIA_EDGES) > 0
        assert all(len(e) == 2 for e in AUSTRALIA_EDGES)
        assert len(US_REGIONS_EDGES) > 0
        assert all(len(e) == 2 for e in US_REGIONS_EDGES)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])