"""
Noise generators for synthesis.

Provides multiple noise colors:
- **White noise**: uniform random, flat spectrum
- **Pink noise**: 1/f spectrum, equal energy per octave (Voss-McCartree algorithm)
- **Brown noise**: 1/f² spectrum, integrated white noise
- **Blue noise**: +3 dB/octave (inverted pink)
- **Violet noise**: +6 dB/octave (differentiated white)

Noise is a fundamental building block for:
- Percussive sounds (snares, hi-hats)
- Texture and atmosphere
- Granular synthesis
- Wind/ocean sound effects
"""

import math
import random
from enum import Enum
from typing import List, Optional


class NoiseColor(Enum):
    """Noise color / spectral slope types."""
    WHITE = "white"
    PINK = "pink"
    BROWN = "brown"
    BLUE = "blue"
    VIOLET = "violet"


class NoiseGenerator:
    """
    Multi-color noise generator.

    Args:
        color: Noise color (white, pink, brown, blue, violet).
        seed: Random seed for reproducibility (default: None = non-deterministic).
        sample_rate: Audio sample rate (default: 44100).
    """

    def __init__(
        self,
        color: NoiseColor = NoiseColor.WHITE,
        seed: Optional[int] = None,
        sample_rate: int = 44100,
    ):
        self.color = color
        self.sample_rate = sample_rate
        self._rng = random.Random(seed)
        self._pink_state = [0.0] * 7  # Voss-McCartree state
        self._pink_counter = 0
        self._brown_state = 0.0

        # Initialize pink noise state
        for i in range(7):
            self._pink_state[i] = self._rng.uniform(-1, 1)

    def _white_sample(self) -> float:
        """Generate a single white noise sample."""
        return self._rng.uniform(-1.0, 1.0)

    def _pink_sample(self) -> float:
        """
        Generate a single pink noise sample using the Voss-McCartree algorithm.

        Uses 7 octave generators, updating one per sample on a rotating basis.
        The sum produces a 1/f spectral slope.
        """
        self._pink_counter = (self._pink_counter + 1) & 0x7F  # 0-127

        # Update one of the 7 generators based on the counter
        # The bit pattern of the counter determines which generator to update
        for i in range(7):
            if self._pink_counter & (1 << i):
                self._pink_state[i] = self._rng.uniform(-1, 1)
                break

        # Sum all generators
        total = sum(self._pink_state) / 7.0
        # Add a bit of white noise to fill in the high-frequency gaps
        total += self._rng.uniform(-1, 1) * 0.05
        # Normalize to approximately [-1, 1]
        return total * 0.7

    def _brown_sample(self) -> float:
        """
        Generate a single brown noise sample (integrated white noise).

        Brown noise has a 1/f² spectrum, producing a low-frequency rumble.
        """
        white = self._rng.uniform(-1, 1)
        self._brown_state = (self._brown_state * 0.99 + white * 0.02)
        return self._brown_state * 6.0  # Scale to usable amplitude

    def _blue_sample(self) -> float:
        """
        Generate a single blue noise sample (+3 dB/octave).

        Blue noise is the spectral inverse of pink noise, emphasising
        high frequencies. Approximated by differentiating pink noise.
        """
        pink = self._pink_sample()
        prev = getattr(self, '_blue_prev', pink)
        self._blue_prev = pink
        return (pink - prev) * 2.0

    def _violet_sample(self) -> float:
        """
        Generate a single violet noise sample (+6 dB/octave).

        Violet noise is differentiated white noise, emphasising the
        highest frequencies.
        """
        white = self._white_sample()
        prev = getattr(self, '_violet_prev', white)
        self._violet_prev = white
        return (white - prev) * 2.0

    def sample(self) -> float:
        """Generate a single noise sample based on the configured color."""
        if self.color == NoiseColor.WHITE:
            return self._white_sample()
        elif self.color == NoiseColor.PINK:
            return self._pink_sample()
        elif self.color == NoiseColor.BROWN:
            return self._brown_sample()
        elif self.color == NoiseColor.BLUE:
            return self._blue_sample()
        elif self.color == NoiseColor.VIOLET:
            return self._violet_sample()
        else:
            return self._white_sample()

    def generate(self, duration: float, amplitude: float = 1.0) -> List[float]:
        """
        Generate noise samples for the given duration.

        Args:
            duration: Duration in seconds.
            amplitude: Peak amplitude (0.0–1.0).

        Returns:
            List of noise samples.
        """
        if duration <= 0:
            raise ValueError(f"Duration must be > 0, got {duration}")
        if not (0.0 <= amplitude <= 1.0):
            raise ValueError(f"Amplitude must be in [0.0, 1.0], got {amplitude}")

        n = int(self.sample_rate * duration)
        return [self.sample() * amplitude for _ in range(n)]

    def generate_normalized(self, duration: float) -> List[float]:
        """
        Generate noise and normalize to peak amplitude 1.0.

        Args:
            duration: Duration in seconds.

        Returns:
            Normalized noise samples.
        """
        raw = self.generate(duration)
        if not raw:
            return raw
        peak = max(abs(s) for s in raw)
        if peak == 0:
            return raw
        return [s / peak for s in raw]


__all__ = ['NoiseColor', 'NoiseGenerator']