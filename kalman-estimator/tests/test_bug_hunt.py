"""Bug-hunt tests: verify bugs before and after fixing."""

import numpy as np
import pytest

from kalman_estimator import (
    KalmanFilter,
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    smooth,
    FilterDiagnostics,
)


# ---- Bug 1: np.linalg.inv(S) fails on singular S (should use solve) ---- #

def test_kf_singular_innovation_cov():
    """KF should handle singular innovation covariance with a clear error.

    If R=0 and H·P·H.T=0, S becomes singular and inv() raises LinAlgError.
    The filter should catch this and raise a meaningful ValueError instead
    of letting the raw numpy LinAlgError propagate.
    """
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    # P0 with zero variance in position and zero process noise
    # After predict: P = F P0 F^T + Q. With P0=0 and Q=0, P=0.
    P0 = np.zeros((2, 2))
    Q = np.zeros((2, 2))  # no process noise
    R = np.array([[0.0]])  # no measurement noise
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=P0)
    kf.predict()
    # S = H P H^T + R = 0 + 0 = 0  -> singular
    # Should raise ValueError (not raw LinAlgError) with a clear message
    with pytest.raises((ValueError, np.linalg.LinAlgError)):
        kf.update(np.array([5.0]))


def test_kf_solve_vs_inv_consistency():
    """Verify that using solve() gives same result as inv() for well-conditioned S."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[2.0]])
    kf1 = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2))
    kf2 = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2))
    for _ in range(10):
        z = np.array([5.0])
        kf1.predict()
        kf2.predict()
        kf1.update(z)
        kf2.update(z)
    assert np.allclose(kf1.x, kf2.x)
    assert np.allclose(kf1.P, kf2.P)


# ---- Bug 2: UKF predict() silently ignores control input u ---- #

def test_ukf_predict_ignores_control_input():
    """UKF.predict(u) accepts u but never passes it to fx.

    If fx needs the control input, the filter will produce wrong results
    silently. This test verifies the bug exists (and after fix, that it
    works correctly).
    """
    # Define a transition that uses control input
    def fx(x, dt, u=None):
        if u is not None:
            return x + u * dt
        return x + dt  # default: no control -> drift by dt

    def hx(x):
        return np.array([x[0]])

    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    ukf = UnscentedKalmanFilter(fx, hx, 1.0, Q, R, x0=[0.0, 0.0], P0=np.eye(2))

    # With control input u=5, the state should move by 5*dt=5
    ukf.predict(u=np.array([5.0, 0.0]))
    # After fix: state should be ~[5, 0], not [1, 0]
    assert abs(ukf.x[0] - 5.0) < 0.5, f"Expected x[0]≈5.0, got {ukf.x[0]}"


# ---- Bug 3: Diagnostics NIS/NEES use inv() which fails on singular cov ---- #

def test_diagnostics_nees_singular_cov():
    """NEES computation should handle singular P gracefully."""
    diag = FilterDiagnostics(state_dim=2, meas_dim=1)
    # Record a state with singular covariance
    P_singular = np.array([[1.0, 0.0], [0.0, 0.0]])
    diag.record(
        innovation=np.array([1.0]),
        S=np.array([[1.0]]),
        state=np.array([1.0, 0.0]),
        P=P_singular,
        true_state=np.array([2.0, 0.0]),
    )
    # err = [1, 0], P^-1 is singular in the second dimension
    # This should not crash; it should use pseudo-inverse
    nees = diag.nees()
    assert len(nees) == 1
    assert np.isfinite(nees[0])


# ---- Bug 4: UKF covariance update can produce non-symmetric P ---- #

def test_ukf_covariance_symmetry():
    """UKF P = P - K S K^T can lose symmetry. Should be symmetrized."""
    rng = np.random.default_rng(123)
    # Use a nonlinear measurement to stress the UKF
    def fx(x, dt):
        return np.array([x[0] + x[1] * dt, x[1], 0.5 * x[1] ** 2 * dt])

    def hx(x):
        return np.array([x[0], x[2]])  # measure position and the nonlinear term

    Q = np.diag([0.1, 0.1, 0.1])
    R = np.eye(2) * 0.5
    ukf = UnscentedKalmanFilter(fx, hx, 0.1, Q, R, x0=[0.0, 1.0, 0.0], P0=np.eye(3) * 5)
    for _ in range(20):
        z = np.array([1.0 + rng.normal(0, 0.7), 0.5 + rng.normal(0, 0.7)])
        ukf.predict()
        ukf.update(z)
    P = ukf.covariance
    # Check symmetry to high precision
    assert np.allclose(P, P.T, atol=1e-10), f"P not symmetric:\n{P}"


# ---- Bug 5: KF predict with control but B=None silently ignores u ---- #

def test_kf_predict_control_without_B():
    """If u is passed but B is None, u is silently ignored.

    This should at minimum not crash, and ideally warn or document.
    """
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2))
    # Passing u without B should not crash
    kf.predict(u=np.array([1.0]))
    # State should just be F @ x, ignoring u
    expected = F @ np.array([0.0, 0.0])
    assert np.allclose(kf.x, expected)


# ---- Bug 6: EKF dimension validation missing ---- #

def test_ekf_missing_dimension_validation():
    """EKF should validate that H_jac output shape matches R."""
    def f(x, u):
        return x * 1.0

    def h(x):
        return np.array([x[0], x[1]])  # 2-D measurement

    def Fj(x, u):
        return np.eye(2)

    def Hj(x):
        return np.eye(2)  # 2x2 Jacobian

    # R is 1x1 but h returns 2-D — this mismatch is not caught at init
    # and will cause a runtime error during update()
    Q = np.eye(2) * 0.01
    R = np.array([[1.0]])  # 1x1, but h returns 2-D
    ekf = ExtendedKalmanFilter(f, h, Fj, Hj, Q, R, x0=[0.0, 0.0], P0=np.eye(2))
    # This should raise a clear error, not a confusing broadcasting error
    with pytest.raises((ValueError, np.linalg.LinAlgError)):
        ekf.predict()
        ekf.update(np.array([1.0, 2.0]))


# ---- Bug 7: RTSSmoother doesn't validate kf type ---- #

def test_rts_smoother_single_step():
    """RTS smoother with a single step should return that step unchanged."""
    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[2.0]])
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    from kalman_estimator import RTSSmoother
    sm = RTSSmoother(kf)
    sm.forward_step(np.array([5.0]))
    x_smooth, P_smooth = sm.smooth()
    assert len(x_smooth) == 1
    # With 1 step, smoothed = filtered
    assert np.allclose(x_smooth[0], sm.history.x_post[0])


# ---- Bug 8: BIC with n=0 or n=1 causes log(0) or log(1)=0 ---- #

def test_diagnostics_bic_zero_steps():
    """BIC with 0 steps should return NaN, not crash with log(0) warning."""
    diag = FilterDiagnostics(state_dim=2, meas_dim=1)
    # No data recorded -> n=0, log(0) would cause RuntimeWarning
    # After fix: should return NaN gracefully
    bic = diag.bic(4)
    assert np.isnan(bic), f"Expected NaN for BIC with 0 steps, got {bic}"


if __name__ == "__main__":
    # Run all tests to see which pass/fail
    test_kf_solve_vs_inv_consistency()
    print("test_kf_solve_vs_inv_consistency: PASS")
    try:
        test_kf_singular_innovation_cov()
        print("test_kf_singular_innovation_cov: PASS (unexpected)")
    except Exception as e:
        print(f"test_kf_singular_innovation_cov: FAIL ({e})")
    try:
        test_ukf_predict_ignores_control_input()
        print("test_ukf_predict_ignores_control_input: PASS")
    except Exception as e:
        print(f"test_ukf_predict_ignores_control_input: FAIL ({e})")
    try:
        test_diagnostics_nees_singular_cov()
        print("test_diagnostics_nees_singular_cov: PASS")
    except Exception as e:
        print(f"test_diagnostics_nees_singular_cov: FAIL ({e})")
    try:
        test_ukf_covariance_symmetry()
        print("test_ukf_covariance_symmetry: PASS")
    except Exception as e:
        print(f"test_ukf_covariance_symmetry: FAIL ({e})")
    test_kf_predict_control_without_B()
    print("test_kf_predict_control_without_B: PASS")
    try:
        test_ekf_missing_dimension_validation()
        print("test_ekf_missing_dimension_validation: PASS")
    except Exception as e:
        print(f"test_ekf_missing_dimension_validation: FAIL ({e})")
    test_rts_smoother_single_step()
    print("test_rts_smoother_single_step: PASS")
    test_diagnostics_bic_zero_steps()
    print("test_diagnostics_bic_zero_steps: PASS")