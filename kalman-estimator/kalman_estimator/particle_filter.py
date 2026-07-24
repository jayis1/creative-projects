"""Particle Filter (Sequential Importance Resampling — SIR).

A bootstrap particle filter that propagates a cloud of weighted particles
through a (possibly nonlinear / non-Gaussian) model.  At each step:

1. **Predict**: propagate each particle through the transition model + noise.
2. **Update**: weight each particle by the likelihood of the measurement.
3. **Resample**: systematically resample when the effective sample size
   drops below a threshold, to avoid particle degeneracy.

This implementation uses *systematic resampling* which has lower
variance than multinomial resampling.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from .base import BaseEstimator


class ParticleFilter(BaseEstimator):
    """Bootstrap particle filter (SIR).

    Parameters
    ----------
    f : callable(x, u=None) -> x_next
        State transition (can be nonlinear, even non-Gaussian).
    h : callable(x) -> z
        Measurement function.
    Q : (n, n) process noise covariance (Gaussian additive).
    R : (m, m) measurement noise covariance (Gaussian additive).
    x0 : (n,) initial mean.
    P0 : (n, n) initial covariance.
    N : int
        Number of particles.
    resample_threshold : float
        Resample when ``N_eff / N < resample_threshold`` (default 0.5).
    seed : int
        Random seed.
    """

    def __init__(
        self,
        f: Callable,
        h: Callable,
        Q: np.ndarray,
        R: np.ndarray,
        x0: np.ndarray,
        P0: np.ndarray,
        N: int = 500,
        resample_threshold: float = 0.5,
        seed: int = 42,
    ):
        self.f = f
        self.h = h
        self.Q = np.atleast_2d(Q).astype(float)
        self.R = np.atleast_2d(R).astype(float)
        self.N = max(N, 2)
        self.n = self.Q.shape[0]
        self.m = self.R.shape[0]
        self.resample_threshold = resample_threshold
        self._rng = np.random.default_rng(seed)

        x0 = np.atleast_1d(x0).astype(float)
        P0 = np.atleast_2d(P0).astype(float)
        if x0.shape != (self.n,):
            raise ValueError(f"x0 must have shape ({self.n},)")
        if P0.shape != (self.n, self.n):
            raise ValueError(f"P0 must have shape ({self.n}, {self.n})")

        L = np.linalg.cholesky(P0 + 1e-12 * np.eye(self.n))
        self.particles = x0[None, :] + (
            self._rng.standard_normal((self.N, self.n)) @ L.T
        )
        self.weights = np.full(self.N, 1.0 / self.N)

    # ------------------------------------------------------------------ #
    #  Prediction
    # ------------------------------------------------------------------ #
    def predict(self, u: Optional[np.ndarray] = None) -> None:
        """Propagate particles through *f* and add Gaussian process noise."""
        L_Q = np.linalg.cholesky(self.Q + 1e-12 * np.eye(self.n))
        for i in range(self.N):
            noise = self._rng.standard_normal(self.n) @ L_Q.T
            try:
                x_new = self.f(self.particles[i], u)
            except TypeError:
                # f doesn't accept u
                x_new = self.f(self.particles[i])
            self.particles[i] = np.asarray(x_new, dtype=float).ravel() + noise

    # ------------------------------------------------------------------ #
    #  Update
    # ------------------------------------------------------------------ #
    def update(self, z: np.ndarray) -> None:
        """Weight particles by measurement likelihood and resample if needed."""
        z = np.atleast_1d(z).astype(float)
        if z.shape != (self.m,):
            raise ValueError(f"measurement must have shape ({self.m},), got {z.shape}")
        if not np.all(np.isfinite(z)):
            raise ValueError("measurement contains NaN or Inf")

        R_inv = np.linalg.inv(self.R)
        log_w = np.empty(self.N)
        for i in range(self.N):
            z_pred = np.asarray(self.h(self.particles[i]), dtype=float).ravel()
            innov = z - z_pred
            # Gaussian log-likelihood
            log_w[i] = -0.5 * innov @ R_inv @ innov

        # normalise in log-space for numerical stability
        log_w -= np.max(log_w)
        w = np.exp(log_w)
        self.weights = w / np.sum(w)

        # effective sample size
        n_eff = 1.0 / np.sum(self.weights ** 2)
        if n_eff / self.N < self.resample_threshold:
            self._systematic_resample()

    def _systematic_resample(self) -> None:
        """Systematic resampling (low variance)."""
        positions = (self._rng.random() + np.arange(self.N)) / self.N
        cumsum = np.cumsum(self.weights)
        cumsum[-1] = 1.0  # guard against rounding
        indices = np.searchsorted(cumsum, positions)
        self.particles = self.particles[indices]
        self.weights = np.full(self.N, 1.0 / self.N)

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #
    @property
    def state(self) -> np.ndarray:
        """Weighted mean of particles."""
        return (self.weights[:, None] * self.particles).sum(axis=0)

    @property
    def covariance(self) -> np.ndarray:
        """Weighted covariance of particles."""
        mean = self.state
        dev = self.particles - mean
        return (self.weights[:, None] * dev).T @ dev

    @property
    def effective_sample_size(self) -> float:
        """Effective sample size ``1 / Σw²``  (before resampling)."""
        return 1.0 / np.sum(self.weights ** 2)

    def step(self, z: np.ndarray, u: Optional[np.ndarray] = None) -> np.ndarray:
        self.predict(u)
        self.update(z)
        return self.state