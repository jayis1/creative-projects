"""Batch utilities: run filters over multiple independent measurement sequences."""

from __future__ import annotations

import numpy as np

from .kf import KalmanFilter


def batch_filter(measurements_list, F, H, Q, R, x0, P0, controls_list=None):
    """Run a linear KF over multiple independent measurement sequences.

    Each sequence gets a fresh filter instance (same model parameters).

    Parameters
    ----------
    measurements_list : list of arrays
        Each element is a (T_k, m) array of measurements for one run.
    F, H, Q, R, x0, P0 : model parameters (same for every run).
    controls_list : list or None
        Optional control inputs per run.

    Returns
    -------
    results : list of (states, covs) tuples
    """
    results = []
    if controls_list is None:
        controls_list = [None] * len(measurements_list)
    for idx, meas in enumerate(measurements_list):
        kf = KalmanFilter(F, H, Q, R, x0=x0, P0=P0)
        u_seq = controls_list[idx]
        states = []
        covs = []
        for t, z in enumerate(meas):
            u = u_seq[t] if u_seq is not None else None
            kf.predict(u)
            kf.update(z)
            states.append(kf.state.copy())
            covs.append(kf.covariance.copy())
        results.append((np.array(states), np.array(covs)))
    return results


def monte_carlo_error(measurements_list, true_states_list, F, H, Q, R, x0, P0):
    """Compute average RMSE over multiple Monte Carlo runs.

    Parameters
    ----------
    measurements_list : list of (T, m) arrays
    true_states_list : list of (T, n) arrays
        Ground-truth states (must match each run).

    Returns
    -------
    rmse : (n,) array — per-dimension average RMSE
    """
    results = batch_filter(measurements_list, F, H, Q, R, x0, P0)
    sq_errors = []
    for (states, _), true in zip(results, true_states_list):
        sq_errors.append((states - true) ** 2)
    rmse = np.sqrt(np.mean(np.concatenate(sq_errors, axis=0), axis=0))
    return rmse