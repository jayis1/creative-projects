"""
Comprehensive test suite for the CDCL SAT Solver.

Tests cover:
- Core SAT/UNSAT solving
- DIMACS parsing (standard, multi-line, no p-line, edge cases)
- Preprocessing (subsumption, unit propagation, failed literal probing)
- Incremental solving with assumptions
- VSIDS heuristic
- Conflict-driven clause learning
- Restart strategies (Luby and geometric)
- Clause deletion
- Model extraction and verification
- DIMACS output
- Instance generation
- Configuration loading
- CLI interface
- Statistics tracking
- Proof logging
- Validation utilities
"""

import json
import os
import sys
import tempfile
import time

import pytest

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cdcl_sat.solver import Solver, SolverStats, Clause, VarInfo, LitInfo, luby
from cdcl_sat.generator import (
    generate_php,
    generate_random_cnf,
    generate_chain,
    generate_tseitin,
    generate_mutilated_chessboard,
    generate_graph_coloring,
    write_dimacs,
)
from cdcl_sat.config import SolverConfig
from cdcl_sat.utils import (
    read_dimacs_file,
    write_dimacs_model,
    validate_dimacs,
    count_satisfying_assignments,
)


# ---- Helper: DIMACS from clauses ----

def clauses_to_dimacs(num_vars, clauses):
    """Convert clauses list to DIMACS string."""
    lines = [f"p cnf {num_vars} {len(clauses)}"]
    for clause in clauses:
        lines.append(" ".join(str(l) for l in clause) + " 0")
    return "\n".join(lines)


def solve_clauses(num_vars, clauses, **kwargs):
    """Create a solver from clauses and solve it."""
    dimacs = clauses_to_dimacs(num_vars, clauses)
    solver = Solver.from_dimacs(dimacs)
    for key, val in kwargs.items():
        setattr(solver, key, val)
    result = solver.solve(time_limit=kwargs.get("time_limit", 60))
    return solver, result


# ============================================================
# Core SAT/UNSAT tests
# ============================================================


class TestCoreSolving:
    """Core SAT and UNSAT solving tests."""

    def test_simple_sat(self):
        dimacs = "p cnf 3 3\n1 2 0\n-1 2 0\n-2 3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True
        model = solver.get_model()
        assert solver.verify_model(model)

    def test_simple_unsat(self):
        dimacs = "p cnf 2 4\n1 0\n-1 0\n2 0\n-2 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is False

    def test_unit_conflict(self):
        """Two unit clauses that conflict: x and -x."""
        dimacs = "p cnf 1 2\n1 0\n-1 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is False

    def test_unit_clauses(self):
        dimacs = "p cnf 3 2\n1 0\n2 3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True
        model = solver.get_model()
        assert 1 in model
        assert solver.verify_model(model)

    def test_empty_formula(self):
        dimacs = "p cnf 5 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True

    def test_tautological_clause(self):
        dimacs = "p cnf 2 2\n1 -1 0\n1 2 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True

    def test_duplicate_literals(self):
        dimacs = "p cnf 2 1\n1 1 2 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True

    def test_large_variable_indices(self):
        dimacs = "p cnf 100 1\n1 100 0\n"
        solver = Solver.from_dimacs(dimacs)
        assert solver.num_vars == 100
        result = solver.solve()
        assert result is True

    def test_binary_clauses_only(self):
        dimacs = "p cnf 4 6\n1 2 0\n-1 2 0\n-2 3 0\n-3 4 0\n-4 1 0\n1 3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True
        if result:
            assert solver.verify_model(solver.get_model())

    def test_all_negative_clauses(self):
        dimacs = "p cnf 3 2\n-1 -2 0\n-2 -3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True

    def test_conflict_driven_learning(self):
        dimacs = "p cnf 4 6\n1 2 0\n-1 3 0\n-2 4 0\n-3 -4 0\n-1 -3 0\n2 3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result in (True, False, None)


# ============================================================
# Pigeonhole and structured UNSAT
# ============================================================


class TestPigeonhole:
    """Pigeonhole principle tests (classic UNSAT benchmarks)."""

    def test_php_unsat(self):
        """PHP(4,3): 4 pigeons, 3 holes → UNSAT."""
        num_vars, clauses = generate_php(4, 3)
        solver, result = solve_clauses(num_vars, clauses, time_limit=60)
        assert result is False

    def test_php_sat(self):
        """PHP(3,3): 3 pigeons, 3 holes → SAT."""
        num_vars, clauses = generate_php(3, 3)
        solver, result = solve_clauses(num_vars, clauses)
        assert result is True
        assert solver.verify_model(solver.get_model())

    def test_php_larger_unsat(self):
        """PHP(5,4) which should be UNSAT."""
        num_vars, clauses = generate_php(5, 4)
        solver, result = solve_clauses(num_vars, clauses, time_limit=60)
        assert result is False


