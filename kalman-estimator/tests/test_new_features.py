"""Comprehensive tests for new v3 features: InfoFilter, AdaptiveKF, EnKF,
ParticleFilter, NumericalJacobian, config, CLI, base class, and performance.
"""

import json
import os
import tempfile

import numpy as np
import pytest

from kalman_estimator import (
    BaseEstimator,
    KalmanFilter,
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    InformationFilter,
    AdaptiveKalmanFilter,
    EnsembleKalmanFilter,
    ParticleFilter,
    NumericalJacobianEKF,
    numerical_jacobian,
    smooth,
    FilterDiagnostics,
    load_config,
    load_filter_from_config,
    save_config,
)


# ======================== BaseEstimator ======================== #

def test_base_estimator_is_abstract():
    """BaseEstimator should not be instantiable directly."""
    with pytest.raises(TypeError):
        BaseEstimator()


def test_all_filters_inherit_base():
    """All filter classes should inherit from BaseEstimator."""
    assert issubclass(KalmanFilter, BaseEstimator)
    assert issubclass(ExtendedKalmanFilter, BaseEstimator)
    assert issubclass(UnscentedKalmanFilter, BaseEstimator)
    assert issubclass(InformationFilter, BaseEstimator)
    assert issubclass(AdaptiveKalmanFilter, BaseEstimator)
    assert issubclass(EnsembleKalmanFilter, BaseEstimator)
    assert issubclass(ParticleFilter, BaseEstimator)


def test_base_estimator_step_method():
    """step() should run predict + update and return state."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    kf = KalmanFilter(F, H, np.eye(2)*0.01, np.array([[1.0]]), x0=[0,0], P0=np.eye(2))
    state = kf.step(np.array([5.0]))
    assert state.shape == (2,)


def test_base_estimator_reset():
    """reset() should restore the filter to a given state."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    kf = KalmanFilter(F, H, np.eye(2)*0.01, np.array([[1.0]]), x0=[0,0], P0=np.eye(2))
    kf.predict()
    kf.update(np.array([10.0]))
    kf.reset([0.0, 0.0], np.eye(2))
    assert np.allclose(kf.state, [0.0, 0.0])
    assert np.allclose(kf.covariance, np.eye(2))


# ======================== InformationFilter ======================== #

def _make_info_filter():
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[2.0]])
    P0 = np.eye(2) * 10.0
    Y0 = np.linalg.inv(P0)
    y0 = Y0 @ np.array([0.0, 0.0])
    return InformationFilter(F, H, Q, R, y0=y0, Y0=Y0)


def test_info_filter_basic():
    """InfoFilter should run predict/update without errors."""
    inf = _make_info_filter()
    inf.predict()
    inf.update(np.array([5.0]))
    assert inf.state.shape == (2,)
    assert inf.covariance.shape == (2, 2)


def test_info_filter_matches_kalman():
    """InfoFilter should give the same results as KalmanFilter."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[2.0]])
    P0 = np.eye(2) * 10.0
    x0 = [0.0, 0.0]

    kf = KalmanFilter(F, H, Q, R, x0=x0, P0=P0)
    Y0 = np.linalg.inv(P0)
    y0 = Y0 @ np.array(x0)
    inf = InformationFilter(F, H, Q, R, y0=y0, Y0=Y0)

    rng = np.random.default_rng(42)
    for _ in range(30):
        z = 5.0 + rng.normal(0, np.sqrt(2.0))
        kf.predict()
        kf.update(np.array([z]))
        inf.predict()
        inf.update(np.array([z]))

    # Should be very close (small numerical differences from inv)
    assert np.allclose(kf.state, inf.state, atol=1e-6)
    assert np.allclose(kf.covariance, inf.covariance, atol=1e-6)


def test_info_filter_rejects_nan():
    inf = _make_info_filter()
    inf.predict()
    with pytest.raises(ValueError):
        inf.update(np.array([np.nan]))


def test_info_filter_dimension_validation():
    F = np.eye(2)
    H = np.array([[1, 0]])
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    with pytest.raises(ValueError):
        InformationFilter(F, H, Q, R, y0=[0, 0, 0], Y0=np.eye(3))


# ======================== AdaptiveKalmanFilter ======================== #

def test_adaptive_kf_basic():
    """AdaptiveKF should run and converge."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])
    akf = AdaptiveKalmanFilter(F, H, Q, R, x0=[0,0], P0=np.eye(2)*10, alpha=0.95)
    rng = np.random.default_rng(42)
    true_pos = 0.0
    for _ in range(100):
        true_pos += 1.0
        z = true_pos + rng.normal(0, 2.0)
        akf.predict()
        akf.update(np.array([z]))
    assert abs(akf.state[0] - true_pos) < 5.0


