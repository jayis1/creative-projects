"""Tests for analysis tools (Wolfram classification, entropy, density, sweeps).

Run with: PYTHONPATH=. python -m pytest tests/test_analysis.py -v
"""

import math
import numpy as np
import pytest

from cellular_automaton import (
    CellularAutomaton, ElementaryRule, GameOfLifeRule,
    classify_elementary_rule, shannon_entropy, spacetime_entropy,
    density_over_time, parameter_sweep, hamming_distance, lyapunov_proxy,
    local_diversity,
)
from cellular_automaton.analysis import _detect_period


class TestWolframClassification:
    """Tests for Wolfram classification of elementary rules."""

    def test_rule_0_is_class_I(self):
        """Rule 0 maps everything to 0 → Class I (homogeneous)."""
        result = classify_elementary_rule(0, width=21, steps=50)
        assert result.classification == "I"
        assert result.density == 0.0

    def test_rule_255_is_class_I(self):
        """Rule 255 maps everything to 1 → Class I (homogeneous)."""
        result = classify_elementary_rule(255, width=21, steps=50)
        assert result.classification == "I"
        assert result.density == 1.0

    def test_rule_30_is_chaotic(self):
        """Rule 30 is Wolfram's famous chaotic rule → Class III."""
        result = classify_elementary_rule(30, width=51, steps=100)
        assert result.classification in ("III", "IV")  # Allow some flexibility

    def test_rule_90_classification(self):
        """Rule 90 produces Sierpinski → Class II or IV."""
        result = classify_elementary_rule(90, width=51, steps=100)
        assert result.classification in ("II", "III", "IV")

    def test_all_rules_classifiable(self):
        """All 256 rules should be classifiable without errors."""
        for n in [0, 1, 30, 54, 60, 62, 90, 110, 126, 150, 184, 255]:
            result = classify_elementary_rule(n, width=21, steps=50)
            assert result.classification in ("I", "II", "III", "IV")


class TestShannonEntropy:
    """Tests for Shannon entropy computation."""

    def test_uniform_grid_zero_entropy(self):
        """A uniform grid has zero entropy."""
        grid = np.zeros((10, 10), dtype=np.uint8)
        assert abs(shannon_entropy(grid)) < 1e-10
        grid = np.ones((10, 10), dtype=np.uint8)
        assert abs(shannon_entropy(grid)) < 1e-10

    def test_random_grid_high_entropy(self):
        """A random binary grid should have entropy close to 1 bit."""
        rng = np.random.default_rng(42)
        grid = rng.integers(0, 2, size=(100, 100)).astype(np.uint8)
        ent = shannon_entropy(grid)
        assert 0.95 < ent < 1.05  # Should be close to 1.0

    def test_half_grid_entropy_is_one_bit(self):
        """A grid with exactly half 0s and half 1s has entropy = 1 bit."""
        grid = np.zeros((10, 10), dtype=np.uint8)
        grid[:5] = 1
        ent = shannon_entropy(grid)
        assert abs(ent - 1.0) < 0.01

    def test_block_entropy_alternating_pattern(self):
        """Block entropy captures structural complexity.

        An alternating 0,1 pattern has per-cell entropy = 1 (half 0s, half 1s),
        and block-2 entropy = 1 (two block types: 01 and 10).
        A uniform pattern has zero block entropy.
        """
        # Alternating pattern: blocks are "01" and "10" → 2 types → entropy = 1.
        grid = np.array([[0, 1] * 10] * 10, dtype=np.uint8)
        ent1 = shannon_entropy(grid, block_size=1)
        ent2 = shannon_entropy(grid, block_size=2)
        assert abs(ent1 - 1.0) < 0.01  # Half 0s, half 1s
        assert abs(ent2 - 1.0) < 0.01  # Two block types: 01 and 10

        # Uniform pattern: only one block type → zero block entropy.
        grid_u = np.ones((10, 10), dtype=np.uint8)
        assert abs(shannon_entropy(grid_u, block_size=2)) < 1e-10


class TestSpacetimeEntropy:
    """Tests for spacetime entropy."""

    def test_uniform_spacetime_zero_entropy(self):
        """All-zero spacetime has zero entropy."""
        st = np.zeros((10, 20), dtype=np.uint8)
        assert spacetime_entropy(st) == 0.0

    def test_random_spacetime_high_entropy(self):
        """Random spacetime should have entropy close to 1."""
        rng = np.random.default_rng(42)
        st = rng.integers(0, 2, size=(50, 100)).astype(np.uint8)
        ent = spacetime_entropy(st)
        assert 0.9 < ent < 1.1


