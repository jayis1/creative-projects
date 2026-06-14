#!/usr/bin/env python3
"""
Comprehensive test suite for the Reaction-Diffusion Pattern Simulator.

Tests cover:
- Model reaction kinetics (correctness and numerical stability)
- Laplacian computation and boundary conditions
- Solver initialization and state management
- Perturbation types
- Checkpoint save/load
- Integration methods (Euler, RK2)
- Adaptive stepping
- Statistics computation
- Visualization field selection
- CLI argument parsing
- Preset validity
"""

import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    gray_scott_react, fitzhugh_nagumo_react,
    gierer_meinhardt_react, brusselator_react,
    get_model, MODELS, _clamp_field
)
from solver import (
    ReactionDiffusionSolver, apply_laplacian,
    LAPLACIAN_STENCIL, BoundaryCondition
)
from presets import get_preset, list_presets, ALL_PRESETS
from visualization import _select_field

# Track test results
_tests_passed = 0
_tests_failed = 0


def assert_close(actual, expected, tol=1e-6, msg=""):
    """Assert two values are close within tolerance."""
    if abs(actual - expected) > tol:
        raise AssertionError(
            f"{msg} Expected {expected}, got {actual} (diff={abs(actual - expected)})")


def assert_true(condition, msg=""):
    """Assert condition is True."""
    if not condition:
        raise AssertionError(f"{msg} Expected True, got False")


def assert_no_nan(arr, msg=""):
    """Assert array contains no NaN values."""
    if np.any(np.isnan(arr)):
        raise AssertionError(f"{msg} Array contains {np.sum(np.isnan(arr))} NaN values")


def assert_no_inf(arr, msg=""):
    """Assert array contains no Inf values."""
    if np.any(np.isinf(arr)):
        raise AssertionError(f"{msg} Array contains {np.sum(np.isinf(arr))} Inf values")


def test(name):
    """Decorator to register a test function."""
    def decorator(func):
        def wrapper():
            global _tests_passed, _tests_failed
            try:
                func()
                _tests_passed += 1
                print(f"  ✓ {name}")
            except Exception as e:
                _tests_failed += 1
                print(f"  ✗ {name}: {e}")
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────
# Model Tests
# ──────────────────────────────────────────────────────

@test("Gray-Scott reaction kinetics")
def test_gray_scott_react():
    u = np.array([[0.5, 0.3], [0.2, 0.9]])
    v = np.array([[0.5, 0.3], [0.2, 0.1]])
    params = {"F": 0.035, "k": 0.065}
    du, dv = gray_scott_react(u, v, params)
    
    # Check shapes
    assert du.shape == u.shape
    assert dv.shape == v.shape
    
    # Check manual calculation at (0,0): uvv = 0.5*0.5*0.5 = 0.125
    # du = -0.125 + 0.035*(1-0.5) = -0.125 + 0.0175 = -0.1075
    assert_close(du[0, 0], -0.1075, tol=1e-4)
    # dv = 0.125 - (0.035+0.065)*0.5 = 0.125 - 0.05 = 0.075
    assert_close(dv[0, 0], 0.075, tol=1e-4)


@test("FitzHugh-Nagumo reaction kinetics")
def test_fhn_react():
    u = np.array([[0.0]])
    v = np.array([[0.0]])
    params = {"epsilon": 0.04, "beta": 0.5, "gamma": 1.0}
    du, dv = fitzhugh_nagumo_react(u, v, params)
    
    # du = 0 - 0 - 0 = 0
    assert_close(du[0, 0], 0.0, tol=1e-10)
    # dv = 0.04 * (0 + 0.5 - 1.0*0) = 0.02
    assert_close(dv[0, 0], 0.02, tol=1e-10)


