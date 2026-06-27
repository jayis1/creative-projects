"""Bug hunt tests: identify and verify bugs before fixing."""

import math
from fractions import Fraction

import pytest

from simplex import LPProblem, LPResult, LPStatus, SimplexSolver, MILPSolver
from simplex.simplex import Tableau
from simplex.mps import read_mps, write_mps
import tempfile
import os


# Bug 1: obj_const not restored after Phase I (cosmetic but affects internal state)
def test_bug_obj_const_after_phase_one():
    """After Phase I, obj_const should reflect the original objective shift."""
    lp = LPProblem(
        name="shift", objective="max",
        variables=("x",),
        objective_coeffs={"x": 1},
        constraints=[
            {"coeffs": {"x": 1}, "relation": ">=", "rhs": 3, "name": "c0"},
        ],
        bounds={"x": (2, None)},  # lb=2, so obj shift = 1*2 = 2
    )
    t = Tableau.from_problem(lp)
    initial_obj_const = t.obj_const  # should be 2 (the shift)
    assert initial_obj_const == 2, f"expected shift=2, got {initial_obj_const}"
    status = t.run_phase_one(max_iter=100)
    assert status is LPStatus.OPTIMAL
    # After Phase I, obj_const should still include the shift constant.
    # The current code resets obj_const = 0 and then sets it to c_B*rhs,
    # losing the original shift. This is a bug if anyone reads obj_const.
    # The objective VALUE is still correct because extract_solution
    # recomputes from scratch, but obj_const is wrong.
    res = t.extract_solution(lp)
    assert res.objective_value == pytest.approx(3.0, abs=1e-6)  # x >= max(2,3) = 3


# Bug 3: MILP node priority key doesn't match node_id
def test_bug_milp_node_id_mismatch():
    """The priority tuple's node_id should match the actual node_id."""
    solver = MILPSolver(max_nodes=10)
    # When pushing two children, the key uses self._node_counter + 1
    # but _new_node increments _node_counter, so the key is off by one.
    # This doesn't cause incorrect results but can cause non-deterministic
    # heap ordering. We test that the solver still produces correct results.
    lp = LPProblem(
        name="test", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 1, "y": 1},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 3, "name": "c0"},
        ],
        bounds={"x": (0, 2), "y": (0, 2)},
        integer={"x", "y"},
    )
    res = solver.solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # x=1, y=2 or x=2, y=1 → obj=3
    assert res.objective_value == pytest.approx(3.0, abs=1e-6)


# Bug 4: MPS writer produces malformed INTEND marker
def test_bug_mps_intend_marker():
    """MPS writer should produce a valid INTEND marker line."""
    lp = LPProblem(
        name="milp_test", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 1, "y": 1},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 3, "name": "c0"},
        ],
        bounds={"x": (0, 1), "y": (0, 1)},
        integer={"x", "y"},
    )
    with tempfile.NamedTemporaryFile(suffix=".mps", mode="w", delete=False) as f:
        write_mps(lp, f.name)
        mps_path = f.name
    try:
        with open(mps_path) as f:
            content = f.read()
        # Check that INTEND marker is properly formatted
        lines = content.split("\n")
        intend_lines = [l for l in lines if "INTEND" in l]
        if intend_lines:
            # Should have column name and marker, not just "MARKER 'INTEND'"
            assert "MARKER" in intend_lines[0]
            # The malformed version is "    MARKER 'INTEND'" without a column name
            assert intend_lines[0].strip() != "MARKER 'INTEND'", \
                "INTEND marker is malformed (missing column name)"
    finally:
        os.unlink(mps_path)


# Bug 5: MPS RANGES handling for L rows
def test_bug_mps_ranges_l_row():
    """RANGES on an L (<=) row should create a range [b-|r|, b], not just overwrite."""
    # Write a simple MPS file with RANGES and test reading it
    mps_content = """NAME          range_test
ROWS
 N  OBJ
 L  R1
COLUMNS
    x        OBJ       1                  R1        2
    y        OBJ       1                  R1        1
RHS
    RHS1     R1        6
RANGES
    RNG1     R1        2
BOUNDS
ENDATA
"""
    with tempfile.NamedTemporaryFile(suffix=".mps", mode="w", delete=False) as f:
        f.write(mps_content)
        mps_path = f.name
    try:
        lp = read_mps(mps_path)
        # L row with range r=2 means: 2x + y <= 6 AND 2x + y >= 6 - 2 = 4
        # So there should be 2 constraints for R1
        r1_constraints = [c for c in lp.constraints if c.get("name", "").startswith("R1")]
        assert len(r1_constraints) == 2, \
            f"expected 2 constraints from RANGES, got {len(r1_constraints)}"
    finally:
        os.unlink(mps_path)


# Bug 6: Reduced costs for basic variables should be 0
def test_bug_reduced_costs_basic_vars():
    """Basic variables should have reduced cost 0."""
    lp = LPProblem(
        name="rc_test", objective="max",
        variables=("x", "y"),
        objective_coeffs={"x": 3, "y": 2},
        constraints=[
            {"coeffs": {"x": 1, "y": 1}, "relation": "<=", "rhs": 4, "name": "c0"},
            {"coeffs": {"x": 2, "y": 1}, "relation": "<=", "rhs": 6, "name": "c1"},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    # x and y are both basic (positive values), so their reduced costs should be ~0
    assert abs(res.reduced_costs.get("x", 999)) < 1e-6, \
        f"basic var x should have rc=0, got {res.reduced_costs.get('x')}"
    assert abs(res.reduced_costs.get("y", 999)) < 1e-6, \
        f"basic var y should have rc=0, got {res.reduced_costs.get('y')}"


# Bug 7: Empty constraint coefficients dict should not crash
def test_bug_empty_coeffs():
    """A constraint with empty coeffs dict should work (0 <= rhs)."""
    lp = LPProblem(
        name="empty", objective="max",
        variables=("x",),
        objective_coeffs={"x": 1},
        constraints=[
            {"coeffs": {}, "relation": "<=", "rhs": 5, "name": "trivial"},
            {"coeffs": {"x": 1}, "relation": "<=", "rhs": 3, "name": "real"},
        ],
    )
    res = SimplexSolver().solve(lp)
    assert res.status is LPStatus.OPTIMAL
    assert res.objective_value == pytest.approx(3.0, abs=1e-6)