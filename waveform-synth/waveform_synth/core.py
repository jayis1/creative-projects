"""
Core oscillator and waveform generation.

Generates audio samples from mathematical waveforms at any frequency,
sample rate, amplitude, and phase offset. Supports additive harmonics
for rich timbral content.
"""

import math
import enum
from typing import List, Optional, Sequence


class Waveform(enum.Enum):
    """Built-in waveform types."""
    SINE = "sine"
    SQUARE = "square"
    SAWTOOTH = "sawtooth"
    TRIANGLE = "triangle"
    NOISE = "noise"


class Oscillator:
    """
    Digital oscillator that generates waveform samples.

    Args:
        waveform: The waveform shape to generate.
        frequency: Frequency in Hz (must be > 0).
        amplitude: Peak amplitude in [0.0, 1.0].
        sample_rate: Samples per second (must be > 0).
        phase: Initial phase offset in radians.
        harmonics: Optional list of (ratio, amplitude) pairs for additive synthesis.
            ratio is relative to the fundamental (e.g., 2.0 for the 2nd harmonic).
            amplitude is relative to the fundamental (e.g., 0.5 for half amplitude).

    Raises:
        ValueError: If frequency <= 0, sample_rate <= 0, or amplitude is out of range.
    """

    def __init__(
        self,
        waveform: Waveform = Waveform.SINE,
        frequency: float = 440.0,
        amplitude: float = 1.0,
        sample_rate: int = 44100,
        phase: float = 0.0,
        harmonics: Optional[List[tuple]] = None,
    ):
        if frequency <= 0:
            raise ValueError(f"Frequency must be > 0, got {frequency}")
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be > 0, got {sample_rate}")
        if not (0.0 <= amplitude <= 1.0):
            raise ValueError(f"Amplitude must be in [0.0, 1.0], got {amplitude}")

        self.waveform = waveform
        self.frequency = frequency
        self.amplitude = amplitude
        self.sample_rate = sample_rate
        self.phase = phase
        self.harmonics = harmonics or []
        self._phase_accumulator = phase

    def _base_wave(self, t: float, waveform: Waveform, freq: float, phase: float = 0.0) -> float:
        """Generate a single sample of the given waveform type at time t."""
        # Phase-wrapped angle
        angle = 2.0 * math.pi * freq * t + phase

        if waveform == Waveform.SINE:
            return math.sin(angle)

        elif waveform == Waveform.SQUARE:
            return 1.0 if math.sin(angle) >= 0 else -1.0

        elif waveform == Waveform.SAWTOOTH:
            # Sawtooth: 2 * (ft - floor(ft + 0.5))
            p = (freq * t + phase / (2 * math.pi)) % 1.0
            return 2.0 * p - 1.0

        elif waveform == Waveform.TRIANGLE:
            # Triangle: 2 * |2 * (ft - floor(ft + 0.5))| - 1
            p = (freq * t + phase / (2 * math.pi)) % 1.0
            return 2.0 * abs(2.0 * p - 1.0) - 1.0

        elif waveform == Waveform.NOISE:
            # Seeded pseudo-random from phase to get deterministic noise per-sample
            # Use a simple hash-like approach for reproducibility
            n = int(t * self.sample_rate)
            # Linear congruential generator style
            val = ((n * 1103515245 + 12345) & 0x7FFFFFFF) / 0x7FFFFFFF
            return 2.0 * val - 1.0

        else:
            raise ValueError(f"Unknown waveform: {waveform}")

    def sample(self, t: float) -> float:
        """
        Generate a single sample at time t (in seconds).

        Includes the fundamental and all additive harmonics.
        """
        # Fundamental
        value = self._base_wave(t, self.waveform, self.frequency, self.phase)

        # Additive harmonics
        for ratio, amp in self.harmonics:
            value += amp * self._base_wave(t, self.waveform, self.frequency * ratio, self.phase)

        return self.amplitude * value

    def generate(self, duration: float) -> List[float]:
        """
        Generate a sequence of samples for the given duration in seconds.

        Args:
            duration: Length of audio in seconds (must be > 0).

        Returns:
            List of float samples in [-amplitude, amplitude].

        Raises:
            ValueError: If duration <= 0.
        """
        if duration <= 0:
            raise ValueError(f"Duration must be > 0, got {duration}")

        num_samples = int(self.sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            samples.append(self.sample(t))
        return samples

    def generate_at(self, times: Sequence[float]) -> List[float]:
        """
        Generate samples at specific time points.

        Args:
            times: Sequence of time values in seconds.

        Returns:
            List of float samples.
        """
        return [self.sample(t) for t in times]


def mix(signals: List[List[float]], weights: Optional[List[float]] = None) -> List[float]:
    """
    Mix multiple audio signals together with optional weighting.

    Args:
        signals: List of sample lists to mix. All must be the same length.
        weights: Optional gain for each signal (defaults to equal weight).
            If provided, must be the same length as signals.

    Returns:
        Mixed sample list.

    Raises:
        ValueError: If signals is empty, lengths don't match, or weights length mismatches.
    """
    if not signals:
        raise ValueError("signals must not be empty")

    length = len(signals[0])
    for s in signals:
        if len(s) != length:
            raise ValueError(f"All signals must have the same length; got {len(s)} vs {length}")

    if weights is None:
        weights = [1.0] * len(signals)
    elif len(weights) != len(signals):
        raise ValueError(f"weights length {len(weights)} doesn't match signals length {len(signals)}")

    total_weight = sum(weights)
    if total_weight == 0:
        return [0.0] * length

    result = []
    for i in range(length):
        val = sum(w * s[i] for w, s in zip(weights, signals))
        result.append(val / total_weight)
    return result


def normalize(samples: List[float], target_peak: float = 1.0) -> List[float]:
    """
    Normalize samples so the peak absolute value equals target_peak.

    Args:
        samples: Audio samples to normalize.
        target_peak: Target peak amplitude (must be > 0).

    Returns:
        Normalized samples.

    Raises:
        ValueError: If samples is empty or target_peak <= 0.
    """
    if not samples:
        raise ValueError("samples must not be empty")
    if target_peak <= 0:
        raise ValueError(f"target_peak must be > 0, got {target_peak}")

    peak = max(abs(s) for s in samples)
    if peak == 0:
        return samples  # All zeros, nothing to normalize

    scale = target_peak / peak
    return [s * scale for s in samples]


def fade_in_out(samples: List[float], fade_samples: int) -> List[float]:
    """
    Apply fade-in and fade-out to a sample list.

    Args:
        samples: Audio samples.
        fade_samples: Number of samples for each fade (must be < half of len(samples)).

    Returns:
        Samples with fades applied.

    Raises:
        ValueError: If fade_samples is negative or too large.
    """
    if fade_samples < 0:
        raise ValueError(f"fade_samples must be >= 0, got {fade_samples}")
    if fade_samples > len(samples) // 2:
        raise ValueError(f"fade_samples ({fade_samples}) must be <= len(samples)//2 ({len(samples)//2})")

    result = list(samples)
    n = len(result)
    for i in range(fade_samples):
        gain = i / fade_samples
        result[i] *= gain
        result[n - 1 - i] *= gain
    return result