"""Standard linear-discrete Kalman filter.

This module implements the textbook linear Kalman filter for models of the form

    x_k = F x_{k-1} + B u_k + w_k      (process / dynamics)
    z_k = H x_k       + v_k            (measurement)

where w ~ N(0, Q) and v ~ N(0, R).
"""

from __future__ import annotations

import numpy as np


class KalmanFilter:
    """Linear Kalman filter.

    Parameters
    ----------
    F : (n, n) array_like
        State transition matrix.
    H : (m, n) array_like
        Observation matrix.
    Q : (n, n) array_like
        Process noise covariance.
    R : (m, m) array_like
        Measurement noise covariance.
    x0 : (n,) array_like
        Initial state estimate.
    P0 : (n, n) array_like
        Initial estimate covariance.
    B : (n, p) array_like or None
        Optional control-input matrix.
    """

    def __init__(
        self,
        F,
        H,
        Q,
        R,
        x0,
        P0,
        B=None,
    ):
        self.F = np.atleast_2d(F).astype(float)
        self.H = np.atleast_2d(H).astype(float)
        self.Q = np.atleast_2d(Q).astype(float)
        self.R = np.atleast_2d(R).astype(float)
        self.x = np.atleast_1d(x0).astype(float)
        self.P = np.atleast_2d(P0).astype(float)
        self.B = None if B is None else np.atleast_2d(B).astype(float)

        # dimension checks
        n = self.F.shape[0]
        m = self.H.shape[0]
        if self.F.shape != (n, n):
            raise ValueError("F must be square (n x n)")
        if self.H.shape[1] != n:
            raise ValueError("H must have shape (m x n)")
        if self.Q.shape != (n, n):
            raise ValueError("Q must have shape (n x n)")
        if self.R.shape != (m, m):
            raise ValueError("R must have shape (m x m)")
        if self.x.shape != (n,):
            raise ValueError(f"x0 must have shape ({n},)")
        if self.P.shape != (n, n):
            raise ValueError(f"P0 must have shape ({n}, {n})")
        if self.B is not None and self.B.shape[0] != n:
            raise ValueError("B must have shape (n, p)")

        self.n = n
        self.m = m
        self.I = np.eye(n)

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def predict(self, u=None):
        """Time-update / prediction step.

        Parameters
        ----------
        u : (p,) array_like or None
            Optional control input.
        """
        if u is not None and self.B is not None:
            self.x = self.F @ self.x + self.B @ np.atleast_1d(u).astype(float)
        else:
            self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, z):
        """Measurement-update / correction step.

        Parameters
        ----------
        z : (m,) array_like
            Measurement vector.
        """
        z = np.atleast_1d(z).astype(float)
        y = z - self.H @ self.x            # innovation / residual
        S = self.H @ self.P @ self.H.T + self.R  # innovation covariance
        K = self.P @ self.H.T @ np.linalg.inv(S)  # Kalman gain
        self.x = self.x + K @ y
        # Joseph form for numerical stability (guarantees symmetric, PSD P)
        KH = K @ self.H
        self.P = (self.I - KH) @ self.P @ (self.I - KH).T + K @ self.R @ K.T

    @property
    def state(self):
        """Current posterior state estimate."""
        return self.x.copy()

    @property
    def covariance(self):
        """Current posterior state covariance."""
        return self.P.copy()

    def step(self, z, u=None):
        """Convenience: run predict() then update(z)."""
        self.predict(u)
        self.update(z)
        return self.state