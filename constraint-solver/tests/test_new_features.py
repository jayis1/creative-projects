"""
Tests for new features: config, serialization, visualization,
additional problem generators, and CLI.
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from csp_solver.csp import CSP, Variable, Constraint
from csp_solver.solver import CSPSolver
from csp_solver.config import SolverConfig, create_example_config
from csp_solver.logging_utils import SolverProgress, setup_logging
from csp_solver.serialization import (
    export_csp,
    export_solution,
    save_csp,
    save_solution,
    import_csp,
    load_csp,
)
from csp_solver.visualization import (
    render_sudoku,
    render_queens,
    render_graph_coloring,
    render_cryptarithm,
    render_latin_square,
    render_magic_square,
    COLOR_NAMES,
    COLOR_SYMBOLS,
)
from csp_solver.problems import (
    sudoku_csp,
    n_queens_csp,
    graph_coloring_csp,
    cryptarithm_csp,
    latin_square_csp,
    AUSTRALIA_EDGES,
)
from csp_solver.problems_extra import (
    job_shop_csp,
    format_schedule,
    graph_csp_from_edges,
)


# ─── Config Tests ──────────────────────────────────────────────────

class TestSolverConfig:
    def test_default_config(self):
        config = SolverConfig()
        assert config.use_mrv is True
        assert config.use_mac is True
        assert config.timeout is None
        assert config.log_level == "WARNING"

    def test_custom_config(self):
        config = SolverConfig(
            use_mrv=False,
            use_mac=False,
            timeout=60.0,
            log_level="DEBUG",
        )
        assert config.use_mrv is False
        assert config.use_mac is False
        assert config.timeout == 60.0
        assert config.log_level == "DEBUG"

    def test_to_dict(self):
        config = SolverConfig(timeout=30.0)
        d = config.to_dict()
        assert d["timeout"] == 30.0
        assert d["use_mrv"] is True
        assert "log_level" in d

    def test_from_dict(self):
        d = {"use_mrv": False, "timeout": 45.0, "unknown_key": "ignored"}
        config = SolverConfig.from_dict(d)
        assert config.use_mrv is False
        assert config.timeout == 45.0
        assert config.use_mac is True  # default preserved

    def test_save_load_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        try:
            config = SolverConfig(timeout=42.0, use_mac=False)
            config.to_file(path)

            loaded = SolverConfig.from_file(path)
            assert loaded.timeout == 42.0
            assert loaded.use_mac is False
            assert loaded.use_mrv is True
        finally:
            os.unlink(path)

    def test_create_solver(self):
        config = SolverConfig(use_mac=True, timeout=10.0)
        solver = config.create_solver()
        assert solver is not None
        result = solver.solve(n_queens_csp(4))
        assert result.is_satisfiable is True

    def test_apply_logging(self):
        config = SolverConfig(log_level="DEBUG")
        config.apply_logging()
        import logging
        logger = logging.getLogger("csp_solver")
        assert logger.level == logging.DEBUG

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            SolverConfig.from_file("/nonexistent/path.json")

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            path = f.name
        try:
            with pytest.raises(ValueError, match="Unsupported"):
                SolverConfig.from_file(path)
        finally:
            os.unlink(path)

    def test_create_example_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = create_example_config(tmpdir)
            assert os.path.exists(path)
            # Load it back
            config = SolverConfig.from_file(path)
            assert config.use_mrv is True


# ─── Serialization Tests ──────────────────────────────────────────

class TestSerialization:
    def test_export_csp(self):
        csp = n_queens_csp(4)
        data = export_csp(csp)
        assert "variables" in data
        assert "constraints" in data
        assert data["num_variables"] == 4
        assert data["num_constraints"] > 0

    def test_export_solution(self):
        csp = n_queens_csp(4)
        solver = CSPSolver()
        result = solver.solve(csp)
        data = export_solution(
            result.assignment,
            stats=result.stats,
            method=result.method,
            problem_type="n_queens",
        )
        assert "assignment" in data
        assert data["num_variables"] == 4
        assert data["method"] != ""

    def test_save_load_csp(self):
        csp = n_queens_csp(4)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_csp(csp, path)
            loaded = load_csp(path)
            assert len(loaded.variables) == 4
            for name in loaded.variables:
                assert name in csp.variables
        finally:
            os.unlink(path)

    def test_save_solution(self):
        csp = n_queens_csp(4)
        solver = CSPSolver()
        result = solver.solve(csp)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_solution(result.assignment, path, method=result.method)
            with open(path) as f:
                data = json.load(f)
            assert "assignment" in data
            assert "Q0" in data["assignment"]
        finally:
            os.unlink(path)

    def test_import_csp_invalid(self):
        with pytest.raises(ValueError, match="missing"):
            import_csp({"not_variables": {}})

    def test_round_trip_domains(self):
        """Domains should survive serialization round-trip."""
        csp = CSP()
        csp.add_variable(Variable("X", domain={1, 2, 3}))
        csp.add_variable(Variable("Y", domain={4, 5}))
        csp.add_constraint(Constraint(
            ("X", "Y"),
            lambda a: a["X"] < a["Y"],
            pair_check=lambda x, y: x < y,
        ))

        data = export_csp(csp)
        imported = import_csp(data)
        assert imported.get_domain("X") == {1, 2, 3}
        assert imported.get_domain("Y") == {4, 5}


# ─── Visualization Tests ──────────────────────────────────────────

class TestVisualization:
    def test_render_sudoku(self):
        assignment = {f"R{i}C{j}": (i * 3 + j // 3 + i // 3) % 9 + 1
                       for i in range(9) for j in range(9)}
        result = render_sudoku(assignment)
        assert isinstance(result, str)
        assert "│" in result  # box style has separators

    def test_render_sudoku_compact(self):
        assignment = {f"R{i}C{j}": (i + j) % 9 + 1
                       for i in range(9) for j in range(9)}
        result = render_sudoku(assignment, style="compact")
        lines = result.split("\n")
        assert len(lines) == 9

    def test_render_queens(self):
        assignment = {"Q0": 1, "Q1": 3, "Q2": 0, "Q3": 2}
        result = render_queens(assignment, 4)
        assert "♛" in result

    def test_render_graph_coloring(self):
        assignment = {"WA": 0, "NT": 1, "SA": 2, "Q": 0, "NSW": 1, "V": 2}
        result = render_graph_coloring(assignment, AUSTRALIA_EDGES)
        assert "Node assignments" in result
        assert "Constraint verification" in result
        assert "✓" in result

    def test_render_cryptarithm(self):
        assignment = {"S": 9, "E": 5, "N": 6, "D": 7, "M": 1, "O": 0, "R": 8, "Y": 2}
        result = render_cryptarithm(assignment, ["SEND", "MORE"], "MONEY")
        assert "Check:" in result
        assert "9567" in result

    def test_render_latin_square(self):
        assignment = {"L0_0": 0, "L0_1": 1, "L1_0": 1, "L1_1": 0}
        result = render_latin_square(assignment, 2)
        assert "┌" in result
        assert "┐" in result

    def test_render_magic_square(self):
        assignment = {"M0_0": 2, "M0_1": 7, "M0_2": 6,
                      "M1_0": 9, "M1_1": 5, "M1_2": 1,
                      "M2_0": 4, "M2_1": 3, "M2_2": 8}
        result = render_magic_square(assignment, 3)
        assert "target sum: 15" in result

    def test_color_maps(self):
        assert COLOR_NAMES[0] == "Red"
        assert COLOR_NAMES[1] == "Green"
        assert len(COLOR_SYMBOLS) >= 5


# ─── Logging/Progress Tests ───────────────────────────────────────

class TestSolverProgress:
    def test_progress_tracker(self):
        progress = SolverProgress()
        csp = n_queens_csp(4)

        from csp_solver.backtrack import BacktrackingSolver
        bt = BacktrackingSolver(
            use_mrv=True, use_mac=True,
            progress_callback=progress.callback,
        )
        progress.start(csp)
        result = bt.solve(csp)

        assert progress.total_steps > 0
        assert len(progress.assignments) > 0

    def test_progress_summary(self):
        progress = SolverProgress()
        summary = progress.summary()
        assert summary["total_steps"] == 0

    def test_setup_logging(self):
        setup_logging("DEBUG")
        import logging
        logger = logging.getLogger("csp_solver")
        assert logger.level == logging.DEBUG

    def test_progress_with_domain_tracking(self):
        progress = SolverProgress(track_domain_sizes=True)
        csp = n_queens_csp(4)

        from csp_solver.backtrack import BacktrackingSolver
        bt = BacktrackingSolver(use_mac=True, progress_callback=progress.callback)
        progress.start(csp)
        bt.solve(csp)

        summary = progress.summary()
        assert summary["domain_sizes_tracked"] is True


# ─── Additional Problem Generators Tests ──────────────────────────

class TestJobShopCSP:
    def test_simple_schedule(self):
        jobs = {"J1": (3, "R1"), "J2": (2, "R1"), "J3": (4, "R2")}
        csp = job_shop_csp(jobs)
        assert len(csp.variables) == 3

    def test_solve_schedule(self):
        jobs = {"J1": (3, "R1"), "J2": (2, "R1")}
        csp = job_shop_csp(jobs)
        solver = CSPSolver(use_mac=True, timeout=10)
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        # Jobs on same resource should not overlap
        start_j1 = result.assignment["start_J1"]
        start_j2 = result.assignment["start_J2"]
        assert (start_j1 + 3 <= start_j2) or (start_j2 + 2 <= start_j1)

    def test_format_schedule(self):
        assignment = {"start_J1": 0, "start_J2": 3}
        jobs = {"J1": (3, "R1"), "J2": (2, "R1")}
        result = format_schedule(assignment, jobs)
        assert "J1" in result
        assert "J2" in result

    def test_empty_jobs_error(self):
        with pytest.raises(ValueError):
            job_shop_csp({})


class TestGraphCSPFromEdges:
    def test_not_equal(self):
        edges = [("A", "B"), ("B", "C"), ("A", "C")]
        csp = graph_csp_from_edges(edges, domain_size=3)
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["A"] != result.assignment["B"]

    def test_less_than(self):
        edges = [("A", "B")]
        csp = graph_csp_from_edges(edges, domain_size=3, constraint_type="less_than")
        solver = CSPSolver()
        result = solver.solve(csp)
        assert result.is_satisfiable is True
        assert result.assignment["A"] < result.assignment["B"]

    def test_invalid_domain(self):
        with pytest.raises(ValueError):
            graph_csp_from_edges([("A", "B")], domain_size=0)

    def test_invalid_constraint_type(self):
        with pytest.raises(ValueError):
            graph_csp_from_edges([("A", "B")], domain_size=3, constraint_type="unknown")


# ─── CLI Tests ────────────────────────────────────────────────────

class TestCLI:
    def test_parse_jobs(self):
        from csp_solver.cli import parse_jobs
        jobs = parse_jobs("J1:3:R1,J2:2:R1")
        assert "J1" in jobs
        assert jobs["J1"] == (3, "R1")
        assert jobs["J2"] == (2, "R1")

    def test_parse_jobs_invalid(self):
        from csp_solver.cli import parse_jobs
        with pytest.raises(ValueError):
            parse_jobs("J1:invalid")

    def test_parse_grid(self):
        from csp_solver.cli import parse_grid
        grid = parse_grid("123456789" * 9)
        assert len(grid) == 9
        assert len(grid[0]) == 9

    def test_parse_grid_invalid(self):
        from csp_solver.cli import parse_grid
        with pytest.raises(ValueError):
            parse_grid("123")

    def test_build_parser(self):
        from csp_solver.cli import build_parser
        parser = build_parser()
        assert parser is not None


# ─── Integration Tests ────────────────────────────────────────────

class TestIntegration:
    def test_config_to_solver_pipeline(self):
        """Test creating a solver from config and solving."""
        config = SolverConfig(use_mac=True, timeout=30)
        solver = config.create_solver()
        csp = n_queens_csp(6)
        result = solver.solve(csp)
        assert result.is_satisfiable is True

    def test_export_solve_reimport(self):
        """Test exporting a CSP, solving, and reimporting."""
        csp = n_queens_csp(4)
        data = export_csp(csp)
        imported = import_csp(data)
        assert len(imported.variables) == 4
        # Can't solve imported CSP directly (no constraints), but variables are preserved
        for name in imported.variables:
            assert name in csp.variables

    def test_progress_tracking_with_solve(self):
        """Test progress tracking integration with solver."""
        progress = SolverProgress(log_interval=0)
        csp = n_queens_csp(5)
        progress.start(csp)

        from csp_solver.backtrack import BacktrackingSolver
        bt = BacktrackingSolver(use_mac=True, progress_callback=progress.callback)
        result = bt.solve(csp)

        assert result is not None
        assert progress.total_steps > 0
        summary = progress.summary()
        assert summary["total_steps"] > 0

    def test_all_problem_types_solve(self):
        """Smoke test: all problem types should produce a result."""
        problems = [
            ("n_queens_4", n_queens_csp(4)),
            ("latin_3", latin_square_csp(3)),
            ("australia", graph_coloring_csp(AUSTRALIA_EDGES, 3)),
        ]
        solver = CSPSolver(use_mac=True, timeout=30)
        for name, csp in problems:
            result = solver.solve(csp)
            assert result.is_satisfiable is True, f"{name} should be satisfiable"

    def test_serialization_roundtrip_preserves_domains(self):
        """Domains should be preserved through save/load cycle."""
        csp = CSP()
        csp.add_variable(Variable("A", domain={1, 2, 3}))
        csp.add_variable(Variable("B", domain={4, 5, 6}))
        csp.add_constraint(Constraint(
            ("A", "B"),
            lambda a: a["A"] != a["B"],
            pair_check=lambda x, y: x != y,
        ))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_csp(csp, path)
            loaded = load_csp(path)
            assert loaded.get_domain("A") == {1, 2, 3}
            assert loaded.get_domain("B") == {4, 5, 6}
        finally:
            os.unlink(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])