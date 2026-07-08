"""
Stationary Wavelet Transform (SWT) — a.k.a. Ã-Trous algorithm.

The SWT is similar to the MODWT: it is non-decimated (output length =
input length at every level) and translation-invariant.  It differs in
implementation — the SWT inserts zeros between filter coefficients at
each level (the à-trous / "with holes" approach), while the MODWT
upsamples the filters by the full period.

This module also provides **cycle-spinning denoising**, which averages
denoised results over all circular shifts of the input to further
reduce wavelet artifacts.

References
----------
Nason & Silverman (1995), "The Stationary Wavelet Transform and Some
Statistical Applications", *Wavelets and Statistics*, Lecture Notes.
Coifman & Donoho (1995), "Translation-Invariant De-Noising".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from .dwt import DWT
from .threshold import Threshold, soft, estimate_sigma, estimate_threshold
from .wavelets import Wavelet

__all__ = ["SWT", "SWTResult", "cycle_spin_denoise"]


@dataclass
class SWTResult:
    """Result of SWT decomposition."""

    approx: List[float] = field(default_factory=list)
    details: List[List[float]] = field(default_factory=list)
    level: int = 0
    wavelet_name: str = ""
    input_length: int = 0

    def __repr__(self) -> str:
        return (f"SWTResult(level={self.level}, wavelet='{self.wavelet_name}', "
                f"len={self.input_length})")


class SWT:
    """Stationary Wavelet Transform (à-trous algorithm).

    Non-decimated, translation-invariant transform.  At each level ``j``,
    the filter is upsampled by inserting ``2^j - 1`` zeros between each
    coefficient (â-trous), and the result is a full-length approximation
    and detail.

    Filters are scaled by 1/√2 per level (same as MODWT) to ensure
    energy preservation and perfect reconstruction.
    """

    def __init__(self, wavelet: Wavelet | str) -> None:
        if isinstance(wavelet, str):
            from .wavelets import wavelet as _w
            wavelet = _w(wavelet)
        self.wavelet = wavelet
        # Scale filters by 1/sqrt(2) for SWT (same as MODWT)
        sq2 = math.sqrt(2)
        self._g = [c / sq2 for c in self.wavelet.dec_lo]   # scaled low-pass (decomposition)
        self._h = [c / sq2 for c in self.wavelet.dec_hi]   # scaled high-pass (decomposition)
        # For reconstruction (cross-correlation), use the same scaled filters
        # for orthogonal wavelets (rec = dec), or scaled rec filters for biorthogonal
        if self.wavelet.orthogonal:
            self._g_rec = list(self._g)
            self._h_rec = list(self._h)
        else:
            self._g_rec = [c / sq2 for c in self.wavelet.rec_lo]
            self._h_rec = [c / sq2 for c in self.wavelet.rec_hi]

    def decompose(self, signal: list[float],
                  level: int | None = None) -> SWTResult:
        """Decompose signal into ``level`` levels of SWT coefficients.

        Output: each detail and the final approximation have the same
        length as the input.
        """
        n = len(signal)
        if n < self.wavelet.filter_length:
            raise ValueError(f"Signal length {n} < filter length {self.wavelet.filter_length}")
        if level is None:
            level = self.max_level(n)
        if level > self.max_level(n):
            raise ValueError(f"Level {level} exceeds max level {self.max_level(n)} for n={n}")
        if level < 1:
            raise ValueError("Level must be >= 1")

        details: list[list[float]] = []
        approx = list(signal)

        for j in range(level):
            # Upsample filters by 2^j (insert 2^j - 1 zeros between coefficients)
            factor = 2 ** j
            lo_up = _atrous_upsample(self._g, factor)
            hi_up = _atrous_upsample(self._h, factor)
            # Convolve (no downsampling), periodic boundary
            new_approx = _conv_periodic(approx, lo_up, n)
            detail = _conv_periodic(approx, hi_up, n)
            details.append(detail)
            approx = new_approx

        return SWTResult(
            approx=approx, details=details, level=level,
            wavelet_name=self.wavelet.name, input_length=n,
        )

    def reconstruct(self, result: SWTResult) -> list[float]:
        """Reconstruct the original signal from SWT coefficients.

        Uses the adjoint (transpose) of the decomposition operator, which
        for the à-trous algorithm is cross-correlation with the same
        upsampled filters.
        """
        n = result.input_length
        approx = list(result.approx)

        for j in reversed(range(result.level)):
            factor = 2 ** j
            lo_up = _atrous_upsample(self._g_rec, factor)
            hi_up = _atrous_upsample(self._h_rec, factor)
            detail = result.details[j]
            # Cross-correlation (adjoint of convolution)
            a_rec = _xcorr_periodic(approx, lo_up, n)
            d_rec = _xcorr_periodic(detail, hi_up, n)
            approx = [a_rec[t] + d_rec[t] for t in range(n)]

        return approx

    def max_level(self, n: int) -> int:
        """Maximum SWT decomposition level."""
        if n < 1:
            return 0
        L = self.wavelet.filter_length
        # Max level: (L-1) * 2^(J-1) < n
        if L <= 1:
            return int(math.floor(math.log2(n)))
        j = 0
        while (L - 1) * (2 ** j) < n:
            j += 1
        return max(0, j)


# -------------------------------------------------------------------------
# Convolution helpers (periodic boundary)
# -------------------------------------------------------------------------
def _atrous_upsample(filt: list[float], factor: int) -> list[float]:
    """Upsample a filter by inserting ``factor - 1`` zeros between each coefficient.

    For factor=1 (level j=0), no upsampling.
    For factor=2 (level j=1), insert 1 zero between each coefficient.
    For factor=4 (level j=2), insert 3 zeros between each coefficient.
    """
    if factor <= 1:
        return list(filt)
    n_zeros = factor - 1
    result = []
    for i, c in enumerate(filt):
        result.append(c)
        if i < len(filt) - 1:
            result.extend([0.0] * n_zeros)
    return result


def _conv_periodic(signal: list[float], filt: list[float],
                   out_len: int) -> list[float]:
    """Periodic convolution (no downsampling).

    out[t] = Σ_l filt[l] · signal[(t - l) mod n]
    """
    n = len(signal)
    L = len(filt)
    out = [0.0] * out_len
    for t in range(out_len):
        acc = 0.0
        for l in range(L):
            idx = (t - l) % n
            acc += signal[idx] * filt[l]
        out[t] = acc
    return out


def _xcorr_periodic(signal: list[float], filt: list[float],
                    out_len: int) -> list[float]:
    """Periodic cross-correlation (adjoint of convolution).

    out[t] = Σ_l filt[l] · signal[(t + l) mod n]
    """
    n = len(signal)
    L = len(filt)
    out = [0.0] * out_len
    for t in range(out_len):
        acc = 0.0
        for l in range(L):
            idx = (t + l) % n
            acc += signal[idx] * filt[l]
        out[t] = acc
    return out


# -------------------------------------------------------------------------
# Cycle-spinning denoising
# -------------------------------------------------------------------------
def cycle_spin_denoise(
    signal: list[float],
    wavelet: Wavelet | str = "db4",
    level: int | None = None,
    threshold_method: Threshold = Threshold.BAYES,
    n_shifts: int = 16,
) -> list[float]:
    """Translation-invariant denoising via cycle spinning.

    Applies wavelet denoising to all ``n_shifts`` circular shifts of the
    input signal, denoises each, shifts back, and averages.  This
    dramatically reduces the pseudo-Gibbs artifacts that plague
    ordinary (decimated) wavelet denoising.

    Parameters
    ----------
    signal : noisy input signal
    wavelet : wavelet name or object
    level : decomposition level (default: max)
    threshold_method : threshold estimation method
    n_shifts : number of circular shifts to try (default: 16).
               Using ``len(signal)`` shifts gives the full cycle-spinning
               average but is O(n²).
    """
    n = len(signal)
    if n_shifts > n:
        n_shifts = n
    if n_shifts < 1:
        n_shifts = 1

    if isinstance(wavelet, str):
        from .wavelets import wavelet as _w
        wavelet = _w(wavelet)

    dwt = DWT(wavelet)
    accum = [0.0] * n

    for s in range(n_shifts):
        shift = (s * n) // n_shifts  # evenly spaced shifts
        # Circular shift
        shifted = signal[shift:] + signal[:shift]
        # Denoise
        result = dwt.decompose(shifted, level)
        if result.details:
            sigma = estimate_sigma(result.details[0])
        else:
            sigma = 0.0
        for i, detail in enumerate(result.details):
            t = estimate_threshold(detail, threshold_method, sigma)
            result.details[i] = [soft(c, t) for c in detail]
        denoised_shifted = dwt.reconstruct(result)
        # Shift back
        if shift > 0:
            unshifted = denoised_shifted[-shift:] + denoised_shifted[:-shift]
        else:
            unshifted = denoised_shifted
        accum = [accum[i] + unshifted[i] for i in range(n)]

    return [a / n_shifts for a in accum]