"""
ADSR Envelope generator.

Implements Attack-Decay-Sustain-Release envelope shaping for
controlling amplitude over time. Supports variable curve shapes
(linear, exponential) for each segment.
"""

import math
from typing import List, Optional


class ADSR:
    """
    Attack-Decay-Sustain-Release envelope.

    Args:
        attack: Attack time in seconds (must be >= 0).
        decay: Decay time in seconds (must be >= 0).
        sustain: Sustain level in [0.0, 1.0] (peak level is always 1.0).
        release: Release time in seconds (must be >= 0).
        peak: Peak level (default 1.0). The envelope rises to this during attack.
        sample_rate: Samples per second (must be > 0).
        curve: Envelope curve type: 'linear' or 'exponential'.

    Raises:
        ValueError: If any parameter is out of range.
    """

    def __init__(
        self,
        attack: float = 0.01,
        decay: float = 0.1,
        sustain: float = 0.7,
        release: float = 0.3,
        peak: float = 1.0,
        sample_rate: int = 44100,
        curve: str = "linear",
    ):
        if attack < 0:
            raise ValueError(f"Attack must be >= 0, got {attack}")
        if decay < 0:
            raise ValueError(f"Decay must be >= 0, got {decay}")
        if not (0.0 <= sustain <= 1.0):
            raise ValueError(f"Sustain must be in [0.0, 1.0], got {sustain}")
        if release < 0:
            raise ValueError(f"Release must be >= 0, got {release}")
        if not (0.0 <= peak <= 1.0):
            raise ValueError(f"Peak must be in [0.0, 1.0], got {peak}")
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be > 0, got {sample_rate}")
        if curve not in ("linear", "exponential"):
            raise ValueError(f"Curve must be 'linear' or 'exponential', got '{curve}'")

        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.peak = peak
        self.sample_rate = sample_rate
        self.curve = curve

    def _interpolate(self, fraction: float, start: float, end: float) -> float:
        """Interpolate between start and end using the configured curve."""
        if self.curve == "linear":
            return start + (end - start) * fraction
        elif self.curve == "exponential":
            # Exponential interpolation — avoid zero crossing
            if start == 0:
                start = 1e-6
            if end == 0:
                end = 1e-6
            return start * ((end / start) ** fraction)
        else:
            return start + (end - start) * fraction  # fallback

    def generate(self, note_duration: float) -> List[float]:
        """
        Generate an envelope for a note of the given duration.

        The envelope has four phases:
          1. Attack: 0 → peak over 'attack' seconds
          2. Decay:  peak → sustain over 'decay' seconds
          3. Sustain: sustain level held for remaining time
          4. Release: sustain → 0 over 'release' seconds

        Args:
            note_duration: Total note-on time in seconds (attack+decay+sustain hold).
                Release is appended after this duration.

        Returns:
            List of envelope values in [0.0, peak].

        Raises:
            ValueError: If note_duration < 0.
        """
        if note_duration < 0:
            raise ValueError(f"Note duration must be >= 0, got {note_duration}")

        attack_samples = max(0, int(self.attack * self.sample_rate))
        decay_samples = max(0, int(self.decay * self.sample_rate))

        # Sustain hold time = note_duration - attack - decay (clamped to 0)
        sustain_hold = max(0.0, note_duration - self.attack - self.decay)
        sustain_samples = max(0, int(sustain_hold * self.sample_rate))

        release_samples = max(0, int(self.release * self.sample_rate))

        total_samples = attack_samples + decay_samples + sustain_samples + release_samples
        envelope = [0.0] * total_samples

        idx = 0

        # Attack phase: 0 → peak
        for i in range(attack_samples):
            frac = i / max(1, attack_samples)
            envelope[idx] = self._interpolate(frac, 0.0, self.peak)
            idx += 1

        # Decay phase: peak → sustain
        for i in range(decay_samples):
            frac = i / max(1, decay_samples)
            envelope[idx] = self._interpolate(frac, self.peak, self.sustain * self.peak)
            idx += 1

        # Sustain hold phase
        for i in range(sustain_samples):
            envelope[idx] = self.sustain * self.peak
            idx += 1

        # Release phase: sustain → 0
        release_start = self.sustain * self.peak
        for i in range(release_samples):
            frac = i / max(1, release_samples)
            envelope[idx] = self._interpolate(frac, release_start, 0.0)
            idx += 1

        return envelope

    def apply(self, samples: List[float], note_duration: Optional[float] = None) -> List[float]:
        """
        Apply the envelope to a list of audio samples.

        If note_duration is None, it's inferred from the sample count and sample rate
        minus the release time.

        Args:
            samples: Audio samples to shape.
            note_duration: Duration of note-on in seconds (excluding release).

        Returns:
            Envelope-shaped samples. The output length includes the release tail.
        """
        if note_duration is None:
            # Infer note_duration from input length minus release
            release_samples = int(self.release * self.sample_rate)
            note_on_samples = max(0, len(samples) - release_samples)
            note_duration = note_on_samples / self.sample_rate

        envelope = self.generate(note_duration)

        # Match lengths — if envelope is longer, truncate; if shorter, pad with 0
        min_len = min(len(samples), len(envelope))
        result = []
        for i in range(min_len):
            result.append(samples[i] * envelope[i])

        # If envelope is longer (release tail), append zeros for remaining audio
        for i in range(min_len, len(envelope)):
            result.append(0.0)

        return result

    def total_duration(self, note_duration: float) -> float:
        """Return the total envelope duration including release, in seconds."""
        return note_duration + self.release