def test_adaptive_kf_estimates_R():
    """AdaptiveKF should adapt R toward the true measurement noise."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    true_R = 9.0  # true measurement noise variance
    R_init = np.array([[1.0]])  # wrong initial guess
    akf = AdaptiveKalmanFilter(
        F, H, Q, R_init, x0=[0,0], P0=np.eye(2)*10,
        alpha=0.98, adapt_Q=False, adapt_R=True,
    )
    rng = np.random.default_rng(42)
    true_pos = 0.0
    for _ in range(500):
        true_pos += 1.0
        z = true_pos + rng.normal(0, np.sqrt(true_R))
        akf.predict()
        akf.update(np.array([z]))
    # adapted R should be closer to true_R than the initial guess
    assert abs(akf.estimated_R[0, 0] - true_R) < abs(R_init[0, 0] - true_R)


def test_adaptive_kf_invalid_alpha():
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    with pytest.raises(ValueError):
        AdaptiveKalmanFilter(F, H, Q, R, x0=[0,0], P0=np.eye(2), alpha=0.0)
    with pytest.raises(ValueError):
        AdaptiveKalmanFilter(F, H, Q, R, x0=[0,0], P0=np.eye(2), alpha=1.5)


# ======================== EnsembleKalmanFilter ======================== #

def test_enkf_basic():
    """EnKF should run and track a constant-velocity object."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])

    def f(x):
        return F @ x
    def h(x):
        return np.array([x[0]])

    enkf = EnsembleKalmanFilter(f, h, Q, R, x0=[0,0], P0=np.eye(2)*10, N=50, seed=42)
    rng = np.random.default_rng(42)
    true_pos = 0.0
    for _ in range(50):
        true_pos += 1.0
        z = true_pos + rng.normal(0, 2.0)
        enkf.predict()
        enkf.update(np.array([z]))
    assert abs(enkf.state[0] - true_pos) < 10.0
    assert enkf.covariance.shape == (2, 2)


def test_enkf_ensemble_size():
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    def f(x):
        return F @ x
    def h(x):
        return np.array([x[0]])
    enkf = EnsembleKalmanFilter(f, h, Q, R, x0=[0,0], P0=np.eye(2), N=30, seed=1)
    assert enkf.ensemble_members.shape == (30, 2)


def test_enkf_rejects_bad_measurement():
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    def f(x):
        return F @ x
    def h(x):
        return np.array([x[0]])
    enkf = EnsembleKalmanFilter(f, h, Q, R, x0=[0,0], P0=np.eye(2), N=10, seed=1)
    enkf.predict()
    with pytest.raises(ValueError):
        enkf.update(np.array([np.nan]))


# ======================== ParticleFilter ======================== #

