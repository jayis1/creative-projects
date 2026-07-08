"""
Utility functions for signal analysis and quality metrics.
"""

from __future__ import annotations

import math


def energy(signal: list[float]) -> float:
    """L² energy of a signal: Σ|x_i|²."""
    return sum(x * x for x in signal)


def power(signal: list[float]) -> float:
    """Average power: (1/n) Σ|x_i|²."""
    if not signal:
        return 0.0
    return energy(signal) / len(signal)


def entropy(signal: list[float]) -> float:
    """Shannon entropy of the signal (treating |x_i|² as probability)."""
    if not signal:
        return 0.0
    s = sum(abs(x) ** 2 for x in signal)
    if s == 0:
        return 0.0
    ent = 0.0
    for x in signal:
        p = (x ** 2) / s
        if p > 0:
            ent -= p * math.log2(p)
    return ent


def mse(original: list[float], reconstructed: list[float]) -> float:
    """Mean Squared Error between two signals."""
    if len(original) != len(reconstructed):
        raise ValueError(f"Length mismatch: {len(original)} vs {len(reconstructed)}")
    if not original:
        return 0.0
    return sum((a - b) ** 2 for a, b in zip(original, reconstructed)) / len(original)


def rmse(original: list[float], reconstructed: list[float]) -> float:
    """Root Mean Squared Error."""
    return math.sqrt(mse(original, reconstructed))


def snr(original: list[float], reconstructed: list[float]) -> float:
    """Signal-to-Noise Ratio in dB."""
    noise = mse(original, reconstructed)
    if noise == 0:
        return float("inf")
    sig_power = power(original)
    return 10 * math.log10(sig_power / noise)


def psnr(original: list[float], reconstructed: list[float],
         max_val: float | None = None) -> float:
    """Peak Signal-to-Noise Ratio in dB.

    ``max_val`` is the maximum possible signal value (e.g. 255 for 8-bit images).
    If None, it is inferred from the signal.
    """
    if max_val is None:
        max_val = max(abs(x) for x in original) if original else 1.0
    noise = mse(original, reconstructed)
    if noise == 0:
        return float("inf")
    return 10 * math.log10((max_val ** 2) / noise)


def mean_absolute_error(original: list[float], reconstructed: list[float]) -> float:
    """Mean Absolute Error."""
    if len(original) != len(reconstructed):
        raise ValueError("Length mismatch")
    if not original:
        return 0.0
    return sum(abs(a - b) for a, b in zip(original, reconstructed)) / len(original)