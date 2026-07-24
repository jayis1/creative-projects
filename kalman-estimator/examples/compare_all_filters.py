"""Example: comparing all filter types on a constant-velocity tracking problem.

This script demonstrates every estimator in the library on the same
1-D tracking scenario and prints a comparison table.

Usage::

    python examples/compare_all_filters.py
"""

import numpy as np

from kalman_estimator import (
    KalmanFilter,
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    InformationFilter,
    AdaptiveKalmanFilter,
    EnsembleKalmanFilter,
    ParticleFilter,
    smooth,
    FilterDiagnostics,
)


def generate_data(steps=100, true_vel=1.0, noise_std=2.0, seed=42):
    """Generate noisy position measurements of a constant-velocity object."""
    rng = np.random.default_rng(seed)
    pos = 0.0
    true_states, measurements = [], []
    for _ in range(steps):
        pos += true_vel
        true_states.append([pos, true_vel])
        measurements.append([pos + rng.normal(0, noise_std)])
    return np.array(true_states), np.array(measurements)


def rmse(est, true):
    return np.sqrt(np.mean((est - true) ** 2))


def main():
    true_states, measurements = generate_data()

    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[4.0]])
    x0 = [0.0, 0.0]
    P0 = np.eye(2) * 10.0

    results = {}

    # --- Linear Kalman Filter --- #
    kf = KalmanFilter(F, H, Q, R, x0=x0, P0=P0)
    states = []
    for z in measurements:
        kf.predict()
        kf.update(z)
        states.append(kf.state.copy())
    results["KF"] = np.array(states)

    # --- Extended Kalman Filter --- #
    def f(x, u):
        return F @ x
    def h(x):
        return np.array([x[0]])
    def Fj(x, u):
        return F
    def Hj(x):
        return H
    ekf = ExtendedKalmanFilter(f, h, Fj, Hj, Q, R, x0=x0, P0=P0)
    states = []
    for z in measurements:
        ekf.predict()
        ekf.update(z)
        states.append(ekf.state.copy())
    results["EKF"] = np.array(states)

    # --- Unscented Kalman Filter --- #
    def fx(x, dt):
        return F @ x
    def hx(x):
        return np.array([x[0]])
    ukf = UnscentedKalmanFilter(fx, hx, 1.0, Q, R, x0=x0, P0=P0)
    states = []
    for z in measurements:
        ukf.predict()
        ukf.update(z)
        states.append(ukf.state.copy())
    results["UKF"] = np.array(states)

    # --- Information Filter --- #
    Y0 = np.linalg.inv(P0)
    y0 = Y0 @ np.array(x0)
    inf = InformationFilter(F, H, Q, R, y0=y0, Y0=Y0)
    states = []
    for z in measurements:
        inf.predict()
        inf.update(z)
        states.append(inf.state.copy())
    results["InfoFilter"] = np.array(states)

    # --- Adaptive Kalman Filter --- #
    akf = AdaptiveKalmanFilter(F, H, Q, R, x0=x0, P0=P0, alpha=0.95)
    states = []
    for z in measurements:
        akf.predict()
        akf.update(z)
        states.append(akf.state.copy())
    results["AdaptiveKF"] = np.array(states)

    # --- Ensemble Kalman Filter --- #
    def fe(x):
        return F @ x
    def he(x):
        return np.array([x[0]])
    enkf = EnsembleKalmanFilter(fe, he, Q, R, x0=x0, P0=P0, N=100, seed=42)
    states = []
    for z in measurements:
        enkf.predict()
        enkf.update(z)
        states.append(enkf.state.copy())
    results["EnKF"] = np.array(states)

    # --- Particle Filter --- #
    def fp(x, u=None):
        return F @ x
    def hp(x):
        return np.array([x[0]])
    pf = ParticleFilter(fp, hp, Q, R, x0=x0, P0=P0, N=500, seed=42)
    states = []
    for z in measurements:
        pf.predict()
        pf.update(z)
        states.append(pf.state.copy())
    results["PF"] = np.array(states)

    # --- RTS Smoother --- #
    kf2 = KalmanFilter(F, H, Q, R, x0=x0, P0=P0)
    _, _, x_sm, _ = smooth(kf2, [z[0] for z in measurements])
    results["RTS"] = np.array(x_sm)

    # Print comparison table
    meas_rmse = rmse(measurements[:, 0], true_states[:, 0])
    print(f"\n{'='*65}")
    print(f"  Filter Comparison on 1-D Constant-Velocity Tracking")
    print(f"  Steps=100, Measurement Noise Std=2.0")
    print(f"{'='*65}")
    print(f"  {'Filter':<15} {'Pos RMSE':>10} {'Vel RMSE':>10} {'Improv %':>10}")
    print(f"  {'-'*49}")
    print(f"  {'Measurements':<15} {meas_rmse:>10.4f} {'--':>10} {'0.0':>10}")
    for name, est in results.items():
        pos_rmse = rmse(est[:, 0], true_states[:, 0])
        vel_rmse = rmse(est[:, 1], true_states[:, 1])
        improv = ((meas_rmse - pos_rmse) / meas_rmse * 100) if meas_rmse > 0 else 0
        print(f"  {name:<15} {pos_rmse:>10.4f} {vel_rmse:>10.4f} {improv:>9.1f}%")
    print(f"{'='*65}")

    # Show adapted noise estimates
    print(f"\n  AdaptiveKF estimated R: {akf.estimated_R[0,0]:.4f} (true: 4.0)")
    print(f"  AdaptiveKF estimated Q: {akf.estimated_Q[0,0]:.4f} (true: 0.01)")
    print(f"  ParticleFilter effective N: {pf.effective_sample_size:.1f} / {pf.N}")


if __name__ == "__main__":
    main()