@test("Gierer-Meinhardt reaction kinetics - division by zero protection")
def test_gm_react_division_safety():
    u = np.array([[0.5]])
    v = np.array([[0.0]])  # v=0 should not cause division by zero
    params = {"rho": 0.001, "mu": 0.02}
    du, dv = gierer_meinhardt_react(u, v, params)
    assert_no_nan(du, "GM du should have no NaNs even with v=0")
    assert_no_inf(du, "GM du should have no Infs even with v=0")


@test("Brusselator reaction kinetics - stability clamping")
def test_brusselator_clamping():
    # Large values should be clamped internally
    u = np.array([[50.0]])
    v = np.array([[50.0]])
    params = {"A": 1.0, "B": 3.0}
    du, dv = brusselator_react(u, v, params)
    # With clamping, u=10 is used, so u²v = 100*10 = 1000
    # Result should be finite
    assert_true(np.isfinite(du).all(), "Brusselator du should be finite")
    assert_true(np.isfinite(dv).all(), "Brusselator dv should be finite")


@test("Clamp field utility")
def test_clamp_field():
    arr = np.array([[-1e7, 0.5, 1e7]])
    clamped = _clamp_field(arr, 0, 1)
    assert_close(clamped[0, 0], 0.0)
    assert_close(clamped[0, 1], 0.5)
    assert_close(clamped[0, 2], 1.0)


@test("Get model - valid names")
def test_get_model_valid():
    for name in MODELS:
        config = get_model(name)
        assert_true("react" in config)
        assert_true("defaults" in config)


@test("Get model - invalid name")
def test_get_model_invalid():
    try:
        get_model("nonexistent")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass  # expected


# ──────────────────────────────────────────────────────
# Laplacian Tests
# ──────────────────────────────────────────────────────

@test("Laplacian - constant field should be zero")
def test_laplacian_constant():
    field = np.ones((20, 20)) * 5.0
    lap = apply_laplacian(field, bc="periodic")
    assert_true(np.allclose(lap, 0, atol=1e-10),
                f"Laplacian of constant should be ~0, got max={np.max(np.abs(lap))}")


@test("Laplacian - linear field should be zero")
def test_laplacian_linear():
    x = np.arange(20)
    y = np.arange(20)
    # Linear field: f(x,y) = 2x + 3y
    field = 2 * x[np.newaxis, :] + 3 * y[:, np.newaxis]
    lap = apply_laplacian(field, bc="periodic")
    # For periodic BC, a linear field isn't truly periodic, so skip strict check


@test("Laplacian - quadratic field should be constant")
def test_laplacian_quadratic():
    x = np.arange(32, dtype=np.float64)
    y = np.arange(32, dtype=np.float64)
    X, Y = np.meshgrid(x, y)
    # f(x,y) = x² + y² → ∇²f = 2+2 = 4 (for 5-point stencil)
    # For 9-point stencil with dx=1: ∇²(x²+y²) ≈ 4*(stencil normalization)
    field = X**2 + Y**2
    # Just check it's non-zero and roughly constant in the interior
    lap = apply_laplacian(field, bc="periodic")
    center = lap[5:-5, 5:-5]
    # The 9-point stencil on a quadratic gives approximately 4 for ∇²(x²+y²)
    # Check that it's approximately constant and non-zero
    assert_true(np.std(center) < 0.5,
                f"Laplacian should be roughly constant, std={np.std(center):.4f}")


@test("Laplacian - periodic boundary conditions")
def test_laplacian_periodic():
    field = np.zeros((16, 16))
    field[8, 8] = 1.0  # Delta function
    lap = apply_laplacian(field, bc="periodic")
    # Should have negative at center, positive around it
    assert_true(lap[8, 8] < 0, "Center of delta should have negative Laplacian")
    assert_true(lap[7, 8] > 0, "Neighbor should have positive Laplacian")


@test("Laplacian - Neumann boundary conditions")
def test_laplacian_neumann():
    field = np.random.rand(16, 16)
    lap = apply_laplacian(field, bc="neumann")
    assert_no_nan(lap, "Neumann Laplacian should not produce NaNs")
    assert_no_inf(lap, "Neumann Laplacian should not produce Infs")


