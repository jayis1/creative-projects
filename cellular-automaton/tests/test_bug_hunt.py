"""Bug hunt tests for the cellular automaton simulator.

Each test verifies a suspected bug before the fix, then confirms the fix works.
Run with: PYTHONPATH=. python -m pytest tests/test_bug_hunt.py -v
"""

import json
import os
import sys
import tempfile

import numpy as np
import pytest

from cellular_automaton import (
    CellularAutomaton, ElementaryRule, GameOfLifeRule, CustomRule,
    get_pattern, place_pattern, parse_rle,
    render_ascii, render_spacetime_ascii,
)
from cellular_automaton.rules import RULES, get_rule, parse_bx_sx_notation
from cellular_automaton.vectorized import (
    step_elementary_vectorized, step_life_vectorized, wolfram_rule_table,
    neighbour_sum_2d,
)


# ===========================================================================
# Bug 1: "reflect" boundary inconsistency between 1D and 2D paths
# ===========================================================================

class TestReflectBoundary:
    """The 1D vectorized 'reflect' uses edge/clamp (ghost=edge cell),
    while 2D and generic paths use numpy 'reflect' (ghost=second-from-edge).
    These are different boundary conditions and should be consistent."""

    def test_reflect_1d_vs_generic_consistency(self):
        """1D vectorized path and generic fallback should give the same
        result for 'reflect' boundary on the same rule."""
        # Rule 90 (Sierpinski) with reflect boundary.
        # Use a grid where the difference would show.
        width = 7
        # Vectorized path
        ca_fast = CellularAutomaton(
            ElementaryRule(90), width=width, boundary="reflect"
        )
        ca_fast.set_grid([0, 0, 1, 0, 0, 0, 0])

        # Generic path: use a CustomRule that mimics Rule 90
        def rule90_func(nb):
            left, centre, right = int(nb[0]), int(nb[1]), int(nb[2])
            return left ^ right  # XOR = Rule 90

        ca_generic = CellularAutomaton(
            CustomRule(rule90_func, radius=1, dimensions=1, name="Rule90custom"),
            width=width, boundary="reflect",
        )
        ca_generic.set_grid([0, 0, 1, 0, 0, 0, 0])

        ca_fast.step(3)
        ca_generic.step(3)

        # These should be the same if 'reflect' is consistent.
        # Before the fix, they differ at the edges.
        assert np.array_equal(ca_fast.grid, ca_generic.grid), (
            f"1D vectorized and generic 'reflect' boundary disagree:\n"
            f"  fast:   {ca_fast.grid.tolist()}\n"
            f"  generic: {ca_generic.grid.tolist()}"
        )

    def test_reflect_2d_edge_cell_neighbour(self):
        """Under 'reflect' boundary, a cell at the edge should see itself
        as its out-of-bounds neighbour (zero-gradient / Neumann condition)."""
        grid = np.array([[1, 0, 0]], dtype=np.uint8)
        # With reflect (edge/clamp), cell 0's left neighbour = cell 0 = 1.
        # So neighbourhood of cell 0 is (1, 1, 0) -> Rule 90: 1 XOR 0 = 1.
        # With numpy reflect, cell 0's left neighbour = cell 1 = 0.
        # So neighbourhood of cell 0 is (0, 1, 0) -> Rule 90: 0 XOR 0 = 0.
        result = step_elementary_vectorized(
            grid[0], wolfram_rule_table(90), mode="reflect"
        )
        # If reflect = edge/clamp: cell 0 stays 1.
        assert result[0] == 1, (
            "reflect boundary should make edge cell see itself as neighbour"
        )


# ===========================================================================
# Bug 2: Incorrect births/deaths statistics formula
# ===========================================================================

class TestBirthsDeathsStats:
    """The total_births and total_deaths formula in run() is incorrect."""

    def test_births_deaths_basic(self):
        """A blinker oscillates between 3 cells (horizontal) and 3 cells
        (vertical). Each step, 2 cells die and 2 are born (changed=4,
        alive_diff=0). So births=2, deaths=2 per step."""
        ca = CellularAutomaton(GameOfLifeRule(), width=5, height=5)
        place_pattern(ca, get_pattern("blinker"), x=1, y=2)
        stats = ca.run(2)
        # After 2 steps (one full cycle), we should have:
        # 2 steps × 2 births/step = 4 births, 4 deaths
        assert stats.total_births == 4, (
            f"Expected 4 births over 2 blinker steps, got {stats.total_births}"
        )
        assert stats.total_deaths == 4, (
            f"Expected 4 deaths over 2 blinker steps, got {stats.total_deaths}"
        )

    def test_births_deaths_net_change(self):
        """An L-shape (3 cells) evolves into a 2x2 block (4 cells):
        all 3 original cells survive (each has 2 neighbours in S2),
        and 1 new cell is born at the empty corner (3 neighbours = B3).
        So births=1, deaths=0."""
        ca = CellularAutomaton(GameOfLifeRule(), width=5, height=5, boundary="zero")
        ca.set_cell(1, 1, 1)
        ca.set_cell(2, 1, 1)
        ca.set_cell(1, 2, 1)
        stats = ca.run(1)
        assert stats.total_births == 1, (
            f"Expected 1 birth, got {stats.total_births}"
        )
        assert stats.total_deaths == 0, (
            f"Expected 0 deaths, got {stats.total_deaths}"
        )
        assert stats.final_alive == 4, (
            f"Expected 4 final alive, got {stats.final_alive}"
        )


