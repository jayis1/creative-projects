"""Tests for enhanced features: diagnostics, batch, serialization."""

import os
import tempfile
import numpy as np
import pytest

from kalman_estimator import (
    KalmanFilter,
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    smooth,
    FilterDiagnostics,
    batch_filter,
    monte_carlo_error,
    save_filter,
    load_filter,
)


def make_kf():
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[2.0]])
    return KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)


# ----------------------- diagnostics ----------------------- #

def test_diagnostics_nis():
    """NIS should average roughly meas_dim when model is correct."""
    rng = np.random.default_rng(42)
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])  # measurement noise
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    diag = FilterDiagnostics(state_dim=2, meas_dim=1)
    true_pos = 0.0
    for _ in range(200):
        true_pos += 1.0
        z = true_pos + rng.normal(0, 2.0)
        kf.predict()
        # compute innovation before update
        y = np.array([z]) - H @ kf.x
        S = H @ kf.P @ H.T + R
        kf.update(z)
        diag.record(y, S, kf.state, kf.covariance, true_state=np.array([true_pos, 1.0]))
    nis = diag.nis()
    assert nis.shape == (200,)
    # mean NIS should be near meas_dim=1 (within generous tolerance)
    assert abs(np.mean(nis) - 1.0) < 0.5


def test_diagnostics_nees():
    """NEES should average roughly state_dim when filter is consistent."""
    rng = np.random.default_rng(99)
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    diag = FilterDiagnostics(state_dim=2, meas_dim=1)
    true_pos = 0.0
    for _ in range(200):
        true_pos += 1.0
        z = true_pos + rng.normal(0, 2.0)
        kf.predict()
        y = np.array([z]) - H @ kf.x
        S = H @ kf.P @ H.T + R
        kf.update(z)
        diag.record(y, S, kf.state, kf.covariance, true_state=np.array([true_pos, 1.0]))
    nees = diag.nees()
    assert nees.shape == (200,)
    assert abs(np.mean(nees) - 2.0) < 1.5


def test_diagnostics_log_likelihood():
    """Log-likelihood should be a finite negative number."""
    rng = np.random.default_rng(7)
    kf = make_kf()
    diag = FilterDiagnostics(state_dim=2, meas_dim=1)
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    R = np.array([[2.0]])
    for _ in range(50):
        z = 5.0 + rng.normal(0, 1.5)
        kf.predict()
        y = np.array([z]) - H @ kf.x
        S = H @ kf.P @ H.T + R
        kf.update(z)
        diag.record(y, S, kf.state, kf.covariance)
    ll = diag.log_likelihood()
    assert np.isfinite(ll)
    assert ll < 0


def test_diagnostics_aic_bic():
    diag = FilterDiagnostics(state_dim=2, meas_dim=1)
    rng = np.random.default_rng(1)
    kf = make_kf()
    H = np.array([[1, 0]], dtype=float)
    R = np.array([[2.0]])
    for _ in range(30):
        z = 3.0 + rng.normal(0, 1.5)
        kf.predict()
        y = np.array([z]) - H @ kf.x
        S = H @ kf.P @ H.T + R
        kf.update(z)
        diag.record(y, S, kf.state, kf.covariance)
    assert diag.aic(4) > 0
    assert diag.bic(4) > 0


def test_diagnostics_summary():
    rng = np.random.default_rng(10)
    kf = make_kf()
    diag = FilterDiagnostics(state_dim=2, meas_dim=1)
    H = np.array([[1, 0]], dtype=float)
    R = np.array([[2.0]])
    for _ in range(20):
        z = 3.0 + rng.normal(0, 1.5)
        kf.predict()
        y = np.array([z]) - H @ kf.x
        S = H @ kf.P @ H.T + R
        kf.update(z)
        diag.record(y, S, kf.state, kf.covariance, true_state=np.array([3.0, 0.0]))
    s = diag.summary()
    assert s["n_steps"] == 20
    assert "log_likelihood" in s
    assert "nis_mean" in s
    assert "nees_mean" in s


# ----------------------- batch ----------------------- #

