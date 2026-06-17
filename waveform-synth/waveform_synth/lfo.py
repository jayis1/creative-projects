"""
Low-Frequency Oscillator (LFO) for modulation.

LFOs operate below the audible range (typically 0.1–20 Hz) and are used
to modulate parameters of other audio objects — amplitude (tremolo),
pitch (vibrato), filter cutoff (auto-wah), and more.

Each LFO supports multiple waveform shapes, sync-to-tempo, and a
configurable depth that determines how strongly it modulates its target.
"""

import math
from enum import Enum
from typing import List, Optional, Callable, Tuple

from .core import Waveform, Oscillator


class LFO:
    """
    Low-Frequency Oscillator for parameter modulation.

    Args:
        waveform: LFO waveform shape (sine, square, sawtooth, triangle).
        rate: LFO rate in Hz (typically 0.1–20 Hz).
        depth: Modulation depth (0.0–1.0), where 1.0 = full modulation.
        phase: Initial phase offset in radians (default 0.0).
        sample_rate: Audio sample rate.

    Raises:
        ValueError: If parameters are out of range.
    """

    def __init__(
        self,
        waveform: Waveform = Waveform.SINE,
        rate: float = 5.0,
        depth: float = 0.5,
        phase: float = 0.0,
        sample_rate: int = 44100,
    ):
        if rate <= 0:
            raise ValueError(f"LFO rate must be > 0, got {rate}")
        if not (0.0 <= depth <= 1.0):
            raise ValueError(f"Depth must be in [0.0, 1.0], got {depth}")
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be > 0, got {sample_rate}")

        self.waveform = waveform
        self.rate = rate
        self.depth = depth
        self.phase = phase
        self.sample_rate = sample_rate
        self._phase_accumulator = 0.0

    def value_at(self, t: float) -> float:
        """
        Compute the LFO output value at time ``t`` (seconds).

        Returns a value in [-1, 1] that callers scale by ``depth``
        before applying to the target parameter.

        For sine/triangle, the output ranges smoothly across [-1, 1].
        For square/sawtooth, the output is piecewise.
        """
        angle = 2.0 * math.pi * self.rate * t + self.phase

        if self.waveform == Waveform.SINE:
            return math.sin(angle)
        elif self.waveform == Waveform.SQUARE:
            return 1.0 if math.sin(angle) >= 0 else -1.0
        elif self.waveform == Waveform.SAWTOOTH:
            p = (self.rate * t + self.phase / (2 * math.pi)) % 1.0
            return 2.0 * p - 1.0
        elif self.waveform == Waveform.TRIANGLE:
            p = (self.rate * t + self.phase / (2 * math.pi)) % 1.0
            return 2.0 * abs(2.0 * p - 1.0) - 1.0
        else:
            return math.sin(angle)

    def generate(self, duration: float) -> List[float]:
        """
        Generate LFO values for the given duration.

        Args:
            duration: Duration in seconds.

        Returns:
            List of LFO values (raw, not scaled by depth).
        """
        if duration <= 0:
            raise ValueError(f"Duration must be > 0, got {duration}")
        n = int(self.sample_rate * duration)
        return [self.value_at(i / self.sample_rate) for i in range(n)]

    def generate_modulation(self, duration: float) -> List[float]:
        """
        Generate depth-scaled modulation values for the given duration.

        Each sample is in [-depth, +depth].

        Args:
            duration: Duration in seconds.

        Returns:
            List of modulation values.
        """
        return [self.depth * v for v in self.generate(duration)]

    def apply_to_amplitude(self, samples: List[float]) -> List[float]:
        """
        Apply amplitude modulation (tremolo effect).

        Multiplies each audio sample by ``(1 + LFO_value * depth) / 2`` so
        the amplitude oscillates between ``1 - depth`` (quiet) and ``1.0``
        (full volume).

        Args:
            samples: Audio samples to modulate.

        Returns:
            Amplitude-modulated samples.
        """
        n = len(samples)
        if n == 0:
            return samples
        result = []
        for i, s in enumerate(samples):
            t = i / self.sample_rate
            lfo_val = self.value_at(t)
            gain = 1.0 - self.depth + self.depth * (0.5 + 0.5 * lfo_val)
            result.append(s * gain)
        return result

    def apply_to_pitch(self, samples: List[float], base_freq: float) -> List[float]:
        """
        Apply pitch modulation (vibrato effect) via frequency variation.

        Uses linear interpolation to resample the original signal at
        time-varying positions based on the LFO-modulated instantaneous
        frequency.

        Args:
            samples: Audio samples to modulate.
            base_freq: Base frequency of the signal in Hz.

        Returns:
            Pitch-modulated samples (same length as input).
        """
        n = len(samples)
        if n == 0:
            return samples
        if base_freq <= 0:
            raise ValueError(f"Base frequency must be > 0, got {base_freq}")

        result = []
        phase_acc = 0.0
        dt = 1.0 / self.sample_rate

        for i in range(n):
            t = i * dt
            lfo_val = self.value_at(t)
            freq = base_freq * (1.0 + self.depth * lfo_val)
            phase_acc += 2.0 * math.pi * freq * dt
            result.append(math.sin(phase_acc))

        # Normalize to match input amplitude
        if n > 0:
            input_peak = max(abs(s) for s in samples) or 1.0
            output_peak = max(abs(s) for s in result) or 1.0
            if output_peak > 0:
                scale = input_peak / output_peak
                result = [s * scale for s in result]
        return result

    @classmethod
    def synced(cls, bpm: float, beats_per_cycle: float = 1.0,
               depth: float = 0.5, waveform: Waveform = Waveform.SINE,
               sample_rate: int = 44100) -> 'LFO':
        """
        Create an LFO synced to a tempo.

        The LFO rate is calculated as ``bpm / 60 / beats_per_cycle``.

        Args:
            bpm: Tempo in beats per minute.
            beats_per_cycle: Number of beats per LFO cycle (e.g. 1.0 = quarter note, 0.5 = eighth note).
            depth: Modulation depth.
            waveform: LFO waveform shape.
            sample_rate: Audio sample rate.

        Returns:
            Configured LFO instance.
        """
        rate = bpm / 60.0 / beats_per_cycle
        return cls(waveform=waveform, rate=rate, depth=depth,
                   sample_rate=sample_rate)

    def __repr__(self):
        return f"LFO({self.waveform.value}, rate={self.rate}Hz, depth={self.depth:.2f})"


__all__ = ['LFO']