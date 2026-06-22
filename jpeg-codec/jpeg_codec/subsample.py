"""Chroma subsampling for JPEG.

JPEG allows the chrominance channels to be downsampled relative to
luminance, reducing the data volume.  Common ratios:

  - 4:4:4 -- no downsampling (1x1 per MCU per channel)
  - 4:2:2 -- horizontal 2:1 (2x1)
  - 4:2:0 -- horizontal & vertical 2:1 (2x2)  [the most common]
  - 4:1:1 -- horizontal 4:1 (4x1)

Each channel has an (h, v) sampling factor.  The MCU (minimum coded unit)
is the block-grid size that covers all channels.  For 4:2:0, luma is 2x2
blocks and each chroma is 1x1 block, so the MCU is 16x16 pixels.

This module provides functions to upsample / downsample channel planes
by integer factors using simple pixel averaging (for downsampling) and
nearest-neighbour replication (for upsampling), which is the standard
JPEG "box" filter behaviour.
"""

import numpy as np

# Sampling factors: name -> (h, v) per channel, for the three channels
# [Y, Cb, Cr].  Y always has (1,1) in this mapping; the chroma factors
# express the *relative* subsampling.
SAMPLING_MODES = {
    "4:4:4": [(1, 1), (1, 1), (1, 1)],
    "4:2:2": [(2, 1), (1, 1), (1, 1)],
    "4:2:0": [(2, 2), (1, 1), (1, 1)],
    "4:1:1": [(4, 1), (1, 1), (1, 1)],
}


def get_sampling_factors(mode: str):
    """Return the (h, v) sampling factors for the three channels."""
    if mode not in SAMPLING_MODES:
        raise ValueError(f"Unknown sampling mode: {mode}")
    return SAMPLING_MODES[mode]


def downsample_channel(channel: np.ndarray, h: int, v: int) -> np.ndarray:
    """Downsample a single-channel plane by factor (h, v) via averaging.

    If h == v == 1 the channel is returned unchanged.
    The input is padded (edge-replicated) so that dimensions divide evenly.
    """
    if h == 1 and v == 1:
        return channel.astype(np.float64).copy()

    rows, cols = channel.shape
    # Pad to a multiple of (v, h) using edge replication.
    pad_r = (v - rows % v) % v
    pad_c = (h - cols % h) % h
    if pad_r or pad_c:
        channel = np.pad(channel, ((0, pad_r), (0, pad_c)), mode="edge")

    channel = channel.astype(np.float64)
    # Reshape and average.
    new_rows = channel.shape[0] // v
    new_cols = channel.shape[1] // h
    reshaped = channel.reshape(new_rows, v, new_cols, h)
    return reshaped.mean(axis=(1, 3))


def upsample_channel(channel: np.ndarray, h: int, v: int,
                     target_shape: tuple) -> np.ndarray:
    """Upsample a single-channel plane to *target_shape* by replication."""
    if h == 1 and v == 1:
        return channel.copy()
    # Nearest-neighbour replication.
    up = np.repeat(np.repeat(channel, v, axis=0), h, axis=1)
    # Crop or pad to the exact target shape (padding with edge values).
    tr, tc = target_shape
    if up.shape[0] < tr or up.shape[1] < tc:
        up = np.pad(up,
                    ((0, tr - up.shape[0]), (0, tc - up.shape[1])),
                    mode="edge")
    return up[:tr, :tc]