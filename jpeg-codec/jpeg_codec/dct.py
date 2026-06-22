"""Forward and inverse 8x8 Discrete Cosine Transform (Type-II).

The 2-D DCT is separable, so we compute it as two 1-D transforms (rows then
columns) via matrix multiplication with a precomputed DCT basis matrix.
This is O(n^3) for an 8x8 block (512 multiplications) -- fast enough and
numerically stable.
"""

import numpy as np

# Precompute the 8x8 DCT-II basis matrix.
_N = 8
_C = np.zeros((_N, _N), dtype=np.float64)
for k in range(_N):
    for n in range(_N):
        if k == 0:
            _C[k, n] = np.sqrt(1.0 / _N)
        else:
            _C[k, n] = np.sqrt(2.0 / _N) * np.cos(
                (2 * n + 1) * k * np.pi / (2 * _N)
            )
# _C is orthogonal: C @ C.T == I, so the inverse is just C.T.
_C_INV = _C.T.copy()


def dct1d(signal: np.ndarray) -> np.ndarray:
    """1-D forward DCT-II of the last axis."""
    return _C @ signal


def idct1d(signal: np.ndarray) -> np.ndarray:
    """1-D inverse DCT-II (DCT-III) of the last axis."""
    return _C_INV @ signal


def dct2d(block: np.ndarray) -> np.ndarray:
    """Forward 2-D DCT-II of an 8x8 block.

    Because the transform is separable:  D = C @ block @ C.T
    """
    return _C @ block @ _C.T


def idct2d(block: np.ndarray) -> np.ndarray:
    """Inverse 2-D DCT-II of an 8x8 block.

    Inverse:  block = C.T @ D @ C
    """
    return _C_INV @ block @ _C