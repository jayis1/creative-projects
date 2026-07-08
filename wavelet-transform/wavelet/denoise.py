"""
Wavelet-based denoising for 1-D and 2-D signals.

The standard denoising pipeline:
  1. Forward DWT (decompose signal into approximation + detail coefficients)
  2. Estimate noise σ from the finest-level detail coefficients (MAD)
  3. Threshold the detail coefficients (soft/hard/garrote)
  4. Inverse DWT (reconstruct denoised signal)
"""

from __future__ import annotations

import math
from typing import Callable

from .dwt import DWT
from .modwt import MODWT
from .threshold import (
    Threshold, soft, hard, garrote, estimate_sigma,
    estimate_threshold, universal_threshold, bayes_threshold,
)
from .wavelets import Wavelet


def denoise1d(
    signal: list[float],
    wavelet: Wavelet | str = "db4",
    level: int | None = None,
    threshold_method: Threshold = Threshold.BAYES,
    threshold_func: Callable = soft,
    transform: str = "dwt",  # "dwt" or "modwt"
) -> list[float]:
    """Denoise a 1-D signal using wavelet thresholding.

    Parameters
    ----------
    signal : input signal
    wavelet : wavelet name or object (default: "db4")
    level : decomposition level (default: max)
    threshold_method : how to estimate the threshold
    threshold_func : soft/hard/garrote
    transform : "dwt" (decimated) or "modwt" (translation-invariant)
    """
    if isinstance(wavelet, str):
        from .wavelets import wavelet as _w
        wavelet = _w(wavelet)

    if transform == "modwt":
        mod = MODWT(wavelet)
        result = mod.decompose(signal, level)
        # Estimate sigma from finest-level details
        if result.details:
            sigma = estimate_sigma(result.details[0])
        else:
            sigma = 0.0
        # Threshold each detail level
        for i, detail in enumerate(result.details):
            t = estimate_threshold(detail, threshold_method, sigma)
            result.details[i] = [threshold_func(c, t) for c in detail]
        return mod.reconstruct(result)
    else:
        dwt = DWT(wavelet)
        result = dwt.decompose(signal, level)
        # Estimate sigma from finest-level details
        if result.details:
            sigma = estimate_sigma(result.details[0])
        else:
            sigma = 0.0
        # Threshold each detail level (not the approximation)
        for i, detail in enumerate(result.details):
            t = estimate_threshold(detail, threshold_method, sigma)
            result.details[i] = [threshold_func(c, t) for c in detail]
        return dwt.reconstruct(result)


def denoise2d(
    matrix: list[list[float]],
    wavelet: Wavelet | str = "db4",
    level: int | None = None,
    threshold_method: Threshold = Threshold.BAYES,
    threshold_func: Callable = soft,
) -> list[list[float]]:
    """Denoise a 2-D signal (image) using 2-D wavelet thresholding.

    Estimates σ from the finest-level HH subband and applies a global
    threshold to all detail subbands.
    """
    if isinstance(wavelet, str):
        from .wavelets import wavelet as _w
        wavelet = _w(wavelet)

    dwt = DWT(wavelet)
    decomp = dwt.decompose2(matrix, level)

    # Estimate sigma from finest-level HH subband
    finest_hh = decomp["subbands"][0]["HH"]
    flat_hh = [c for row in finest_hh for c in row]
    sigma = estimate_sigma(flat_hh)

    # Threshold all detail subbands
    for sb in decomp["subbands"]:
        for key in ("LH", "HL", "HH"):
            sub = sb[key]
            flat = [c for row in sub for c in row]
            t = estimate_threshold(flat, threshold_method, sigma)
            sb[key] = [[threshold_func(c, t) for c in row] for row in sub]

    return dwt.reconstruct2(decomp)