"""Benchmark utilities for the jpeg-codec.

Provides :func:`benchmark` to measure encode/decode throughput
and :func:`quality_sweep` to evaluate quality metrics across a
range of quality settings.
"""

import time
import numpy as np

from .encoder import encode_image
from .decoder import decode_image
from .metrics import quality_report

__all__ = ["benchmark", "quality_sweep", "compare_sampling"]


def benchmark(image: np.ndarray, quality: int = 85,
              sampling: str = "4:2:0",
              runs: int = 3) -> dict:
    """Benchmark encode and decode performance.

    Parameters
    ----------
    image : np.ndarray
        Input image (HxWx3 or HxW).
    quality : int
        JPEG quality.
    sampling : str
        Subsampling mode.
    runs : int
        Number of runs to average over (median is used).

    Returns
    -------
    dict
        Keys: encode_time_s, decode_time_s, encode_mpix/s,
        decode_mpix/s, compressed_bytes, compression_ratio.
    """
    encode_times = []
    decode_times = []
    jpeg_data = None

    for _ in range(runs):
        t0 = time.perf_counter()
        jpeg_data = encode_image(image, quality=quality, sampling=sampling)
        t1 = time.perf_counter()
        encode_times.append(t1 - t0)

        t0 = time.perf_counter()
        _ = decode_image(jpeg_data)
        t1 = time.perf_counter()
        decode_times.append(t1 - t0)

    npixels = image.shape[0] * image.shape[1]
    orig_bytes = image.nbytes

    return {
        "encode_time_s": sorted(encode_times)[len(encode_times) // 2],
        "decode_time_s": sorted(decode_times)[len(decode_times) // 2],
        "encode_mpix_per_s": npixels / 1e6 / sorted(encode_times)[len(encode_times) // 2],
        "decode_mpix_per_s": npixels / 1e6 / sorted(decode_times)[len(decode_times) // 2],
        "compressed_bytes": len(jpeg_data),
        "compression_ratio": orig_bytes / len(jpeg_data),
        "image_size": f"{image.shape[0]}x{image.shape[1]}",
        "quality": quality,
        "sampling": sampling,
    }


def quality_sweep(image: np.ndarray,
                  qualities: list = None,
                  sampling: str = "4:2:0") -> list:
    """Evaluate quality metrics across a range of quality settings.

    Parameters
    ----------
    image : np.ndarray
        Input image.
    qualities : list of int
        Quality values to test (default [10, 25, 50, 75, 90, 95]).
    sampling : str
        Subsampling mode.

    Returns
    -------
    list of dict
        One :func:`quality_report` dict per quality level, with an
        added ``quality`` key.
    """
    if qualities is None:
        qualities = [10, 25, 50, 75, 90, 95]
    results = []
    for q in qualities:
        jpeg_data = encode_image(image, quality=q, sampling=sampling)
        recon = decode_image(jpeg_data)
        report = quality_report(image, recon, image.nbytes, len(jpeg_data))
        report["quality"] = q
        results.append(report)
    return results


def compare_sampling(image: np.ndarray,
                     quality: int = 85) -> list:
    """Compare different subsampling modes at the same quality.

    Returns a list of dicts with sampling mode, PSNR, SSIM,
    compressed size, and compression ratio.
    """
    modes = ["4:4:4", "4:2:2", "4:2:0", "4:1:1"]
    if image.ndim == 2:
        return []  # Grayscale: no subsampling.
    results = []
    for mode in modes:
        jpeg_data = encode_image(image, quality=quality, sampling=mode)
        recon = decode_image(jpeg_data)
        report = quality_report(image, recon, image.nbytes, len(jpeg_data))
        report["sampling"] = mode
        results.append(report)
    return results