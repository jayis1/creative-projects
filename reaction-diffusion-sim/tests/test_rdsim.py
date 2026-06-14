#!/usr/bin/env python3
"""
Comprehensive test suite for the Reaction-Diffusion Pattern Simulator.

Organized with pytest for clean, discoverable test structure.
"""

import os
import sys
import tempfile
import json
from pathlib import Path

import numpy as np
import pytest

# Ensure package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rdsim.models import (
    gray_scott_react, fitzhugh_nagumo_react,
    gierer_meinhardt_react, brusselator_react, schnakenberg_react,
    get_model, MODELS, _clamp_field, register_model,
)
from rdsim.solver import (
    ReactionDiffusionSolver, apply_laplacian,
    LAPLACIAN_STENCIL, BoundaryCondition, SimulationEvent,
)
from rdsim.presets import get_preset, list_presets, ALL_PRESETS, register_preset
from rdsim.visualization import _select_field, _apply_colormap, save_frame_fast
from rdsim.config import SimulationConfig, load_config, PerturbationConfig, VisualizationConfig


# ──────────────────────────────────────────────────────
# Model Tests
# ──────────────────────────────────────────────────────

class TestGrayScott:
    """Tests for Gray-Scott model reaction kinetics."""

    def test_reaction_kinetics(self):
        u = np.array([[0.5, 0.3], [0.2, 0.9]])
        v = np.array([[0.5, 0.3], [0.2, 0.1]])
        params = {"F": 0.035, "k": 0.065}
        du, dv = gray_scott_react(u, v, params)
        assert du.shape == u.shape
        assert dv.shape == v.shape
        # At (0,0): uvv = 0.5*0.5*0.5 = 0.125
        # du = -0.125 + 0.035*(1-0.5) = -0.1075
        assert abs(du[0, 0] - (-0.1075)) < 1e-4
        # dv = 0.125 - (0.035+0.065)*0.5 = 0.075
        assert abs(dv[0, 0] - 0.075) < 1e-4

    def test_default_state(self):
        from rdsim.models import gray_scott_default_state
        u, v = gray_scott_default_state(32)
        assert u.shape == (32, 32)
        assert np.allclose(u, 1.0)
        assert np.allclose(v, 0.0)


class TestFitzHughNagumo:
    """Tests for FitzHugh-Nagumo model."""

    def test_reaction_kinetics(self):
        u = np.array([[0.0]])
        v = np.array([[0.0]])
        params = {"epsilon": 0.04, "beta": 0.5, "gamma": 1.0}
        du, dv = fitzhugh_nagumo_react(u, v, params)
        assert abs(du[0, 0]) < 1e-10
        assert abs(dv[0, 0] - 0.02) < 1e-10

    def test_fixed_point(self):
        from rdsim.models import fitzhugh_nagumo_default_state
        u, v = fitzhugh_nagumo_default_state(32, params={"beta": 0.5, "gamma": 1.0})
        u_mean, v_mean = u[0, 0], v[0, 0]
        du = u_mean - u_mean**3 / 3 - v_mean
        dv = 0.04 * (u_mean + 0.5 - v_mean)
        assert abs(du) < 0.1
        assert abs(dv) < 0.01


class TestGiererMeinhardt:
    """Tests for Gierer-Meinhardt model."""

    def test_division_by_zero_protection(self):
        u = np.array([[0.5]])
        v = np.array([[0.0]])
        params = {"rho": 0.001, "mu": 0.02}
        du, dv = gierer_meinhardt_react(u, v, params)
        assert not np.any(np.isnan(du))
        assert not np.any(np.isinf(du))


class TestBrusselator:
    """Tests for Brusselator model."""

    def test_stability_clamping(self):
        u = np.array([[50.0]])
        v = np.array([[50.0]])
        params = {"A": 1.0, "B": 3.0}
        du, dv = brusselator_react(u, v, params)
        assert np.all(np.isfinite(du))
        assert np.all(np.isfinite(dv))

    def test_default_state_uses_params(self):
        from rdsim.models import brusselator_default_state
        u, v = brusselator_default_state(32, params={"A": 2.0, "B": 6.0})
        assert abs(u[0, 0] - 2.0) < 1e-10
        assert abs(v[0, 0] - 3.0) < 1e-10


