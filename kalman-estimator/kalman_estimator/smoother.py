"""Rauch-Tung-Striebel (RTS) fixed-interval smoother.

Given the filtered estimates (means and covariances) from a forward
Kalman pass, the RTS smoother performs a backward recursion to produce
smoothed estimates that use all measurements in the interval.

For a linear model:

    x_k = F_k x_{k-1} + w_k
    z_k = H_k x_k     + v_k

the RTS recursion is:

    C_k   = P_{k-1} F_k^T (P_k^-)^{-1}
    x_s  = x_{k-1} + C_k (x_s,k - x_k^-)
    P_s  = P_{k-1} + C_k (P_s,k - P_k^-) C_k^T

where superscript '-' denotes the *prior* (predicted) quantities saved
during the forward pass.
"""

from __future__ import annotations

import numpy as np


class _ForwardHistory:
    """Stores the data needed by the RTS smoother during a forward pass."""

    def __init__(self):
        self.x_prior = []     # predicted mean  x_k^-
        self.P_prior = []     # predicted cov   P_k^-
        self.x_post = []      # posterior mean  x_k
        self.P_post = []      # posterior cov   P_k
        self.F_list = []       # transition matrix used at step k


class RTSSmoother:
    """RTS smoother that works with a linear KalmanFilter forward pass.

    Parameters
    ----------
    kf : KalmanFilter
        A configured linear Kalman filter instance.

    Example
    -------
    ::

        kf = KalmanFilter(...)
        sm = RTSSmoother(kf)
        for z in measurements:
            sm.forward_step(z)
        x_smooth, P_smooth = sm.smooth()
    """

    def __init__(self, kf):
        self.kf = kf
        self.history = _ForwardHistory()

    def forward_step(self, z, u=None):
        """Run one predict-update step and record history."""
        # record the transition matrix used at this step
        F = self.kf.F.copy()

        # predict
        self.kf.predict(u)
        x_prior = self.kf.x.copy()
        P_prior = self.kf.P.copy()

        # update
        self.kf.update(z)
        x_post = self.kf.x.copy()
        P_post = self.kf.P.copy()

        self.history.x_prior.append(x_prior)
        self.history.P_prior.append(P_prior)
        self.history.x_post.append(x_post)
        self.history.P_post.append(P_post)
        self.history.F_list.append(F)

    def smooth(self):
        """Run the RTS backward recursion.

        Returns
        -------
        x_smooth : list of ndarray
            Smoothed state means (same length as forward steps).
        P_smooth : list of ndarray
            Smoothed state covariances.
        """
        N = len(self.history.x_post)
        if N == 0:
            return [], []

        x_smooth = [None] * N
        P_smooth = [None] * N
        x_smooth[-1] = self.history.x_post[-1].copy()
        P_smooth[-1] = self.history.P_post[-1].copy()

        for k in range(N - 2, -1, -1):
            # Note: P_prior at index k+1 corresponds to the prediction step
            # that transitions from time k to time k+1, using F at index k+1.
            P_prior_next = self.history.P_prior[k + 1]
            F_next = self.history.F_list[k + 1]
            x_prior_next = self.history.x_prior[k + 1]

            C = (
                self.history.P_post[k]
                @ F_next.T
                @ np.linalg.inv(P_prior_next)
            )
            x_smooth[k] = (
                self.history.x_post[k]
                + C @ (x_smooth[k + 1] - x_prior_next)
            )
            P_smooth[k] = (
                self.history.P_post[k]
                + C @ (P_smooth[k + 1] - P_prior_next) @ C.T
            )
        return x_smooth, P_smooth


def smooth(kf, measurements, controls=None):
    """Convenience: run a full forward+backward RTS smoothing pass.

    Parameters
    ----------
    kf : KalmanFilter
    measurements : sequence of ndarray
    controls : sequence of ndarray or None

    Returns
    -------
    x_filtered, P_filtered, x_smoothed, P_smoothed
    """
    sm = RTSSmoother(kf)
    if controls is None:
        controls = [None] * len(measurements)
    for z, u in zip(measurements, controls):
        sm.forward_step(z, u)
    x_smooth, P_smooth = sm.smooth()
    x_filt = sm.history.x_post
    P_filt = sm.history.P_post
    return x_filt, P_filt, x_smooth, P_smooth