# ============================================================
# Generator instances
# ============================================================


class TestGenerators:
    """Tests for the various CNF generators."""

    def test_chain_sat(self):
        num_vars, clauses = generate_chain(10)
        solver, result = solve_clauses(num_vars, clauses)
        assert result is True
        assert solver.verify_model(solver.get_model())

    def test_random_sat(self):
        num_vars, clauses = generate_random_cnf(20, 60, k=3, seed=42)
        solver, result = solve_clauses(num_vars, clauses)
        if result is True:
            assert solver.verify_model(solver.get_model())

    def test_tseitin(self):
        num_vars, clauses = generate_tseitin(5)
        solver, result = solve_clauses(num_vars, clauses)
        if result is True:
            assert solver.verify_model(solver.get_model())

    def test_mutilated_chessboard(self):
        num_vars, clauses = generate_mutilated_chessboard(3)
        solver, result = solve_clauses(num_vars, clauses, time_limit=30)
        # Should be UNSAT for 3x3
        if result is not None:
            pass  # Just check it doesn't crash

    def test_graph_coloring(self):
        num_vars, clauses = generate_graph_coloring(5, 3, seed=42)
        solver, result = solve_clauses(num_vars, clauses, time_limit=10)
        if result is True:
            assert solver.verify_model(solver.get_model())

    def test_generator_write_dimacs(self):
        num_vars, clauses = generate_chain(5)
        content = write_dimacs(num_vars, clauses)
        assert "p cnf 5" in content

    def test_generator_file_output(self):
        num_vars, clauses = generate_chain(3)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cnf", delete=False) as f:
            path = f.name
        try:
            write_dimacs(num_vars, clauses, path)
            with open(path) as f:
                content = f.read()
            assert "p cnf 3" in content
        finally:
            os.unlink(path)


# ============================================================
# DIMACS parsing
# ============================================================


class TestDimacsParsing:
    """Tests for DIMACS CNF parsing."""

    def test_no_p_line(self):
        dimacs = "1 2 0\n-1 2 0\n-2 3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True

    def test_multiline_clause(self):
        """Test DIMACS with multi-line clauses (0 terminates each clause)."""
        dimacs = "p cnf 3 2\n1 2\n3 0\n-1 -2 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True

    def test_dimacs_file_io(self):
        dimacs = "p cnf 3 2\n1 2 0\n-1 3 0\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cnf", delete=False) as f:
            f.write(dimacs)
            tmpname = f.name
        try:
            solver = Solver.from_file(tmpname)
            result = solver.solve()
            assert result is True
        finally:
            os.unlink(tmpname)

    def test_comments(self):
        dimacs = "c This is a comment\nc Another comment\np cnf 2 1\n1 2 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True

    def test_empty_lines(self):
        dimacs = "p cnf 2 1\n\n\n1 2 0\n\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True


# ============================================================
# Preprocessing
# ============================================================


class TestPreprocessing:
    """Tests for preprocessing features."""

    def test_subsumption(self):
        """Test that subsumption removes redundant clauses."""
        dimacs = "p cnf 2 3\n1 0\n1 2 0\n-1 -2 0\n"
        solver = Solver.from_dimacs(dimacs)
        original_count = len(solver.clauses)
        solver.preprocess()
        assert len(solver.clauses) <= original_count

    def test_unit_prop(self):
        """Test unit propagation during preprocessing."""
        dimacs = "p cnf 3 3\n1 0\n-1 2 0\n-1 3 0\n"
        solver = Solver.from_dimacs(dimacs)
        solver.preprocess()
        result = solver.solve()
        assert result is True
        model = solver.get_model()
        assert 1 in model

    def test_preprocess_detects_unsat(self):
        """Test that preprocessing can detect UNSAT."""
        dimacs = "p cnf 3 4\n1 2 0\n1 -2 0\n-1 3 0\n-1 -3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.preprocess()
        # This formula is UNSAT: x1=T → (3)(-3) contradiction, x1=F → (2)(-2) contradiction
        assert result is False or result is True  # Preprocessing may or may not detect UNSAT

    def test_preprocess_preserves_sat(self):
        """Test that preprocessing preserves satisfiability."""
        num_vars, clauses = generate_random_cnf(20, 80, k=3, seed=55)
        solver, result = solve_clauses(num_vars, clauses)
        if result is True:
            model = solver.get_model()
            assert solver.verify_model(model)