# ===========================================================================
# Bug 3: from_dict deserialization fails for custom-named GameOfLife rules
# ===========================================================================

class TestSerialization:
    """from_dict uses get_rule() which raises KeyError, but the code
    checks `if rule is None` which never triggers. So deserializing
    a custom Bxx/Sxx rule stored by name fails."""

    def test_roundtrip_custom_named_rule(self):
        """A GameOfLifeRule with a custom name (e.g. from Bxx/Sxx parsing)
        should survive serialization round-trip."""
        rule = parse_bx_sx_notation("B36/S23")
        ca = CellularAutomaton(rule, width=10, height=5)
        ca.randomize(0.3, seed=42)
        ca.step(3)

        d = ca.to_dict()
        # The rule name is "B36/S23" — not in the RULES registry by that name.
        assert d["rule"] == "B36/S23"

        # This should not raise KeyError.
        ca2 = CellularAutomaton.from_dict(d)
        assert np.array_equal(ca.grid, ca2.grid), "Grid mismatch after round-trip"
        assert ca2.rule.name == "B36/S23"

    def test_roundtrip_standard_rule(self):
        """Standard rules should round-trip fine."""
        ca = CellularAutomaton(ElementaryRule(30), width=10)
        ca.center_seed()
        ca.step(5)
        ca2 = CellularAutomaton.from_dict(ca.to_dict())
        assert np.array_equal(ca.grid, ca2.grid)


# ===========================================================================
# Bug 4: render_png fallback creates wrong filename in animation
# ===========================================================================

class TestRenderPngFallback:
    """When PIL is not available, render_png writes to path + '.ppm'.
    In animation, this creates files like 'frame_00000.png.ppm' instead
    of 'frame_00000.png'."""

    def test_png_fallback_extension(self):
        """render_png should write to the exact path given, not path+'.ppm'."""
        from cellular_automaton.visualizer import render_png
        grid = np.array([[1, 0], [0, 1]], dtype=np.uint8)

        with tempfile.TemporaryDirectory() as tmpdir:
            outpath = os.path.join(tmpdir, "test.png")
            render_png(grid, outpath, cell_size=2)
            # The file should be at outpath, not outpath + ".ppm"
            if not os.path.exists(outpath):
                ppm_path = outpath + ".ppm"
                pytest.fail(
                    f"render_png wrote to {ppm_path} instead of {outpath}. "
                    f"PIL not available, fallback creates wrong filename."
                )


# ===========================================================================
# Bug 5: fixed_value > 1 causes IndexError in elementary vectorized path
# ===========================================================================

class TestFixedValueOverflow:
    """If fixed_value is set to a value > 1 (or any non-binary value),
    the elementary vectorized path produces an index > 7, causing an
    IndexError on the 8-element lookup table."""

    def test_fixed_value_1_elementary(self):
        """fixed_value=1 should work correctly (all boundary cells alive)."""
        ca = CellularAutomaton(
            ElementaryRule(90), width=5, boundary="fixed", fixed_value=1
        )
        ca.set_grid([0, 1, 0, 1, 0])
        # Should not raise
        ca.step(3)

    def test_fixed_value_large_no_crash(self):
        """fixed_value > 1 should not crash — it should be clamped to binary."""
        ca = CellularAutomaton(
            ElementaryRule(90), width=5, boundary="fixed", fixed_value=5
        )
        ca.set_grid([0, 1, 0, 1, 0])
        try:
            ca.step(1)
        except IndexError:
            pytest.fail(
                "fixed_value=5 caused IndexError in elementary vectorized path"
            )


# ===========================================================================
# Bug 6: Pulsar pattern correctness
# ===========================================================================

class TestPulsarPattern:
    """Verify the pulsar is a period-3 oscillator (returns to same state
    after 3 steps)."""

    def test_pulsar_period3(self):
        ca = CellularAutomaton(GameOfLifeRule(), width=17, height=17)
        place_pattern(ca, get_pattern("pulsar"), x=2, y=2)
        initial = ca.grid.copy()
        ca.step(3)
        assert np.array_equal(ca.grid, initial), (
            "Pulsar should return to initial state after 3 steps (period 3)"
        )


# ===========================================================================
# Bug 7: Pentadecathlon pattern correctness
# ===========================================================================

