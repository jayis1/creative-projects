"""Tests for continuous cellular automata (reaction-diffusion models)."""

import pytest
import numpy as np

from cellular_automaton import (
    GrayScott, FitzHughNagumo, ContinuousCA,
    GRAY_SCOTT_PRESETS, CONTINUOUS_MODELS,
    get_continuous_model, is_continuous_model,
    render_continuous_ascii,
)


class TestGrayScott:
    def test_construction(self):
        gs = GrayScott(50, 50)
        assert gs.width == 50
        assert gs.height == 50
        assert gs.n_species == 2
        assert gs.states.shape == (2, 50, 50)
        # Default: u=1, v=0 (quiescent).
        assert np.allclose(gs.states[0], 1.0)
        assert np.allclose(gs.states[1], 0.0)

    def test_invalid_dimensions(self):
        with pytest.raises(ValueError):
            GrayScott(-1, 50)
        with pytest.raises(ValueError):
            GrayScott(50, 0)

    def test_step_changes_state(self):
        gs = GrayScott(30, 30, F=0.025, k=0.06)
        gs.seed_square(15, 15, 5)
        before = gs.states.copy()
        gs.step(10)
        assert not np.allclose(before, gs.states)

    def test_quiescent_stays(self):
        """With no seed, a quiescent grid should stay quiescent."""
        gs = GrayScott(20, 20, F=0.025, k=0.06)
        gs.step(50)
        # u should stay ~1, v ~0 (no reaction without v).
        assert np.allclose(gs.states[0], 1.0, atol=1e-6)
        assert np.allclose(gs.states[1], 0.0, atol=1e-6)

    def test_seed_square(self):
        gs = GrayScott(40, 40)
        gs.seed_square(20, 20, 5)
        # The seeded area should have v > 0.
        assert gs.states[1, 15:25, 15:25].max() > 0.0
        # Outside should still be ~0.
        assert gs.states[1, 0, 0] < 0.01

    def test_seed_random(self):
        gs = GrayScott(40, 40)
        gs.seed_random(n_seeds=5, seed=42)
        assert gs.states[1].max() > 0.0

    def test_randomize(self):
        gs = GrayScott(30, 30)
        gs.randomize(seed=42)
        assert gs.states[1].max() > 0.0

    def test_presets(self):
        for name in GRAY_SCOTT_PRESETS:
            gs = GrayScott.from_preset(name, width=20, height=20)
            assert isinstance(gs, GrayScott)

    def test_unknown_preset(self):
        with pytest.raises(ValueError):
            GrayScott.from_preset("nonexistent", 20, 20)

    def test_step_count(self):
        gs = GrayScott(20, 20)
        gs.step(7)
        assert gs.step_count == 7

    def test_values_in_range(self):
        """Concentrations should stay in [0, 1] after many steps."""
        gs = GrayScott(30, 30, F=0.025, k=0.06)
        gs.seed_square(15, 15, 5)
        gs.step(200)
        assert gs.states.min() >= 0.0
        assert gs.states.max() <= 1.0

    def test_serialization(self):
        gs = GrayScott(20, 20, F=0.03, k=0.055)
        gs.seed_square(10, 10, 4)
        gs.step(10)
        data = gs.to_dict()
        gs2 = GrayScott.from_dict(data)
        assert gs2.step_count == 10
        assert np.allclose(gs.states, gs2.states)


class TestFitzHughNagumo:
    def test_construction(self):
        fhn = FitzHughNagumo(50, 50)
        assert fhn.width == 50
        assert fhn.n_species == 2

    def test_step_changes_state(self):
        fhn = FitzHughNagumo(30, 30)
        fhn.seed_spiral(15, 15)
        before = fhn.states.copy()
        fhn.step(10)
        assert not np.allclose(before, fhn.states)

    def test_spiral_seed(self):
        fhn = FitzHughNagumo(40, 40)
        fhn.seed_spiral(20, 20)
        # The voltage field should have non-zero values.
        assert fhn.states[0].max() > 0.5
        assert fhn.states[0].min() < -0.5

    def test_randomize(self):
        fhn = FitzHughNagumo(30, 30)
        fhn.randomize(seed=42)
        assert fhn.states[0].std() > 0.1


class TestContinuousRendering:
    def test_render_ascii(self):
        field = np.random.default_rng(42).random((10, 20))
        result = render_continuous_ascii(field)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "\n" in result

    def test_render_ascii_custom_chars(self):
        field = np.array([[0.0, 0.5, 1.0]])
        result = render_continuous_ascii(field, chars=" .#")
        lines = result.split("\n")
        assert lines[0][0] == " "
        assert lines[0][2] == "#"

    def test_render_ascii_vmin_vmax(self):
        field = np.array([[1.0, 2.0, 3.0]])
        result = render_continuous_ascii(field, chars=" .#", vmin=1.0, vmax=3.0)
        lines = result.split("\n")
        assert lines[0][0] == " "
        assert lines[0][2] == "#"

    def test_render_1d(self):
        field = np.array([0.0, 0.5, 1.0])
        result = render_continuous_ascii(field)
        assert isinstance(result, str)


class TestRegistry:
    def test_get_model(self):
        gs = get_continuous_model("GrayScott", width=20, height=20)
        assert isinstance(gs, GrayScott)

    def test_get_model_case_insensitive(self):
        fhn = get_continuous_model("fitzhughnagumo", width=20, height=20)
        assert isinstance(fhn, FitzHughNagumo)

    def test_unknown_model(self):
        with pytest.raises(KeyError):
            get_continuous_model("Nonexistent", width=20, height=20)

    def test_is_continuous_model(self):
        assert is_continuous_model("GrayScott")
        assert is_continuous_model("grayscott")
        assert not is_continuous_model("GameOfLife")

    def test_models_registry(self):
        assert "GrayScott" in CONTINUOUS_MODELS
        assert "FitzHughNagumo" in CONTINUOUS_MODELS