"""Extended Kalman Filter (EKF).

For nonlinear models

    x_k = f(x_{k-1}, u_k) + w_k
    z_k = h(x_k)          + v_k

the EKF linearises f and h around the current estimate using Jacobians.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from .base import BaseEstimator


class ExtendedKalmanFilter(BaseEstimator):
    """Extended Kalman Filter.

    Parameters
    ----------
    f : callable(x, u) -> x_next
        Nonlinear state transition function.
    h : callable(x) -> z
        Nonlinear measurement function.
    F_jac : callable(x, u) -> (n, n)
        Jacobian of f w.r.t. x.
    H_jac : callable(x) -> (m, n)
        Jacobian of h w.r.t. x.
    Q, R, x0, P0 : as in KalmanFilter.
    """

    def __init__(self, f, h, F_jac, H_jac, Q, R, x0, P0):
        self.f = f
        self.h = h
        self.F_jac = F_jac
        self.H_jac = H_jac
        self.Q = np.atleast_2d(Q).astype(float)
        self.R = np.atleast_2d(R).astype(float)
        self.x = np.atleast_1d(x0).astype(float)
        self.P = np.atleast_2d(P0).astype(float)

        self.n = self.Q.shape[0]
        self.m = self.R.shape[0]
        if self.P.shape != (self.n, self.n):
            raise ValueError("P0 shape mismatch with Q")
        if self.x.shape != (self.n,):
            raise ValueError("x0 shape mismatch with Q")
        self.I = np.eye(self.n)

    def predict(self, u: Optional[np.ndarray] = None) -> None:
        """EKF prediction step (uses Jacobian of f at current state)."""
        F = np.atleast_2d(self.F_jac(self.x, u)).astype(float)
        self.x = np.asarray(self.f(self.x, u), dtype=float).ravel()
        self.P = F @ self.P @ F.T + self.Q

    def update(self, z: np.ndarray) -> None:
        """EKF update step (uses Jacobian of h at predicted state).

        Raises
        ------
        ValueError
            If *z* contains NaN or Inf.
        """
        z = np.atleast_1d(z).astype(float)
        if not np.all(np.isfinite(z)):
            raise ValueError("measurement contains NaN or Inf")
        H = np.atleast_2d(self.H_jac(self.x)).astype(float)
        y = z - np.asarray(self.h(self.x), dtype=float).ravel()  # innovation
        S = H @ self.P @ H.T + self.R
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            raise ValueError(
                "Innovation covariance S is singular in EKF update."
            )
        self.x = self.x + K @ y
        KH = K @ H
        self.P = (self.I - KH) @ self.P @ (self.I - KH).T + K @ self.R @ K.T

    @property
    def state(self):
        return self.x.copy()

    @property
    def covariance(self):
        return self.P.copy()

    def step(self, z: np.ndarray, u: Optional[np.ndarray] = None) -> np.ndarray:
        self.predict(u)
        self.update(z)
        return self.state