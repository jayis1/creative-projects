"""Basic sanity tests for the kalman-estimator library."""

import numpy as np
from kalman_estimator import (
    KalmanFilter,
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    smooth,
)


def make_kf():
    F = np.array([[1, 1], [0, 1]])
    H = np.array([[1, 0]])
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    return KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2))


def test_kf_converges():
    """KF estimate should approach true state with enough measurements."""
    rng = np.random.default_rng(0)
    true_pos = 0.0
    kf = make_kf()
    for _ in range(100):
        true_pos += 1.0
        z = true_pos + rng.normal(0, 1)
        kf.predict()
        kf.update(z)
    assert abs(kf.state[0] - true_pos) < 5.0
    assert abs(kf.state[1] - 1.0) < 1.0


def test_kf_covariance_symmetric():
    kf = make_kf()
    kf.predict()
    kf.update(np.array([5.0]))
    P = kf.covariance
    assert np.allclose(P, P.T, atol=1e-10)


def test_ekf_linear_matches_kf():
    """For a linear model, EKF should give results very close to KF."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2))

    def f(x, u):
        return F @ x

    def h(x):
        return np.array([x[0]])

    def Fj(x, u):
        return F

    def Hj(x):
        return H

    ekf = ExtendedKalmanFilter(f, h, Fj, Hj, Q, R, x0=[0.0, 0.0], P0=np.eye(2))
    rng = np.random.default_rng(1)
    for _ in range(20):
        z = 5.0 + rng.normal(0, 1)
        kf.predict()
        kf.update(z)
        ekf.predict()
        ekf.update(z)
    assert np.allclose(kf.state, ekf.state, atol=1e-6)


def test_ukf_linear_matches_kf():
    """For a linear model, UKF should match KF very closely."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2))

    def fx(x, dt):
        return F @ x

    def hx(x):
        return np.array([x[0]])

    ukf = UnscentedKalmanFilter(fx, hx, 1.0, Q, R, x0=[0.0, 0.0], P0=np.eye(2))
    rng = np.random.default_rng(2)
    for _ in range(20):
        z = 5.0 + rng.normal(0, 1)
        kf.predict()
        kf.update(z)
        ukf.predict()
        ukf.update(np.array([z]))
    assert np.allclose(kf.state, ukf.state, atol=1e-4)


def test_rts_smoother_reduces_error():
    """RTS-smoothed estimates should have <= RMS error than filtered."""
    rng = np.random.default_rng(3)
    true_pos = 0.0
    true_states = []
    meas = []
    for _ in range(50):
        true_pos += 1.0
        true_states.append(true_pos)
        meas.append(true_pos + rng.normal(0, 2))
    true_states = np.array(true_states)
    meas = np.array(meas)

    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    x_filt, P_filt, x_smooth, P_smooth = smooth(kf, meas)

    rmse_filt = np.sqrt(np.mean((np.array([x[0] for x in x_filt]) - true_states) ** 2))
    rmse_smooth = np.sqrt(np.mean((np.array([x[0] for x in x_smooth]) - true_states) ** 2))
    assert rmse_smooth <= rmse_filt


def test_dimension_validation():
    """Bad dimensions should raise ValueError."""
    import pytest

    with pytest.raises(ValueError):
        KalmanFilter(
            F=np.eye(3),       # 3x3
            H=np.array([[1, 0]]),  # 1x2 -- mismatch
            Q=np.eye(3),
            R=np.array([[1.0]]),
            x0=[0, 0, 0],
            P0=np.eye(3),
        )


if __name__ == "__main__":
    test_kf_converges()
    test_kf_covariance_symmetric()
    test_ekf_linear_matches_kf()
    test_ukf_linear_matches_kf()
    test_rts_smoother_reduces_error()
    test_dimension_validation()
    print("All tests passed.")