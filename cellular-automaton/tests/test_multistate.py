"""Tests for multi-state cellular automata (Wireworld, Brian's Brain, etc.).

Run with: PYTHONPATH=. python -m pytest tests/test_multistate.py -v
"""

import numpy as np
import pytest

from cellular_automaton import (
    CellularAutomaton, WireworldRule, BriansBrainRule,
    ForestFireRule, CyclicRule, ImmigrationRule,
)
from cellular_automaton.multistate import (
    MULTISTATE_RULES, get_multistate_rule, is_multistate_rule,
    _moore_neighbour_count,
)


class TestWireworld:
    """Wireworld CA tests."""

    def test_electron_head_becomes_tail(self):
        """Head → Tail transition."""
        rule = WireworldRule()
        grid = np.array([[1]], dtype=np.uint8)  # single head
        new = rule.step(grid, mode="zero")
        assert new[0, 0] == WireworldRule.TAIL

    def test_electron_tail_becomes_conductor(self):
        """Tail → Conductor transition."""
        rule = WireworldRule()
        grid = np.array([[2]], dtype=np.uint8)  # single tail
        new = rule.step(grid, mode="zero")
        assert new[0, 0] == WireworldRule.CONDUCTOR

    def test_conductor_with_one_head_neighbour_becomes_head(self):
        """Conductor with exactly 1 head neighbour → Head."""
        rule = WireworldRule()
        # 3x3 grid: conductor at center, one head neighbour.
        grid = np.array([
            [0, 0, 0],
            [0, 3, 0],
            [1, 0, 0],
        ], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        assert new[1, 1] == WireworldRule.HEAD

    def test_conductor_with_three_head_neighbours_stays_conductor(self):
        """Conductor with 3 head neighbours stays conductor (needs 1 or 2)."""
        rule = WireworldRule()
        grid = np.array([
            [1, 1, 0],
            [0, 3, 0],
            [1, 0, 0],
        ], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        # Centre conductor has 3 head neighbours → stays conductor.
        assert new[1, 1] == WireworldRule.CONDUCTOR

    def test_empty_stays_empty(self):
        """Empty cells stay empty."""
        rule = WireworldRule()
        grid = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        assert np.all(new == 0)

    def test_wireworld_via_engine(self):
        """Wireworld runs through the engine correctly."""
        ca = CellularAutomaton(WireworldRule(), width=10, height=5, boundary="zero")
        # Set up a wire with an electron.
        for x in range(2, 8):
            ca.set_cell(x, 2, WireworldRule.CONDUCTOR)
        ca.set_cell(3, 2, WireworldRule.HEAD)
        ca.set_cell(2, 2, WireworldRule.TAIL)
        ca.step()
        # The head should have moved.
        assert ca.grid[2, 3] == WireworldRule.TAIL
        assert ca.grid[2, 4] == WireworldRule.HEAD

    def test_state_colors(self):
        """Wireworld should have state colors for all 4 states."""
        colors = WireworldRule().state_colors()
        assert set(colors.keys()) == {0, 1, 2, 3}
        for state, color in colors.items():
            assert len(color) == 3  # RGB


class TestBriansBrain:
    """Brian's Brain CA tests."""

    def test_alive_becomes_dying(self):
        """Alive → Dying."""
        rule = BriansBrainRule()
        grid = np.array([[1]], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        assert new[0, 0] == BriansBrainRule.DYING

    def test_dying_becomes_dead(self):
        """Dying → Dead."""
        rule = BriansBrainRule()
        grid = np.array([[2]], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        assert new[0, 0] == BriansBrainRule.DEAD

    def test_dead_with_two_alive_becomes_alive(self):
        """Dead cell with exactly 2 alive neighbours → Alive."""
        rule = BriansBrainRule()
        grid = np.array([
            [1, 0, 0],
            [0, 0, 0],
            [0, 0, 1],
        ], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        # Centre cell (1,1) has 2 alive neighbours → born.
        assert new[1, 1] == BriansBrainRule.ALIVE

    def test_dead_with_three_alive_stays_dead(self):
        """Dead cell with 3 alive neighbours stays dead (needs exactly 2)."""
        rule = BriansBrainRule()
        grid = np.array([
            [1, 1, 0],
            [0, 0, 0],
            [0, 1, 0],
        ], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        assert new[1, 1] == BriansBrainRule.DEAD


class TestForestFire:
    """Forest Fire CA tests."""

    def test_burning_becomes_empty(self):
        """Burning → Empty."""
        rule = ForestFireRule(p=0.0, g=0.0)
        grid = np.array([[2]], dtype=np.uint8)
        rng = np.random.default_rng(42)
        new = rule.step(grid, mode="zero", rng=rng)
        assert new[0, 0] == ForestFireRule.EMPTY

    def test_tree_next_to_burning_ignites(self):
        """Tree next to a burning cell ignites."""
        rule = ForestFireRule(p=0.0, g=0.0)
        grid = np.array([
            [2, 1, 0],
        ], dtype=np.uint8)
        rng = np.random.default_rng(42)
        new = rule.step(grid, mode="zero", rng=rng)
        assert new[0, 1] == ForestFireRule.BURNING

    def test_tree_spontaneous_ignition(self):
        """Trees can spontaneously ignite with probability p."""
        rule = ForestFireRule(p=1.0, g=0.0)  # p=1.0 → always ignite
        grid = np.array([[1]], dtype=np.uint8)
        rng = np.random.default_rng(42)
        new = rule.step(grid, mode="zero", rng=rng)
        assert new[0, 0] == ForestFireRule.BURNING

    def test_empty_grows_tree(self):
        """Empty cells grow trees with probability g."""
        rule = ForestFireRule(p=0.0, g=1.0)  # g=1.0 → always grow
        grid = np.array([[0]], dtype=np.uint8)
        rng = np.random.default_rng(42)
        new = rule.step(grid, mode="zero", rng=rng)
        assert new[0, 0] == ForestFireRule.TREE

    def test_forest_fire_via_engine(self):
        """Forest fire runs through the engine."""
        ca = CellularAutomaton(ForestFireRule(p=0.0, g=0.0), width=5, height=5, boundary="zero")
        ca.set_rng(42)
        ca.set_cell(2, 2, ForestFireRule.BURNING)
        ca.set_cell(3, 2, ForestFireRule.TREE)
        ca.step()
        assert ca.grid[2, 2] == ForestFireRule.EMPTY  # burned out
        assert ca.grid[2, 3] == ForestFireRule.BURNING  # ignited


class TestCyclic:
    """Cyclic CA tests."""

    def test_cell_advances_with_enough_next_state_neighbours(self):
        """Cell in state k advances to k+1 with enough neighbours in k+1."""
        rule = CyclicRule(n_states=3, threshold=2)
        # Centre cell is state 0, 3 neighbours in state 1.
        grid = np.array([
            [1, 1, 0],
            [1, 0, 0],
            [0, 0, 0],
        ], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        assert new[1, 1] == 1  # advanced from 0 to 1

    def test_cell_doesnt_advance_with_too_few_neighbours(self):
        """Cell stays in state k if too few neighbours in k+1."""
        rule = CyclicRule(n_states=3, threshold=3)
        grid = np.array([
            [1, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        assert new[1, 1] == 0  # stayed

    def test_cyclic_wraps_around(self):
        """State n-1 advances to state 0 (cyclic wrap)."""
        rule = CyclicRule(n_states=3, threshold=2)
        grid = np.array([
            [0, 0, 0],
            [0, 2, 0],
            [0, 0, 0],
        ], dtype=np.uint8)
        # Surround with state 0 (which is the "next" state for state 2).
        grid[0, 1] = 0
        grid[1, 0] = 0
        grid[1, 2] = 0
        grid[2, 1] = 0
        # Actually we need to place state 0 neighbours around the state 2 cell.
        # But they're already 0. With threshold=2 and 4 neighbours in state 0,
        # the state-2 cell should advance to state 0.
        new = rule.step(grid, mode="zero")
        assert new[1, 1] == 0

    def test_invalid_n_states(self):
        """n_states < 2 should raise."""
        with pytest.raises(ValueError):
            CyclicRule(n_states=1)

    def test_state_colors_rainbow(self):
        """Cyclic rule should generate rainbow colors."""
        colors = CyclicRule(n_states=5).state_colors()
        assert len(colors) == 5


class TestImmigration:
    """Immigration CA tests."""

    def test_survival_with_2_neighbours(self):
        """Alive cell with 2 neighbours survives."""
        rule = ImmigrationRule()
        grid = np.array([
            [0, 1, 0],
            [0, 1, 0],
            [0, 1, 0],
        ], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        # Centre cell (1,1) has 2 neighbours → survives.
        assert new[1, 1] == ImmigrationRule.A

    def test_birth_adopts_majority_color(self):
        """Dead cell born with 3 neighbours adopts majority colour."""
        rule = ImmigrationRule()
        # 3 neighbours: 2 of species A, 1 of species B → born as A.
        grid = np.array([
            [1, 1, 0],
            [0, 0, 0],
            [2, 0, 0],
        ], dtype=np.uint8)
        new = rule.step(grid, mode="zero")
        # Centre (1,1) has 3 neighbours (2 A, 1 B) → born as A.
        assert new[1, 1] == ImmigrationRule.A


class TestMultistateRegistry:
    """Registry and lookup tests."""

    def test_registry_has_all_rules(self):
        """All 5 multi-state rules should be in the registry."""
        assert "Wireworld" in MULTISTATE_RULES
        assert "BriansBrain" in MULTISTATE_RULES
        assert "ForestFire" in MULTISTATE_RULES
        assert "Cyclic" in MULTISTATE_RULES
        assert "Immigration" in MULTISTATE_RULES

    def test_get_multistate_rule_case_insensitive(self):
        """Rule lookup should be case-insensitive."""
        rule = get_multistate_rule("wireworld")
        assert isinstance(rule, WireworldRule)

    def test_get_multistate_rule_unknown_raises(self):
        """Unknown rule name should raise KeyError."""
        with pytest.raises(KeyError):
            get_multistate_rule("NonExistent")

    def test_is_multistate_rule(self):
        """is_multistate_rule should correctly identify multi-state rules."""
        assert is_multistate_rule("Wireworld")
        assert is_multistate_rule("briansbrain")
        assert not is_multistate_rule("GameOfLife")
        assert not is_multistate_rule("Rule30")

    def test_get_multistate_rule_with_kwargs(self):
        """Parameterized rules should accept kwargs."""
        rule = get_multistate_rule("ForestFire", p=0.01, g=0.1)
        assert rule.p == 0.01
        assert rule.g == 0.1


class TestMooreNeighbourCount:
    """Tests for the _moore_neighbour_count helper."""

    def test_single_cell_zero_neighbours(self):
        """A single 1 cell with zero boundary has 0 neighbours."""
        mask = np.array([[1]], dtype=np.int32)
        result = _moore_neighbour_count(mask, mode="zero")
        assert result[0, 0] == 0

    def test_two_adjacent_cells(self):
        """Two adjacent cells count each other as neighbours."""
        mask = np.array([[1, 1]], dtype=np.int32)
        result = _moore_neighbour_count(mask, mode="zero")
        assert result[0, 0] == 1  # cell 0 has 1 neighbour (cell 1)
        assert result[0, 1] == 1  # cell 1 has 1 neighbour (cell 0)

    def test_periodic_boundary(self):
        """Periodic boundary wraps around (2D Moore neighbours).

        For a 1-row grid [1,0,0,0,1] with periodic wrapping, cell 0 has
        neighbours that wrap both horizontally and vertically. The left
        neighbour wraps to cell 4 (value=1), and the top/bottom rows wrap
        to the same row, so the cell sees many copies of itself and cell 4.
        """
        mask = np.array([[1, 0, 0, 0, 1]], dtype=np.int32)
        result = _moore_neighbour_count(mask, mode="periodic")
        # Cell 0 has 5 live neighbours (cell 4 via left-wrap appears 3x
        # through top/bottom/same-row, cell 0 itself via top/bottom = 2x).
        assert result[0, 0] == 5