"""
Thresholding functions for wavelet-based denoising.

Implements soft, hard, non-negative garrote, and firm thresholding,
plus threshold estimation methods (universal/VisuShrink, SURE/ SureShrink,
BayesShrink).
"""

from __future__ import annotations

import math
from enum import Enum


class Threshold(Enum):
    """Threshold estimation methods."""
    UNIVERSAL = "universal"  # VisuShrink: T = σ√(2 ln n)
    SURE = "sure"             # SureShrink: minimize Stein's risk
    BAYES = "bayes"           # BayesShrink: adapt to subband statistics
    MINIMAX = "minimax"       # Minimax threshold


# -------------------------------------------------------------------------
# Thresholding operators
# -------------------------------------------------------------------------
def soft(x: float, t: float) -> float:
    """Soft threshold: sign(x) * max(|x| - t, 0)."""
    if abs(x) <= t:
        return 0.0
    return math.copysign(abs(x) - t, x)


def hard(x: float, t: float) -> float:
    """Hard threshold: x if |x| > t, else 0."""
    if abs(x) <= t:
        return 0.0
    return x


def garrote(x: float, t: float) -> float:
    """Non-negative garrote: x - t²/x for |x| > t, else 0."""
    if abs(x) <= t or x == 0:
        return 0.0
    return x - t * t / x


def firm(x: float, t1: float, t2: float) -> float:
    """Firm thresholding with two thresholds t1 < t2.

    0 for |x| ≤ t1, linear ramp for t1 < |x| < t2, identity for |x| ≥ t2.
    """
    if t2 <= t1:
        raise ValueError("t2 must be greater than t1 for firm thresholding")
    ax = abs(x)
    if ax <= t1:
        return 0.0
    if ax >= t2:
        return x
    return x * (ax - t1) / (t2 - t1)


# -------------------------------------------------------------------------
# Threshold estimation
# -------------------------------------------------------------------------
def estimate_sigma(details: list[float]) -> float:
    """Robust noise standard deviation estimate via median absolute deviation (MAD).

    σ̂ = MAD / 0.6745, where MAD = median(|d_i|).
    """
    if not details:
        return 0.0
    abs_coeffs = sorted(abs(c) for c in details)
    n = len(abs_coeffs)
    if n % 2 == 1:
        med = abs_coeffs[n // 2]
    else:
        med = (abs_coeffs[n // 2 - 1] + abs_coeffs[n // 2]) / 2.0
    return med / 0.6745


def universal_threshold(n: int, sigma: float) -> float:
    """VisuShrink universal threshold: T = σ√(2 ln n)."""
    if n <= 0:
        return 0.0
    return sigma * math.sqrt(2 * math.log(n))


def sure_threshold(coeffs: list[float], sigma: float) -> float:
    """SureShrink: find threshold minimizing Stein's Unbiased Risk Estimate.

    For each candidate threshold t, SURE(t) = n - 2*#{|c_i| ≤ t} + Σ_{|c_i|≤t} min(|c_i|, t)².
    We minimize over candidate thresholds = the sorted absolute coefficients.
    """
    if not coeffs:
        return 0.0
    n = len(coeffs)
    abs_sorted = sorted(abs(c) for c in coeffs)
    # SURE for each candidate
    risk = [0.0] * n
    for k in range(n):
        t = abs_sorted[k]
        count_below = k + 1  # elements ≤ t (since sorted)
        # Σ min(|c_i|, t)² over all i
        s = 0.0
        for i in range(n):
            s += min(abs_sorted[i], t) ** 2
        risk[k] = n - 2 * count_below + s / (sigma ** 2 if sigma > 0 else 1.0)
    best_k = min(range(n), key=lambda k: risk[k])
    return abs_sorted[best_k]


def bayes_threshold(detail_coeffs: list[float], sigma: float) -> float:
    """BayesShrink: threshold = σ² / σ_signal, where σ_signal = √max(σ²_Y - σ², 0).

    σ_Y is the standard deviation of the detail coefficients.
    """
    if not detail_coeffs:
        return 0.0
    n = len(detail_coeffs)
    mean_y = sum(detail_coeffs) / n
    var_y = sum((c - mean_y) ** 2 for c in detail_coeffs) / n
    var_signal = max(var_y - sigma ** 2, 0.0)
    if var_signal == 0:
        return universal_threshold(n, sigma)  # fallback
    return sigma ** 2 / math.sqrt(var_signal)


def minimax_threshold(n: int, sigma: float) -> float:
    """Minimax threshold (Donoho & Johnstone 1994).

    Approximated by the asymptotic formula.
    """
    if n <= 0:
        return 0.0
    if n <= 5:
        return 0.0
    # Minimax risk threshold ~ σ * (0.3937 + 0.1829 * log2(n))
    return sigma * (0.3937 + 0.1829 * math.log2(n))


def estimate_threshold(coeffs: list[float], method: Threshold,
                       sigma: float | None = None) -> float:
    """Estimate threshold for ``coeffs`` using ``method``."""
    if sigma is None:
        sigma = estimate_sigma(coeffs)
    if method == Threshold.UNIVERSAL:
        return universal_threshold(len(coeffs), sigma)
    if method == Threshold.SURE:
        return sure_threshold(coeffs, sigma)
    if method == Threshold.BAYES:
        return bayes_threshold(coeffs, sigma)
    if method == Threshold.MINIMAX:
        return minimax_threshold(len(coeffs), sigma)
    raise ValueError(f"Unknown threshold method: {method}")