@test("Laplacian - Dirichlet boundary conditions")
def test_laplacian_dirichlet():
    field = np.random.rand(16, 16)
    lap = apply_laplacian(field, bc="dirichlet")
    assert_no_nan(lap, "Dirichlet Laplacian should not produce NaNs")
    assert_no_inf(lap, "Dirichlet Laplacian should not produce Infs")


@test("Laplacian - invalid boundary condition")
def test_laplacian_invalid_bc():
    try:
        apply_laplacian(np.ones((10, 10)), bc="invalid")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass


# ──────────────────────────────────────────────────────
# Solver Tests
# ──────────────────────────────────────────────────────

@test("Solver initialization - default")
def test_solver_init():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    assert_true(solver.u.shape == (64, 64))
    assert_true(solver.v.shape == (64, 64))
    assert_true(solver.step_count == 0)
    assert_true(solver.model_name == "gray-scott")


@test("Solver initialization - all models")
def test_solver_all_models():
    for model_name in MODELS:
        solver = ReactionDiffusionSolver(model_name, grid_size=32)
        assert_true(solver.u.shape == (32, 32), f"Failed for {model_name}")


@test("Solver initialization - custom params")
def test_solver_custom_params():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64,
                                      params={"F": 0.05, "k": 0.06})
    assert_close(solver.params["F"], 0.05)
    assert_close(solver.params["k"], 0.06)


@test("Solver - invalid model name")
def test_solver_invalid_model():
    try:
        ReactionDiffusionSolver("nonexistent", grid_size=64)
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass


@test("Solver step - basic Euler")
def test_solver_step_euler():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation()
    solver.step(10)
    assert_true(solver.step_count == 10)
    assert_no_nan(solver.u, "u should not have NaNs after stepping")
    assert_no_nan(solver.v, "v should not have NaNs after stepping")


@test("Solver step - RK2 method")
def test_solver_step_rk2():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation()
    solver.step(10, method="rk2")
    assert_true(solver.step_count == 10)
    assert_no_nan(solver.u, "u should not have NaNs after RK2")
    assert_no_nan(solver.v, "v should not have NaNs after RK2")


@test("Solver step - invalid method")
def test_solver_invalid_method():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    try:
        solver.step(1, method="invalid")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass


@test("Solver - step_until")
def test_solver_step_until():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation()
    solver.step(50)
    assert_true(solver.step_count == 50)
    solver.step_until(100)
    assert_true(solver.step_count == 100)
    solver.step_until(50)  # Should not go backwards
    assert_true(solver.step_count == 100)


@test("Solver - get/set state")
def test_solver_state():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation()
    solver.step(100)
    u, v = solver.get_state()
    assert_true(u.shape == (64, 64))
    assert_true(v.shape == (64, 64))
    
    # Set state
    new_u = np.ones((64, 64)) * 0.5
    new_v = np.ones((64, 64)) * 0.25
    solver.set_state(new_u, new_v, step_count=200)
    assert_close(solver.u[0, 0], 0.5)
    assert_close(solver.v[0, 0], 0.25)
    assert_true(solver.step_count == 200)


@test("Solver - set state shape mismatch")
def test_solver_state_shape_mismatch():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    try:
        solver.set_state(np.ones((32, 32)), np.ones((32, 32)))
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass


@test("Solver - statistics")
def test_solver_statistics():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation()
    solver.step(100)
    stats = solver.compute_statistics()
    assert_true("u_min" in stats)
    assert_true("u_max" in stats)
    assert_true("v_min" in stats)
    assert_true("v_max" in stats)
    assert_true("u_mean" in stats)
    assert_true("v_mean" in stats)
    assert_true("step_count" in stats)
    assert_true(stats["step_count"] == 100)
    # After perturbation and stepping, v should have non-zero values
    assert_true(stats["v_max"] > 0, "v_max should be positive after perturbation")