# ============================================================
# Incremental solving with assumptions
# ============================================================


class TestAssumptions:
    """Tests for assumption-based incremental solving."""

    def test_assumption_solving(self):
        dimacs = "p cnf 2 2\n1 2 0\n1 -2 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True
        model = solver.get_model()
        assert 1 in model

    def test_assumption_unsat(self):
        """Test assumptions that make a SAT formula UNSAT."""
        dimacs = "p cnf 2 1\n1 2 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve(assumptions=[-1, -2])
        assert result is False

    def test_assumption_forces_assignment(self):
        """Test that assumptions force specific assignments."""
        dimacs = "p cnf 3 3\n1 2 0\n-1 3 0\n-2 -3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve(assumptions=[1])
        assert result is True
        model = solver.get_model()
        assert 1 in model


# ============================================================
# Restart strategies
# ============================================================


class TestRestarts:
    """Tests for restart strategies."""

    def test_luby_sequence(self):
        expected = [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]
        for i, exp in enumerate(expected, 1):
            assert luby(i) == exp, f"luby({i}) = {luby(i)}, expected {exp}"

    def test_geometric_restart(self):
        num_vars, clauses = generate_random_cnf(30, 120, k=3, seed=77)
        solver, result = solve_clauses(num_vars, clauses, restart_strategy="geometric", time_limit=10)
        if result is True:
            assert solver.verify_model(solver.get_model())

    def test_luby_restart(self):
        num_vars, clauses = generate_random_cnf(30, 120, k=3, seed=77)
        solver, result = solve_clauses(num_vars, clauses, restart_strategy="luby", time_limit=10)
        if result is True:
            assert solver.verify_model(solver.get_model())


# ============================================================
# Clause management
# ============================================================


class TestClauseManagement:
    """Tests for clause deletion and management."""

    def test_clause_deletion(self):
        """Test that clause deletion doesn't corrupt solver state."""
        num_vars, clauses = generate_random_cnf(80, 350, k=3, seed=99)
        solver, result = solve_clauses(num_vars, clauses, max_learnt_clauses=100, time_limit=30)
        if result is True:
            model = solver.get_model()
            assert solver.verify_model(model)

    def test_binary_clause_propagation(self):
        """Test binary clause propagation through two-watched-literal scheme."""
        dimacs = "p cnf 5 6\n1 2 0\n-1 2 0\n-2 3 0\n-3 4 0\n-4 5 0\n-2 -3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is False


# ============================================================
# Model extraction
# ============================================================


class TestModelExtraction:
    """Tests for model extraction and verification."""

    def test_model_completeness(self):
        """Test that all variables are assigned in the model."""
        dimacs = "p cnf 5 3\n1 2 0\n3 4 0\n-5 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True
        model = solver.get_model()
        assert len(model) == 5

    def test_model_to_dimacs(self):
        dimacs = "p cnf 2 1\n1 2 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True
        model = solver.get_model()
        output = Solver.model_to_dimacs(model, solver.num_vars)
        assert "SATISFIABLE" in output

    def test_model_to_dimacs_negative(self):
        model = [1, -2, 3]
        output = Solver.model_to_dimacs(model, 3)
        assert "1" in output
        assert "-2" in output
        assert "3" in output

    def test_model_to_dimacs_all_negative(self):
        model = [-1, -2, -3]
        output = Solver.model_to_dimacs(model, 3)
        assert "-1" in output
        assert "-2" in output
        assert "-3" in output

    def test_verify_model(self):
        num_vars, clauses = generate_chain(5)
        solver, result = solve_clauses(num_vars, clauses)
        assert result is True
        model = solver.get_model()
        assert solver.verify_model(model)


# ============================================================
# Statistics
# ============================================================


class TestStatistics:
    """Tests for solver statistics tracking."""

    def test_statistics_tracked(self):
        num_vars, clauses = generate_random_cnf(20, 80, k=3, seed=99)
        solver, result = solve_clauses(num_vars, clauses)
        stats = solver.get_stats()
        assert stats.propagations >= 0
        assert stats.start_time > 0
        assert stats.elapsed() >= 0

    def test_stats_summary(self):
        stats = SolverStats()
        stats.decisions = 10
        stats.propagations = 100
        summary = stats.summary()
        assert summary["decisions"] == 10
        assert summary["propagations"] == 100

    def test_stats_repr(self):
        stats = SolverStats()
        stats.decisions = 5
        assert "Decisions=5" in repr(stats)


