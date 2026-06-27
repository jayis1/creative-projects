"""Enhanced tests: iteration counting, validation, MPS roundtrip, more LPs."""

import os
import tempfile
from fractions import Fraction

import pytest

from simplex import LPProblem, LPResult, LPStatus, SimplexSolver, MILPSolver
from simplex.mps import read_mps, write_mps


def test_iteration_counting():
    """The solver should report the number of pivots."""
    lp = LPProblem(
        name="iter_test", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
            {"coeffs": {"x": 2, "y": 1}, "relation": "<=", "rhs": 6, "name": "c1"},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    assert res.iterations > 0


def test_dantzig_rule():
    """Dantzig's rule should also find the optimum."""
    lp = LPProblem(
        name="dantzig", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
            {"coeffs": {"x": 2, "y": 1}, "relation": "<=", "rhs": 6, "name": "c1"},
        ],
    )
    res = SimplexSolver(bland=False).solve(lp)
    assert res.status is LPStatus.OPTIMAL
    assert res.objective_value == pytest.approx(10.0, abs=1e-6)


def test_validation_ok():
    """A well-formed problem should pass validation."""
    lp = LPProblem(
        name="valid", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 1, "y": 1},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 5, "name": "c0"},
        ],
    )
    errors = lp.validate()
    assert errors == []


def test_validation_bad_var():
    """Constraints referencing unknown variables should fail validation."""
    lp = LPProblem(
        name="bad", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 1, "y": 1},
        constraints=[
            {"coeffs": {"x": 1, "z": 1}, "relation": "<=", "rhs": 5, "name": "c0"},
        ],
    )
    errors = lp.validate()
    assert any("unknown variable 'z'" in e for e in errors)


def test_validation_bounds_conflict():
    """lb > ub should fail validation."""
    lp = LPProblem(
        name="bad_bounds", objective="max",
        variables=("x",),
        objective_coeffs={"x": 1},
        constraints=[
            {"coeffs": {"x": 1}, "relation": "<=", "rhs": 10, "name": "c0"},
        ],
        bounds={"x": (5, 3)},  # lb > ub
    )
    errors = lp.validate()
    assert any("lower bound" in e and "upper bound" in e for e in errors)


def test_production_problem():
    """Production planning problem with 3 products and 3 resources."""
    lp = LPProblem(
        name="production", objective="max",
        variables=("x", "y", "z"),
        objective_coeffs={"x": 30, "y": 20, "z": 50},
        constraints=[
            {"coeffs": {"x": 2, "y": 1, "z": 3}, "relation": "<=", "rhs": 100, "name": "labor"},
            {"coeffs": {"x": 1, "y": 3, "z": 2}, "relation": "<=", "rhs": 120, "name": "machine"},
            {"coeffs": {"x": 1, "y": 1, "z": 1}, "relation": "<=", "rhs": 50, "name": "material"},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # obj = 12200/7 ≈ 1742.857
    assert res.objective_value == pytest.approx(12200 / 7, abs=1e-4)


def test_transportation_problem():
    """2-supplier, 3-customer transportation problem."""
    lp = LPProblem(
        name="transport", objective="min",
        variables=("x11", "x12", "x13", "x21", "x22", "x23"),
        objective_coeffs={"x11": 4, "x12": 6, "x13": 8, "x21": 5, "x22": 7, "x23": 6},
        constraints=[
            {"coeffs": {"x11": 1, "x12": 1, "x13": 1}, "relation": "<=", "rhs": 50, "name": "s1"},
            {"coeffs": {"x21": 1, "x22": 1, "x23": 1}, "relation": "<=", "rhs": 40, "name": "s2"},
            {"coeffs": {"x11": 1, "x21": 1}, "relation": ">=", "rhs": 30, "name": "d1"},
            {"coeffs": {"x12": 1, "x22": 1}, "relation": ">=", "rhs": 35, "name": "d2"},
            {"coeffs": {"x13": 1, "x23": 1}, "relation": ">=", "rhs": 25, "name": "d3"},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    assert res.objective_value == pytest.approx(495.0, abs=1e-6)


def test_mps_roundtrip():
    """Write a problem to MPS, read it back, and verify the solution matches."""
    lp = LPProblem(
        name="mps_test", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
            {"coeffs": {"x": 2, "y": 1}, "relation": "<=", "rhs": 6, "name": "c1"},
        ],
    )
    # Solve original.
    res1 = SimplexSolver().solve(lp)
    assert res1.status is LPStatus.OPTIMAL
    # Write to MPS.
    with tempfile.NamedTemporaryFile(suffix=".mps", mode="w", delete=False) as f:
        write_mps(lp, f.name)
        mps_path = f.name
    try:
        # Read back.
        lp2 = read_mps(mps_path)
        res2 = SimplexSolver().solve(lp2)
        assert res2.status is LPStatus.OPTIMAL
        assert res2.objective_value == pytest.approx(res1.objective_value, abs=1e-6)
    finally:
        os.unlink(mps_path)


def test_milp_assignment():
    """Simple assignment problem: 3 workers, 3 tasks, minimise cost."""
    # c[i][j] = cost of worker i doing task j
    # vars: x_ij binary
    costs = {"x11": 4, "x12": 5, "x13": 6, "x21": 3, "x22": 6, "x23": 2, "x31": 8, "x32": 1, "x33": 7}
    lp = LPProblem(
        name="assignment", objective="min",
        variables=("x11", "x12", "x13", "x21", "x22", "x23", "x31", "x32", "x33"),
        objective_coeffs=costs,
        constraints=[
            # each worker does exactly 1 task
            {"coeffs": {"x11": 1, "x12": 1, "x13": 1}, "relation": "=", "rhs": 1, "name": "w1"},
            {"coeffs": {"x21": 1, "x22": 1, "x23": 1}, "relation": "=", "rhs": 1, "name": "w2"},
            {"coeffs": {"x31": 1, "x32": 1, "x33": 1}, "relation": "=", "rhs": 1, "name": "w3"},
            # each task assigned to exactly 1 worker
            {"coeffs": {"x11": 1, "x21": 1, "x31": 1}, "relation": "=", "rhs": 1, "name": "t1"},
            {"coeffs": {"x12": 1, "x22": 1, "x32": 1}, "relation": "=", "rhs": 1, "name": "t2"},
            {"coeffs": {"x13": 1, "x23": 1, "x33": 1}, "relation": "=", "rhs": 1, "name": "t3"},
        ],
        bounds={v: (0, 1) for v in costs},
        integer=set(costs.keys()),
    )
    res = MILPSolver(max_nodes=500).solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # Optimal: w1→t1(4), w2→t3(2), w3→t2(1) = 7
    assert res.objective_value == pytest.approx(7.0, abs=1e-6)


def test_minimization():
    """Minimisation problem with >= constraints."""
    lp = LPProblem(
        name="min_test", objective="min",
        variables=("x", "y"),
        objective_coeffs={"x": 5, "y": 4},
        constraints=[
            {"coeffs": {"x": 2, "y": 1}, "relation": ">=", "rhs": 6, "name": "c0"},
            {"coeffs": {"x": 1, "y": 1}, "relation": ">=", "rhs": 4, "name": "c1"},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # x=2, y=2 → obj = 18
    assert res.objective_value == pytest.approx(18.0, abs=1e-6)