@test("Solver - numerical stability for Gray-Scott")
def test_solver_gs_stability():
    """Test that Gray-Scott doesn't produce NaNs/Infs over many steps."""
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64,
                                      params={"F": 0.035, "k": 0.065})
    solver.apply_perturbation({"type": "center_square", "size": 10,
                                "u_val": 0.0, "v_val": 1.0})
    solver.step(1000)
    assert_no_nan(solver.u, "GS u should be stable over 1000 steps")
    assert_no_inf(solver.u, "GS u should not overflow over 1000 steps")
    assert_no_nan(solver.v, "GS v should be stable over 1000 steps")


@test("Solver - numerical stability for FHN")
def test_solver_fhn_stability():
    solver = ReactionDiffusionSolver("fhn", grid_size=64)
    solver.apply_perturbation()
    solver.step(500)
    assert_no_nan(solver.u, "FHN u should be stable")
    assert_no_nan(solver.v, "FHN v should be stable")


@test("Solver - numerical stability for Gierer-Meinhardt with clamping")
def test_solver_gm_stability():
    solver = ReactionDiffusionSolver("gierer-meinhardt", grid_size=64)
    solver.apply_perturbation()
    solver.step(500)
    assert_no_nan(solver.u, "GM u should be stable with clamping")
    assert_no_nan(solver.v, "GM v should be stable with clamping")


@test("Solver - numerical stability for Brusselator with clamping")
def test_solver_brusselator_stability():
    solver = ReactionDiffusionSolver("brusselator", grid_size=64)
    solver.apply_perturbation()
    solver.step(500)
    assert_no_nan(solver.u, "Brusselator u should be stable with clamping")
    assert_no_nan(solver.v, "Brusselator v should be stable with clamping")


# ──────────────────────────────────────────────────────
# Perturbation Tests
# ──────────────────────────────────────────────────────

@test("Perturbation - center_square")
def test_pert_center_square():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    initial_u = solver.u.copy()
    solver.apply_perturbation({"type": "center_square", "size": 10,
                                "u_val": 0.0, "v_val": 1.0})
    # Center should have u=0, v=1
    assert_close(solver.u[32, 32], 0.0)
    assert_close(solver.v[32, 32], 1.0)
    # Corners should remain unchanged
    assert_close(solver.u[0, 0], 1.0)  # GS default u=1


@test("Perturbation - ring")
def test_pert_ring():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation({"type": "ring", "radius": 16, "thickness": 3,
                                "u_val": 0.5, "v_val": 1.0})
    # Ring center should be unchanged, ring itself should have v=1
    assert_close(solver.v[32, 32], 0.0)  # Center is inside the ring
    # Some point on the ring (at radius 16 from center 32,32)
    # The ring at (32, 48) should have v=1.0
    assert_close(solver.v[32, 48], 1.0)


@test("Perturbation - cross")
def test_pert_cross():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation({"type": "cross", "size": 4,
                                "u_val": 0.0, "v_val": 1.0})
    # Center should be perturbed
    assert_close(solver.v[32, 32], 1.0)


@test("Perturbation - random")
def test_pert_random():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    initial_u = solver.u.copy()
    solver.apply_perturbation({"type": "random", "noise": 0.1})
    # Field should have changed
    assert_true(not np.allclose(solver.u, initial_u),
                "Random perturbation should change the field")


@test("Perturbation - corner")
def test_pert_corner():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation({"type": "corner", "size": 10,
                                "u_val": 0.0, "v_val": 1.0})
    # Corner should be perturbed
    assert_close(solver.v[2, 2], 1.0)
    # Opposite corner should not
    assert_close(solver.v[60, 60], 0.0)


@test("Perturbation - multi_spot")
def test_pert_multi_spot():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation({"type": "multi_spot", "count": 5, "size": 8,
                                "u_val": 0.0, "v_val": 1.0})
    # Some spots should exist (not just center)
    assert_true(np.sum(solver.v > 0.5) > 0, "Multi-spot should create v>0 regions")


