"""
seamcarving/energy.py — Energy functions for seam carving.

Each energy function takes a grayscale image ``(H, W)`` as ``float64``
and returns an energy map of the same shape.  Higher energy = more
visually important — the seam carving algorithm removes low-energy seams.

Available functions
-------------------
- ``sobel``      — Sobel operator gradient magnitude (default)
- ``prewitt``    — Prewitt operator gradient magnitude
- ``laplacian``  — Laplacian (second derivative) energy
- ``gradient``   — Simple central-difference gradient
- ``forward``    — Forward energy (Avidan et al. 2008)
- ``hofer``      — Hölder exponent energy (texture-based)
- ``entropy``    — Local entropy energy (window-based)
"""

from __future__ import annotations

import enum
from typing import Callable, Dict

import numpy as np

from .exceptions import EnergyComputationError


class EnergyType(enum.Enum):
    """Available energy functions for seam computation."""

    SOBEL = "sobel"
    PREWITT = "prewitt"
    LAPLACIAN = "laplacian"
    GRADIENT = "gradient"
    FORWARD = "forward"
    HOFER = "hofer"
    ENTROPY = "entropy"


# ---------------------------------------------------------------------------
# Grayscale conversion
# ---------------------------------------------------------------------------

def to_gray(img: np.ndarray) -> np.ndarray:
    """Convert an RGB image to grayscale using Rec. 601 luminance weights.

    Uses integer arithmetic internally to avoid floating-point precision
    artifacts (e.g., ``128*0.299 + 128*0.587 + 128*0.114 != 128.0`` exactly),
    then converts to ``float64`` for downstream gradient computation.
    """
    if img.ndim == 2:
        return img.astype(np.float64)
    if img.shape[2] == 1:
        return img[:, :, 0].astype(np.float64)
    # Integer-weighted sum: 299 + 587 + 114 = 1000
    gray_int = (
        img[:, :, 0].astype(np.int32) * 299
        + img[:, :, 1].astype(np.int32) * 587
        + img[:, :, 2].astype(np.int32) * 114
    )
    return gray_int.astype(np.float64) / 1000.0


# ---------------------------------------------------------------------------
# Energy functions
# ---------------------------------------------------------------------------

def sobel_energy(gray: np.ndarray) -> np.ndarray:
    """Compute energy using Sobel operator magnitude (|Gx| + |Gy|)."""
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[1:-1, 1:-1] = (
        -gray[:-2, :-2] - 2 * gray[:-2, 1:-1] - gray[:-2, 2:]
        + gray[2:, :-2] + 2 * gray[2:, 1:-1] + gray[2:, 2:]
    )
    gy[1:-1, 1:-1] = (
        -gray[:-2, :-2] + gray[:-2, 2:]
        - 2 * gray[1:-1, :-2] + 2 * gray[1:-1, 2:]
        - gray[2:, :-2] + gray[2:, 2:]
    )
    return np.abs(gx) + np.abs(gy)


def prewitt_energy(gray: np.ndarray) -> np.ndarray:
    """Compute energy using Prewitt operator magnitude (|Gx| + |Gy|)."""
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[1:-1, 1:-1] = (
        -gray[:-2, :-2] - gray[:-2, 1:-1] - gray[:-2, 2:]
        + gray[2:, :-2] + gray[2:, 1:-1] + gray[2:, 2:]
    )
    gy[1:-1, 1:-1] = (
        -gray[:-2, :-2] + gray[:-2, 2:]
        - gray[1:-1, :-2] + gray[1:-1, 2:]
        - gray[2:, :-2] + gray[2:, 2:]
    )
    return np.abs(gx) + np.abs(gy)


def laplacian_energy(gray: np.ndarray) -> np.ndarray:
    """Compute energy using Laplacian (second derivative)."""
    lap = np.zeros_like(gray)
    lap[1:-1, 1:-1] = (
        -gray[:-2, 1:-1] - gray[2:, 1:-1]
        - gray[1:-1, :-2] - gray[1:-1, 2:]
        + 4 * gray[1:-1, 1:-1]
    )
    return np.abs(lap)


def gradient_energy(gray: np.ndarray) -> np.ndarray:
    """Simple central-difference gradient energy."""
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = (gray[:, 2:] - gray[:, :-2]) / 2.0
    gy[1:-1, :] = (gray[2:, :] - gray[:-2, :]) / 2.0
    return np.abs(gx) + np.abs(gy)


