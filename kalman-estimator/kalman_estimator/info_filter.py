"""Information Filter — the dual of the Kalman Filter.

Instead of maintaining (x, P) (mean and covariance), the information
filter maintains the *information vector* ``y = P⁻¹ x`` and the
*information matrix* ``Y = P⁻¹``.  This formulation makes the prediction
step more expensive but the update step trivial — useful when
measurements are very precise or when fusing many independent sources.

Model::

    x_k = F x_{k-1} + w_k      (w ~ N(0, Q))
    z_k = H x_k       + v_k    (v ~ N(0, R))
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .base import BaseEstimator


class InformationFilter(BaseEstimator):
    """Linear information filter (dual of KalmanFilter).

    Parameters
    ----------
    F, H, Q, R : model matrices (same meaning as KalmanFilter).
    y0 : (n,) initial information vector (= P0⁻¹ x0).
    Y0 : (n, n) initial information matrix (= P0⁻¹).
    """

    def __init__(self, F, H, Q, R, y0, Y0):
        self.F = np.atleast_2d(F).astype(float)
        self.H = np.atleast_2d(H).astype(float)
        self.Q = np.atleast_2d(Q).astype(float)
        self.R = np.atleast_2d(R).astype(float)
        self.y = np.atleast_1d(y0).astype(float)       # info vector
        self.Y = np.atleast_2d(Y0).astype(float)        # info matrix

        self.n = self.F.shape[0]
        self.m = self.H.shape[0]
        if self.F.shape != (self.n, self.n):
            raise ValueError("F must be (n, n)")
        if self.H.shape[1] != self.n:
            raise ValueError("H must be (m, n)")
        if self.Q.shape != (self.n, self.n):
            raise ValueError("Q must be (n, n)")
        if self.R.shape != (self.m, self.m):
            raise ValueError("R must be (m, m)")
        if self.y.shape != (self.n,):
            raise ValueError(f"y0 must have shape ({self.n},)")
        if self.Y.shape != (self.n, self.n):
            raise ValueError(f"Y0 must have shape ({self.n}, {self.n})")

        # pre-compute useful quantities
        self.I_n = np.eye(self.n)
        self._F_inv = np.linalg.inv(self.F)  # F assumed invertible

    # ------------------------------------------------------------------ #
    #  Prediction (expensive — requires matrix inversion)
    # ------------------------------------------------------------------ #
    def predict(self, u: Optional[np.ndarray] = None) -> None:
        """Information-form prediction step.

        .. math::
            Y_k^- = [F Y_{k-1}^{-1} F^T + Q]^{-1}
            y_k^- = Y_k^- F Y_{k-1}^{-1} y_{k-1}

        Control input *u* is ignored in the information form unless
        a control matrix ``B`` has been set via :attr:`B`.
        """
        # Recover covariance for prediction
        P = np.linalg.inv(self.Y)
        P_pred = self.F @ P @ self.F.T + self.Q
        x = np.linalg.solve(self.Y, self.y)  # = P y_info = x
        x_pred = self.F @ x
        self.Y = np.linalg.inv(P_pred)
        self.y = self.Y @ x_pred

    # ------------------------------------------------------------------ #
    #  Update (trivial — just add information)
    # ------------------------------------------------------------------ #
    def update(self, z: np.ndarray) -> None:
        """Information-form update: ``Y += Hᵀ R⁻¹ H``, ``y += Hᵀ R⁻¹ z``."""
        z = np.atleast_1d(z).astype(float)
        if z.shape != (self.m,):
            raise ValueError(f"measurement must have shape ({self.m},), got {z.shape}")
        if not np.all(np.isfinite(z)):
            raise ValueError("measurement contains NaN or Inf")
        Ht_Rinv = self.H.T @ np.linalg.inv(self.R)
        self.Y = self.Y + Ht_Rinv @ self.H
        self.y = self.y + Ht_Rinv @ z

    # ------------------------------------------------------------------ #
    #  Conversions
    # ------------------------------------------------------------------ #
    @property
    def state(self) -> np.ndarray:
        """Recover the mean estimate ``x = Y⁻¹ y``."""
        return np.linalg.solve(self.Y, self.y).copy()

    @property
    def covariance(self) -> np.ndarray:
        """Recover the covariance ``P = Y⁻¹``."""
        return np.linalg.inv(self.Y).copy()

    def step(self, z: np.ndarray, u: Optional[np.ndarray] = None) -> np.ndarray:
        self.predict(u)
        self.update(z)
        return self.state