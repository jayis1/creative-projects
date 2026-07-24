"""Abstract base class for all estimators in the kalman-estimator library.

Defines the common interface that every filter implements, enabling
polymorphic use (e.g. swapping a KF for a UKF in a pipeline without
changing calling code).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple

import numpy as np


class BaseEstimator(ABC):
    """Abstract base for all state estimators.

    Every subclass must implement :meth:`predict`, :meth:`update`,
    and expose ``state`` / ``covariance`` properties.
    """

    @abstractmethod
    def predict(self, u: Optional[np.ndarray] = None) -> None:
        """Time-update / prediction step.

        Parameters
        ----------
        u : optional control input vector.
        """

    @abstractmethod
    def update(self, z: np.ndarray) -> None:
        """Measurement-update / correction step.

        Parameters
        ----------
        z : measurement vector.
        """

    @property
    @abstractmethod
    def state(self) -> np.ndarray:
        """Current posterior state estimate (copy)."""

    @property
    @abstractmethod
    def covariance(self) -> np.ndarray:
        """Current posterior state covariance (copy)."""

    # ------------------------------------------------------------------ #
    #  Shared convenience methods
    # ------------------------------------------------------------------ #
    def step(self, z: np.ndarray, u: Optional[np.ndarray] = None) -> np.ndarray:
        """Run ``predict(u)`` then ``update(z)`` and return the new state."""
        self.predict(u)
        self.update(z)
        return self.state

    def reset(self, x0: np.ndarray, P0: np.ndarray) -> None:
        """Reset the filter state and covariance to new initial values.

        Subclasses that store additional history (e.g. sigma points)
        should override this to clear their internal buffers.
        """
        self.x = np.atleast_1d(x0).astype(float).copy()
        self.P = np.atleast_2d(P0).astype(float).copy()

    def log_likelihood_step(self, z: np.ndarray) -> float:
        """One-step log-likelihood of measurement *z* given current prior.

        Uses the Gaussian innovation form::

            ln p(z | z_{1:k-1}) = -½ [yᵀ S⁻¹ y + ln|S| + m ln(2π)]

        where ``y = z − H·x_prior`` and ``S = H·P_prior·Hᵀ + R``.

        This default implementation works only for linear filters
        (KalmanFilter / InformationFilter).  Subclasses with nonlinear
        measurement models should override.
        """
        raise NotImplementedError(
            "log_likelihood_step is only available on linear filters "
            "or subclasses that override it."
        )