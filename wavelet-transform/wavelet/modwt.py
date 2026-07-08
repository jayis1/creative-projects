"""
Maximal Overlap Discrete Wavelet Transform (MODWT).

Unlike the standard DWT, the MODWT:
  - Does not decimate (output length = input length at every level)
  - Is translation-invariant
  - Is defined for any sample size (not just powers of 2)

This implementation follows Percival & Walden (2000), "Wavelet Methods for
Time Series Analysis".

The MODWT uses the same filter coefficients as the DWT but:
  - Filters are scaled by 1/√2
  - Filters are upsampled by 2^(j-1) at level j (inserting zeros)
  - No downsampling is applied
  - Convolution is used for decomposition, cross-correlation for reconstruction
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from .wavelets import Wavelet


@dataclass
class MODWTResult:
    """Result of multilevel MODWT decomposition."""

    approx: List[float] = field(default_factory=list)
    details: List[List[float]] = field(default_factory=list)
    level: int = 0
    wavelet_name: str = ""
    input_length: int = 0

    def __repr__(self) -> str:
        return (f"MODWTResult(level={self.level}, wavelet='{self.wavelet_name}', "
                f"len={self.input_length})")


def _upsample_filter(filt: list[float], factor: int) -> list[float]:
    """Upsample a filter by inserting ``factor-1`` zeros between each coefficient."""
    if factor <= 1:
        return list(filt)
    result = []
    for i, c in enumerate(filt):
        result.append(c)
        if i < len(filt) - 1:
            result.extend([0.0] * (factor - 1))
    return result


class MODWT:
    """Maximal Overlap DWT (translation-invariant, non-decimated).

    Uses convolution for decomposition and cross-correlation for reconstruction,
    matching the DWT convention.  Filters are scaled by 1/√2 per level.
    """

    def __init__(self, wavelet: Wavelet | str) -> None:
        if isinstance(wavelet, str):
            from .wavelets import wavelet as _w
            wavelet = _w(wavelet)
        self.wavelet = wavelet
        # Scale filters by 1/sqrt(2) for MODWT
        sq2 = math.sqrt(2)
        self._g = [c / sq2 for c in self.wavelet.dec_lo]   # scaled low-pass (decomposition)
        self._h = [c / sq2 for c in self.wavelet.dec_hi]   # scaled high-pass (decomposition)
        # For MODWT reconstruction (cross-correlation), use the same scaled filters
        # as decomposition. For orthogonal wavelets rec = dec, so this is correct.
        # For biorthogonal wavelets, use the rec filters (scaled).
        if self.wavelet.orthogonal:
            self._g_rec = list(self._g)
            self._h_rec = list(self._h)
        else:
            self._g_rec = [c / sq2 for c in self.wavelet.rec_lo]
            self._h_rec = [c / sq2 for c in self.wavelet.rec_hi]

    def decompose(self, signal: list[float], level: int | None = None) -> MODWTResult:
        """Decompose signal into ``level`` levels."""
        n = len(signal)
        if n < self.wavelet.filter_length:
            raise ValueError(f"Signal length {n} < filter length {self.wavelet.filter_length}")
        if level is None:
            level = self.max_level(n)
        if level > self.max_level(n):
            raise ValueError(f"Level {level} exceeds max level {self.max_level(n)}")

        details: list[list[float]] = []
        approx = list(signal)

        for j in range(1, level + 1):
            detail, approx = self._level_transform(approx, j)
            details.append(detail)

        return MODWTResult(
            approx=approx, details=details, level=level,
            wavelet_name=self.wavelet.name, input_length=n,
        )

    def reconstruct(self, result: MODWTResult) -> list[float]:
        """Reconstruct the original signal from MODWT coefficients."""
        approx = list(result.approx)   # V (approximation)
        n = result.input_length
        for j in reversed(range(1, result.level + 1)):
            detail = result.details[j - 1]  # W (detail)
            # _inverse_level expects (W, V, j) — note the order!
            approx = self._inverse_level(detail, approx, j)
        return approx

    def _level_transform(self, signal: list[float], j: int) -> tuple[list[float], list[float]]:
        """One level of MODWT (level j). Returns (W_j, V_j).

        Uses convolution with periodically upsampled filters (no downsampling).
        W_j[t] = Σ_l h_j[l] * signal[(t - l) mod n]   (convolution)
        V_j[t] = Σ_l g_j[l] * signal[(t - l) mod n]
        """
        n = len(signal)
        scale = 2 ** (j - 1)
        g_j = _upsample_filter(self._g, scale)
        h_j = _upsample_filter(self._h, scale)
        W = [0.0] * n
        V = [0.0] * n
        Lj = len(g_j)
        for t in range(n):
            w_sum = 0.0
            v_sum = 0.0
            for l in range(Lj):
                idx = (t - l) % n  # convolution
                w_sum += signal[idx] * h_j[l]
                v_sum += signal[idx] * g_j[l]
            W[t] = w_sum
            V[t] = v_sum
        return W, V

    def _inverse_level(self, W: list[float], V: list[float], j: int) -> list[float]:
        """Inverse of one MODWT level (level j). Returns reconstructed signal.

        Uses cross-correlation with periodically upsampled filters.
        x[t] = Σ_l (W[t+l] * h_j[l] + V[t+l] * g_j[l])   (cross-correlation)
        """
        n = len(V)
        scale = 2 ** (j - 1)
        g_j = _upsample_filter(self._g_rec, scale)
        h_j = _upsample_filter(self._h_rec, scale)
        Lj = len(g_j)
        out = [0.0] * n
        for t in range(n):
            s = 0.0
            for l in range(Lj):
                idx = (t + l) % n  # cross-correlation
                s += W[idx] * h_j[l] + V[idx] * g_j[l]
            out[t] = s
        return out

    def max_level(self, n: int) -> int:
        """Maximum decomposition level (MODWT can go to log2(n))."""
        if n < 1:
            return 0
        return max(1, int(math.floor(math.log2(n))))