def test_particle_filter_basic():
    """PF should run and track a constant-velocity object."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])

    def f(x, u=None):
        return F @ x
    def h(x):
        return np.array([x[0]])

    pf = ParticleFilter(f, h, Q, R, x0=[0,0], P0=np.eye(2)*10, N=200, seed=42)
    rng = np.random.default_rng(42)
    true_pos = 0.0
    for _ in range(50):
        true_pos += 1.0
        z = true_pos + rng.normal(0, 2.0)
        pf.predict()
        pf.update(np.array([z]))
    assert abs(pf.state[0] - true_pos) < 10.0


def test_particle_filter_resampling():
    """Effective sample size should stay reasonable after resampling."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])

    def f(x, u=None):
        return F @ x
    def h(x):
        return np.array([x[0]])

    pf = ParticleFilter(f, h, Q, R, x0=[0,0], P0=np.eye(2), N=100, seed=42,
                        resample_threshold=0.5)
    for _ in range(20):
        pf.predict()
        pf.update(np.array([5.0]))
    # After resampling, weights should be uniform -> N_eff ≈ N
    assert pf.effective_sample_size > 50


def test_particle_filter_rejects_bad_measurement():
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    def f(x, u=None):
        return F @ x
    def h(x):
        return np.array([x[0]])
    pf = ParticleFilter(f, h, Q, R, x0=[0,0], P0=np.eye(2), N=50, seed=1)
    pf.predict()
    with pytest.raises(ValueError):
        pf.update(np.array([np.inf]))


# ======================== Numerical Jacobian ======================== #

def test_numerical_jacobian_linear():
    """Jacobian of a linear function should be the matrix itself."""
    A = np.array([[2, 1], [0, 3]], dtype=float)
    def func(x):
        return A @ x
    x = np.array([1.0, 2.0])
    J = numerical_jacobian(func, x)
    assert np.allclose(J, A, atol=1e-5)


def test_numerical_jacobian_nonlinear():
    """Jacobian of a nonlinear function should match analytical."""
    def func(x):
        return np.array([x[0]**2, x[0]*x[1], np.sin(x[1])])
    x = np.array([1.0, 0.5])
    J = numerical_jacobian(func, x, eps=1e-8)
    # Analytical: [[2x, 0], [y, x], [0, cos(y)]]
    J_analytical = np.array([
        [2*x[0], 0],
        [x[1], x[0]],
        [0, np.cos(x[1])],
    ])
    assert np.allclose(J, J_analytical, atol=1e-4)


