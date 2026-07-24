"""Demo: track a 1-D constant-velocity object with all four estimators."""

import numpy as np
from kalman_estimator import (
    KalmanFilter,
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    smooth,
)


def generate_data(true_pos0=0.0, true_vel=1.0, steps=50, meas_noise=2.0, seed=42):
    rng = np.random.default_rng(seed)
    pos = true_pos0
    positions = []
    measurements = []
    for _ in range(steps):
        pos += true_vel
        positions.append(pos)
        measurements.append(pos + rng.normal(0, np.sqrt(meas_noise)))
    return np.array(positions), np.array(measurements)


def run_kf(measurements):
    """Standard linear KF on constant-velocity model."""
    dt = 1.0
    F = np.array([[1, dt], [0, 1]])
    H = np.array([[1, 0]])
    Q = np.array([[0.01, 0], [0, 0.01]])
    R = np.array([[2.0]])
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    states = []
    for z in measurements:
        kf.predict()
        kf.update(z)
        states.append(kf.state.copy())
    return np.array(states)


def run_ekf(measurements):
    """EKF for the same linear model (f and h are linear here)."""
    dt = 1.0

    def f(x, u):
        F = np.array([[1, dt], [0, 1]])
        return F @ x

    def h(x):
        return np.array([x[0]])

    def F_jac(x, u):
        return np.array([[1, dt], [0, 1]])

    def H_jac(x):
        return np.array([[1, 0]])

    Q = np.array([[0.01, 0], [0, 0.01]])
    R = np.array([[2.0]])
    ekf = ExtendedKalmanFilter(f, h, F_jac, H_jac, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    states = []
    for z in measurements:
        ekf.predict()
        ekf.update(z)
        states.append(ekf.state.copy())
    return np.array(states)


def run_ukf(measurements):
    """UKF for the same linear model."""
    dt = 1.0

    def fx(x, dt):
        F = np.array([[1, dt], [0, 1]])
        return F @ x

    def hx(x):
        return np.array([x[0]])

    Q = np.array([[0.01, 0], [0, 0.01]])
    R = np.array([[2.0]])
    ukf = UnscentedKalmanFilter(fx, hx, dt, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    states = []
    for z in measurements:
        ukf.predict()
        ukf.update(np.array([z]))
        states.append(ukf.state.copy())
    return np.array(states)


def run_smoother(measurements):
    """RTS smoother applied to the linear KF forward pass."""
    dt = 1.0
    F = np.array([[1, dt], [0, 1]])
    H = np.array([[1, 0]])
    Q = np.array([[0.01, 0], [0, 0.01]])
    R = np.array([[2.0]])
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    x_filt, P_filt, x_smooth, P_smooth = smooth(kf, measurements)
    return np.array(x_smooth)


def main():
    true_pos, meas = generate_data()
    print(f"Generated {len(true_pos)} steps; true final pos = {true_pos[-1]:.2f}")

    kf_states = run_kf(meas)
    ekf_states = run_ekf(meas)
    ukf_states = run_ukf(meas)
    sm_states = run_smoother(meas)

    print("\nFinal position estimates (true = {:.2f}):".format(true_pos[-1]))
    print(f"  KF       : {kf_states[-1, 0]:.3f}")
    print(f"  EKF      : {ekf_states[-1, 0]:.3f}")
    print(f"  UKF      : {ukf_states[-1, 0]:.3f}")
    print(f"  RTS smooth: {sm_states[-1, 0]:.3f}")

    # RMS errors
    def rmse(est, true):
        return np.sqrt(np.mean((est - true) ** 2))

    print("\nRMS position error:")
    print(f"  Measurements: {rmse(meas, true_pos):.3f}")
    print(f"  KF          : {rmse(kf_states[:, 0], true_pos):.3f}")
    print(f"  EKF         : {rmse(ekf_states[:, 0], true_pos):.3f}")
    print(f"  UKF         : {rmse(ukf_states[:, 0], true_pos):.3f}")
    print(f"  RTS smooth  : {rmse(sm_states[:, 0], true_pos):.3f}")


if __name__ == "__main__":
    main()