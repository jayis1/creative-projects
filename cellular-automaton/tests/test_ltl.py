"""Tests for Larger-than-Life (LtL) cellular automata."""

import pytest
import numpy as np

from cellular_automaton import (
    CellularAutomaton, LargerThanLifeRule, parse_ltl_notation, LTL_PRESETS,
)
from cellular_automaton.ltl import LTL_PRESETS as _LTL


class TestLtlParsing:
    def test_parse_basic_notation(self):
        rule = parse_ltl_notation("B5678/S45678/R5")
        assert rule is not None
        assert rule.radius == 5
        assert rule.birth == frozenset({5, 6, 7, 8})
        assert rule.survive == frozenset({4, 5, 6, 7, 8})

    def test_parse_radius_2(self):
        rule = parse_ltl_notation("B3/S23/R2")
        assert rule is not None
        assert rule.radius == 2
        assert rule.birth == frozenset({3})
        assert rule.survive == frozenset({2, 3})

    def test_parse_case_insensitive(self):
        rule = parse_ltl_notation("b5678/s45678/r5")
        assert rule is not None
        assert rule.radius == 5

    def test_parse_invalid_returns_none(self):
        assert parse_ltl_notation("invalid") is None
        assert parse_ltl_notation("B3/S23") is None  # missing R
        assert parse_ltl_notation("") is None

    def test_parse_with_spaces(self):
        rule = parse_ltl_notation("  B3 / S23 / R2  ")
        assert rule is not None
        assert rule.radius == 2

    def test_rule_string_roundtrip(self):
        rule = parse_ltl_notation("B5678/S45678/R5")
        rs = rule.rule_string()
        parsed = parse_ltl_notation(rs)
        assert parsed is not None
        assert parsed.radius == rule.radius
        assert parsed.birth == rule.birth
        assert parsed.survive == rule.survive


class TestLtlRule:
    def test_invalid_radius(self):
        with pytest.raises(ValueError):
            LargerThanLifeRule((3,), (23,), radius=0)

    def test_radius_1_matches_life(self):
        """LtL with R1, B3/S23 should match Conway's Life."""
        rule = LargerThanLifeRule((3,), (2, 3), radius=1, name="LifeR1")
        ca = CellularAutomaton(rule, width=10, height=10)
        # Place a blinker.
        ca.set_cell(4, 5, 1)
        ca.set_cell(5, 5, 1)
        ca.set_cell(6, 5, 1)
        ca.step()
        # Blinker should rotate to vertical.
        assert ca.grid[4, 5] == 1
        assert ca.grid[5, 5] == 1
        assert ca.grid[6, 5] == 1
        assert ca.grid[5, 4] == 0
        assert ca.grid[5, 6] == 0

    def test_step_produces_changes(self):
        rule = LTL_PRESETS["Boon"]
        ca = CellularAutomaton(rule, width=20, height=20)
        ca.randomize(0.3, seed=42)
        initial = ca.grid.copy()
        ca.step(5)
        assert not np.array_equal(initial, ca.grid)

    def test_quiescent_grid_stays(self):
        """An all-dead grid should stay dead."""
        rule = LargerThanLifeRule((5678,), (45678,), radius=3)
        ca = CellularAutomaton(rule, width=15, height=15)
        ca.step(10)
        assert ca.alive_count() == 0

    def test_presets_exist(self):
        assert "Boon" in LTL_PRESETS
        assert "Grenville" in LTL_PRESETS
        for name, rule in LTL_PRESETS.items():
            assert rule.radius >= 1

    def test_ltl_serialization_roundtrip(self):
        rule = parse_ltl_notation("B3/S23/R2")
        ca = CellularAutomaton(rule, width=10, height=10)
        ca.randomize(0.3, seed=42)
        ca.step(5)
        data = ca.to_dict()
        assert "B3/S23/R2" in data["rule"] or data["rule"].startswith("B3/S23/R2")
        ca2 = CellularAutomaton.from_dict(data)
        assert ca2.step_count == 5
        assert np.array_equal(ca.grid, ca2.grid)