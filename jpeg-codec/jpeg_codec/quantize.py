"""Quantisation tables and per-block quantisation / dequantisation.

JPEG compresses by dividing each DCT coefficient by a quantisation step
and rounding to the nearest integer.  Larger steps discard more information
(higher compression, lower quality).

The standard JPEG quantisation tables (Annex K of the JPEG standard, the
"examples" from the Independent JPEG Group) are used by default, scaled by
a quality factor derived from the user-supplied quality (1-100).
"""

import numpy as np

from .zigzag import ZIGZAG_ORDER

# Standard JPEG luminance quantisation table (zig-zag order, flat 64).
STD_LUMINANCE_QT_ZZ = np.array([
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68,109,103, 77, 24, 35, 55, 64, 81,104,113, 92,
    49, 64, 78, 87,103,121,120,101, 72, 92, 95, 98,112,100,103, 99,
], dtype=np.float64)

# Standard JPEG chrominance quantisation table (zig-zag order, flat 64).
STD_CHROMINANCE_QT_ZZ = np.array([
    17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99,
    24, 26, 56, 99, 99, 99, 99, 99, 47, 66, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
], dtype=np.float64)


def _unzigzag(flat_zz: np.ndarray) -> np.ndarray:
    """Convert a 64-element zig-zag-ordered array to an 8x8 block.

    ``ZIGZAG_ORDER[i]`` gives the flat 8x8 index of the i-th zig-zag
    position, so we scatter each value to its natural position.
    """
    block = np.zeros(64, dtype=flat_zz.dtype)
    for i in range(64):
        block[ZIGZAG_ORDER[i]] = flat_zz[i]
    return block.reshape(8, 8)


def get_quantization_tables(quality: int = 50):
    """Return (luma_qt, chroma_qt) as 8x8 arrays scaled for *quality*.

    Parameters
    ----------
    quality : int
        1 (worst) .. 100 (best).  50 uses the unscaled standard tables.

    Returns
    -------
    (np.ndarray, np.ndarray)
        Two 8x8 quantisation tables (luminance, chrominance), in natural
        (row-major) 8x8 layout.
    """
    if not 1 <= quality <= 100:
        raise ValueError(f"quality must be in [1, 100], got {quality}")

    # Standard JPEG quality scaling (libjpeg-compatible).
    if quality < 50:
        scale = 5000 / quality
    else:
        scale = 200 - 2 * quality

    def _scale_table(std_zz: np.ndarray) -> np.ndarray:
        scaled = (std_zz * scale + 50) / 100
        scaled = np.clip(scaled, 1, 255)
        # Round to integers so the encoder and DQT segment agree exactly.
        scaled = np.round(scaled).astype(np.int32).astype(np.float64)
        return _unzigzag(scaled)

    luma_qt = _scale_table(STD_LUMINANCE_QT_ZZ)
    chroma_qt = _scale_table(STD_CHROMINANCE_QT_ZZ)
    return luma_qt, chroma_qt


def quantize_block(block: np.ndarray, qt: np.ndarray) -> np.ndarray:
    """Quantise a DCT coefficient block: round(block / qt)."""
    return np.round(block / qt).astype(np.int32)


def dequantize_block(coeffs: np.ndarray, qt: np.ndarray) -> np.ndarray:
    """Reverse quantisation: coeffs * qt."""
    return coeffs.astype(np.float64) * qt