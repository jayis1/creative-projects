"""Example: GPS-like position tracking with the Kalman Filter.

Simulates a 2-D tracking scenario where a moving object is observed
via noisy position measurements (like GPS).  Uses a constant-velocity
model and shows how the KF estimates both position and velocity.

Usage::

    python examples/gps_tracking.py
"""

import numpy as np

from kalman_estimator import KalmanFilter, smooth, FilterDiagnostics


def main():
    # Ground truth: object moving at constant velocity in 2-D
    dt = 0.1
    steps = 200
    true_vel = np.array([3.0, 4.0])  # 5 m/s at 53° angle
    true_pos = np.array([0.0, 0.0])

    rng = np.random.default_rng(42)
    true_states = []
    measurements = []

    for _ in range(steps):
        true_pos = true_pos + true_vel * dt
        true_states.append([true_pos[0], true_pos[1], true_vel[0], true_vel[1]])
        # GPS measurement with 5m std-dev noise
        meas = true_pos + rng.normal(0, 5.0, size=2)
        measurements.append(meas)

    true_states = np.array(true_states)
    measurements = np.array(measurements)

    # State: [x, y, vx, vy]
    F = np.array([
        [1, 0, dt, 0],
        [0, 1, 0, dt],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ], dtype=float)
    H = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
    ], dtype=float)
    Q = np.diag([0.1, 0.1, 0.01, 0.01])
    R = np.eye(2) * 25.0  # 5^2 = 25
    x0 = [0.0, 0.0, 0.0, 0.0]
    P0 = np.diag([100.0, 100.0, 10.0, 10.0])

    kf = KalmanFilter(F, H, Q, R, x0=x0, P0=P0)
    diag = FilterDiagnostics(state_dim=4, meas_dim=2)

    filtered_states = []
    for z in measurements:
        kf.predict()
        # compute innovation for diagnostics
        y = z - H @ kf.x
        S = H @ kf.P @ H.T + R
        kf.update(z)
        filtered_states.append(kf.state.copy())
        diag.record(y, S, kf.state, kf.covariance,
                    true_state=true_states[len(filtered_states) - 1])

    filtered_states = np.array(filtered_states)

    # RTS smoothing
    kf2 = KalmanFilter(F, H, Q, R, x0=x0, P0=P0)
    _, _, x_smooth, _ = smooth(kf2, measurements)

    smoothed_states = np.array(x_smooth)

    # Print results
    def rmse(est, true):
        return np.sqrt(np.mean((est - true) ** 2))

    pos_rmse_meas = rmse(measurements[:, 0], true_states[:, 0])
    pos_rmse_filt = rmse(filtered_states[:, 0], true_states[:, 0])
    pos_rmse_smooth = rmse(smoothed_states[:, 0], true_states[:, 0])
    vel_rmse_filt = rmse(filtered_states[:, 2], true_states[:, 2])

    print(f"\n{'='*55}")
    print(f"  2-D GPS Tracking with KF + RTS Smoother")
    print(f"{'='*55}")
    print(f"  True velocity:  ({true_vel[0]}, {true_vel[1]}) m/s")
    print(f"  Estimated vel:  ({filtered_states[-1, 2]:.2f}, {filtered_states[-1, 3]:.2f}) m/s")
    print(f"\n  Position RMSE:")
    print(f"    GPS (raw):      {pos_rmse_meas:.3f} m")
    print(f"    KF filtered:    {pos_rmse_filt:.3f} m")
    print(f"    RTS smoothed:   {pos_rmse_smooth:.3f} m")
    print(f"  Velocity RMSE (KF): {vel_rmse_filt:.3f} m/s")
    print(f"{'='*55}")

    # Diagnostics
    s = diag.summary()
    print(f"\n  Diagnostics:")
    print(f"    NIS mean:       {s['nis_mean']:.3f} (expected ~2.0)")
    print(f"    NEES mean:      {s['nees_mean']:.3f} (expected ~4.0)")
    print(f"    Log-likelihood: {s['log_likelihood']:.2f}")
    print(f"    NIS in 95% CI:  {s.get('nis_in_ci', 'N/A')*100:.1f}%")


if __name__ == "__main__":
    main()