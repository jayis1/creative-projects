"""Tests for the LP format reader/writer and pretty-printing."""

import os
import tempfile
from fractions import Fraction

import pytest

from simplex import LPProblem, SimplexSolver, LPStatus
from simplex.formatting import write_lp, read_lp, format_result, format_tableau


def _make_production_lp() -> LPProblem:
    return LPProblem(
        name="production", objective="max",
        variables=("x", "y", "z"),
        objective_coeffs={"x": 30, "y": 20, "z": 50},
        constraints=[
            {"coeffs": {"x": 2, "y": 1, "z": 3}, "relation": "<=", "rhs": 100, "name": "labor"},
            {"coeffs": {"x": 1, "y": 3, "z": 2}, "relation": "<=", "rhs": 120, "name": "machine"},
            {"coeffs": {"x": 1, "y": 1, "z": 1}, "relation": "<=", "rhs": 50, "name": "material"},
        ],
    )


def test_lp_roundtrip_simple():
    """Write to LP format, read back, and verify the solution matches."""
    lp = _make_production_lp()
    res1 = SimplexSolver().solve(lp)
    assert res1.status is LPStatus.OPTIMAL
    with tempfile.NamedTemporaryFile(suffix=".lp", mode="w", delete=False) as f:
        write_lp(lp, f.name)
        lp_path = f.name
    try:
        lp2 = read_lp(lp_path)
        res2 = SimplexSolver().solve(lp2)
        assert res2.status is LPStatus.OPTIMAL
        assert res2.objective_value == pytest.approx(res1.objective_value, abs=1e-4)
    finally:
        os.unlink(lp_path)


def test_lp_format_with_bounds():
    """LP format should correctly round-trip variable bounds."""
    lp = LPProblem(
        name="bounded", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 10, "name": "c0"},
        ],
        bounds={"x": (0, 5), "y": (1, 8)},
    )
    with tempfile.NamedTemporaryFile(suffix=".lp", mode="w", delete=False) as f:
        write_lp(lp, f.name)
        lp_path = f.name
    try:
        lp2 = read_lp(lp_path)
        assert "x" in lp2.bounds
        assert lp2.bounds["x"][0] == 0
        assert lp2.bounds["x"][1] == 5
        assert lp2.bounds["y"][0] == 1
        assert lp2.bounds["y"][1] == 8
    finally:
        os.unlink(lp_path)


def test_lp_format_free_variable():
    """LP format should correctly round-trip free variables."""
    lp = LPProblem(
        name="free_var", objective="max",
        variables=("x",),
        objective_coeffs={"x": 1},
        constraints=[
            {"coeffs": {"x": 1}, "relation": "<=", "rhs": 5, "name": "c0"},
            {"coeffs": {"x": -1}, "relation": "<=", "rhs": 3, "name": "c1"},
        ],
        bounds={"x": (None, None)},
    )
    with tempfile.NamedTemporaryFile(suffix=".lp", mode="w", delete=False) as f:
        write_lp(lp, f.name)
        lp_path = f.name
    try:
        lp2 = read_lp(lp_path)
        assert lp2.bounds["x"] == (None, None)
        res = SimplexSolver().solve(lp2)
        assert res.status is LPStatus.OPTIMAL
        assert res.objective_value == pytest.approx(5.0, abs=1e-6)
    finally:
        os.unlink(lp_path)


def test_lp_format_integer_vars():
    """LP format should correctly round-trip integer declarations."""
    lp = LPProblem(
        name="milp", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 1, "y": 1},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 3, "name": "c0"},
        ],
        bounds={"x": (0, 2), "y": (0, 2)},
        integer={"x", "y"},
    )
    with tempfile.NamedTemporaryFile(suffix=".lp", mode="w", delete=False) as f:
        write_lp(lp, f.name)
        lp_path = f.name
    try:
        lp2 = read_lp(lp_path)
        assert "x" in lp2.integer
        assert "y" in lp2.integer
    finally:
        os.unlink(lp_path)


def test_format_result_output():
    """format_result should produce a readable boxed table."""
    lp = LPProblem(
        name="test", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
        ],
    )
    res = SimplexSolver().solve(lp)
    out = format_result(res, lp)
    assert "OPTIMAL" in out or "optimal" in out
    assert "x" in out
    assert "y" in out
    assert "┌" in out  # Box drawing


def test_format_tableau_output():
    """format_tableau should produce a readable summary."""
    lp = LPProblem(
        name="test", objective="max",
        variables=("x",),
        objective_coeffs={"x": 1},
        constraints=[
            {"coeffs": {"x": 1}, "relation": "<=", "rhs": 5, "name": "c0"},
        ],
    )
    res = SimplexSolver().solve(lp)
    out = format_tableau(lp, res)
    assert "MAX" in out
    assert "x" in out
    assert "Optimal" in out or "optimal" in out