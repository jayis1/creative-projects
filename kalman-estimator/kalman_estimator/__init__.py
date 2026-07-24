"""
kalman-estimator
===============

A from-scratch state-estimation library implementing four core estimators:

* **KalmanFilter**       — standard linear-discrete Kalman filter
* **ExtendedKalmanFilter** — Extended Kalman Filter (EKF) for nonlinear models
* **UnscentedKalmanFilter** — Unscented Kalman Filter (UKF) using the scaled unscented transform
* **RTSSmoother**          — Rauch-Tung-Striebel fixed-interval backward smoother

The library is written in pure Python with NumPy as the only dependency.
No external filtering / estimation packages are used — every algorithm is
implemented from first principles so the code is readable and auditable.

Typical usage
-------------

::

    import numpy as np
    from kalman_estimator import KalmanFilter

    kf = KalmanFilter(
        F=np.array([[1, 1], [0, 1]]),      # state transition
        H=np.array([[1, 0]]),              # observation
        Q=np.eye(2) * 0.01,                # process noise
        R=np.array([[1.0]]),              # measurement noise
        x0=np.array([0.0, 0.0]),           # initial state
        P0=np.eye(2) * 1.0,                # initial covariance
    )

    for z in measurements:
        kf.predict()
        kf.update(z)
        print(kf.state)
"""

from .kf import KalmanFilter
from .ekf import ExtendedKalmanFilter
from .ukf import UnscentedKalmanFilter
from .smoother import RTSSmoother, smooth

__all__ = [
    "KalmanFilter",
    "ExtendedKalmanFilter",
    "UnscentedKalmanFilter",
    "RTSSmoother",
    "smooth",
]

__version__ = "1.0.0"