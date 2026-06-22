"""Image quality metrics for JPEG evaluation.

Provides PSNR, SSIM, MSE, compression ratio, and a combined
quality report.  These are useful for benchmarking the codec
and for the CLI's ``--metrics`` flag.
"""

import math
import numpy as np

__all__ = [
    "mse",
    "rmse",
    "psnr",
    "ssim",
    "compression_ratio",
    "quality_report",
]


def mse(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """Mean squared error between two images.

    Parameters
    ----------
    original, reconstructed : np.ndarray
        uint8 or float images of the same shape.

    Returns
    -------
    float
        Mean of the squared per-pixel differences.
    """
    a = original.astype(np.float64)
    b = reconstructed.astype(np.float64)
    if a.shape != b.shape:
        raise ValueError(
            f"Shape mismatch: {a.shape} vs {b.shape}"
        )
    return float(np.mean((a - b) ** 2))


def rmse(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """Root mean squared error."""
    return math.sqrt(mse(original, reconstructed))


def psnr(original: np.ndarray, reconstructed: np.ndarray,
         max_val: float = 255.0) -> float:
    """Peak signal-to-noise ratio in dB.

    Returns ``inf`` when the images are identical (MSE == 0).
    """
    m = mse(original, reconstructed)
    if m == 0:
        return float("inf")
    return 10.0 * math.log10(max_val ** 2 / m)


def _ssim_window_mean(img: np.ndarray) -> float:
    return float(img.mean())


def _ssim_window_var(img: np.ndarray, mean: float) -> float:
    return float(np.mean((img - mean) ** 2))


def _gaussian_kernel(size: int = 11, sigma: float = 1.5) -> np.ndarray:
    """Create a 2-D Gaussian kernel for SSIM weighting."""
    ax = np.arange(size) - (size - 1) / 2.0
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))
    kernel /= kernel.sum()
    return kernel


def _conv2d(img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """2-D convolution with 'valid' boundary handling."""
    kh, kw = kernel.shape
    ih, iw = img.shape
    oh, ow = ih - kh + 1, iw - kw + 1
    # Use stride tricks for efficiency.
    from numpy.lib.stride_tricks import as_strided
    s0, s1 = img.strides
    windows = as_strided(
        img, shape=(oh, ow, kh, kw), strides=(s0, s1, s0, s1)
    )
    return np.einsum("ijkl,kl->ij", windows, kernel)


def ssim(original: np.ndarray, reconstructed: np.ndarray,
         max_val: float = 255.0) -> float:
    """Structural Similarity Index (SSIM) between two images.

    Implements the global SSIM with an 11×11 Gaussian window
    (σ=1.5), matching the reference implementation from
    Wang et al. (2004).  Works on grayscale or per-channel
    for color images (returns the average over channels).

    Returns a float in [-1, 1] where 1 = perfect similarity.
    """
    a = original.astype(np.float64)
    b = reconstructed.astype(np.float64)
    if a.shape != b.shape:
        raise ValueError(
            f"Shape mismatch: {a.shape} vs {b.shape}"
        )

    # Handle multi-channel by averaging SSIM over channels.
    if a.ndim == 3:
        return float(np.mean([
            ssim(a[..., c], b[..., c], max_val)
            for c in range(a.shape[2])
        ]))

    # Constants for stability (Wang et al.).
    c1 = (0.01 * max_val) ** 2
    c2 = (0.03 * max_val) ** 2

    kernel = _gaussian_kernel(11, 1.5)
    mu_a = _conv2d(a, kernel)
    mu_b = _conv2d(b, kernel)
    mu_a_sq = mu_a ** 2
    mu_b_sq = mu_b ** 2
    mu_ab = mu_a * mu_b

    sigma_a_sq = _conv2d(a ** 2, kernel) - mu_a_sq
    sigma_b_sq = _conv2d(b ** 2, kernel) - mu_b_sq
    sigma_ab = _conv2d(a * b, kernel) - mu_ab

    numerator = (2 * mu_ab + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a_sq + mu_b_sq + c1) * (
        sigma_a_sq + sigma_b_sq + c2
    )
    ssim_map = numerator / denominator
    return float(ssim_map.mean())


def compression_ratio(
    original_size: int, compressed_size: int
) -> float:
    """Compression ratio (original / compressed)."""
    if compressed_size == 0:
        return float("inf")
    return original_size / compressed_size


def quality_report(
    original: np.ndarray,
    reconstructed: np.ndarray,
    original_size: int,
    compressed_size: int,
) -> dict:
    """Generate a comprehensive quality report.

    Returns a dict with keys: mse, rmse, psnr, ssim,
    compression_ratio, bits_per_pixel.
    """
    bpp = (compressed_size * 8) / (
        original.shape[0] * original.shape[1]
        * (original.shape[2] if original.ndim == 3 else 1)
    )
    return {
        "mse": mse(original, reconstructed),
        "rmse": rmse(original, reconstructed),
        "psnr_db": psnr(original, reconstructed),
        "ssim": ssim(original, reconstructed),
        "compression_ratio": compression_ratio(
            original_size, compressed_size
        ),
        "compressed_bytes": compressed_size,
        "bits_per_pixel": bpp,
    }