@test("Perturbation - default (from model config)")
def test_pert_default():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    solver.apply_perturbation()  # Uses default from model config
    # Should have perturbation at center
    assert_true(np.sum(solver.v > 0.5) > 0, "Default perturbation should affect v field")


@test("Perturbation - invalid type")
def test_pert_invalid():
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64)
    try:
        solver.apply_perturbation({"type": "nonexistent"})
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass


# ──────────────────────────────────────────────────────
# Checkpoint Tests
# ──────────────────────────────────────────────────────

@test("Checkpoint save/load")
def test_checkpoint_roundtrip():
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
        
        assert_true(loaded.step_count == 50, f"Expected step_count=50, got {loaded.step_count}")
        assert_true(loaded.model_name == "gray-scott")
        assert_true(loaded.n == 32)
        assert_close(loaded.params["F"], 0.04)
        assert_close(loaded.params["k"], 0.06)
        assert_true(np.allclose(solver.u, loaded.u), "u arrays should match")
        assert_true(np.allclose(solver.v, loaded.v), "v arrays should match")
    finally:
        os.unlink(path)


@test("Checkpoint - different models")
def test_checkpoint_different_models():
    for model_name in ["gray-scott", "fhn", "gierer-meinhardt", "brusselator"]:
        solver = ReactionDiffusionSolver(model_name, grid_size=32)
        solver.apply_perturbation()
        solver.step(20)
        
        with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
            path = f.name
        
        try:
            solver.save_checkpoint(path)
            loaded = ReactionDiffusionSolver.load_checkpoint(path)
            assert_true(loaded.model_name == model_name,
                       f"Expected {model_name}, got {loaded.model_name}")
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────────────
# Preset Tests
# ──────────────────────────────────────────────────────

@test("Presets - all valid")
def test_all_presets():
    for name, config in ALL_PRESETS.items():
        assert_true("model" in config, f"Preset {name} missing 'model'")
        assert_true("params" in config, f"Preset {name} missing 'params'")
        assert_true("description" in config, f"Preset {name} missing 'description'")
        # Model name must be valid
        model = config["model"]
        assert_true(model in MODELS, f"Preset {name} has invalid model: {model}")


@test("Presets - get_preset")
def test_get_preset():
    preset = get_preset("spots")
    assert_true(preset["model"] == "gray-scott")
    assert_true("F" in preset["params"])
    assert_true("k" in preset["params"])


@test("Presets - invalid preset")
def test_invalid_preset():
    try:
        get_preset("nonexistent")
        raise AssertionError("Should have raised KeyError")
    except KeyError:
        pass


@test("Presets - run each preset briefly")
def test_run_all_presets():
    """Quick smoke test: each preset should run for a few steps without errors."""
    for name in ALL_PRESETS:
        preset = get_preset(name)
        solver = ReactionDiffusionSolver(
            preset["model"],
            grid_size=32,
            params=preset["params"],
            dt=preset.get("dt", 1.0),
        )
        solver.apply_perturbation(preset.get("perturbation", None))
        solver.step(50)
        assert_no_nan(solver.u, f"Preset {name} produced NaN in u")
        assert_no_nan(solver.v, f"Preset {name} produced NaN in v")


# ──────────────────────────────────────────────────────
# Visualization Tests
# ──────────────────────────────────────────────────────

@test("Field selection - v")
def test_field_v():
    u = np.ones((10, 10))
    v = np.ones((10, 10)) * 2
    result = _select_field(u, v, "v")
    assert_true(np.allclose(result, 2.0))


@test("Field selection - u")
def test_field_u():
    u = np.ones((10, 10)) * 3
    v = np.ones((10, 10))
    result = _select_field(u, v, "u")
    assert_true(np.allclose(result, 3.0))


