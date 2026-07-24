"""
kalman-estimator
===============

A from-scratch state-estimation library implementing eight estimators:

* **KalmanFilter**            — standard linear-discrete Kalman filter
* **ExtendedKalmanFilter**    — Extended Kalman Filter (EKF) for nonlinear models
* **UnscentedKalmanFilter**   — Unscented Kalman Filter (UKF) using the scaled unscented transform
* **InformationFilter**       — information-form (dual) Kalman filter
* **AdaptiveKalmanFilter**    — Sage-Husa adaptive KF with online Q/R estimation
* **EnsembleKalmanFilter**    — Monte-Carlo ensemble Kalman filter
* **ParticleFilter**          — bootstrap particle filter (SIR)
* **RTSSmoother** / smooth()  — Rauch-Tung-Striebel fixed-interval backward smoother

Plus supporting utilities:

* **NumericalJacobianEKF**    — EKF with automatic finite-difference Jacobians
* **numerical_jacobian**      — central-difference Jacobian helper
* **FilterDiagnostics**       — NIS, NEES, log-likelihood, AIC/BIC
* **batch_filter / monte_carlo_error** — multi-run utilities
* **save_filter / load_filter** — JSON serialization
* **load_config / load_filter_from_config** — JSON/TOML config support

The library is written in pure Python with NumPy as the only hard dependency.
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

from .base import BaseEstimator
from .kf import KalmanFilter
from .ekf import ExtendedKalmanFilter
from .ukf import UnscentedKalmanFilter
from .info_filter import InformationFilter
from .adaptive import AdaptiveKalmanFilter
from .enkf import EnsembleKalmanFilter
from .particle_filter import ParticleFilter
from .smoother import RTSSmoother, smooth
from .diagnostics import FilterDiagnostics
from .batch import batch_filter, monte_carlo_error
from .serialization import save_filter, load_filter
from .numerical_jacobian import numerical_jacobian, NumericalJacobianEKF
from .config import load_config, load_filter_from_config, save_config

__all__ = [
    # Base
    "BaseEstimator",
    # Filters
    "KalmanFilter",
    "ExtendedKalmanFilter",
    "UnscentedKalmanFilter",
    "InformationFilter",
    "AdaptiveKalmanFilter",
    "EnsembleKalmanFilter",
    "ParticleFilter",
    # Smoother
    "RTSSmoother",
    "smooth",
    # Diagnostics
    "FilterDiagnostics",
    # Batch utilities
    "batch_filter",
    "monte_carlo_error",
    # Serialization
    "save_filter",
    "load_filter",
    # Numerical Jacobians
    "numerical_jacobian",
    "NumericalJacobianEKF",
    # Config
    "load_config",
    "load_filter_from_config",
    "save_config",
]

__version__ = "3.0.0"