def test_numerical_jacobian_ekf():
    """NumericalJacobianEKF should match analytical EKF on a linear model."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])

    def f(x, u):
        return F @ x
    def h(x):
        return np.array([x[0]])

    ekf_analytical = ExtendedKalmanFilter(
        f, h, lambda x, u: F, lambda x: H, Q, R, x0=[0,0], P0=np.eye(2)
    )
    ekf_numerical = NumericalJacobianEKF(f, h, Q, R, x0=[0,0], P0=np.eye(2))

    rng = np.random.default_rng(42)
    for _ in range(20):
        z = 5.0 + rng.normal(0, 1)
        ekf_analytical.predict()
        ekf_analytical.update(np.array([z]))
        ekf_numerical.predict()
        ekf_numerical.update(np.array([z]))
    assert np.allclose(ekf_analytical.state, ekf_numerical.state, atol=1e-4)


# ======================== Config ======================== #

def test_config_save_load_json():
    """Save and load a config file."""
    config = {
        "filter": "kalman",
        "F": [[1, 1], [0, 1]],
        "H": [[1, 0]],
        "Q": [[0.01, 0], [0, 0.01]],
        "R": [[2.0]],
        "x0": [0.0, 0.0],
        "P0": [[10, 0], [0, 10]],
    }
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        save_config(config, path)
        loaded = load_config(path)
        assert loaded["F"] == config["F"]
        kf = load_filter_from_config(path)
        assert isinstance(kf, KalmanFilter)
        assert np.allclose(kf.F, np.array(config["F"]))
    finally:
        os.unlink(path)


def test_config_load_information_filter():
    """Config with filter='information' should create an InformationFilter."""
    config = {
        "filter": "information",
        "F": [[1, 1], [0, 1]],
        "H": [[1, 0]],
        "Q": [[0.01, 0], [0, 0.01]],
        "R": [[2.0]],
        "x0": [0.0, 0.0],
        "P0": [[10, 0], [0, 10]],
    }
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        save_config(config, path)
        kf = load_filter_from_config(path)
        assert isinstance(kf, InformationFilter)
    finally:
        os.unlink(path)


def test_config_unknown_filter_type():
    config = {
        "filter": "nonexistent",
        "F": [[1, 1], [0, 1]],
        "H": [[1, 0]],
        "Q": [[0.01, 0], [0, 0.01]],
        "R": [[2.0]],
        "x0": [0.0, 0.0],
        "P0": [[10, 0], [0, 10]],
    }
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        save_config(config, path)
        with pytest.raises(ValueError):
            load_filter_from_config(path)
    finally:
        os.unlink(path)


# ======================== CLI ======================== #

def test_cli_simulate_kf():
    """CLI simulate command should work with --filter kf."""
    from kalman_estimator.cli import main
    ret = main(["simulate", "--filter", "kf", "--steps", "20", "--noise", "2.0"])
    assert ret == 0


def test_cli_simulate_ukf():
    from kalman_estimator.cli import main
    ret = main(["simulate", "--filter", "ukf", "--steps", "20"])
    assert ret == 0


def test_cli_simulate_adaptive():
    from kalman_estimator.cli import main
    ret = main(["simulate", "--filter", "adaptive", "--steps", "20"])
    assert ret == 0


def test_cli_simulate_pf():
    from kalman_estimator.cli import main
    ret = main(["simulate", "--filter", "pf", "--steps", "20", "--seed", "99"])
    assert ret == 0


def test_cli_compare():
    from kalman_estimator.cli import main
    ret = main(["compare", "--steps", "30", "--noise", "3.0"])
    assert ret == 0


def test_cli_no_command():
    """CLI with no command should print help and return 0."""
    from kalman_estimator.cli import main
    ret = main([])
    assert ret == 0


def test_cli_run_with_config():
    """CLI run command should load a config and process measurements."""
    from kalman_estimator.cli import main
    config = {
        "filter": "kalman",
        "F": [[1, 1], [0, 1]],
        "H": [[1, 0]],
        "Q": [[0.01, 0], [0, 0.01]],
        "R": [[2.0]],
        "x0": [0.0, 0.0],
        "P0": [[10, 0], [0, 10]],
    }
    meas_data = [[1.5], [2.3], [3.1], [4.0], [5.2]]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as cfg_tmp:
        cfg_path = cfg_tmp.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as meas_tmp:
        meas_path = meas_tmp.name
    try:
        save_config(config, cfg_path)
        with open(meas_path, "w") as mf:
            json.dump(meas_data, mf)
        ret = main(["run", "--config", cfg_path, "--measurements", meas_path])
        assert ret == 0
    finally:
        os.unlink(cfg_path)
        os.unlink(meas_path)


# ======================== Logging ======================== #

def test_logging_get_logger():
    from kalman_estimator.logging_util import get_logger
    import logging
    logger = get_logger("test_ke", level=logging.DEBUG)
    assert logger.name == "test_ke"
    assert logger.level == logging.DEBUG


# ======================== Performance / Vectorisation ======================== #

def test_ukf_vectorised_matches_loop():
    """Vectorised UKF update should match the original loop-based logic.

    Since we replaced the loops with vectorised numpy, this test ensures
    the results are still correct on a linear model where we know the
    expected output.
    """
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])

    def fx(x, dt):
        return F @ x
    def hx(x):
        return np.array([x[0]])

    ukf = UnscentedKalmanFilter(fx, hx, 1.0, Q, R, x0=[0,0], P0=np.eye(2))
    kf = KalmanFilter(F, H, Q, R, x0=[0,0], P0=np.eye(2))

    rng = np.random.default_rng(42)
    for _ in range(20):
        z = 5.0 + rng.normal(0, 1)
        ukf.predict()
        ukf.update(np.array([z]))
        kf.predict()
        kf.update(np.array([z]))

    # UKF should match KF very closely on a linear model
    assert np.allclose(kf.state, ukf.state, atol=1e-4)
    assert np.allclose(kf.covariance, ukf.covariance, atol=1e-4)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])