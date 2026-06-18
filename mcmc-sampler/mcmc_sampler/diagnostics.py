"""
Convergence diagnostics for MCMC chains.
"""

from __future__ import annotations

import math
from typing import List, Sequence

import numpy as np

from .trace import Trace


def autocorrelation(x: np.ndarray, max_lag: int = 50) -> np.ndarray:
    """Empirical autocorrelation function up to ``max_lag``."""
    x = np.asarray(x, dtype=float).ravel()
    n = x.shape[0]
    if n < 2:
        return np.array([1.0])
    x = x - x.mean()
    var = (x * x).sum()
    if var == 0:
        return np.ones(min(max_lag + 1, n))
    max_lag = min(max_lag, n - 1)
    acf = np.empty(max_lag + 1)
    acf[0] = 1.0
    for k in range(1, max_lag + 1):
        acf[k] = (x[:n - k] * x[k:]).sum() / var
    return acf


def effective_sample_size(x: np.ndarray, max_lag: int = 50) -> float:
    """ESS using the initial-positive-sequence estimator (Geyer)."""
    x = np.asarray(x, dtype=float).ravel()
    n = x.shape[0]
    if n < 2:
        return float(n)
    acf = autocorrelation(x, max_lag=max_lag)
    # Geyer's initial positive sequence: sum pairs until negative
    ess = 1.0
    k = 1
    while k + 1 < len(acf):
        pair = acf[k] + acf[k + 1]
        if pair <= 0:
            break
        ess += 2 * pair
        k += 2
    # truncate to at most n
    return float(max(1.0, min(n, n / ess if ess > 0 else n)))


def gelman_rubin(chains: Sequence[Sequence[float]]) -> float:
    """Potential scale reduction factor (R-hat) for ≥2 chains."""
    chains = [np.asarray(c, dtype=float).ravel() for c in chains]
    m = len(chains)
    if m < 2:
        raise ValueError("need at least 2 chains")
    n = min(len(c) for c in chains)
    chains = [c[:n] for c in chains]
    means = np.array([c.mean() for c in chains])
    vars_ = np.array([c.var(ddof=1) for c in chains])
    W = vars_.mean()
    B = n * means.var(ddof=1)
    if W == 0:
        return float("inf") if B > 0 else 1.0
    var_hat = (n - 1) / n * W + B / n
    return float(math.sqrt(var_hat / W))


def monte_carlo_error(x: np.ndarray) -> float:
    """MC standard error accounting for autocorrelation: std / sqrt(ESS)."""
    x = np.asarray(x, dtype=float).ravel()
    if x.shape[0] < 2:
        return 0.0
    ess = effective_sample_size(x)
    return float(x.std(ddof=1) / math.sqrt(ess))


def highest_density_interval(x: np.ndarray, prob: float = 0.95) -> tuple:
    """Highest-density interval for a 1-D sample."""
    x = np.asarray(x, dtype=float).ravel()
    n = x.shape[0]
    if n < 2:
        raise ValueError("need at least 2 samples")
    if not 0 < prob < 1:
        raise ValueError("prob must be in (0,1)")
    xs = np.sort(x)
    k = int(math.floor(prob * n))
    if k < 1:
        k = 1
    widths = xs[k:] - xs[: n - k]
    i = int(np.argmin(widths))
    return float(xs[i]), float(xs[i + k])