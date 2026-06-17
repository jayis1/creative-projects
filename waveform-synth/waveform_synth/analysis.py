"""
Audio analysis tools.

Provides spectral analysis, peak detection, RMS measurement,
signal-to-noise estimation, and zero-crossing rate computation.
"""

import math
from typing import List, Tuple, Dict


def rms(samples: List[float]) -> float:
    """
    Compute the root mean square (RMS) level of audio samples.

    Args:
        samples: Audio samples.

    Returns:
        RMS value.

    Raises:
        ValueError: If samples is empty.
    """
    if not samples:
        raise ValueError("Cannot compute RMS of empty sample list")
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def peak_level(samples: List[float]) -> float:
    """
    Compute the peak absolute level.

    Args:
        samples: Audio samples.

    Returns:
        Peak absolute value.
    """
    if not samples:
        raise ValueError("Cannot compute peak of empty sample list")
    return max(abs(s) for s in samples)


def crest_factor(samples: List[float]) -> float:
    """
    Compute crest factor (peak / RMS).

    A crest factor of 1.0 means a square wave, higher values indicate
    more dynamic range.

    Args:
        samples: Audio samples.

    Returns:
        Crest factor.
    """
    r = rms(samples)
    if r == 0:
        return float('inf')
    return peak_level(samples) / r


def zero_crossing_rate(samples: List[float]) -> float:
    """
    Compute the zero-crossing rate (proportion of sign changes).

    Useful for distinguishing tonal (low ZCR) vs. noisy (high ZCR) signals.

    Args:
        samples: Audio samples.

    Returns:
        Zero-crossing rate in [0.0, 1.0].
    """
    if len(samples) < 2:
        return 0.0
    crossings = sum(1 for i in range(1, len(samples))
                    if (samples[i] >= 0) != (samples[i - 1] >= 0))
    return crossings / (len(samples) - 1)


def spectral_analysis(samples: List[float], sample_rate: int = 44100,
                      num_bins: int = 512) -> List[Tuple[float, float]]:
    """
    Compute a simple DFT-based spectral analysis.

    Returns frequency-magnitude pairs for the given number of bins.

    Args:
        samples: Audio samples.
        sample_rate: Sample rate in Hz.
        num_bins: Number of frequency bins (use power of 2).

    Returns:
        List of (frequency, magnitude) tuples, sorted by frequency.
    """
    if not samples:
        return []

    n = len(samples)
    result = []

    # Only compute up to Nyquist
    max_bin = min(num_bins, n // 2)

    for k in range(max_bin):
        freq = k * sample_rate / n
        real = 0.0
        imag = 0.0
        for j in range(min(n, 4096)):  # Limit computation
            angle = 2.0 * math.pi * k * j / n
            real += samples[j] * math.cos(angle)
            imag -= samples[j] * math.sin(angle)
        magnitude = math.sqrt(real * real + imag * imag) / n
        result.append((freq, magnitude))

    return result


def fundamental_frequency(samples: List[float], sample_rate: int = 44100) -> float:
    """
    Estimate the fundamental frequency using autocorrelation.

    Args:
        samples: Audio samples (should be at least a few periods long).
        sample_rate: Sample rate in Hz.

    Returns:
        Estimated fundamental frequency in Hz, or 0.0 if not detected.
    """
    if len(samples) < sample_rate // 20:  # Need at least ~50ms
        return 0.0

    # Normalize
    peak = max(abs(s) for s in samples) or 1.0
    normalized = [s / peak for s in samples]

    # Search for fundamental period using autocorrelation
    min_period = sample_rate // 2000  # Max ~2000 Hz
    max_period = min(sample_rate // 50, len(normalized) // 2)  # Min ~50 Hz

    best_period = 0
    best_corr = -1.0

    n = len(normalized)
    for period in range(min_period, max_period):
        corr = 0.0
        count = 0
        for i in range(min(n - period, sample_rate // 4)):  # Limit computation
            corr += normalized[i] * normalized[i + period]
            count += 1
        if count > 0:
            corr /= count
        if corr > best_corr:
            best_corr = corr
            best_period = period

    if best_period == 0:
        return 0.0

    return sample_rate / best_period


def detect_peaks(samples: List[float], threshold: float = 0.5) -> List[int]:
    """
    Detect peak positions in audio samples.

    A peak is a sample that is greater than its neighbors and exceeds
    the threshold relative to the signal's peak level.

    Args:
        samples: Audio samples.
        threshold: Relative threshold (0.0 to 1.0) for peak detection.

    Returns:
        List of sample indices where peaks occur.
    """
    if len(samples) < 3:
        return []

    peak = max(abs(s) for s in samples)
    if peak == 0:
        return []

    abs_threshold = threshold * peak
    peaks = []

    for i in range(1, len(samples) - 1):
        if abs(samples[i]) > abs_threshold:
            if samples[i] > samples[i - 1] and samples[i] > samples[i + 1]:
                peaks.append(i)

    return peaks


def compute_stats(samples: List[float]) -> Dict[str, float]:
    """
    Compute comprehensive statistics for audio samples.

    Args:
        samples: Audio samples.

    Returns:
        Dictionary with keys: rms, peak, crest_factor, zero_crossing_rate,
        mean, variance, min, max, duration_seconds (requires sample_rate).
    """
    if not samples:
        return {}

    r = rms(samples)
    p = peak_level(samples)

    mean = sum(samples) / len(samples)
    variance = sum((s - mean) ** 2 for s in samples) / len(samples)

    return {
        "rms": r,
        "peak": p,
        "crest_factor": p / r if r > 0 else float('inf'),
        "zero_crossing_rate": zero_crossing_rate(samples),
        "mean": mean,
        "variance": variance,
        "min": min(samples),
        "max": max(samples),
        "num_samples": len(samples),
    }