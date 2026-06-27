"""Basic sanity tests for the simplex solver (Phase 1 minimal set)."""

from fractions import Fraction

import pytest

from simplex import LPProblem, LPResult, LPStatus, SimplexSolver, MILPSolver


def _make_diet_lp() -> LPProblem:
    """Classic diet problem (minimise cost subject to nutrient minimums)."""
    # Variables: x= bread units, y= milk units
    # Bread: $2/unit, 1 cal, 2 vit
    # Milk:  $3/unit, 3 cal, 1 vit
    # Need >= 5 cal, >= 4 vit
    return LPProblem(
        name="diet",
        objective="min",
        variables=("bread", "milk"),
        objective_coeffs={"bread": 2, "milk": 3},
        constraints=[
            {"coeffs": {"bread": 1, "milk": 3}, "relation": ">=", "rhs": 5, "name": "cal"},
            {"coeffs": {"bread": 2, "milk": 1}, "relation": ">=", "rhs": 4, "name": "vit"},
        ],
    )


def test_diet_optimal():
    lp = _make_diet_lp()
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # Optimal: x=1.4, y=1.2, cost = 2*1.4 + 3*1.2 = 6.4
    assert res.objective_value == pytest.approx(6.4, abs=1e-6)
    assert res.solution["bread"] == pytest.approx(1.4, abs=1e-6)
    assert res.solution["milk"] == pytest.approx(1.2, abs=1e-6)


def test_unbounded():
    lp = LPProblem(
        name="unbounded",
        objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 1, "y": 1},
        constraints=[
            {"coeffs": {"x": 1, "y": -1}, "relation": "<=", "rhs": 1},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.UNBOUNDED


def test_infeasible():
    lp = LPProblem(
        name="infeasible",
        objective="max",
        variables=("x",),
        objective_coeffs={"x": 1},
        constraints=[
            {"coeffs": {"x": 1}, "relation": ">=", "rhs": 5},
            {"coeffs": {"x": 1}, "relation": "<=", "rhs": 2},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.INFEASIBLE


def test_equality_constraint():
    lp = LPProblem(
        name="eq",
        objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "=", "rhs": 4},
            {"coeffs": {"x": 2, "y": 1}, "relation": "<=", "rhs": 6},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # x=2, y=2 → obj=10
    assert res.objective_value == pytest.approx(10.0, abs=1e-6)


def test_milp_knapsack():
    # 0/1 knapsack: items with values and weights, capacity 10.
    # item1: v=60 w=5, item2: v=50 w=3, item3: v=70 w=4
    lp = LPProblem(
        name="knapsack",
        objective="max",
        variables=("i1", "i2", "i3"),
        objective_coeffs={"i1": 60, "i2": 50, "i3": 70},
        constraints=[
            {"coeffs": {"i1": 5, "i2": 3, "i3": 4}, "relation": "<=", "rhs": 10, "name": "cap"},
        ],
        bounds={"i1": (0, 1), "i2": (0, 1), "i3": (0, 1)},
        integer={"i1", "i2", "i3"},
    )
    res = MILPSolver(max_nodes=1000).solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # Optimal: i1=1, i3=1 → 130 (weight 9), or i2=1, i3=1 → 120 (weight 7)
    # i1+i3 = 130 is best.
    assert res.objective_value == pytest.approx(130.0, abs=1e-6)


def test_free_variable():
    # x is free; maximise x s.t. x <= 5 and -x <= 3 → x in [-3, 5] → x=5
    lp = LPProblem(
        name="free",
        objective="max",
        variables=("x",),
        objective_coeffs={"x": 1},
        constraints=[
            {"coeffs": {"x": 1}, "relation": "<=", "rhs": 5},
            {"coeffs": {"x": -1}, "relation": "<=", "rhs": 3},
        ],
        bounds={"x": (None, None)},
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    assert res.objective_value == pytest.approx(5.0, abs=1e-6)


def test_upper_bound():
    # max x, x <= 10, 2x <= 15 → x <= 7.5
    lp = LPProblem(
        name="ub",
        objective="max",
        variables=("x",),
        objective_coeffs={"x": 1},
        constraints=[
            {"coeffs": {"x": 2}, "relation": "<=", "rhs": 15},
        ],
        bounds={"x": (0, 10)},
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    assert res.objective_value == pytest.approx(7.5, abs=1e-6)


def test_duals_basic():
    # max 3x + 2y  s.t.  x+y <= 4, 2x+y <= 6 → x=2,y=2, obj=10
    # duals: y1=1 (constraint 1 marginal), y2=1
    lp = LPProblem(
        name="dual",
        objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
            {"coeffs": {"x": 2, "y": 1}, "relation": "<=", "rhs": 6, "name": "c1"},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    assert res.objective_value == pytest.approx(10.0, abs=1e-6)
    # Duals should be 1 and 1 (by complementary slackness both tight).
    assert res.duals["c0"] == pytest.approx(1.0, abs=1e-6)
    assert res.duals["c1"] == pytest.approx(1.0, abs=1e-6)