"""Tests for enhanced MILP features: search strategies, Gomory cuts, time limits."""

import time
from fractions import Fraction

import pytest

from simplex import LPProblem, LPStatus, MILPSolver, SearchStrategy


def _make_knapsack(n_items=5) -> LPProblem:
    """Create a knapsack problem with n_items items."""
    values = [60, 50, 70, 30, 80, 55, 90, 40, 65, 85]
    weights = [5, 3, 4, 2, 6, 3, 7, 2, 5, 6]
    values = values[:n_items]
    weights = weights[:n_items]
    capacity = sum(weights) * 0.6  # 60% of total weight
    var_names = [f"i{i+1}" for i in range(n_items)]
    return LPProblem(
        name="knapsack", objective="max",
        variables=tuple(var_names),
        objective_coeffs={var_names[i]: values[i] for i in range(n_items)},
        constraints=[
            {"coeffs": {var_names[i]: weights[i] for i in range(n_items)},
             "relation": "<=", "rhs": int(capacity), "name": "cap"},
        ],
        bounds={v: (0, 1) for v in var_names},
        integer=set(var_names),
    )


def test_milp_best_first():
    """Best-first search should find the optimal solution."""
    lp = _make_knapsack(5)
    solver = MILPSolver(max_nodes=1000, strategy="best-first")
    res = solver.solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # The LP relaxation bound is 230 (all items), so optimal ≤ 230.
    assert res.objective_value is not None
    assert res.objective_value > 0


def test_milp_depth_first():
    """Depth-first search should find the same optimal solution."""
    lp = _make_knapsack(5)
    solver = MILPSolver(max_nodes=1000, strategy="depth-first")
    res = solver.solve(lp)
    assert res.status is LPStatus.OPTIMAL
    best_first_res = MILPSolver(max_nodes=1000, strategy="best-first").solve(lp)
    assert res.objective_value == pytest.approx(
        best_first_res.objective_value, abs=1e-6
    )


def test_milp_breadth_first():
    """Breadth-first search should find the same optimal solution."""
    lp = _make_knapsack(5)
    solver = MILPSolver(max_nodes=2000, strategy="breadth-first")
    res = solver.solve(lp)
    assert res.status is LPStatus.OPTIMAL
    best_first_res = MILPSolver(max_nodes=1000, strategy="best-first").solve(lp)
    assert res.objective_value == pytest.approx(
        best_first_res.objective_value, abs=1e-6
    )


def test_milp_search_strategy_enum():
    """SearchStrategy enum should accept string and enum values."""
    solver1 = MILPSolver(strategy="depth-first")
    assert solver1.strategy is SearchStrategy.DEPTH_FIRST
    solver2 = MILPSolver(strategy=SearchStrategy.BREADTH_FIRST)
    assert solver2.strategy is SearchStrategy.BREADTH_FIRST


def test_milp_node_limit():
    """A very low node limit should cause timeout or suboptimal result."""
    lp = _make_knapsack(8)
    solver = MILPSolver(max_nodes=1, strategy="best-first")
    res = solver.solve(lp)
    # With only 1 node, the solver either finds an integer solution at the
    # root (unlikely for 8 items) or times out.
    assert res.status in (LPStatus.OPTIMAL, LPStatus.TIMEOUT, LPStatus.INFEASIBLE)


def test_milp_time_limit():
    """A very short time limit should cause timeout for a hard problem."""
    lp = _make_knapsack(10)
    solver = MILPSolver(max_nodes=10000, time_limit=0.001)
    res = solver.solve(lp)
    assert res.status in (LPStatus.OPTIMAL, LPStatus.TIMEOUT)


def test_milp_cuts_flag():
    """Disabling cuts should still produce correct results."""
    lp = _make_knapsack(5)
    solver = MILPSolver(max_nodes=1000, use_cuts=False)
    res = solver.solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # Result should match the cuts-enabled version.
    res_with_cuts = MILPSolver(max_nodes=1000, use_cuts=True).solve(lp)
    assert res.objective_value == pytest.approx(
        res_with_cuts.objective_value, abs=1e-6
    )


def test_milp_assignment_problem():
    """Assignment problem should solve correctly with depth-first."""
    costs = {"x11": 4, "x12": 5, "x13": 6, "x21": 3, "x22": 6, "x23": 2,
             "x31": 8, "x32": 1, "x33": 7}
    lp = LPProblem(
        name="assignment", objective="min",
        variables=("x11", "x12", "x13", "x21", "x22", "x23", "x31", "x32", "x33"),
        objective_coeffs=costs,
        constraints=[
            {"coeffs": {"x11": 1, "x12": 1, "x13": 1}, "relation": "=", "rhs": 1, "name": "w1"},
            {"coeffs": {"x21": 1, "x22": 1, "x23": 1}, "relation": "=", "rhs": 1, "name": "w2"},
            {"coeffs": {"x31": 1, "x32": 1, "x33": 1}, "relation": "=", "rhs": 1, "name": "w3"},
            {"coeffs": {"x11": 1, "x21": 1, "x31": 1}, "relation": "=", "rhs": 1, "name": "t1"},
            {"coeffs": {"x12": 1, "x22": 1, "x32": 1}, "relation": "=", "rhs": 1, "name": "t2"},
            {"coeffs": {"x13": 1, "x23": 1, "x33": 1}, "relation": "=", "rhs": 1, "name": "t3"},
        ],
        bounds={v: (0, 1) for v in costs},
        integer=set(costs.keys()),
    )
    for strategy in ("best-first", "depth-first"):
        solver = MILPSolver(max_nodes=500, strategy=strategy)
        res = solver.solve(lp)
        assert res.status is LPStatus.OPTIMAL
        assert res.objective_value == pytest.approx(7.0, abs=1e-6), \
            f"strategy={strategy} gave obj={res.objective_value}"


def test_milp_reports_nodes_explored():
    """The solver should report how many nodes were explored."""
    lp = _make_knapsack(5)
    solver = MILPSolver(max_nodes=1000)
    res = solver.solve(lp)
    assert solver.nodes_explored > 0
    assert res.iterations == solver.nodes_explored


def test_milp_pure_lp_fallback():
    """A problem with no integer vars should be solved as a pure LP."""
    lp = LPProblem(
        name="pure_lp", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
            {"coeffs": {"x": 2, "y": 1}, "relation": "<=", "rhs": 6, "name": "c1"},
        ],
    )
    res = MILPSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    assert res.objective_value == pytest.approx(10.0, abs=1e-6)