"""Ensemble Kalman Filter (EnKF).

The EnKF is a Monte-Carlo variant of the Kalman filter designed for
high-dimensional or nonlinear systems where maintaining the full
covariance matrix is infeasible.  Instead, it propagates an *ensemble*
of N state samples and estimates the mean/covariance empirically.

Model::

    x_k = f(x_{k-1}) + w_k      (nonlinear transition OK)
    z_k = h(x_k)       + v_k    (nonlinear measurement OK)

The EnKF works with both linear and nonlinear models — no Jacobians
required.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from .base import BaseEstimator


class EnsembleKalmanFilter(BaseEstimator):
    """Ensemble Kalman Filter.

    Parameters
    ----------
    f : callable(x) -> x_next
        State transition function (can be nonlinear).
    h : callable(x) -> z
        Measurement function (can be nonlinear).
    Q : (n, n) process noise covariance.
    R : (m, m) measurement noise covariance.
    x0 : (n,) initial mean.
    P0 : (n, n) initial covariance.
    N : int
        Ensemble size (number of particles).
    seed : int
        Random seed for reproducibility.
    """

    def __init__(
        self,
        f: Callable,
        h: Callable,
        Q: np.ndarray,
        R: np.ndarray,
        x0: np.ndarray,
        P0: np.ndarray,
        N: int = 50,
        seed: int = 42,
    ):
        self.f = f
        self.h = h
        self.Q = np.atleast_2d(Q).astype(float)
        self.R = np.atleast_2d(R).astype(float)
        self.N = max(N, 2)
        self.n = self.Q.shape[0]
        self.m = self.R.shape[0]
        self._rng = np.random.default_rng(seed)

        x0 = np.atleast_1d(x0).astype(float)
        P0 = np.atleast_2d(P0).astype(float)
        if x0.shape != (self.n,):
            raise ValueError(f"x0 must have shape ({self.n},)")
        if P0.shape != (self.n, self.n):
            raise ValueError(f"P0 must have shape ({self.n}, {self.n})")

        # initialise ensemble by sampling from N(x0, P0)
        L = np.linalg.cholesky(P0 + 1e-12 * np.eye(self.n))
        self.ensemble = x0[None, :] + (self._rng.standard_normal((self.N, self.n)) @ L.T)

    # ------------------------------------------------------------------ #
    #  Prediction
    # ------------------------------------------------------------------ #
    def predict(self, u: Optional[np.ndarray] = None) -> None:
        """Propagate each ensemble member through *f* and add process noise."""
        L_Q = np.linalg.cholesky(self.Q + 1e-12 * np.eye(self.n))
        for i in range(self.N):
            noise = self._rng.standard_normal(self.n) @ L_Q.T
            self.ensemble[i] = np.asarray(
                self.f(self.ensemble[i]), dtype=float
            ).ravel() + noise

    # ------------------------------------------------------------------ #
    #  Update
    # ------------------------------------------------------------------ #
    def update(self, z: np.ndarray) -> None:
        """Stochastic EnKF update using perturbed observations."""
        z = np.atleast_1d(z).astype(float)
        if z.shape != (self.m,):
            raise ValueError(f"measurement must have shape ({self.m},), got {z.shape}")
        if not np.all(np.isfinite(z)):
            raise ValueError("measurement contains NaN or Inf")

        # predicted measurements from ensemble
        Z_pred = np.zeros((self.N, self.m))
        for i in range(self.N):
            Z_pred[i] = np.asarray(self.h(self.ensemble[i]), dtype=float).ravel()

        x_mean = self.ensemble.mean(axis=0)
        z_mean = Z_pred.mean(axis=0)

        # empirical covariances
        X_dev = self.ensemble - x_mean           # (N, n)
        Z_dev = Z_pred - z_mean                  # (N, m)
        P_xz = (X_dev.T @ Z_dev) / (self.N - 1)  # (n, m)
        P_zz = (Z_dev.T @ Z_dev) / (self.N - 1) + self.R  # (m, m)

        try:
            K = P_xz @ np.linalg.inv(P_zz)
        except np.linalg.LinAlgError:
            K = P_xz @ np.linalg.pinv(P_zz)

        # perturbed observations (stochastic EnKF)
        L_R = np.linalg.cholesky(self.R + 1e-12 * np.eye(self.m))
        for i in range(self.N):
            noise = self._rng.standard_normal(self.m) @ L_R.T
            z_perturbed = z + noise
            self.ensemble[i] = self.ensemble[i] + K @ (z_perturbed - Z_pred[i])

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #
    @property
    def state(self) -> np.ndarray:
        """Ensemble mean as the state estimate."""
        return self.ensemble.mean(axis=0).copy()

    @property
    def covariance(self) -> np.ndarray:
        """Empirical ensemble covariance."""
        X_dev = self.ensemble - self.ensemble.mean(axis=0)
        return (X_dev.T @ X_dev) / (self.N - 1)

    @property
    def ensemble_members(self) -> np.ndarray:
        """Current ensemble (N × n array)."""
        return self.ensemble.copy()

    def step(self, z: np.ndarray, u: Optional[np.ndarray] = None) -> np.ndarray:
        self.predict(u)
        self.update(z)
        return self.state