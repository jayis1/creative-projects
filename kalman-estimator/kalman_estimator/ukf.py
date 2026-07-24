"""Unscented Kalman Filter (UKF).

Uses the scaled unscented transform (Merwe et al. 2000) to pick sigma
points and propagate them through the nonlinear functions directly —
no Jacobians required.
"""

from __future__ import annotations

import numpy as np


def _sigma_points(x, P, alpha=1e-3, beta=2.0, kappa=0.0):
    """Generate sigma points and weights for the scaled unscented transform.

    Parameters
    ----------
    x : (n,) mean
    P : (n, n) covariance
    alpha, beta, kappa : scaling parameters

    Returns
    -------
    sigmas : (2n+1, n) sigma points
    Wm : (2n+1,) mean weights
    Wc : (2n+1,) covariance weights
    """
    x = np.asarray(x, dtype=float).ravel()
    P = np.atleast_2d(P).astype(float)
    n = x.shape[0]

    # regularize P for Cholesky stability (add tiny jitter if needed)
    P_reg = P + 1e-12 * np.eye(n)
    L = np.linalg.cholesky(P_reg)

    lambda_ = alpha ** 2 * (n + kappa) - n
    scale = n + lambda_

    sigmas = np.zeros((2 * n + 1, n))
    sigmas[0] = x
    for i in range(n):
        # scale the columns of L by sqrt(n + lambda_)
        sigma_offset = np.sqrt(scale) * L[:, i]
        sigmas[1 + i] = x + sigma_offset
        sigmas[1 + n + i] = x - sigma_offset

    Wm = np.zeros(2 * n + 1)
    Wc = np.zeros(2 * n + 1)
    Wm[0] = lambda_ / scale
    Wc[0] = lambda_ / scale + (1 - alpha ** 2 + beta)
    Wm[1:] = 1.0 / (2 * scale)
    Wc[1:] = 1.0 / (2 * scale)
    return sigmas, Wm, Wc


class UnscentedKalmanFilter:
    """Unscented Kalman Filter.

    Parameters
    ----------
    fx : callable(x, dt) -> x_next
        Nonlinear state transition. Must take state vector and time step.
    hx : callable(x) -> z
        Nonlinear measurement function.
    dt : float
        Time step.
    Q : (n, n) process noise covariance.
    R : (m, m) measurement noise covariance.
    x0, P0 : initial state and covariance.
    alpha, beta, kappa : UKF sigma-point tuning parameters.
    """

    def __init__(
        self,
        fx,
        hx,
        dt,
        Q,
        R,
        x0,
        P0,
        alpha=1e-3,
        beta=2.0,
        kappa=0.0,
    ):
        self.fx = fx
        self.hx = hx
        self.dt = dt
        self.Q = np.atleast_2d(Q).astype(float)
        self.R = np.atleast_2d(R).astype(float)
        self.x = np.atleast_1d(x0).astype(float)
        self.P = np.atleast_2d(P0).astype(float)
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa

        self.n = self.Q.shape[0]
        self.m = self.R.shape[0]
        if self.P.shape != (self.n, self.n):
            raise ValueError("P0 shape mismatch with Q")
        if self.x.shape != (self.n,):
            raise ValueError("x0 shape mismatch with Q")

    def _ut(self, sigmas, Wm, Wc, noise_cov=None):
        """Unscented transform: propagate sigma points, return mean & cov."""
        n_pts = sigmas.shape[0]
        dim_out = sigmas.shape[1]
        points = np.zeros((n_pts, dim_out))
        for i in range(n_pts):
            points[i] = sigmas[i]  # already propagated by caller
        x_mean = np.dot(Wm, points)
        P_cov = np.zeros((dim_out, dim_out))
        for i in range(n_pts):
            d = (points[i] - x_mean).reshape(-1, 1)
            P_cov += Wc[i] * (d @ d.T)
        if noise_cov is not None:
            P_cov += noise_cov
        return x_mean, P_cov

    def predict(self, u=None):
        """UKF prediction step.

        Parameters
        ----------
        u : optional control input, passed to fx if fx accepts it.
        """
        sigmas, Wm, Wc = _sigma_points(
            self.x, self.P, self.alpha, self.beta, self.kappa
        )
        # propagate sigma points through transition function
        # Try passing u to fx; if fx doesn't accept u, fall back gracefully
        import inspect
        sig_fx = inspect.signature(self.fx)
        for i in range(sigmas.shape[0]):
            if "u" in sig_fx.parameters or len(sig_fx.parameters) > 2:
                sigmas[i] = np.asarray(self.fx(sigmas[i], self.dt, u), dtype=float).ravel()
            else:
                sigmas[i] = np.asarray(self.fx(sigmas[i], self.dt), dtype=float).ravel()
        x_pred, P_pred = self._ut(sigmas, Wm, Wc, self.Q)
        self.x = x_pred
        self.P = P_pred

    def update(self, z):
        """UKF update step.

        Raises
        ------
        ValueError
            If *z* contains NaN or Inf.
        """
        z = np.atleast_1d(z).astype(float)
        if not np.all(np.isfinite(z)):
            raise ValueError("measurement contains NaN or Inf")
        sigmas, Wm, Wc = _sigma_points(
            self.x, self.P, self.alpha, self.beta, self.kappa
        )
        # propagate sigma points through measurement function
        m = self.R.shape[0]
        z_sigmas = np.zeros((sigmas.shape[0], m))
        for i in range(sigmas.shape[0]):
            z_sigmas[i] = np.asarray(self.hx(sigmas[i]), dtype=float).ravel()
        z_mean = np.dot(Wm, z_sigmas)

        # innovation covariance S
        S = np.zeros((m, m))
        for i in range(sigmas.shape[0]):
            d = (z_sigmas[i] - z_mean).reshape(-1, 1)
            S += Wc[i] * (d @ d.T)
        S += self.R

        # cross-covariance Pxz
        Pxz = np.zeros((self.n, m))
        for i in range(sigmas.shape[0]):
            dx = (sigmas[i] - self.x).reshape(-1, 1)
            dz = (z_sigmas[i] - z_mean).reshape(-1, 1)
            Pxz += Wc[i] * (dx @ dz.T)

        try:
            K = Pxz @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            raise ValueError(
                "Innovation covariance S is singular in UKF update."
            )
        y = z - z_mean
        self.x = self.x + (K @ y).ravel()
        self.P = self.P - K @ S @ K.T
        # Symmetrize to prevent numerical drift away from symmetry
        self.P = (self.P + self.P.T) / 2.0

    @property
    def state(self):
        return self.x.copy()

    @property
    def covariance(self):
        return self.P.copy()

    def step(self, z, u=None):
        self.predict(u)
        self.update(z)
        return self.state