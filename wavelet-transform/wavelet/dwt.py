"""
Discrete Wavelet Transform (DWT) — 1-D and 2-D multilevel decomposition & reconstruction.

Implements the Mallat algorithm with periodic (circular) boundary extension.

Convention (matching PyWavelets):
  Decomposition (convolution + downsample):
    a[i] = Σ_j dec_lo[j] * signal[(2i - j) mod n]
    d[i] = Σ_j dec_hi[j] * signal[(2i - j) mod n]

  Reconstruction (upsample + convolution):
    x[m] = Σ_j rec_lo[j] * a_up[(m - j) mod N] + Σ_j rec_hi[j] * d_up[(m - j) mod N]
    where a_up[k] = a[k//2] if k is even, 0 if k is odd.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from .wavelets import Wavelet


@dataclass
class DWTResult:
    """Result of a multilevel 1-D DWT decomposition.

    ``approx`` holds the final-level approximation coefficients.
    ``details`` is a list of detail coefficient arrays, one per level
    (index 0 = finest scale, index -1 = coarsest scale).
    ``level_lengths`` stores the signal length at each decomposition level
    (needed for correct reconstruction with periodic boundary).
    """

    approx: List[float] = field(default_factory=list)
    details: List[List[float]] = field(default_factory=list)
    level: int = 0
    wavelet_name: str = ""
    input_length: int = 0
    # Length of the signal at each level: [n, n1, n2, ..., n_level]
    # where n is the input length and n_k is the approx length after level k
    level_lengths: List[int] = field(default_factory=list)

    def __repr__(self) -> str:
        sizes = [len(d) for d in self.details] + [len(self.approx)]
        return (f"DWTResult(level={self.level}, wavelet='{self.wavelet_name}', "
                f"sizes={sizes})")

    def coeffs(self) -> List[List[float]]:
        """Return all coefficients as a list: [detail_0, ..., detail_{L-1}, approx]."""
        return list(self.details) + [list(self.approx)]


# -------------------------------------------------------------------------
# Convolution / downsampling helpers
# -------------------------------------------------------------------------
def _conv_downsample(signal: list[float], filt: list[float]) -> list[float]:
    """Convolve signal with filter and downsample by 2.

    Computes: out[i] = Σ_j filt[j] * signal[(2i - j) mod n]
    (convolution with periodic boundary, then keep even indices).

    Output length is n // 2.
    """
    n = len(signal)
    L = len(filt)
    out_len = n // 2
    out = [0.0] * out_len
    for i in range(out_len):
        k = 2 * i
        acc = 0.0
        for j in range(L):
            idx = (k - j) % n  # convolution: 2i - j
            acc += signal[idx] * filt[j]
        out[i] = acc
    return out


def _upsample_convolve(signal: list[float], filt: list[float],
                       out_len: int) -> list[float]:
    """Upsample signal by 2 (insert zeros at odd positions), cross-correlate with filter.

    Computes: out[m] = Σ_j filt[j] * upsampled[(m + j) mod out_len]
    where upsampled[k] = signal[k // 2] if k is even, 0 if k is odd.

    This is the adjoint (transpose) of the convolution+downsample operation,
    which ensures perfect reconstruction when the same filter is used for both
    decomposition and reconstruction (for orthogonal wavelets).
    """
    n = len(signal)
    L = len(filt)
    out = [0.0] * out_len
    for i in range(out_len):
        acc = 0.0
        for j in range(L):
            src_idx = (i + j) % out_len  # cross-correlation: m + j
            if src_idx % 2 != 0:
                continue  # zero from upsampling (only even positions have data)
            signal_idx = src_idx // 2
            if 0 <= signal_idx < n:
                acc += signal[signal_idx] * filt[j]
        out[i] = acc
    return out


# -------------------------------------------------------------------------
# Single-level transform
# -------------------------------------------------------------------------
class DWT:
    """Discrete Wavelet Transform with multilevel support (1-D and 2-D)."""

    def __init__(self, wavelet: Wavelet | str) -> None:
        if isinstance(wavelet, str):
            from .wavelets import wavelet as _w
            wavelet = _w(wavelet)
        self.wavelet = wavelet

    # --- 1-D single level -------------------------------------------------
    def decompose1(self, signal: list[float]) -> tuple[list[float], list[float]]:
        """Single-level 1-D decomposition -> (approx, detail)."""
        approx = _conv_downsample(signal, self.wavelet.dec_lo)
        detail = _conv_downsample(signal, self.wavelet.dec_hi)
        return approx, detail

    def reconstruct1(self, approx: list[float],
                     detail: list[float], out_len: int | None = None) -> list[float]:
        """Single-level 1-D reconstruction.

        ``out_len`` should be the length of the original signal (before
        decompose1).  If None, it is inferred as 2*len(approx).
        """
        if out_len is None:
            out_len = 2 * len(approx)
        a = _upsample_convolve(approx, self.wavelet.rec_lo, out_len)
        d = _upsample_convolve(detail, self.wavelet.rec_hi, out_len)
        return [a[i] + d[i] for i in range(out_len)]

    # --- 1-D multilevel ----------------------------------------------------
    def decompose(self, signal: list[float], level: int | None = None) -> DWTResult:
        """Multilevel 1-D decomposition (wavelet decomposition tree).

        Repeatedly decomposes the approximation coefficients.
        """
        n = len(signal)
        if n < self.wavelet.filter_length:
            raise ValueError(f"Signal length {n} < filter length {self.wavelet.filter_length}")
        max_level = self.max_level(n)
        if level is None:
            level = max_level
        if level > max_level:
            raise ValueError(f"Level {level} exceeds max level {max_level} for length {n}")
        if level < 1:
            raise ValueError("Level must be >= 1")

        details: list[list[float]] = []
        approx = list(signal)
        level_lengths = [n]
        for _ in range(level):
            approx, detail = self.decompose1(approx)
            details.append(detail)
            level_lengths.append(len(approx))
        return DWTResult(
            approx=approx,
            details=details,
            level=level,
            wavelet_name=self.wavelet.name,
            input_length=n,
            level_lengths=level_lengths,
        )

    def reconstruct(self, result: DWTResult) -> list[float]:
        """Multilevel reconstruction from a DWTResult."""
        approx = list(result.approx)
        details = list(reversed(result.details))
        # Use stored level lengths for correct reconstruction sizes
        # level_lengths = [n, n1, n2, ..., n_L]
        # Reconstruction goes from level L back to 0:
        # level L -> level L-1: out_len = level_lengths[L-1]
        # level L-1 -> level L-2: out_len = level_lengths[L-2]
        # ...
        # level 1 -> level 0: out_len = level_lengths[0] = input_length
        for i, detail in enumerate(details):
            # The target output length for this reconstruction step
            # is the length of the signal BEFORE the corresponding decomposition.
            # details is reversed, so the first element is the coarsest detail.
            # If original level = L, reversed details = [d_L, d_{L-1}, ..., d_1]
            # Step 0: reconstruct from level L to L-1 -> out_len = level_lengths[L-1]
            # Step 1: reconstruct from level L-1 to L-2 -> out_len = level_lengths[L-2]
            # Step i: out_len = level_lengths[L - 1 - i]
            if result.level_lengths:
                level_idx = result.level - 1 - i
                out_len = result.level_lengths[level_idx]
            else:
                out_len = 2 * len(approx)
            approx = self.reconstruct1(approx, detail, out_len=out_len)
        return list(approx)

    def max_level(self, n: int) -> int:
        """Maximum decomposition level for a signal of length n."""
        L = self.wavelet.filter_length
        if n < L:
            return 0
        if L <= 1:
            return int(math.floor(math.log2(n))) if n > 1 else 0
        return int(math.floor(math.log2(n / (L - 1))))

    # --- 2-D transforms ---------------------------------------------------
    def decompose2(self, matrix: list[list[float]],
                   level: int | None = None) -> dict:
        """2-D wavelet decomposition (separable: rows then columns).

        Returns a dict of subbands per level.  Each level produces 4 subbands:
        'LL', 'LH', 'HL', 'HH'.  The 'LL' of each level is further decomposed.
        """
        rows = len(matrix)
        cols = len(matrix[0]) if rows else 0
        if rows < self.wavelet.filter_length or cols < self.wavelet.filter_length:
            raise ValueError(f"Matrix {rows}x{cols} too small for wavelet length {self.wavelet.filter_length}")
        max_level = min(self.max_level(rows), self.max_level(cols))
        if level is None:
            level = max_level
        if level > max_level:
            raise ValueError(f"Level {level} exceeds max level {max_level}")

        result = {"subbands": [], "level": level, "shape": (rows, cols),
                  "wavelet": self.wavelet.name}
        LL = [list(row) for row in matrix]
        for lv in range(level):
            # Decompose each row -> half-width
            low_rows = []
            high_rows = []
            for r in range(len(LL)):
                a, d = self.decompose1(LL[r])
                low_rows.append(a)
                high_rows.append(d)
            # Decompose each column of [low_rows] and [high_rows]
            LL_new, LH = self._decompose_cols(low_rows)
            HL, HH = self._decompose_cols(high_rows)
            result["subbands"].append({"LH": LH, "HL": HL, "HH": HH})
            LL = LL_new
        result["LL"] = LL
        return result

    def reconstruct2(self, decomp: dict) -> list[list[float]]:
        """2-D wavelet reconstruction from decompose2 output."""
        rows, cols = decomp["shape"]
        LL = [list(row) for row in decomp["LL"]]
        for lv in reversed(range(decomp["level"])):
            sb = decomp["subbands"][lv]
            LH, HL, HH = sb["LH"], sb["HL"], sb["HH"]
            # First reconstruct columns (inverse column transform)
            low_rows = self._reconstruct_cols(LL, LH)
            high_rows = self._reconstruct_cols(HL, HH)
            # Then reconstruct rows
            full = []
            for r in range(len(low_rows)):
                out_w = 2 * len(low_rows[r])
                row = self.reconstruct1(low_rows[r], high_rows[r], out_len=out_w)
                full.append(row)
            LL = full
        # Trim to original shape
        return [row[:cols] for row in LL[:rows]]

    def _decompose_cols(self, rows: list[list[float]]) -> tuple[list[list[float]], list[list[float]]]:
        """Decompose columns of a matrix -> (low_cols_matrix, high_cols_matrix)."""
        nrows = len(rows)
        ncols = len(rows[0]) if nrows else 0
        # Transpose, decompose each row (was column), transpose back
        cols_T = [[rows[r][c] for r in range(nrows)] for c in range(ncols)]
        low_cols = []
        high_cols = []
        for c in range(ncols):
            a, d = self.decompose1(cols_T[c])
            low_cols.append(a)
            high_cols.append(d)
        # Transpose back
        low_nrows = len(low_cols[0]) if low_cols else 0
        low_mat = [[low_cols[c][r] for c in range(ncols)] for r in range(low_nrows)]
        high_mat = [[high_cols[c][r] for c in range(ncols)] for r in range(low_nrows)]
        return low_mat, high_mat

    def _reconstruct_cols(self, low_mat: list[list[float]],
                          high_mat: list[list[float]]) -> list[list[float]]:
        """Inverse column transform: reconstruct full columns from low/high."""
        nrows = len(low_mat)
        ncols = len(low_mat[0]) if nrows else 0
        out_nrows = 2 * nrows
        # Transpose to work column-wise
        low_T = [[low_mat[r][c] for r in range(nrows)] for c in range(ncols)]
        high_T = [[high_mat[r][c] for r in range(nrows)] for c in range(ncols)]
        full_T = []
        for c in range(ncols):
            out_h = 2 * len(low_T[c])
            col = self.reconstruct1(low_T[c], high_T[c], out_len=out_h)
            full_T.append(col)
        # Transpose back
        result = [[full_T[c][r] for c in range(ncols)] for r in range(out_nrows)]
        return result