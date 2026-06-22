"""Zig-zag scan order for JPEG 8x8 blocks.

The JPEG standard reorders the 64 DCT coefficients of each 8x8 block in a
zig-zag pattern so that low-frequency coefficients come first.  This ordering
maximises the length of the trailing run of zeros, which the run-length
encoder exploits.
"""

import numpy as np

# The canonical JPEG zig-zag order, as a flat 64-element list of
# (row, col) pairs traversed in scan order.
_ZZ_POS = [
    (0, 0), (0, 1), (1, 0), (2, 0), (1, 1), (0, 2), (0, 3), (1, 2),
    (2, 1), (3, 0), (4, 0), (3, 1), (2, 2), (1, 3), (0, 4), (0, 5),
    (1, 4), (2, 3), (3, 2), (4, 1), (5, 0), (6, 0), (5, 1), (4, 2),
    (3, 3), (2, 4), (1, 5), (0, 6), (0, 7), (1, 6), (2, 5), (3, 4),
    (4, 3), (5, 2), (6, 1), (7, 0), (7, 1), (6, 2), (5, 3), (4, 4),
    (3, 5), (2, 6), (1, 7), (2, 7), (3, 6), (4, 5), (5, 4), (6, 3),
    (7, 2), (7, 3), (6, 4), (5, 5), (4, 6), (3, 7), (4, 7), (5, 6),
    (6, 5), (7, 4), (7, 5), (6, 6), (5, 7), (6, 7), (7, 6), (7, 7),
]

# Linear indices into a flattened 8x8 array, in zig-zag order.
ZIGZAG_ORDER = [r * 8 + c for (r, c) in _ZZ_POS]

# Inverse: given a position in zig-zag order, where does it land in the
# 8x8 block?  IZIGZAG_ORDER[zz_index] -> flat 8x8 index.
IZIGZAG_ORDER = [0] * 64
for _i, _idx in enumerate(ZIGZAG_ORDER):
    IZIGZAG_ORDER[_idx] = _i


def zigzag_block(block: np.ndarray) -> np.ndarray:
    """Flatten an 8x8 block into a 64-element 1-D array in zig-zag order."""
    flat = block.flatten()
    return flat[ZIGZAG_ORDER]


def izigzag_block(coefficients: np.ndarray) -> np.ndarray:
    """Reconstruct an 8x8 block from a 64-element zig-zag-ordered array.

    ``ZIGZAG_ORDER[i]`` gives the flat 8x8 index of the i-th zig-zag
    position, so we scatter the coefficients into those positions.
    """
    block = np.zeros(64, dtype=coefficients.dtype)
    block[ZIGZAG_ORDER] = coefficients
    return block.reshape(8, 8)