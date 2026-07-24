"""
Nonlinear tracking demo: a falling object with air drag.

State:  x = [position, velocity, drag_coeff]
    dx/dt = v
    dv/dt = g - drag * v^2
    ddrag/dt = 0   (constant unknown parameter to be estimated)

We track this with EKF and UKF (no Jacobians needed for UKF).
"""

import numpy as np
from kalman_estimator import ExtendedKalmanFilter, UnscentedKalmanFilter


def generate_falling_data(
    x0=100.0, v0=0.0, drag=0.01, g=9.81, dt=0.1, steps=100, meas_noise=2.0, seed=42
):
    """Generate noisy position measurements of a falling object with drag."""
    rng = np.random.default_rng(seed)
    pos, vel = x0, v0
    true_states = []
    measurements = []
    for _ in range(steps):
        # simple Euler integration
        vel += (g - drag * vel ** 2) * dt
        pos -= vel * dt
        true_states.append([pos, vel, drag])
        measurements.append(pos + rng.normal(0, np.sqrt(meas_noise)))
    return np.array(true_states), np.array(measurements)


def run_ekf_falling(measurements, dt=0.1, g=9.81):
    """EKF for falling-with-drag model."""

    def f(x, u):
        """State transition (Euler integration)."""
        pos, vel, drag = x
        vel_new = vel + (g - drag * vel ** 2) * dt
        pos_new = pos - vel_new * dt
        return np.array([pos_new, vel_new, drag])

    def h(x):
        return np.array([x[0]])

    def F_jac(x, u):
        """Jacobian of f w.r.t. x = [pos, vel, drag]."""
        pos, vel, drag = x
        # d(vel_new)/d(vel) = 1 - 2*drag*vel*dt
        # d(vel_new)/d(drag) = -vel^2 * dt
        dvel_dvel = 1 - 2 * drag * vel * dt
        dvel_ddrag = -vel ** 2 * dt
        # d(pos_new)/d(pos) = 1, d(pos_new)/d(vel) = -dt
        return np.array([
            [1.0, -dt, 0.0],
            [0.0, dvel_dvel, dvel_ddrag],
            [0.0, 0.0, 1.0],
        ])

    def H_jac(x):
        return np.array([[1.0, 0.0, 0.0]])

    Q = np.diag([0.1, 0.1, 1e-6])
    R = np.array([[4.0]])
    ekf = ExtendedKalmanFilter(
        f, h, F_jac, H_jac, Q, R,
        x0=[100.0, 0.0, 0.005],
        P0=np.diag([100.0, 10.0, 1.0]),
    )
    states = []
    for z in measurements:
        ekf.predict()
        ekf.update(z)
        states.append(ekf.state.copy())
    return np.array(states)


def run_ukf_falling(measurements, dt=0.1, g=9.81):
    """UKF for falling-with-drag model (no Jacobians needed)."""

    def fx(x, dt):
        pos, vel, drag = x
        vel_new = vel + (g - drag * vel ** 2) * dt
        pos_new = pos - vel_new * dt
        return np.array([pos_new, vel_new, drag])

    def hx(x):
        return np.array([x[0]])

    Q = np.diag([0.1, 0.1, 1e-6])
    R = np.array([[4.0]])
    ukf = UnscentedKalmanFilter(
        fx, hx, dt, Q, R,
        x0=[100.0, 0.0, 0.005],
        P0=np.diag([100.0, 10.0, 1.0]),
    )
    states = []
    for z in measurements:
        ukf.predict()
        ukf.update(np.array([z]))
        states.append(ukf.state.copy())
    return np.array(states)


def main():
    true_states, meas = generate_falling_data()
    print(f"Falling object: {len(true_states)} steps, true drag = {true_states[0, 2]}")
    print(f"True final pos = {true_states[-1, 0]:.2f}, vel = {true_states[-1, 1]:.2f}")

    ekf_states = run_ekf_falling(meas)
    ukf_states = run_ukf_falling(meas)

    print(f"\nFinal state estimates (true = {true_states[-1]}):")
    print(f"  EKF: pos={ekf_states[-1, 0]:.2f}, vel={ekf_states[-1, 1]:.2f}, "
          f"drag={ekf_states[-1, 2]:.4f}")
    print(f"  UKF: pos={ukf_states[-1, 0]:.2f}, vel={ukf_states[-1, 1]:.2f}, "
          f"drag={ukf_states[-1, 2]:.4f}")

    def rmse(est, true):
        return np.sqrt(np.mean((est - true) ** 2))

    print("\nRMS errors:")
    print(f"  EKF position RMSE: {rmse(ekf_states[:, 0], true_states[:, 0]):.3f}")
    print(f"  UKF position RMSE: {rmse(ukf_states[:, 0], true_states[:, 0]):.3f}")
    print(f"  EKF velocity RMSE: {rmse(ekf_states[:, 1], true_states[:, 1]):.3f}")
    print(f"  UKF velocity RMSE: {rmse(ukf_states[:, 1], true_states[:, 1]):.3f}")
    print(f"  EKF drag    RMSE: {rmse(ekf_states[:, 2], true_states[:, 2]):.4f}")
    print(f"  UKF drag    RMSE: {rmse(ukf_states[:, 2], true_states[:, 2]):.4f}")


if __name__ == "__main__":
    main()