def forward_energy(gray: np.ndarray) -> np.ndarray:
    """Forward energy cost (Avidan et al. 2008).

    Accounts for the energy *introduced* by removing a seam, not just
    the energy at the pixel.  Minimises the new adjacency cost created
    when neighbouring pixels become adjacent after seam removal.
    """
    h, w = gray.shape
    cu = np.zeros_like(gray)
    cL = np.zeros_like(gray)
    cR = np.zeros_like(gray)

    cu[:, 1:-1] = np.abs(gray[:, 2:] - gray[:, :-2])
    cL[:, 1:-1] = np.abs(gray[:, 1:-1] - gray[:, :-2]) + cu[:, 1:-1]
    cR[:, 1:-1] = np.abs(gray[:, 1:-1] - gray[:, 2:]) + cu[:, 1:-1]

    M = np.zeros((h, w), dtype=np.float64)
    M[0] = cu[0]
    for i in range(1, h):
        up = M[i - 1, :]
        left = np.empty(w)
        right = np.empty(w)
        left[0] = np.inf
        left[1:] = up[:-1]
        right[-1] = np.inf
        right[:-1] = up[1:]

        cost_up = up + cu[i]
        cost_left = left + cL[i]
        cost_right = right + cR[i]

        M[i] = np.minimum(np.minimum(cost_up, cost_left), cost_right)

    return M


def hofer_energy(gray: np.ndarray, window: int = 3) -> np.ndarray:
    """Hölder exponent energy — estimates local roughness.

    The Hölder (Lipschitz) exponent is estimated from the decay of
    wavelet-like coefficients across scales.  Lower exponents indicate
    rougher, more textured regions that should be preserved.
    """
    h, w = gray.shape
    # Compute differences at multiple scales
    scales = [1, 2, 4]
    diffs = []
    for s in scales:
        d = np.zeros_like(gray)
        d[s:, s:] = np.abs(gray[s:, s:] - gray[:-s, :-s])
        diffs.append(d)

    # Estimate Hölder exponent via log-log slope
    log_scales = np.log(np.array(scales, dtype=np.float64))
    energy = np.zeros_like(gray)
    log_diffs = np.stack([np.log(d + 1e-10) for d in diffs], axis=0)

    # Linear regression slope for each pixel
    mean_xs = log_scales.mean()
    mean_ys = log_diffs.mean(axis=0)
    cov_xy = ((log_scales - mean_xs)[:, None, None] * (log_diffs - mean_ys)).mean(axis=0)
    var_x = ((log_scales - mean_xs) ** 2).mean()
    slopes = cov_xy / (var_x + 1e-10)

    # Higher slope = smoother region = lower energy
    energy = np.abs(slopes)
    # Normalise to comparable range as other energy functions
    e_max = float(energy.max())
    if e_max > 1e-10:
        energy = energy / e_max * 255.0
    return energy


def entropy_energy(gray: np.ndarray, window: int = 9) -> np.ndarray:
    """Local Shannon entropy energy — measures local information content.

    Computes the entropy of pixel intensities within a sliding window.
    High-entropy regions (lots of detail) get high energy.
    """
    h, w = gray.shape
    # Quantise to 32 bins for efficient histogram
    quantised = np.clip((gray / 256.0 * 32).astype(np.int32), 0, 31)
    energy = np.zeros_like(gray)

    half = window // 2
    for i in range(h):
        for j in range(w):
            r0 = max(0, i - half)
            r1 = min(h, i + half + 1)
            c0 = max(0, j - half)
            c1 = min(w, j + half + 1)
            patch = quantised[r0:r1, c0:c1].ravel()
            # Compute histogram
            hist = np.bincount(patch, minlength=32).astype(np.float64)
            hist = hist[hist > 0]
            p = hist / hist.sum()
            entropy = -np.sum(p * np.log2(p))
            energy[i, j] = entropy

    # Scale to 0-255 range
    e_max = float(energy.max())
    if e_max > 1e-10:
        energy = energy / e_max * 255.0
    return energy


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ENERGY_FUNCTIONS: Dict[EnergyType, Callable[[np.ndarray], np.ndarray]] = {
    EnergyType.SOBEL: sobel_energy,
    EnergyType.PREWITT: prewitt_energy,
    EnergyType.LAPLACIAN: laplacian_energy,
    EnergyType.GRADIENT: gradient_energy,
    EnergyType.FORWARD: forward_energy,
    EnergyType.HOFER: hofer_energy,
    EnergyType.ENTROPY: entropy_energy,
}


def compute_energy(gray: np.ndarray, energy_type: EnergyType) -> np.ndarray:
    """Dispatch to the appropriate energy function.

    Parameters
    ----------
    gray : np.ndarray
        Grayscale image ``(H, W)`` as ``float64``.
    energy_type : EnergyType
        Which energy function to use.

    Returns
    -------
    np.ndarray
        Energy map ``(H, W)`` as ``float64``.

    Raises
    ------
    EnergyComputationError
        If ``energy_type`` is not recognised.
    """
    func = ENERGY_FUNCTIONS.get(energy_type)
    if func is None:
        raise EnergyComputationError(f"Unknown energy type: {energy_type}")
    return func(gray)