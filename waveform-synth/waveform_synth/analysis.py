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

    # Limit computation for performance
    n = min(len(samples), 4096)
    truncated = samples[:n]
    result = []

    # Only compute up to Nyquist
    max_bin = min(num_bins, n // 2)

    for k in range(max_bin):
        freq = k * sample_rate / n
        real = 0.0
        imag = 0.0
        for j in range(n):
            angle = 2.0 * math.pi * k * j / n
            real += truncated[j] * math.cos(angle)
            imag -= truncated[j] * math.sin(angle)
        magnitude = math.sqrt(real * real + imag * imag) / n
        result.append((freq, magnitude))

    return result


def fundamental_frequency(samples: List[float], sample_rate: int = 44100) -> float:
    """
    Estimate the fundamental frequency using the YIN pitch detection algorithm.

    YIN uses a difference function to find the period that best explains
    the signal's periodicity, then uses parabolic interpolation for
    sub-sample accuracy.

    Args:
        samples: Audio samples (should be at least a few periods long).
        sample_rate: Sample rate in Hz.

    Returns:
        Estimated fundamental frequency in Hz, or 0.0 if not detected.
    """
    if len(samples) < sample_rate // 20:  # Need at least ~50ms
        return 0.0

    # YIN algorithm parameters
    min_freq = 50    # Minimum detectable frequency (Hz)
    max_freq = 2000  # Maximum detectable frequency (Hz)
    threshold = 0.15  # YIN threshold for absolute minimum

    min_period = int(sample_rate / max_freq)
    max_period = int(sample_rate / min_freq)
    n = len(samples)

    # Limit the range of periods to search
    max_period = min(max_period, n // 2)
    if min_period >= max_period:
        return 0.0

    # Step 1: Difference function
    # d(tau) = sum_{j=0}^{W-1} (x(j) - x(j+tau))^2
    # where W = n - max_period to keep the window consistent
    w = n - max_period
    if w <= 0:
        w = n // 2

    diff = []
    for tau in range(min_period, max_period + 1):
        d = 0.0
        for j in range(w):
            diff_val = samples[j] - samples[j + tau]
            d += diff_val * diff_val
        diff.append((tau, d))

    if not diff:
        return 0.0

    # Step 2: Cumulative mean normalized difference function
    # d'(tau) = d(tau) / ((1/tau) * sum_{j=1}^{tau} d(j))
    cmndf = []
    running_sum = 0.0
    for idx, (tau, d) in enumerate(diff):
        running_sum += d
        if running_sum == 0.0:
            cmndf.append((tau, 1.0))
        else:
            cmndf.append((tau, d * (idx + 1) / running_sum))

    # Step 3: Find the first dip below the threshold (absolute minimum)
    best_period = None
    for i in range(1, len(cmndf) - 1):
        if cmndf[i][1] < threshold:
            # Found a dip below threshold; look for the local minimum
            # in this region
            min_idx = i
            min_val = cmndf[i][1]
            for j in range(i, len(cmndf)):
                if cmndf[j][1] < min_val:
                    min_val = cmndf[j][1]
                    min_idx = j
                elif cmndf[j][1] > min_val * 1.5:
                    # Values are rising again, we've passed the minimum
                    break
            best_period = cmndf[min_idx][0]
            break

    if best_period is None:
        # No clear fundamental found; use the global minimum
        best_period = min(cmndf, key=lambda x: x[1])[0]

    # Step 4: Parabolic interpolation for sub-sample accuracy
    # Find the index in diff corresponding to best_period
    diff_dict = {tau: d for tau, d in diff}
    if best_period in diff_dict and (best_period - 1) in diff_dict and (best_period + 1) in diff_dict:
        # Parabolic interpolation
        s_minus = diff_dict.get(best_period - 1, diff_dict[best_period])
        s_zero = diff_dict[best_period]
        s_plus = diff_dict.get(best_period + 1, diff_dict[best_period])
        if 2 * s_zero != 0:
            shift = (s_minus - s_plus) / (2 * (s_minus - 2 * s_zero + s_plus))
            best_period = best_period + shift

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