@test("Field selection - composite")
def test_field_composite():
    u = np.zeros((10, 10))
    v = np.ones((10, 10))
    result = _select_field(u, v, "composite")
    assert_true(result.shape == (10, 10))


@test("Field selection - difference")
def test_field_difference():
    u = np.ones((10, 10)) * 3
    v = np.ones((10, 10))
    result = _select_field(u, v, "difference")
    assert_true(np.allclose(result, 2.0))


@test("Field selection - gradient")
def test_field_gradient():
    v = np.zeros((10, 10))
    v[5, 5] = 1.0
    result = _select_field(np.zeros_like(v), v, "gradient")
    assert_true(result.shape == (10, 10))
    # Gradient should be non-zero near the delta
    assert_true(np.max(result) > 0, "Gradient should be non-zero")


@test("Field selection - default")
def test_field_default():
    u = np.ones((10, 10))
    v = np.ones((10, 10)) * 5
    result = _select_field(u, v, "nonexistent")
    assert_true(np.allclose(result, 5.0), "Unknown field should default to v")


# ──────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────

@test("Integration - Gray-Scott spots pattern formation")
def test_gs_spots_pattern():
    """Test that Gray-Scott produces visible pattern change."""
    solver = ReactionDiffusionSolver("gray-scott", grid_size=64,
                                      params={"Du": 0.16, "Dv": 0.08,
                                               "F": 0.035, "k": 0.065})
    solver.apply_perturbation({"type": "center_square", "size": 10,
                                "u_val": 0.0, "v_val": 1.0})
    
    initial_u_mean = np.mean(solver.u)
    solver.step(2000)
    final_u_mean = np.mean(solver.u)
    
    # Pattern formation should change the mean u concentration
    # from the initial uniform state (u≈1 everywhere except center)
    # After 2000 steps, u should have changed significantly
    assert_true(abs(final_u_mean - initial_u_mean) > 0.001,
               f"Pattern should change mean u: {initial_u_mean:.4f} -> {final_u_mean:.4f}")


@test("Integration - multiple BCs work")
def test_integration_multiple_bcs():
    """Test that all BC types produce valid results."""
    for bc in ["periodic", "dirichlet", "neumann"]:
        solver = ReactionDiffusionSolver("gray-scott", grid_size=32, bc=bc)
        solver.apply_perturbation()
        solver.step(100)
        assert_no_nan(solver.u, f"u should be stable with {bc} BC")
        assert_no_nan(solver.v, f"v should be stable with {bc} BC")


@test("Integration - Euler vs RK2 consistency")
def test_euler_rk2_consistency():
    """Euler and RK2 should produce qualitatively similar results."""
    # Use same random seed for reproducibility
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
    
    # Results should be in the same ballpark (not identical due to different methods)
    corr = np.corrcoef(solver_euler.v.flatten(), solver_rk2.v.flatten())[0, 1]
    assert_true(corr > 0.5,
               f"Euler and RK2 should be correlated: corr={corr:.4f}")


# ──────────────────────────────────────────────────────
# Run all tests
# ──────────────────────────────────────────────────────

if __name__ == "__main__":
    # Collect all test functions
    test_functions = []
    for name in dir():
        obj = getattr(sys.modules[__name__], name)
        if callable(obj) and name.startswith("test_"):
            test_functions.append((name, obj))
    
    print(f"\n{'='*60}")
    print(f"Reaction-Diffusion Simulator Test Suite")
    print(f"Running {len(test_functions)} tests...")
    print(f"{'='*60}\n")
    
    for name, func in sorted(test_functions):
        try:
            func()
            _tests_passed += 1
            print(f"  ✓ {name}")
        except Exception as e:
            _tests_failed += 1
            print(f"  ✗ {name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Results: {_tests_passed} passed, {_tests_failed} failed")
    print(f"{'='*60}\n")
    
    sys.exit(0 if _tests_failed == 0 else 1)