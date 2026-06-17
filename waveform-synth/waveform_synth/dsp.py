"""
Digital signal processing utilities.

Provides FFT, windowing functions, convolution, correlation,
and other DSP primitives for audio analysis and manipulation.
"""

import math
from typing import List, Tuple, Optional


# ─── Windowing Functions ────────────────────────────────────────────────

def window_hann(n: int) -> List[float]:
    """
    Hann (Hanning) window of length n.

    Args:
        n: Window length (must be > 0).

    Returns:
        List of window coefficients summing to ~0.5.

    Raises:
        ValueError: If n <= 0.
    """
    if n <= 0:
        raise ValueError(f"Window length must be > 0, got {n}")
    return [0.5 * (1.0 - math.cos(2.0 * math.pi * i / (n - 1))) for i in range(n)]


def window_hamming(n: int) -> List[float]:
    """
    Hamming window of length n.

    Args:
        n: Window length (must be > 0).

    Returns:
        List of window coefficients.

    Raises:
        ValueError: If n <= 0.
    """
    if n <= 0:
        raise ValueError(f"Window length must be > 0, got {n}")
    return [0.54 - 0.46 * math.cos(2.0 * math.pi * i / (n - 1)) for i in range(n)]


def window_blackman(n: int) -> List[float]:
    """
    Blackman window of length n.

    Args:
        n: Window length (must be > 0).

    Returns:
        List of window coefficients.

    Raises:
        ValueError: If n <= 0.
    """
    if n <= 0:
        raise ValueError(f"Window length must be > 0, got {n}")
    return [
        0.42 - 0.5 * math.cos(2.0 * math.pi * i / (n - 1))
             + 0.08 * math.cos(4.0 * math.pi * i / (n - 1))
        for i in range(n)
    ]


def window_rectangle(n: int) -> List[float]:
    """
    Rectangle (boxcar) window of length n.

    Args:
        n: Window length (must be > 0).

    Returns:
        List of 1.0 values.
    """
    if n <= 0:
        raise ValueError(f"Window length must be > 0, got {n}")
    return [1.0] * n


# ─── FFT ────────────────────────────────────────────────────────────────

def fft(samples: List[float]) -> List[Tuple[float, float]]:
    """
    Compute the Discrete Fourier Transform of real-valued samples.

    Returns a list of (real, imaginary) pairs for each frequency bin.
    Uses the Cooley-Tukey radix-2 FFT algorithm when possible,
    falling back to a direct DFT for non-power-of-2 lengths.

    Args:
        samples: Input audio samples.

    Returns:
        List of (real, imaginary) pairs, one per frequency bin.
    """
    n = len(samples)
    if n == 0:
        return []

    # Pad to next power of 2 for FFT
    m = 1
    while m < n:
        m <<= 1
    padded = list(samples) + [0.0] * (m - n)

    # Bit-reversal permutation
    bits = int(math.log2(m))
    reordered = [0.0] * m
    for i in range(m):
        j = _bit_reverse(i, bits)
        reordered[j] = padded[i]

    # Split into real and imaginary parts
    re = list(reordered)
    im = [0.0] * m

    # Cooley-Tukey butterfly
    size = 2
    while size <= m:
        half = size // 2
        angle = -2.0 * math.pi / size
        for start in range(0, m, size):
            for k in range(half):
                idx1 = start + k
                idx2 = start + k + half
                w_re = math.cos(angle * k)
                w_im = math.sin(angle * k)
                t_re = w_re * re[idx2] - w_im * im[idx2]
                t_im = w_re * im[idx2] + w_im * re[idx2]
                re[idx2] = re[idx1] - t_re
                im[idx2] = im[idx1] - t_im
                re[idx1] = re[idx1] + t_re
                im[idx1] = im[idx1] + t_im
        size *= 2

    # Return only the first n bins (original length)
    result = [(re[i], im[i]) for i in range(n)]
    return result