def test_batch_filter():
    """Batch filter should produce one result per measurement sequence."""
    rng = np.random.default_rng(5)
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])
    meas_list = []
    for _ in range(3):
        seq = []
        pos = 0.0
        for _ in range(30):
            pos += 1.0
            seq.append(pos + rng.normal(0, 2))
        meas_list.append(seq)
    results = batch_filter(meas_list, F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    assert len(results) == 3
    for states, covs in results:
        assert states.shape == (30, 2)
        assert covs.shape == (30, 2, 2)


def test_monte_carlo_error():
    """Monte Carlo RMSE should be lower than measurement noise."""
    rng = np.random.default_rng(6)
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])
    meas_list = []
    true_list = []
    for _ in range(5):
        meas_seq = []
        true_seq = []
        pos = 0.0
        for _ in range(50):
            pos += 1.0
            true_seq.append([pos, 1.0])
            meas_seq.append(pos + rng.normal(0, 2))
        meas_list.append(meas_seq)
        true_list.append(true_seq)
    rmse = monte_carlo_error(meas_list, true_list, F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    assert rmse.shape == (2,)
    assert rmse[0] < 3.0  # position RMSE < measurement noise


# ----------------------- serialization ----------------------- #

def test_save_load_filter_roundtrip():
    """Save and load should preserve filter state."""
    kf = make_kf()
    kf.predict()
    kf.update(np.array([5.0]))
    x_before = kf.x.copy()
    P_before = kf.P.copy()

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        save_filter(kf, path)
        kf2, _ = load_filter(path)
        assert np.allclose(kf2.x, x_before)
        assert np.allclose(kf2.P, P_before)
    finally:
        os.unlink(path)


def test_save_load_with_history():
    """Save with history should round-trip the history."""
    from kalman_estimator.smoother import RTSSmoother
    kf = make_kf()
    sm = RTSSmoother(kf)
    for _ in range(10):
        sm.forward_step(np.array([3.0]))
    # build history dict
    history = {
        "x_prior": sm.history.x_prior,
        "P_prior": sm.history.P_prior,
        "x_post": sm.history.x_post,
        "P_post": sm.history.P_post,
        "F_list": sm.history.F_list,
    }
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        save_filter(kf, path, include_history=True, history=history)
        kf2, hist = load_filter(path)
        assert hist is not None
        assert len(hist["x_post"]) == 10
    finally:
        os.unlink(path)


# ----------------------- EKF nonlinear ----------------------- #

def test_ekf_nonlinear_tracking():
    """EKF should track a nonlinear falling object better than raw measurements."""
    from demo_nonlinear import generate_falling_data, run_ekf_falling
    true_states, meas = generate_falling_data(seed=123, steps=80)
    ekf_states = run_ekf_falling(meas)
    # EKF position RMSE should be less than measurement RMSE
    meas_rmse = np.sqrt(np.mean((meas - true_states[:, 0]) ** 2))
    ekf_rmse = np.sqrt(np.mean((ekf_states[:, 0] - true_states[:, 0]) ** 2))
    assert ekf_rmse < meas_rmse


def test_ukf_nonlinear_tracking():
    """UKF should track the falling object better than raw measurements."""
    from demo_nonlinear import generate_falling_data, run_ukf_falling
    true_states, meas = generate_falling_data(seed=123, steps=80)
    ukf_states = run_ukf_falling(meas)
    meas_rmse = np.sqrt(np.mean((meas - true_states[:, 0]) ** 2))
    ukf_rmse = np.sqrt(np.mean((ukf_states[:, 0] - true_states[:, 0]) ** 2))
    assert ukf_rmse < meas_rmse


# ----------------------- input validation ----------------------- #

def test_kf_rejects_nan_measurement():
    kf = make_kf()
    kf.predict()
    with pytest.raises(ValueError):
        kf.update(np.array([np.nan]))


def test_ukf_rejects_mismatched_x0():
    from kalman_estimator import UnscentedKalmanFilter
    with pytest.raises(ValueError):
        UnscentedKalmanFilter(
            fx=lambda x, dt: x,
            hx=lambda x: np.array([x[0]]),
            dt=0.1,
            Q=np.eye(3),
            R=np.array([[1.0]]),
            x0=[0.0, 0.0],  # wrong dim — should be 3
            P0=np.eye(3),
        )


if __name__ == "__main__":
    test_diagnostics_nis()
    test_diagnostics_nees()
    test_diagnostics_log_likelihood()
    test_diagnostics_aic_bic()
    test_diagnostics_summary()
    test_batch_filter()
    test_monte_carlo_error()
    test_save_load_filter_roundtrip()
    test_save_load_with_history()
    test_ekf_nonlinear_tracking()
    test_ukf_nonlinear_tracking()
    test_kf_rejects_nan_measurement()
    test_ukf_rejects_mismatched_x0()
    print("All enhanced tests passed.")