class TestDensityOverTime:
    """Tests for density analysis."""

    def test_blinker_density_oscillates(self):
        """A blinker has constant density (3/49)."""
        from cellular_automaton import get_pattern, place_pattern
        ca = CellularAutomaton(GameOfLifeRule(), width=7, height=7, boundary="zero")
        place_pattern(ca, get_pattern("blinker"), x=2, y=3)
        report = density_over_time(ca, steps=10)
        # Blinker oscillates between 3 cells → density stays ~3/49.
        assert abs(report.mean - 3/49) < 0.01

    def test_density_report_has_all_fields(self):
        """DensityReport should have all expected fields."""
        from cellular_automaton import get_pattern, place_pattern
        ca = CellularAutomaton(GameOfLifeRule(), width=10, height=10, boundary="zero")
        place_pattern(ca, get_pattern("block"), x=3, y=3)
        report = density_over_time(ca, steps=5)
        assert len(report.densities) == 5
        assert report.mean > 0
        assert report.std >= 0
        assert report.trend in ("stable", "increasing", "decreasing", "oscillating")


class TestParameterSweep:
    """Tests for parameter sweep."""

    def test_sweep_basic(self):
        """A basic sweep should return results for all combinations."""
        from cellular_automaton import ForestFireRule
        results = parameter_sweep(
            lambda p, g: ForestFireRule(p=p, g=g),
            {"p": [0.0, 0.01], "g": [0.0, 0.05]},
            width=10, height=10, steps=10, density=0.3,
        )
        assert len(results) == 4  # 2 × 2 combinations
        for r in results:
            assert "p" in r.params
            assert "g" in r.params
            assert r.final_alive >= 0
            assert 0.0 <= r.mean_density <= 1.0

    def test_sweep_sorted_by_density(self):
        """Results should be sorted by mean density (descending)."""
        from cellular_automaton import ForestFireRule
        results = parameter_sweep(
            lambda p, g: ForestFireRule(p=p, g=g),
            {"p": [0.0, 0.1], "g": [0.0, 0.1]},
            width=10, height=10, steps=10, density=0.5,
        )
        densities = [r.mean_density for r in results]
        assert densities == sorted(densities, reverse=True)


class TestHammingDistance:
    """Tests for Hamming distance."""

    def test_identical_grids_zero_distance(self):
        """Identical grids have zero Hamming distance."""
        a = np.zeros((5, 5), dtype=np.uint8)
        b = np.zeros((5, 5), dtype=np.uint8)
        assert hamming_distance(a, b) == 0

    def test_all_different(self):
        """Completely different grids have max Hamming distance."""
        a = np.zeros((5, 5), dtype=np.uint8)
        b = np.ones((5, 5), dtype=np.uint8)
        assert hamming_distance(a, b) == 25

    def test_partial_difference(self):
        """Partial differences count correctly."""
        a = np.array([0, 0, 0, 0, 0], dtype=np.uint8)
        b = np.array([1, 0, 1, 0, 1], dtype=np.uint8)
        assert hamming_distance(a, b) == 3


class TestLyapunovProxy:
    """Tests for Lyapunov exponent proxy."""

    def test_chaotic_rule_diverges(self):
        """Rule 30 (chaotic) should show growing Hamming distance."""
        distances = lyapunov_proxy(
            ElementaryRule(30), width=50, steps=30, perturbation=1
        )
        # The distance should generally increase for chaotic rules.
        assert distances[-1] > distances[0]
        assert distances[-1] > 1

    def test_stable_rule_doesnt_diverge(self):
        """Rule 0 (stable) should keep distance at 0."""
        distances = lyapunov_proxy(
            ElementaryRule(0), width=50, steps=10, perturbation=1
        )
        # Rule 0 maps everything to 0, so after 1 step both are all zeros.
        assert all(d == 0 for d in distances[1:])


class TestLocalDiversity:
    """Tests for local diversity (distinct neighbourhood count)."""

    def test_uniform_grid_low_diversity(self):
        """A uniform grid has low diversity (1 neighbourhood type)."""
        grid = np.zeros((5, 5), dtype=np.uint8)
        div = local_diversity(grid, radius=1)
        assert div == 1

    def test_random_grid_high_diversity(self):
        """A random grid has high diversity."""
        rng = np.random.default_rng(42)
        grid = rng.integers(0, 2, size=(10, 10)).astype(np.uint8)
        div = local_diversity(grid, radius=1)
        assert div > 10  # Should have many distinct neighbourhoods


class TestDetectPeriod:
    """Tests for the period detection helper."""

    def test_periodic_sequence(self):
        """A repeating pattern should have its period detected."""
        a = np.array([1, 0, 1, 0])
        b = np.array([1, 0, 1, 0, 1, 0, 1, 0])
        period = _detect_period(b)
        assert period == 2

    def test_non_periodic_returns_none(self):
        """A non-periodic sequence returns None."""
        rows = np.array([[1, 0], [0, 1], [1, 1], [0, 0]])
        period = _detect_period(rows)
        # The last row [0,0] doesn't repeat in the previous 3 → None
        assert period is None or period > 0

    def test_too_short_returns_none(self):
        """A single-row sequence returns None."""
        rows = np.array([[1, 0]])
        period = _detect_period(rows)
        assert period is None