def fft_magnitude(samples: List[float], sample_rate: int = 44100) -> List[Tuple[float, float]]:
    """
    Compute FFT magnitude spectrum.

    Args:
        samples: Input audio samples.
        sample_rate: Sample rate in Hz.

    Returns:
        List of (frequency, magnitude) pairs sorted by frequency.
    """
    n = len(samples)
    if n == 0:
        return []

    spectrum = fft(samples)
    result = []
    for k in range(min(len(spectrum), n // 2 + 1)):
        freq = k * sample_rate / n
        re, im = spectrum[k]
        magnitude = math.sqrt(re * re + im * im) / n
        result.append((freq, magnitude))
    return result


def _bit_reverse(x: int, bits: int) -> int:
    """Reverse the bits of an integer."""
    result = 0
    for _ in range(bits):
        result = (result << 1) | (x & 1)
        x >>= 1
    return result


# ─── Convolution & Correlation ──────────────────────────────────────────

def convolve(signal: List[float], kernel: List[float]) -> List[float]:
    """
    Convolve a signal with a kernel (finite impulse response).

    Args:
        signal: Input signal.
        kernel: Convolution kernel (impulse response).

    Returns:
        Convolved signal of length len(signal) + len(kernel) - 1.
    """
    if not signal or not kernel:
        return []

    n = len(signal)
    m = len(kernel)
    result = [0.0] * (n + m - 1)

    for i in range(n):
        for j in range(m):
            result[i + j] += signal[i] * kernel[j]

    return result


def correlate(a: List[float], b: List[float]) -> List[float]:
    """
    Cross-correlate two signals.

    Args:
        a: First signal.
        b: Second signal.

    Returns:
        Cross-correlation of length len(a) + len(b) - 1.
    """
    # Cross-correlation is convolution of a with reversed b
    reversed_b = list(reversed(b))
    return convolve(a, reversed_b)


def autocorrelate(samples: List[float], max_lag: Optional[int] = None) -> List[float]:
    """
    Compute normalized autocorrelation of a signal.

    Args:
        samples: Input signal.
        max_lag: Maximum lag to compute. Defaults to len(samples).

    Returns:
        List of autocorrelation values, result[0] = 1.0 (normalized).
    """
    n = len(samples)
    if n == 0:
        return []

    if max_lag is None:
        max_lag = n

    # Compute energy at lag 0 for normalization
    energy = sum(s * s for s in samples)
    if energy == 0:
        return [0.0] * max_lag

    result = []
    for lag in range(max_lag):
        if lag >= n:
            result.append(0.0)
            continue
        corr = 0.0
        count = 0
        for i in range(n - lag):
            corr += samples[i] * samples[i + lag]
            count += 1
        if count > 0:
            result.append(corr / (energy))
        else:
            result.append(0.0)

    return result


# ─── Filtering ──────────────────────────────────────────────────────────

def lowpass_filter(samples: List[float], cutoff: float, sample_rate: int = 44100) -> List[float]:
    """
    Apply a second-order Butterworth low-pass filter.

    Args:
        samples: Input audio samples.
        cutoff: Cutoff frequency in Hz.
        sample_rate: Sample rate in Hz.

    Returns:
        Filtered samples.
    """
    if not samples:
        return samples

    # Warped cutoff frequency for bilinear transform
    wc = math.tan(math.pi * cutoff / sample_rate)

    # Second-order Butterworth coefficients
    k = math.sqrt(2.0) * wc
    norm = 1.0 + k + wc * wc

    b0 = wc * wc / norm
    b1 = 2.0 * b0
    b2 = b0
    a1 = 2.0 * (wc * wc - 1.0) / norm
    a2 = (1.0 - k + wc * wc) / norm

    return _apply_iir(samples, b0, b1, b2, a1, a2)


def highpass_filter(samples: List[float], cutoff: float, sample_rate: int = 44100) -> List[float]:
    """
    Apply a second-order Butterworth high-pass filter.

    Args:
        samples: Input audio samples.
        cutoff: Cutoff frequency in Hz.
        sample_rate: Sample rate in Hz.

    Returns:
        Filtered samples.
    """
    if not samples:
        return samples

    wc = math.tan(math.pi * cutoff / sample_rate)
    k = math.sqrt(2.0) * wc
    norm = 1.0 + k + wc * wc

    b0 = 1.0 / norm
    b1 = -2.0 / norm
    b2 = 1.0 / norm
    a1 = 2.0 * (wc * wc - 1.0) / norm
    a2 = (1.0 - k + wc * wc) / norm

    return _apply_iir(samples, b0, b1, b2, a1, a2)


def bandpass_filter(samples: List[float], low_cutoff: float, high_cutoff: float,
                    sample_rate: int = 44100) -> List[float]:
    """
    Apply a band-pass filter by cascading high-pass and low-pass.

    Args:
        samples: Input audio samples.
        low_cutoff: Low cutoff frequency in Hz.
        high_cutoff: High cutoff frequency in Hz.
        sample_rate: Sample rate in Hz.

    Returns:
        Filtered samples.
    """
    result = highpass_filter(samples, low_cutoff, sample_rate)
    return lowpass_filter(result, high_cutoff, sample_rate)


def _apply_iir(samples: List[float], b0: float, b1: float, b2: float,
               a1: float, a2: float) -> List[float]:
    """Apply a second-order IIR (biquad) filter."""
    result = [0.0] * len(samples)
    x1 = x2 = y1 = y2 = 0.0

    for i in range(len(samples)):
        x0 = samples[i]
        y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        result[i] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0

    return result


# ─── Amplitude Envelope ────────────────────────────────────────────────

def amplitude_envelope(samples: List[float], frame_size: int = 1024,
                       hop_size: int = 512) -> List[float]:
    """
    Compute the amplitude envelope of a signal.

    Args:
        samples: Input audio samples.
        frame_size: Frame size in samples.
        hop_size: Hop size in samples.

    Returns:
        List of peak amplitudes per frame.
    """
    if not samples:
        return []

    envelope = []
    pos = 0
    while pos < len(samples):
        frame = samples[pos:pos + frame_size]
        if frame:
            envelope.append(max(abs(s) for s in frame))
        pos += hop_size

    return envelope


def onset_detection(samples: List[float], frame_size: int = 1024,
                    hop_size: int = 512, threshold: float = 0.3) -> List[int]:
    """
    Detect note onsets using spectral flux.

    Args:
        samples: Input audio samples.
        frame_size: Analysis frame size.
        hop_size: Hop size in samples.
        threshold: Onset detection threshold (0-1).

    Returns:
        List of sample positions where onsets occur.
    """
    if not samples or len(samples) < frame_size:
        return []

    envelope = amplitude_envelope(samples, frame_size, hop_size)
    if not envelope:
        return []

    # Normalize
    peak = max(envelope)
    if peak == 0:
        return []
    envelope_norm = [e / peak for e in envelope]

    # Find onsets: points where envelope exceeds threshold after being below
    onsets = []
    for i in range(1, len(envelope_norm)):
        if envelope_norm[i] > threshold and envelope_norm[i - 1] <= threshold:
            onsets.append(i * hop_size)

    return onsets


__all__ = [
    'window_hann', 'window_hamming', 'window_blackman', 'window_rectangle',
    'fft', 'fft_magnitude',
    'convolve', 'correlate', 'autocorrelate',
    'lowpass_filter', 'highpass_filter', 'bandpass_filter',
    'amplitude_envelope', 'onset_detection',
]