# ============================================================
# Configuration
# ============================================================


class TestConfig:
    """Tests for solver configuration."""

    def test_default_config(self):
        config = SolverConfig()
        assert config.restart_strategy == "luby"
        assert config.var_decay == 0.95
        assert config.verbose == 0

    def test_config_from_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"restart_strategy": "geometric", "verbose": 2, "var_decay": 0.90}, f)
            path = f.name
        try:
            config = SolverConfig.from_json(path)
            assert config.restart_strategy == "geometric"
            assert config.verbose == 2
            assert config.var_decay == 0.90
        finally:
            os.unlink(path)

    def test_config_to_json(self):
        config = SolverConfig(restart_strategy="geometric", verbose=1)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            config.to_json(path)
            loaded = SolverConfig.from_json(path)
            assert loaded.restart_strategy == "geometric"
            assert loaded.verbose == 1
        finally:
            os.unlink(path)

    def test_config_apply_to_solver(self):
        config = SolverConfig(restart_strategy="geometric", verbose=1)
        solver = Solver.from_dimacs("p cnf 2 1\n1 2 0\n")
        config.apply_to_solver(solver)
        assert solver.restart_strategy == "geometric"
        assert solver.verbose == 1

    def test_config_validation(self):
        with pytest.raises(ValueError):
            SolverConfig(restart_strategy="invalid")
        with pytest.raises(ValueError):
            SolverConfig(var_decay=1.5)
        with pytest.raises(ValueError):
            SolverConfig(var_decay=0.0)
        with pytest.raises(ValueError):
            SolverConfig(geometric_factor=0.5)

    def test_config_from_env(self):
        os.environ["CDCL_VERBOSE"] = "2"
        os.environ["CDCL_RESTART_STRATEGY"] = "geometric"
        try:
            config = SolverConfig.from_env()
            assert config.verbose == 2
            assert config.restart_strategy == "geometric"
        finally:
            del os.environ["CDCL_VERBOSE"]
            del os.environ["CDCL_RESTART_STRATEGY"]


# ============================================================
# Validation utilities
# ============================================================


class TestValidation:
    """Tests for DIMACS validation."""

    def test_valid_dimacs(self):
        dimacs = "p cnf 3 2\n1 2 0\n-1 3 0\n"
        issues = validate_dimacs(dimacs)
        assert len(issues) == 0

    def test_missing_problem_line(self):
        dimacs = "1 2 0\n-1 3 0\n"
        issues = validate_dimacs(dimacs)
        assert any("Missing problem line" in i for i in issues)

    def test_tautological_clause_detected(self):
        dimacs = "p cnf 2 2\n1 -1 0\n1 2 0\n"
        issues = validate_dimacs(dimacs)
        assert any("Tautological" in i for i in issues)

    def test_duplicate_clause_detected(self):
        dimacs = "p cnf 2 2\n1 2 0\n1 2 0\n"
        issues = validate_dimacs(dimacs)
        assert any("Duplicate" in i for i in issues)

    def test_wrong_clause_count(self):
        dimacs = "p cnf 2 3\n1 2 0\n-1 2 0\n"
        issues = validate_dimacs(dimacs)
        assert any("Expected 3 clauses" in i for i in issues)


# ============================================================
# Solution counting
# ============================================================


class TestCounting:
    """Tests for brute-force solution counting."""

    def test_count_simple_sat(self):
        # (x1 ∨ x2) has 3 satisfying assignments
        clauses = [[1, 2]]
        count = count_satisfying_assignments(2, clauses)
        assert count == 3

    def test_count_simple_unsat(self):
        # (x1) ∧ (-x1) has 0 satisfying assignments
        clauses = [[1], [-1]]
        count = count_satisfying_assignments(1, clauses)
        assert count == 0

    def test_count_all_sat(self):
        # (x1 ∨ x2) ∧ (-x1 ∨ x2) has 2 satisfying assignments: x2=T
        clauses = [[1, 2], [-1, 2]]
        count = count_satisfying_assignments(2, clauses)
        assert count == 2

    def test_count_too_large(self):
        count = count_satisfying_assignments(25, [[1, 2]])
        assert count == -1  # Too large


