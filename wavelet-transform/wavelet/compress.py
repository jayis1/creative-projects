"""
Wavelet-based signal compression.

Compression strategy:
  1. Forward DWT
  2. Threshold / quantize detail coefficients (set small coefficients to zero)
  3. Run-length encode the sparse coefficient array
  4. Store as a compact binary format

Decompression reverses the process.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from typing import List

from .dwt import DWT
from .wavelets import Wavelet


@dataclass
class CompressedSignal:
    """Compressed signal representation."""

    wavelet_name: str = ""
    input_length: int = 0
    level: int = 0
    approx: List[float] = field(default_factory=list)
    detail_thresholds: List[float] = field(default_factory=list)
    # Run-length-encoded details: list of (value, count) pairs per level
    rle_details: List[List[tuple[float, int]]] = field(default_factory=list)
    n_coeffs_total: int = 0  # original number of coefficients
    n_coeffs_kept: int = 0   # non-zero after thresholding

    @property
    def compression_ratio(self) -> float:
        if self.n_coeffs_kept == 0:
            return float("inf")
        return self.n_coeffs_total / self.n_coeffs_kept

    @property
    def sparsity(self) -> float:
        if self.n_coeffs_total == 0:
            return 0.0
        return 1.0 - (self.n_coeffs_kept / self.n_coeffs_total)


def _rle_encode(data: list[float]) -> list[tuple[float, int]]:
    """Run-length encode a list of floats (consecutive equal values)."""
    if not data:
        return []
    result = []
    current = data[0]
    count = 1
    for val in data[1:]:
        if val == current:
            count += 1
        else:
            result.append((current, count))
            current = val
            count = 1
    result.append((current, count))
    return result


def _rle_decode(rle: list[tuple[float, int]]) -> list[float]:
    """Decode run-length encoded data."""
    result = []
    for val, count in rle:
        result.extend([val] * count)
    return result


def compress1d(
    signal: list[float],
    wavelet: Wavelet | str = "db4",
    level: int | None = None,
    threshold: float | None = None,
    keep_ratio: float | None = None,
) -> CompressedSignal:
    """Compress a 1-D signal using wavelet thresholding + RLE.

    Either ``threshold`` (absolute) or ``keep_ratio`` (fraction of coefficients
    to keep, sorted by magnitude) can be specified.  If neither, threshold=0.
    """
    if isinstance(wavelet, str):
        from .wavelets import wavelet as _w
        wavelet = _w(wavelet)

    dwt = DWT(wavelet)
    result = dwt.decompose(signal, level)

    # Determine threshold
    detail_thresholds = []
    all_details = []
    for d in result.details:
        all_details.extend(d)

    if threshold is not None:
        t = threshold
    elif keep_ratio is not None:
        if not (0 < keep_ratio <= 1):
            raise ValueError("keep_ratio must be in (0, 1]")
        abs_sorted = sorted(abs(c) for c in all_details)
        n_keep = max(1, int(len(abs_sorted) * keep_ratio))
        t = abs_sorted[-n_keep] if n_keep <= len(abs_sorted) else 0.0
    else:
        t = 0.0

    # Apply threshold to detail coefficients
    from .threshold import soft
    rle_details = []
    n_total = 0
    n_kept = 0
    for detail in result.details:
        threshed = [soft(c, t) for c in detail]
        n_total += len(threshed)
        n_kept += sum(1 for c in threshed if c != 0.0)
        detail_thresholds.append(t)
        rle_details.append(_rle_encode(threshed))

    return CompressedSignal(
        wavelet_name=wavelet.name,
        input_length=result.input_length,
        level=result.level,
        approx=list(result.approx),
        detail_thresholds=detail_thresholds,
        rle_details=rle_details,
        n_coeffs_total=n_total,
        n_coeffs_kept=n_kept,
    )


def decompress1d(compressed: CompressedSignal) -> list[float]:
    """Decompress a CompressedSignal back to the time domain."""
    from .wavelets import wavelet as _w
    wavelet = _w(compressed.wavelet_name)
    dwt = DWT(wavelet)

    details = [_rle_decode(rle) for rle in compressed.rle_details]

    from .dwt import DWTResult
    result = DWTResult(
        approx=list(compressed.approx),
        details=details,
        level=compressed.level,
        wavelet_name=compressed.wavelet_name,
        input_length=compressed.input_length,
    )
    return dwt.reconstruct(result)


def serialize(compressed: CompressedSignal) -> bytes:
    """Serialize a CompressedSignal to a compact binary format."""
    parts = []
    # Header: wavelet name, input_length, level, n_total, n_kept
    name_bytes = compressed.wavelet_name.encode("utf-8")
    parts.append(struct.pack("I", len(name_bytes)))
    parts.append(name_bytes)
    parts.append(struct.pack("III", compressed.input_length, compressed.level,
                             compressed.n_coeffs_total))
    parts.append(struct.pack("I", compressed.n_coeffs_kept))
    # Approximation coefficients
    parts.append(struct.pack("I", len(compressed.approx)))
    for c in compressed.approx:
        parts.append(struct.pack("d", c))
    # RLE details per level
    parts.append(struct.pack("I", len(compressed.rle_details)))
    for level_rle in compressed.rle_details:
        parts.append(struct.pack("I", len(level_rle)))
        for val, count in level_rle:
            parts.append(struct.pack("dI", val, count))
    return b"".join(parts)


def deserialize(data: bytes) -> CompressedSignal:
    """Deserialize bytes back to a CompressedSignal."""
    offset = 0

    def unpack(fmt: str):
        nonlocal offset
        size = struct.calcsize(fmt)
        result = struct.unpack_from(fmt, data, offset)
        offset += size
        return result

    name_len = unpack("I")[0]
    name = data[offset:offset + name_len].decode("utf-8")
    offset += name_len
    input_length, level, n_total = unpack("III")
    n_kept = unpack("I")[0]
    approx_len = unpack("I")[0]
    approx = []
    for _ in range(approx_len):
        approx.append(unpack("d")[0])
    n_levels = unpack("I")[0]
    rle_details = []
    for _ in range(n_levels):
        n_pairs = unpack("I")[0]
        pairs = []
        for _ in range(n_pairs):
            val, count = unpack("dI")
            pairs.append((val, count))
        rle_details.append(pairs)

    return CompressedSignal(
        wavelet_name=name, input_length=input_length, level=level,
        approx=approx, rle_details=rle_details,
        n_coeffs_total=n_total, n_coeffs_kept=n_kept,
    )