"""Adaptive Kalman Filter with online noise-covariance estimation.

Implements two adaptation strategies:

1. **Innovation-based adaptation** (Sage & Husa, 1969):
   Q and R are recursively updated from the innovation sequence.

2. **Robust adaptation** using a fading memory factor ``alpha``
   (0 < alpha < 1) that weights recent innovations more heavily.

The filter is a drop-in replacement for :class:`KalmanFilter` —
it inherits the same predict/update interface but *learns* Q and R
on-line instead of requiring them to be fixed.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .kf import KalmanFilter


class AdaptiveKalmanFilter(KalmanFilter):
    """Kalman filter with on-line Q/R adaptation.

    Parameters
    ----------
    F, H, Q, R, x0, P0, B : as in :class:`KalmanFilter`.
    alpha : float in (0, 1]
        Forgetting factor for the exponential moving average of the
        innovation statistics.  ``alpha=1`` means full memory (standard
        Sage-Husa); smaller values adapt faster but are noisier.
    adapt_Q : bool
        Whether to adapt the process noise covariance.
    adapt_R : bool
        Whether to adapt the measurement noise covariance.
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
        alpha: float = 0.95,
        adapt_Q: bool = True,
        adapt_R: bool = True,
    ):
        super().__init__(F, H, Q, R, x0, P0, B)
        if not (0.0 < alpha <= 1.0):
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self.adapt_Q = adapt_Q
        self.adapt_R = adapt_R
        self._step_count = 0
        # running estimates
        self._R_hat = self.R.copy()
        self._Q_hat = self.Q.copy()
        # store last innovation for diagnostics
        self.last_innovation: Optional[np.ndarray] = None
        self.last_S: Optional[np.ndarray] = None

    @property
    def estimated_R(self) -> np.ndarray:
        """Current adapted measurement-noise covariance."""
        return self._R_hat.copy()

    @property
    def estimated_Q(self) -> np.ndarray:
        """Current adapted process-noise covariance."""
        return self._Q_hat.copy()

    def update(self, z: np.ndarray) -> None:
        """Measurement update with adaptive R (and Q after step >= 2)."""
        z = np.atleast_1d(z).astype(float)
        if z.shape != (self.m,):
            raise ValueError(f"measurement must have shape ({self.m},), got {z.shape}")
        if not np.all(np.isfinite(z)):
            raise ValueError("measurement contains NaN or Inf")

        # Use adapted R in the innovation covariance
        R_eff = self._R_hat
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + R_eff

        try:
            K = self.P @ self.H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            raise ValueError(
                "Innovation covariance S is singular in AdaptiveKF update."
            )

        # --- Sage-Husa R update ---
        # R_hat = alpha * R_hat + (1-alpha) * (y y^T - H P H^T)
        if self.adapt_R:
            self._R_hat = (
                self.alpha * self._R_hat
                + (1 - self.alpha) * (np.outer(y, y) - self.H @ self.P @ self.H.T)
            )
            # symmetrize and floor to PSD
            self._R_hat = (self._R_hat + self._R_hat.T) / 2.0
            # ensure diagonal entries are non-negative
            self._R_hat = np.maximum(self._R_hat, np.eye(self.m) * 1e-12)

        self.x = self.x + K @ y
        KH = K @ self.H
        self.P = (self.I - KH) @ self.P @ (self.I - KH).T + K @ R_eff @ K.T

        # --- Sage-Husa Q update (needs at least 2 steps) ---
        self._step_count += 1
        if self.adapt_Q and self._step_count >= 2 and self.last_innovation is not None:
            # Q update using the difference of consecutive innovations
            dy = y - self.last_innovation
            self._Q_hat = (
                self.alpha * self._Q_hat + (1 - self.alpha) * np.outer(dy, dy)
            )
            self._Q_hat = (self._Q_hat + self._Q_hat.T) / 2.0
            self._Q_hat = np.maximum(self._Q_hat, np.eye(self.n) * 1e-12)

        self.last_innovation = y.copy()
        self.last_S = S.copy()

    def predict(self, u: Optional[np.ndarray] = None) -> None:
        """Prediction step using the adapted Q."""
        Q_eff = self._Q_hat
        if u is not None and self.B is not None:
            self.x = self.F @ self.x + self.B @ np.atleast_1d(u).astype(float)
        else:
            self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + Q_eff