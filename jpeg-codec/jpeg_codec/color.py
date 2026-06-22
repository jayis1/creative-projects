"""RGB <-> YCbCr colour-space conversion.

JPEG operates in the YCbCr colour space (defined by JFIF / ITU-R BT.601)
rather than RGB.  The luminance (Y) channel carries most of the perceptual
detail; the two chrominance channels (Cb, Cr) can be subsampled without
much visible loss.
"""

import numpy as np


def rgb_to_ycbcr(rgb: np.ndarray) -> np.ndarray:
    """Convert an (..., 3) RGB array (range 0-255) to YCbCr (range 0-255).

    Parameters
    ----------
    rgb : np.ndarray
        Floating-point array with last dimension 3, values in [0, 255].

    Returns
    -------
    np.ndarray
        Same shape, channels ordered [Y, Cb, Cr].
    """
    rgb = rgb.astype(np.float64)
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]

    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b + 128.0
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b + 128.0

    return np.stack([y, cb, cr], axis=-1)


def ycbcr_to_rgb(ycbcr: np.ndarray) -> np.ndarray:
    """Convert an (..., 3) YCbCr array back to RGB (range 0-255)."""
    ycbcr = ycbcr.astype(np.float64)
    y = ycbcr[..., 0]
    cb = ycbcr[..., 1] - 128.0
    cr = ycbcr[..., 2] - 128.0

    r = y + 1.402 * cr
    g = y - 0.344136 * cb - 0.714136 * cr
    b = y + 1.772 * cb

    rgb = np.stack([r, g, b], axis=-1)
    return np.clip(rgb, 0, 255)


def level_shift(block: np.ndarray) -> np.ndarray:
    """Level-shift a block from [0, 255] to [-128, 127] before the DCT."""
    return block.astype(np.float64) - 128.0


def unlevel_shift(block: np.ndarray) -> np.ndarray:
    """Reverse the level shift applied by :func:`level_shift`."""
    return block + 128.0