class TestSchnakenberg:
    """Tests for Schnakenberg model."""

    def test_reaction_kinetics(self):
        u = np.array([[1.0]])
        v = np.array([[0.5]])
        params = {"a": 0.1, "b": 0.9}
        du, dv = schnakenberg_react(u, v, params)
        # du = 0.1 - 1.0 + 1.0*1.0*0.5 = -0.4
        assert abs(du[0, 0] - (-0.4)) < 1e-10

    def test_default_state(self):
        from rdsim.models import schnakenberg_default_state
        u, v = schnakenberg_default_state(32, params={"a": 0.1, "b": 0.9})
        # Steady state: u = a+b = 1.0, v = b/u^2 = 0.9
        assert abs(u[0, 0] - 1.0) < 1e-10
        assert abs(v[0, 0] - 0.9) < 1e-10


class TestModelRegistry:
    """Tests for model registry and registration."""

    def test_valid_names(self):
        for name in MODELS:
            config = get_model(name)
            assert "react" in config
            assert "defaults" in config

    def test_invalid_name(self):
        with pytest.raises(ValueError):
            get_model("nonexistent")

    def test_register_custom_model(self):
        def custom_react(u, v, params):
            return -u + v, u - v

        register_model(
            "custom-test",
            react_fn=custom_react,
            defaults={"Du": 0.1, "Dv": 0.2},
            default_state_fn=lambda n, params=None: (np.ones((n, n)), np.zeros((n, n))),
            perturbation_fn=lambda: {"type": "center_square", "size": 10},
            param_names=["Du", "Dv"],
            description="Test custom model",
        )
        assert "custom-test" in MODELS
        config = get_model("custom-test")
        assert config["description"] == "Test custom model"
        # Cleanup
        del MODELS["custom-test"]


class TestClampField:
    """Tests for the _clamp_field utility."""

    def test_basic_clamping(self):
        arr = np.array([[-1e7, 0.5, 1e7]])
        clamped = _clamp_field(arr, 0, 1)
        assert abs(clamped[0, 0] - 0.0) < 1e-10
        assert abs(clamped[0, 1] - 0.5) < 1e-10
        assert abs(clamped[0, 2] - 1.0) < 1e-10


# ──────────────────────────────────────────────────────
# Laplacian Tests
# ──────────────────────────────────────────────────────

class TestLaplacian:
    """Tests for Laplacian computation."""

    def test_constant_field_is_zero(self):
        field = np.ones((20, 20)) * 5.0
        lap = apply_laplacian(field, bc="periodic")
        assert np.allclose(lap, 0, atol=1e-10)

    def test_quadratic_field_is_constant(self):
        x = np.arange(32, dtype=np.float64)
        y = np.arange(32, dtype=np.float64)
        X, Y = np.meshgrid(x, y)
        field = X**2 + Y**2
        lap = apply_laplacian(field, bc="periodic")
        center = lap[5:-5, 5:-5]
        assert np.std(center) < 0.5

    def test_periodic_boundary(self):
        field = np.zeros((16, 16))
        field[8, 8] = 1.0
        lap = apply_laplacian(field, bc="periodic")
        assert lap[8, 8] < 0
        assert lap[7, 8] > 0

    def test_neumann_boundary(self):
        field = np.random.rand(16, 16)
        lap = apply_laplacian(field, bc="neumann")
        assert not np.any(np.isnan(lap))

    def test_dirichlet_boundary(self):
        field = np.random.rand(16, 16)
        lap = apply_laplacian(field, bc="dirichlet")
        assert not np.any(np.isnan(lap))

    def test_invalid_boundary(self):
        with pytest.raises(ValueError):
            apply_laplacian(np.ones((10, 10)), bc="invalid")


# ──────────────────────────────────────────────────────
# Solver Tests
# ──────────────────────────────────────────────────────