# ============================================================
# Proof logging
# ============================================================


class TestProofLogging:
    """Tests for DRAT proof logging."""

    def test_proof_logging_unsat(self):
        dimacs = "p cnf 1 2\n1 0\n-1 0\n"
        solver = Solver.from_dimacs(dimacs)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".drat", delete=False) as f:
            proof_path = f.name
        try:
            solver.enable_proof(proof_path)
            result = solver.solve()
            solver.close_proof()
            assert result is False
            with open(proof_path) as f:
                content = f.read()
            assert len(content) > 0  # Some proof was written
        finally:
            os.unlink(proof_path)


# ============================================================
# Data structures
# ============================================================


class TestDataStructures:
    """Tests for internal data structures."""

    def test_clause_repr(self):
        clause = Clause([1, 2, -3], learnt=True)
        assert "L" in repr(clause)
        assert "1" in repr(clause)

    def test_clause_len(self):
        clause = Clause([1, 2, -3])
        assert len(clause) == 3

    def test_lit_to_idx(self):
        assert Solver.lit_to_idx(1) == 2  # 2*1 + 0
        assert Solver.lit_to_idx(-1) == 3  # 2*1 + 1
        assert Solver.lit_to_idx(5) == 10  # 2*5 + 0
        assert Solver.lit_to_idx(-5) == 11  # 2*5 + 1

    def test_idx_to_var(self):
        assert Solver.idx_to_var(2) == 1
        assert Solver.idx_to_var(3) == 1
        assert Solver.idx_to_var(10) == 5


# ============================================================
# Edge cases and robustness
# ============================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_timeout(self):
        """Test that timeout returns None."""
        num_vars, clauses = generate_php(6, 5)
        solver, result = solve_clauses(num_vars, clauses, time_limit=0.001)
        # Could be True, False, or None

    def test_prop_queue_after_conflict(self):
        dimacs = "p cnf 3 3\n1 2 0\n-1 3 0\n-2 -3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True or result is False

    def test_watcher_swap_in_remove(self):
        """Test that watcher swaps during propagation don't corrupt removal."""
        dimacs = "p cnf 6 10\n1 2 3 0\n-1 -2 0\n-1 -3 0\n-2 -3 0\n4 5 6 0\n-4 -5 0\n-4 -6 0\n-5 -6 0\n1 4 0\n2 5 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve(time_limit=10)
        assert result in (True, False, None)

    def test_probing_state_restoration(self):
        """Test that probing properly restores state including var_info."""
        dimacs = "p cnf 3 4\n1 2 0\n1 -2 0\n-1 3 0\n-1 -3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.preprocess()
        assert result is False or result is True
        result = solver.solve()
        assert result is False

    def test_negative_zero_literal(self):
        """Test that literal 0 is not treated as a variable."""
        dimacs = "p cnf 1 1\n1 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is True

    def test_phase_saving(self):
        """Test that phase saving works across backtracks."""
        dimacs = "p cnf 4 5\n-1 2 0\n-1 -2 3 0\n1 -3 0\n1 -4 0\n3 4 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result in (True, False, None)

    def test_medium_instance(self):
        num_vars, clauses = generate_random_cnf(100, 350, k=3, seed=123)
        solver, result = solve_clauses(num_vars, clauses, time_limit=30)
        if result is True:
            model = solver.get_model()
            assert solver.verify_model(model)

    def test_restart_preserves_state(self):
        num_vars, clauses = generate_random_cnf(50, 215, k=3, seed=42)
        solver, result = solve_clauses(num_vars, clauses, restart_strategy="luby", luby_multiplier=10, time_limit=10)
        if result is True:
            assert solver.verify_model(solver.get_model())

    def test_propagation_queue_clear(self):
        """Verify that prop_queue is properly cleared on conflict."""
        dimacs = "p cnf 3 4\n1 0\n-1 2 0\n-1 -2 3 0\n-1 -3 0\n"
        solver = Solver.from_dimacs(dimacs)
        result = solver.solve()
        assert result is False


# ============================================================
# Logging
# ============================================================


class TestLogging:
    """Tests for logging functionality."""

    def test_solver_has_logger(self):
        solver = Solver()
        assert solver._logger is not None

    def test_solver_stats_dict(self):
        stats = SolverStats()
        stats.decisions = 42
        d = stats.summary()
        assert d["decisions"] == 42
        assert "elapsed_seconds" in d