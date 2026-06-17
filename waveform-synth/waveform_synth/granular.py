"""
Granular synthesis.

Granular synthesis generates audio from many short sound "grains" —
tiny windows of sound (1–100ms) that can be scattered, layered, and
manipulated independently. This creates textures, clouds, and
time-stretching effects that are impossible with traditional
oscillator-based synthesis.

This module provides:
- :class:`GranularSynth` — generates grains from a source buffer
- Grain parameters: size, density, pitch, position, pan, envelope
- Randomization for organic textures
- Synchronous (ordered) and asynchronous (scattered) modes
"""

import math
import random
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

from .dsp import window_hann, window_hamming, window_blackman
from .core import normalize


@dataclass
class GrainParams:
    """Parameters for grain generation."""
    position: float = 0.0      # 0.0–1.0 position in source buffer
    pitch_shift: float = 1.0   # frequency multiplier (1.0 = original)
    amplitude: float = 1.0    # grain amplitude (0.0–1.0)
    pan: float = 0.0           # -1.0 (left) to 1.0 (right)
    duration: float = 0.05    # grain duration in seconds


class GranularSynth:
    """
    Granular synthesis processor.

    Reads grains from a source audio buffer and places them at randomized
    or sequential positions, optionally with pitch shifting and
    spatialization.

    Args:
        source: Source audio buffer (list of float samples).
        grain_size: Grain duration in seconds (0.005–0.5).
        density: Grains per second (1–100).
        pitch_spread: Random pitch variation (0.0 = none, 1.0 = ±1 octave).
        position_spread: Random position variation (0.0 = none, 1.0 = full buffer).
        random_pan: Whether to randomize pan per grain.
        window_type: Grain envelope window ('hann', 'hamming', 'blackman', 'triangle').
        sample_rate: Audio sample rate.
        seed: Random seed for reproducibility.

    Raises:
        ValueError: If parameters are out of range.
    """

    def __init__(
        self,
        source: List[float],
        grain_size: float = 0.05,
        density: float = 20.0,
        pitch_spread: float = 0.0,
        position_spread: float = 0.0,
        random_pan: bool = False,
        window_type: str = "hann",
        sample_rate: int = 44100,
        seed: Optional[int] = None,
    ):
        if not source:
            raise ValueError("Source buffer cannot be empty")
        if grain_size <= 0 or grain_size > 0.5:
            raise ValueError(f"Grain size must be in (0, 0.5], got {grain_size}")
        if density <= 0 or density > 100:
            raise ValueError(f"Density must be in (0, 100], got {density}")
        if not (0.0 <= pitch_spread <= 2.0):
            raise ValueError(f"Pitch spread must be in [0.0, 2.0], got {pitch_spread}")
        if not (0.0 <= position_spread <= 1.0):
            raise ValueError(f"Position spread must be in [0.0, 1.0], got {position_spread}")
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be > 0, got {sample_rate}")

        self.source = source
        self.grain_size = grain_size
        self.density = density
        self.pitch_spread = pitch_spread
        self.position_spread = position_spread
        self.random_pan = random_pan
        self.window_type = window_type
        self.sample_rate = sample_rate
        self._rng = random.Random(seed)

    def _make_window(self, size: int) -> List[float]:
        """Generate the grain envelope window."""
        if self.window_type == "hann":
            return window_hann(size)
        elif self.window_type == "hamming":
            return window_hamming(size)
        elif self.window_type == "blackman":
            return window_blackman(size)
        elif self.window_type == "triangle":
            return [1.0 - abs(2.0 * i / (size - 1) - 1.0) for i in range(size)]
        else:
            return window_hann(size)

    def _extract_grain(self, position: float, pitch: float,
                       amplitude: float) -> List[float]:
        """Extract and process a single grain from the source."""
        grain_samples = int(self.grain_size * self.sample_rate)
        window = self._make_window(grain_samples)

        # Source position in samples
        src_start = int(position * len(self.source))
        src_start = max(0, min(src_start, len(self.source) - 1))

        grain = []
        for i in range(grain_samples):
            # Source position with pitch shift
            src_pos = src_start + (i / pitch)
            src_idx = int(src_pos)

            if src_idx < 0:
                grain.append(0.0)
            elif src_idx >= len(self.source):
                grain.append(0.0)
            else:
                # Linear interpolation
                frac = src_pos - src_idx
                if src_idx + 1 < len(self.source):
                    val = self.source[src_idx] * (1.0 - frac) + self.source[src_idx + 1] * frac
                else:
                    val = self.source[src_idx]
                grain.append(val * window[i] * amplitude)

        return grain

    def generate(self, duration: float) -> List[float]:
        """
        Generate granular audio for the given duration.

        Args:
            duration: Output duration in seconds.

        Returns:
            Audio samples.
        """
        if duration <= 0:
            raise ValueError(f"Duration must be > 0, got {duration}")

        total_samples = int(duration * self.sample_rate)
        output = [0.0] * total_samples

        # Number of grains to place
        num_grains = int(self.density * duration)
        grain_samples = int(self.grain_size * self.sample_rate)

        for g in range(num_grains):
            # Random position in the output
            grain_start = self._rng.randint(0, max(0, total_samples - grain_samples))

            # Position in source (random within spread)
            base_position = self._rng.random()
            if self.position_spread > 0:
                base_position += self._rng.uniform(-self.position_spread / 2,
                                                     self.position_spread / 2)
            base_position = max(0.0, min(1.0, base_position))

            # Pitch
            if self.pitch_spread > 0:
                pitch = 2.0 ** self._rng.uniform(-self.pitch_spread, self.pitch_spread)
            else:
                pitch = 1.0

            # Amplitude
            amplitude = 0.3  # Low per-grain amplitude to avoid clipping

            # Extract grain
            grain = self._extract_grain(base_position, pitch, amplitude)

            # Mix into output
            for i, s in enumerate(grain):
                idx = grain_start + i
                if idx < total_samples:
                    output[idx] += s

        # Normalize
        output = normalize(output, target_peak=0.9)
        return output

    def generate_stereo(self, duration: float) -> Tuple[List[float], List[float]]:
        """
        Generate stereo granular audio with per-grain panning.

        Args:
            duration: Output duration in seconds.

        Returns:
            Tuple of (left, right) channel samples.
        """
        if duration <= 0:
            raise ValueError(f"Duration must be > 0, got {duration}")

        total_samples = int(duration * self.sample_rate)
        left = [0.0] * total_samples
        right = [0.0] * total_samples

        num_grains = int(self.density * duration)
        grain_samples = int(self.grain_size * self.sample_rate)

        for g in range(num_grains):
            grain_start = self._rng.randint(0, max(0, total_samples - grain_samples))

            base_position = self._rng.random()
            if self.position_spread > 0:
                base_position += self._rng.uniform(-self.position_spread / 2,
                                                     self.position_spread / 2)
            base_position = max(0.0, min(1.0, base_position))

            if self.pitch_spread > 0:
                pitch = 2.0 ** self._rng.uniform(-self.pitch_spread, self.pitch_spread)
            else:
                pitch = 1.0

            amplitude = 0.3

            # Pan
            if self.random_pan:
                pan = self._rng.uniform(-1.0, 1.0)
            else:
                pan = 0.0
            left_gain = math.cos((pan + 1.0) * math.pi / 4.0)
            right_gain = math.sin((pan + 1.0) * math.pi / 4.0)

            grain = self._extract_grain(base_position, pitch, amplitude)

            for i, s in enumerate(grain):
                idx = grain_start + i
                if idx < total_samples:
                    left[idx] += s * left_gain
                    right[idx] += s * right_gain

        # Normalize
        left = normalize(left, target_peak=0.9)
        right = normalize(right, target_peak=0.9)
        return left, right


def window_triangle(n: int) -> List[float]:
    """Triangle window of length n."""
    if n <= 0:
        raise ValueError(f"Window length must be > 0, got {n}")
    return [1.0 - abs(2.0 * i / (n - 1) - 1.0) for i in range(n)]


__all__ = ['GranularSynth', 'GrainParams', 'window_triangle']