class TestSolverInit:
    """Tests for solver initialization."""

    def test_default_init(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        assert solver.u.shape == (64, 64)
        assert solver.v.shape == (64, 64)
        assert solver.step_count == 0
        assert solver.model_name == "gray-scott"

    def test_all_models(self):
        for model_name in MODELS:
            solver = ReactionDiffusionSolver(model_name, grid_size=32)
            assert solver.u.shape == (32, 32)

    def test_custom_params(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64,
                                          params={"F": 0.05, "k": 0.06})
        assert abs(solver.params["F"] - 0.05) < 1e-10
        assert abs(solver.params["k"] - 0.06) < 1e-10

    def test_invalid_model(self):
        with pytest.raises(ValueError):
            ReactionDiffusionSolver("nonexistent", grid_size=64)

    def test_invalid_grid_size(self):
        with pytest.raises(ValueError):
            ReactionDiffusionSolver("gray-scott", grid_size=2)


class TestSolverStep:
    """Tests for solver stepping."""

    def test_euler(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation()
        solver.step(10)
        assert solver.step_count == 10
        assert not np.any(np.isnan(solver.u))

    def test_rk2(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation()
        solver.step(10, method="rk2")
        assert solver.step_count == 10
        assert not np.any(np.isnan(solver.u))

    def test_rk4(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation()
        solver.step(10, method="rk4")
        assert solver.step_count == 10
        assert not np.any(np.isnan(solver.u))

    def test_invalid_method(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        with pytest.raises(ValueError):
            solver.step(1, method="invalid")

    def test_invalid_steps(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        with pytest.raises(ValueError):
            solver.step(0)

    def test_step_until(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation()
        solver.step(50)
        assert solver.step_count == 50
        solver.step_until(100)
        assert solver.step_count == 100
        solver.step_until(50)  # Should not go backwards
        assert solver.step_count == 100


class TestSolverState:
    """Tests for state management."""

    def test_get_set_state(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation()
        solver.step(100)
        u, v = solver.get_state()
        assert u.shape == (64, 64)

        new_u = np.ones((64, 64)) * 0.5
        new_v = np.ones((64, 64)) * 0.25
        solver.set_state(new_u, new_v, step_count=200)
        assert abs(solver.u[0, 0] - 0.5) < 1e-10
        assert abs(solver.v[0, 0] - 0.25) < 1e-10
        assert solver.step_count == 200

    def test_set_state_shape_mismatch(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        with pytest.raises(ValueError):
            solver.set_state(np.ones((32, 32)), np.ones((32, 32)))


class TestSolverStability:
    """Tests for numerical stability across models."""

    @pytest.mark.parametrize("model_name", list(MODELS.keys()))
    def test_stability(self, model_name):
        solver = ReactionDiffusionSolver(model_name, grid_size=64)
        solver.apply_perturbation()
        solver.step(500)
        assert not np.any(np.isnan(solver.u)), f"{model_name} u has NaNs"
        assert not np.any(np.isnan(solver.v)), f"{model_name} v has NaNs"

    def test_gs_long_run(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64,
                                          params={"F": 0.035, "k": 0.065})
        solver.apply_perturbation({"type": "center_square", "size": 10,
                                    "u_val": 0.0, "v_val": 1.0})
        solver.step(1000)
        assert not np.any(np.isnan(solver.u))
        assert not np.any(np.isinf(solver.u))


class TestSolverStatistics:
    """Tests for statistics computation."""

    def test_statistics_keys(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation()
        solver.step(100)
        stats = solver.compute_statistics()
        assert "u_min" in stats
        assert "u_max" in stats
        assert "v_min" in stats
        assert "v_max" in stats
        assert "step_count" in stats
        assert stats["step_count"] == 100
        assert stats["v_max"] > 0


class TestSolverCallbacks:
    """Tests for callback and event systems."""

    def test_callback_system(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation()
        call_count = [0]

        def my_callback(solver):
            call_count[0] += 1

        solver.add_callback(my_callback, every=50)
        solver.step(200)
        assert call_count[0] == 4  # 200 / 50 = 4 calls

    def test_event_system(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        events_received = []

        def listener(solver, **kwargs):
            events_received.append(kwargs.get("pert_type", "unknown"))

        solver.on(SimulationEvent.PERTURBATION_APPLIED, listener)
        solver.apply_perturbation()
        assert len(events_received) == 1


# ──────────────────────────────────────────────────────
# Perturbation Tests
# ──────────────────────────────────────────────────────

class TestPerturbations:
    """Tests for perturbation types."""

    def test_center_square(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation({"type": "center_square", "size": 10,
                                    "u_val": 0.0, "v_val": 1.0})
        assert abs(solver.u[32, 32] - 0.0) < 1e-10
        assert abs(solver.v[32, 32] - 1.0) < 1e-10
        assert abs(solver.u[0, 0] - 1.0) < 1e-10

    def test_ring(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation({"type": "ring", "radius": 16, "thickness": 3,
                                    "u_val": 0.5, "v_val": 1.0})
        assert abs(solver.v[32, 32] - 0.0) < 1e-10
        assert abs(solver.v[32, 48] - 1.0) < 1e-10

    def test_cross(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation({"type": "cross", "size": 4,
                                    "u_val": 0.0, "v_val": 1.0})
        assert abs(solver.v[32, 32] - 1.0) < 1e-10

    def test_random(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        initial_u = solver.u.copy()
        solver.apply_perturbation({"type": "random", "noise": 0.1})
        assert not np.allclose(solver.u, initial_u)

    def test_corner(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation({"type": "corner", "size": 10,
                                    "u_val": 0.0, "v_val": 1.0})
        assert abs(solver.v[2, 2] - 1.0) < 1e-10
        assert abs(solver.v[60, 60] - 0.0) < 1e-10

    def test_multi_spot(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation({"type": "multi_spot", "count": 5, "size": 8,
                                    "u_val": 0.0, "v_val": 1.0})
        assert np.sum(solver.v > 0.5) > 0
        # Verify u and v perturbation patterns are identical
        u_perturbed = solver.u < 0.5
        v_perturbed = solver.v > 0.5
        assert np.array_equal(u_perturbed, v_perturbed)

    def test_default_perturbation(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation()
        assert np.sum(solver.v > 0.5) > 0

    def test_invalid_type(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        with pytest.raises(ValueError):
            solver.apply_perturbation({"type": "nonexistent"})


# ──────────────────────────────────────────────────────
# Checkpoint Tests
# ──────────────────────────────────────────────────────

class TestCheckpoints:
    """Tests for checkpoint save/load."""

    def test_roundtrip(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=32,
                                          params={"F": 0.04, "k": 0.06})
        solver.apply_perturbation({"type": "center_square", "size": 6,
                                    "u_val": 0.0, "v_val": 1.0})
        solver.step(50)

        with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
            path = f.name

        try:
            solver.save_checkpoint(path)
            loaded = ReactionDiffusionSolver.load_checkpoint(path)
            assert loaded.step_count == 50
            assert loaded.model_name == "gray-scott"
            assert loaded.n == 32
            assert abs(loaded.params["F"] - 0.04) < 1e-10
            assert np.allclose(solver.u, loaded.u)
            assert np.allclose(solver.v, loaded.v)
        finally:
            os.unlink(path)

    @pytest.mark.parametrize("model_name", ["gray-scott", "fhn",
                                             "gierer-meinhardt", "brusselator"])
    def test_different_models(self, model_name):
        solver = ReactionDiffusionSolver(model_name, grid_size=32)
        solver.apply_perturbation()
        solver.step(20)

        with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
            path = f.name

        try:
            solver.save_checkpoint(path)
            loaded = ReactionDiffusionSolver.load_checkpoint(path)
            assert loaded.model_name == model_name
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────────────
# Preset Tests
# ──────────────────────────────────────────────────────

class TestPresets:
    """Tests for preset system."""

    def test_all_valid(self):
        for name, config in ALL_PRESETS.items():
            assert "model" in config, f"Preset {name} missing 'model'"
            assert "params" in config, f"Preset {name} missing 'params'"
            assert config["model"] in MODELS, f"Preset {name} has invalid model"

    def test_get_preset(self):
        preset = get_preset("spots")
        assert preset["model"] == "gray-scott"
        assert "F" in preset["params"]

    def test_invalid_preset(self):
        with pytest.raises(KeyError):
            get_preset("nonexistent")

    @pytest.mark.parametrize("name", list(ALL_PRESETS.keys()))
    def test_run_each_preset(self, name):
        preset = get_preset(name)
        solver = ReactionDiffusionSolver(
            preset["model"], grid_size=32,
            params=preset["params"], dt=preset.get("dt", 1.0),
        )
        solver.apply_perturbation(preset.get("perturbation", None))
        solver.step(50)
        assert not np.any(np.isnan(solver.u)), f"Preset {name} produced NaN in u"

    def test_register_preset(self):
        register_preset("test-custom", {
            "model": "gray-scott",
            "params": {"Du": 0.16, "Dv": 0.08, "F": 0.035, "k": 0.065},
            "grid_size": 32,
            "dt": 1.0,
            "steps": 100,
            "perturbation": {"type": "center_square", "size": 10},
            "description": "Custom test preset",
        })
        assert "test-custom" in ALL_PRESETS
        del ALL_PRESETS["test-custom"]


# ──────────────────────────────────────────────────────
# Visualization Tests
# ──────────────────────────────────────────────────────

class TestVisualization:
    """Tests for visualization module."""

    def test_field_selection_v(self):
        u = np.ones((10, 10))
        v = np.ones((10, 10)) * 2
        result = _select_field(u, v, "v")
        assert np.allclose(result, 2.0)

    def test_field_selection_u(self):
        u = np.ones((10, 10)) * 3
        v = np.ones((10, 10))
        result = _select_field(u, v, "u")
        assert np.allclose(result, 3.0)

    def test_field_selection_composite(self):
        u = np.zeros((10, 10))
        v = np.ones((10, 10))
        result = _select_field(u, v, "composite")
        assert result.shape == (10, 10)

    def test_field_selection_difference(self):
        u = np.ones((10, 10)) * 3
        v = np.ones((10, 10))
        result = _select_field(u, v, "difference")
        assert np.allclose(result, 2.0)

    def test_field_selection_gradient(self):
        v = np.zeros((10, 10))
        v[5, 5] = 1.0
        result = _select_field(np.zeros_like(v), v, "gradient")
        assert np.max(result) > 0

    def test_field_selection_default(self):
        u = np.ones((10, 10))
        v = np.ones((10, 10)) * 5
        result = _select_field(u, v, "nonexistent")
        assert np.allclose(result, 5.0)

    def test_apply_colormap_returns_uint8(self):
        data = np.random.rand(10, 10)
        rgb = _apply_colormap(data, "inferno")
        assert rgb.dtype == np.uint8

    def test_save_frame_fast(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=32)
        solver.apply_perturbation()
        solver.step(10)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            save_frame_fast(solver.u, solver.v, path, field="v", cmap="inferno")
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────────────
# Configuration Tests
# ──────────────────────────────────────────────────────

class TestConfig:
    """Tests for configuration module."""

    def test_default_config(self):
        config = SimulationConfig()
        assert config.model == "gray-scott"
        assert config.grid_size == 128
        assert config.steps == 5000

    def test_validation_valid(self):
        config = SimulationConfig(model="gray-scott", grid_size=128)
        config.validate()  # Should not raise

    def test_validation_invalid_model(self):
        config = SimulationConfig(model="nonexistent")
        with pytest.raises(ValueError):
            config.validate()

    def test_validation_invalid_grid_size(self):
        config = SimulationConfig(grid_size=2)
        with pytest.raises(ValueError):
            config.validate()

    def test_validation_invalid_dt(self):
        config = SimulationConfig(dt=-1.0)
        with pytest.raises(ValueError):
            config.validate()

    def test_validation_invalid_method(self):
        config = SimulationConfig(method="invalid")
        with pytest.raises(ValueError):
            config.validate()

    def test_to_dict(self):
        config = SimulationConfig(model="fhn", grid_size=256)
        d = config.to_dict()
        assert d["model"] == "fhn"
        assert d["grid_size"] == 256

    def test_load_yaml(self):
        config_dict = {
            "model": "gray-scott",
            "grid_size": 64,
            "steps": 1000,
            "params": {"F": 0.03, "k": 0.06},
        }
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w",
                                         delete=False) as f:
            import yaml
            yaml.dump(config_dict, f)
            path = f.name

        try:
            loaded = load_config(path)
            assert loaded.model == "gray-scott"
            assert loaded.grid_size == 64
            assert loaded.params["F"] == 0.03
        finally:
            os.unlink(path)

    def test_load_json(self):
        config_dict = {
            "model": "fhn",
            "grid_size": 128,
            "steps": 2000,
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w",
                                         delete=False) as f:
            json.dump(config_dict, f)
            path = f.name

        try:
            loaded = load_config(path)
            assert loaded.model == "fhn"
            assert loaded.grid_size == 128
        finally:
            os.unlink(path)

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path.yaml")

    def test_perturbation_config(self):
        pert = PerturbationConfig(type="ring", radius=16, thickness=3)
        d = pert.to_dict()
        assert d["type"] == "ring"
        assert d["radius"] == 16

    def test_to_yaml(self):
        config = SimulationConfig(model="gray-scott", grid_size=64)
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            config.to_yaml(path)
            loaded = load_config(path)
            assert loaded.model == "gray-scott"
        finally:
            os.unlink(path)

    def test_to_json(self):
        config = SimulationConfig(model="fhn", grid_size=128)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            config.to_json(path)
            assert os.path.exists(path)
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for end-to-end scenarios."""

    def test_gs_spots_pattern_formation(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64,
                                          params={"F": 0.035, "k": 0.065})
        solver.apply_perturbation({"type": "center_square", "size": 10,
                                    "u_val": 0.0, "v_val": 1.0})
        initial_u_mean = np.mean(solver.u)
        solver.step(2000)
        final_u_mean = np.mean(solver.u)
        assert abs(final_u_mean - initial_u_mean) > 0.001

    @pytest.mark.parametrize("bc", ["periodic", "dirichlet", "neumann"])
    def test_multiple_bcs(self, bc):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=32, bc=bc)
        solver.apply_perturbation()
        solver.step(100)
        assert not np.any(np.isnan(solver.u))
        assert not np.any(np.isnan(solver.v))

    def test_euler_rk2_consistency(self):
        np.random.seed(42)
        solver_euler = ReactionDiffusionSolver("gray-scott", grid_size=32,
                                                params={"F": 0.035, "k": 0.065})
        solver_euler.apply_perturbation({"type": "center_square", "size": 8,
                                          "u_val": 0.0, "v_val": 1.0})
        np.random.seed(42)
        solver_rk2 = ReactionDiffusionSolver("gray-scott", grid_size=32,
                                              params={"F": 0.035, "k": 0.065})
        solver_rk2.apply_perturbation({"type": "center_square", "size": 8,
                                        "u_val": 0.0, "v_val": 1.0})
        solver_euler.step(100, method="euler")
        solver_rk2.step(100, method="rk2")
        corr = np.corrcoef(solver_euler.v.flatten(), solver_rk2.v.flatten())[0, 1]
        assert corr > 0.5

    def test_adaptive_step_restores_dt(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=32)
        original_dt = solver.dt
        solver.apply_perturbation()
        solver.adaptive_step(10)
        assert abs(solver.dt - original_dt) < 1e-10

    def test_parameter_sweep(self):
        results = ReactionDiffusionSolver.parameter_sweep(
            "gray-scott", "F",
            [0.03, 0.04, 0.05],
            grid_size=32, steps=200,
        )
        assert len(results) == 3
        assert all(isinstance(v, float) for v in results.values())


# ──────────────────────────────────────────────────────
# Bug-specific regression tests
# ──────────────────────────────────────────────────────

class TestBugFixes:
    """Regression tests for previously fixed bugs."""

    def test_multi_spot_v_indexing(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
        solver.apply_perturbation({"type": "multi_spot", "count": 10, "size": 8,
                                    "u_val": 0.0, "v_val": 1.0})
        u_perturbed = solver.u < 0.5
        v_perturbed = solver.v > 0.5
        assert np.array_equal(u_perturbed, v_perturbed)

    def test_adaptive_step_dt_restore(self):
        solver = ReactionDiffusionSolver("gray-scott", grid_size=32)
        original_dt = solver.dt
        solver.apply_perturbation()
        solver.adaptive_step(10)
        assert abs(solver.dt - original_dt) < 1e-10

    def test_apply_colormap_uint8(self):
        data = np.random.rand(10, 10)
        rgb = _apply_colormap(data, "inferno")
        assert rgb.dtype == np.uint8

    def test_fhn_fixed_point(self):
        from rdsim.models import fitzhugh_nagumo_default_state
        u, v = fitzhugh_nagumo_default_state(32, params={"beta": 0.5, "gamma": 1.0})
        u_mean, v_mean = u[0, 0], v[0, 0]
        du = u_mean - u_mean**3 / 3 - v_mean
        assert abs(du) < 0.1

    def test_brusselator_default_state_params(self):
        from rdsim.models import brusselator_default_state
        u, v = brusselator_default_state(32, params={"A": 2.0, "B": 6.0})
        assert abs(u[0, 0] - 2.0) < 1e-10
        assert abs(v[0, 0] - 3.0) < 1e-10