class TestPentadecathlonPattern:
    """Verify the pentadecathlon is a period-15 oscillator."""

    def test_pentadecathlon_period15(self):
        """Verify the pentadecathlon is a period-15 oscillator."""
        # The pattern spans 10×3; use a large enough grid with zero boundary.
        ca = CellularAutomaton(GameOfLifeRule(), width=25, height=15, boundary="zero")
        place_pattern(ca, get_pattern("pentadecathlon"), x=8, y=6)
        initial = ca.grid.copy()
        ca.step(15)
        assert np.array_equal(ca.grid, initial), (
            "Pentadecathlon should return to initial state after 15 steps"
        )


# ===========================================================================
# Bug 8: Beacon pattern correctness (period 2)
# ===========================================================================

class TestBeaconPattern:
    """Verify the beacon is a period-2 oscillator."""

    def test_beacon_period2(self):
        ca = CellularAutomaton(GameOfLifeRule(), width=6, height=6, boundary="zero")
        place_pattern(ca, get_pattern("beacon"), x=1, y=1)
        initial = ca.grid.copy()
        ca.step(2)
        assert np.array_equal(ca.grid, initial), (
            "Beacon should return to initial state after 2 steps"
        )


# ===========================================================================
# Additional correctness tests
# ===========================================================================

class TestElementaryRuleCorrectness:
    """Verify known elementary rule behaviours."""

    def test_rule90_sierpinski(self):
        """Rule 90 from a single centre cell produces a Sierpinski triangle."""
        ca = CellularAutomaton(ElementaryRule(90), width=31, boundary="zero")
        ca.center_seed()
        ca.step(15)
        st = ca.get_spacetime_array()
        # Row 15 should have the Sierpinski pattern.
        # Rule 90 = XOR of left and right neighbours.
        # With zero boundary, row n should match Pascal's triangle mod 2.
        row = st[15]
        # Verify against manual computation
        expected = np.zeros(31, dtype=np.uint8)
        prev = np.zeros(31, dtype=np.uint8)
        prev[15] = 1
        for _ in range(15):
            nxt = np.zeros(31, dtype=np.uint8)
            for i in range(31):
                l = prev[i-1] if i > 0 else 0
                r = prev[i+1] if i < 30 else 0
                nxt[i] = l ^ r
            prev = nxt
        assert np.array_equal(row, prev), "Rule 90 should match XOR computation"

    def test_rule184_traffic(self):
        """Rule 184 models traffic flow — cars move right when the space ahead
        is free.  For a block of 4 consecutive 1s, the rightmost car moves
        into the empty space (111→1, 110→0, 011→1)."""
        ca = CellularAutomaton(ElementaryRule(184), width=10, boundary="zero")
        ca.set_grid([0, 0, 1, 1, 1, 1, 0, 0, 0, 0])
        ca.step(1)
        # Rule 184: 111->1, 110->0, 101->1, 100->1, 011->1, 010->0, 001->0, 000->0
        # pos 2: (0,1,1)->1, pos 3: (1,1,1)->1, pos 4: (1,1,1)->1,
        # pos 5: (1,1,0)->0, pos 6: (1,0,0)->1
        expected = [0, 0, 1, 1, 1, 0, 1, 0, 0, 0]
        assert ca.grid[0].tolist() == expected, (
            f"Rule 184 traffic: expected {expected}, got {ca.grid[0].tolist()}"
        )


class TestGliderMovement:
    """Verify the glider moves diagonally."""

    def test_glider_moves_1_1_per_4_steps(self):
        ca = CellularAutomaton(GameOfLifeRule(), width=20, height=20, boundary="zero")
        place_pattern(ca, get_pattern("glider"), x=5, y=5)
        initial = ca.grid.copy()
        ca.step(4)
        # The glider should have moved 1 cell down and 1 cell right.
        expected = np.zeros((20, 20), dtype=np.uint8)
        for dx, dy in get_pattern("glider"):
            expected[5 + dy + 1, 5 + dx + 1] = 1
        assert np.array_equal(ca.grid, expected), (
            "Glider should move 1 cell down-right per 4 steps"
        )


class TestCycleDetection:
    """Verify cycle detection works for known oscillators."""

    def test_blinker_cycle_length2(self):
        ca = CellularAutomaton(GameOfLifeRule(), width=7, height=7, boundary="zero")
        place_pattern(ca, get_pattern("blinker"), x=2, y=3)
        stats = ca.run(20)
        assert stats.cycle_detected, "Blinker should be detected as cyclic"
        assert stats.cycle_length == 2, (
            f"Blinker cycle length should be 2, got {stats.cycle_length}"
        )

    def test_block_stable(self):
        ca = CellularAutomaton(GameOfLifeRule(), width=6, height=6)
        place_pattern(ca, get_pattern("block"), x=2, y=2)
        stats = ca.run(10)
        assert stats.stable, "Block should be stable"
        assert stats.final_alive == 4


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))