"""
Boundary extension strategies for the wavelet transform.

The base DWT implementation uses periodic (circular) boundary extension.
This module provides alternative boundary handling modes that can be
used with the single-level DWT:

  - **periodic** (default): wrap around — ``signal[-1]`` connects to ``signal[0]``
  - **symmetric**: mirror the signal at the boundary (a.k.a. half-point symmetry)
  - **zero-pad**: extend with zeros
  - **constant**: extend with the edge value
  - **reflect**: mirror without repeating the edge sample (a.k.a. whole-point)

These are applied by extending the signal before decomposition and
trimming the result after reconstruction.  They can reduce boundary
artifacts compared to periodic extension for non-periodic signals.
"""

from __future__ import annotations

import math

__all__ = [
    "BoundaryMode",
    "extend_signal",
    "trim_signal",
    "conv_downsample_boundary",
    "upsample_convolve_boundary",
]


class BoundaryMode:
    """Boundary extension mode constants."""
    PERIODIC = "periodic"
    SYMMETRIC = "symmetric"
    ZERO = "zero"
    CONSTANT = "constant"
    REFLECT = "reflect"

    ALL = (PERIODIC, SYMMETRIC, ZERO, CONSTANT, REFLECT)


def extend_signal(signal: list[float], filter_len: int,
                  mode: str = BoundaryMode.SYMMETRIC) -> list[float]:
    """Extend a signal for boundary handling.

    The extension length is ``filter_len - 1`` samples on each side
    (enough for convolution with a filter of length ``filter_len``).
    """
    n = len(signal)
    if n == 0:
        return []
    ext = filter_len - 1
    if ext <= 0:
        return list(signal)

    left: list[float] = []
    right: list[float] = []

    if mode == BoundaryMode.PERIODIC:
        left = [signal[(i % n)] for i in range(-ext, 0)]
        right = [signal[(i % n)] for i in range(n, n + ext)]
    elif mode == BoundaryMode.SYMMETRIC:
        # Half-point symmetric: abc | cba...abc | cba
        for i in range(1, ext + 1):
            left.append(signal[(-i) % n if n > 0 else 0])
        # Actually, proper symmetric: mirror around boundary
        left = []
        idx = n - 1
        direction = -1
        for _ in range(ext):
            left.append(signal[idx])
            idx += direction
            if idx < 0:
                idx = 1
                direction = 1
            elif idx >= n:
                idx = n - 2
                direction = -1
        right = []
        idx = 0
        direction = 1
        for _ in range(ext):
            right.append(signal[idx])
            idx += direction
            if idx < 0:
                idx = 1
                direction = 1
            elif idx >= n:
                idx = n - 2
                direction = -1
    elif mode == BoundaryMode.ZERO:
        left = [0.0] * ext
        right = [0.0] * ext
    elif mode == BoundaryMode.CONSTANT:
        left = [signal[0]] * ext
        right = [signal[-1]] * ext
    elif mode == BoundaryMode.REFLECT:
        # Whole-point symmetric: (d c) b a | a b c d | (d c) b a
        left = []
        for i in range(1, ext + 1):
            left.append(signal[i % n])
        left.reverse()
        right = []
        for i in range(ext):
            right.append(signal[(n - 2 - i) % n])
    else:
        raise ValueError(f"Unknown boundary mode '{mode}'. "
                         f"Supported: {BoundaryMode.ALL}")

    return left + list(signal) + right


def trim_signal(extended: list[float], orig_len: int,
                filter_len: int) -> list[float]:
    """Remove the boundary extension from a reconstructed signal."""
    ext = filter_len - 1
    if ext <= 0:
        return list(extended)
    start = ext
    end = start + orig_len
    return extended[start:end]


def conv_downsample_boundary(signal: list[float], filt: list[float],
                             mode: str = BoundaryMode.PERIODIC) -> list[float]:
    """Convolve + downsample with a specified boundary mode.

    Returns coefficients of length ``len(signal) // 2``.
    """
    n = len(signal)
    L = len(filt)
    if mode == BoundaryMode.PERIODIC:
        # Use the fast periodic version
        out_len = n // 2
        out = [0.0] * out_len
        for i in range(out_len):
            k = 2 * i
            acc = 0.0
            for j in range(L):
                idx = (k - j) % n
                acc += signal[idx] * filt[j]
            out[i] = acc
        return out

    # For other modes: extend, convolve (linear), then downsample
    ext_signal = extend_signal(signal, L, mode)
    total_len = len(ext_signal)
    # Full convolution then pick the right samples
    out_len = n // 2
    out = [0.0] * out_len
    for i in range(out_len):
        k = 2 * i + (L - 1)  # offset due to extension on the left
        acc = 0.0
        for j in range(L):
            idx = k - j
            if 0 <= idx < total_len:
                acc += ext_signal[idx] * filt[j]
        out[i] = acc
    return out


def upsample_convolve_boundary(signal: list[float], filt: list[float],
                               out_len: int,
                               mode: str = BoundaryMode.PERIODIC) -> list[float]:
    """Upsample + cross-correlate with a specified boundary mode.

    Returns a signal of length ``out_len``.
    """
    n = len(signal)
    L = len(filt)
    if mode == BoundaryMode.PERIODIC:
        out = [0.0] * out_len
        for i in range(out_len):
            acc = 0.0
            for j in range(L):
                src_idx = (i + j) % out_len
                if src_idx % 2 != 0:
                    continue
                signal_idx = src_idx // 2
                if 0 <= signal_idx < n:
                    acc += signal[signal_idx] * filt[j]
            out[i] = acc
        return out

    # For other modes: cross-correlate with boundary handling
    out = [0.0] * out_len
    for i in range(out_len):
        acc = 0.0
        for j in range(L):
            src_idx = i + j
            if src_idx % 2 != 0:
                continue
            signal_idx = src_idx // 2
            if 0 <= signal_idx < n:
                acc += signal[signal_idx] * filt[j]
            elif mode == BoundaryMode.ZERO:
                pass  # zero contribution
            elif mode == BoundaryMode.CONSTANT:
                if signal_idx < 0:
                    acc += signal[0] * filt[j]
                else:
                    acc += signal[-1] * filt[j]
            elif mode in (BoundaryMode.SYMMETRIC, BoundaryMode.REFLECT):
                # Mirror the index
                mirrored = _mirror_index(signal_idx, n, mode)
                if 0 <= mirrored < n:
                    acc += signal[mirrored] * filt[j]
        out[i] = acc
    return out


def _mirror_index(idx: int, n: int, mode: str) -> int:
    """Map an out-of-range index to a valid index using mirroring."""
    if n == 0:
        return 0
    if mode == BoundaryMode.SYMMETRIC:
        period = 2 * n
        idx = idx % period
        if idx >= n:
            idx = period - 1 - idx
        return idx
    elif mode == BoundaryMode.REFLECT:
        if n == 1:
            return 0
        period = 2 * (n - 1)
        idx = idx % period
        if idx >= n:
            idx = period - idx
        return idx
    return max(0, min(n - 1, idx))