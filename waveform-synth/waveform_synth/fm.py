"""
FM (Frequency Modulation) Synthesis.

Implements John Chowning-style FM synthesis where a modulator oscillator's
output modulates the carrier's frequency, creating rich harmonic spectra
from just two oscillators.

The FM equation: y(t) = A * sin(2π * fc * t + I * sin(2π * fm * t))

where fc = carrier frequency, fm = modulator frequency, I = modulation index.
"""

import math
from typing import List, Optional

from .core import Oscillator, Waveform


class FMSynth:
    """
    FM Synthesis engine.

    Args:
        carrier_freq: Carrier frequency in Hz (must be > 0).
        modulator_freq: Modulator frequency in Hz (must be > 0).
        modulation_index: Modulation depth — higher values produce more harmonics.
            Must be >= 0.
        carrier_waveform: Waveform for the carrier oscillator.
        modulator_waveform: Waveform for the modulator oscillator.
        amplitude: Output amplitude in [0.0, 1.0].
        sample_rate: Samples per second (must be > 0).

    Raises:
        ValueError: If any parameter is out of range.
    """

    def __init__(
        self,
        carrier_freq: float = 440.0,
        modulator_freq: float = 440.0,
        modulation_index: float = 2.0,
        carrier_waveform: Waveform = Waveform.SINE,
        modulator_waveform: Waveform = Waveform.SINE,
        amplitude: float = 0.8,
        sample_rate: int = 44100,
    ):
        if carrier_freq <= 0:
            raise ValueError(f"Carrier frequency must be > 0, got {carrier_freq}")
        if modulator_freq <= 0:
            raise ValueError(f"Modulator frequency must be > 0, got {modulator_freq}")
        if modulation_index < 0:
            raise ValueError(f"Modulation index must be >= 0, got {modulation_index}")
        if not (0.0 <= amplitude <= 1.0):
            raise ValueError(f"Amplitude must be in [0.0, 1.0], got {amplitude}")
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be > 0, got {sample_rate}")

        self.carrier_freq = carrier_freq
        self.modulator_freq = modulator_freq
        self.modulation_index = modulation_index
        self.carrier_waveform = carrier_waveform
        self.modulator_waveform = modulator_waveform
        self.amplitude = amplitude
        self.sample_rate = sample_rate

    def sample(self, t: float) -> float:
        """
        Generate a single FM synthesis sample at time t.

        Uses the equation:
            y(t) = A * carrier_wave(fc * t + I * modulator_wave(fm * t) / (2π))

        For sine waves this reduces to the classic FM equation.
        """
        # Modulator phase: I * sin(2π * fm * t)
        mod_angle = 2.0 * math.pi * self.modulator_freq * t
        if self.modulator_waveform == Waveform.SINE:
            mod_value = math.sin(mod_angle)
        elif self.modulator_waveform == Waveform.SQUARE:
            mod_value = 1.0 if math.sin(mod_angle) >= 0 else -1.0
        elif self.modulator_waveform == Waveform.SAWTOOTH:
            p = (self.modulator_freq * t) % 1.0
            mod_value = 2.0 * p - 1.0
        elif self.modulator_waveform == Waveform.TRIANGLE:
            p = (self.modulator_freq * t) % 1.0
            mod_value = 2.0 * abs(2.0 * p - 1.0) - 1.0
        elif self.modulator_waveform == Waveform.NOISE:
            n = int(t * self.sample_rate)
            val = ((n * 1103515245 + 12345) & 0x7FFFFFFF) / 0x7FFFFFFF
            mod_value = 2.0 * val - 1.0
        else:
            mod_value = math.sin(mod_angle)

        # Carrier with FM: carrier_wave(fc * t + I * modulator / (2π))
        # The division by 2π normalizes so the modulation index represents
        # peak deviation in Hz: deviation = I * fm
        carrier_angle = 2.0 * math.pi * self.carrier_freq * t + self.modulation_index * mod_value
        if self.carrier_waveform == Waveform.SINE:
            carrier_value = math.sin(carrier_angle)
        elif self.carrier_waveform == Waveform.SQUARE:
            carrier_value = 1.0 if math.sin(carrier_angle) >= 0 else -1.0
        elif self.carrier_waveform == Waveform.SAWTOOTH:
            # For sawtooth carrier with FM, we need to be more careful
            # Use the total phase
            total_phase = (carrier_angle / (2.0 * math.pi)) % 1.0
            carrier_value = 2.0 * total_phase - 1.0
        elif self.carrier_waveform == Waveform.TRIANGLE:
            total_phase = (carrier_angle / (2.0 * math.pi)) % 1.0
            carrier_value = 2.0 * abs(2.0 * total_phase - 1.0) - 1.0
        elif self.carrier_waveform == Waveform.NOISE:
            n = int(t * self.sample_rate)
            val = ((n * 1103515245 + 12345) & 0x7FFFFFFF) / 0x7FFFFFFF
            carrier_value = 2.0 * val - 1.0
        else:
            carrier_value = math.sin(carrier_angle)

        return self.amplitude * carrier_value

    def generate(self, duration: float) -> List[float]:
        """
        Generate a sequence of FM synthesis samples.

        Args:
            duration: Length in seconds (must be > 0).

        Returns:
            List of float samples.
        """
        if duration <= 0:
            raise ValueError(f"Duration must be > 0, got {duration}")

        num_samples = int(self.sample_rate * duration)
        return [self.sample(i / self.sample_rate) for i in range(num_samples)]

    def generate_with_envelope(self, duration: float, envelope: 'ADSR') -> List[float]:
        """
        Generate FM synthesis samples shaped by an ADSR envelope.

        Args:
            duration: Note-on duration in seconds.
            envelope: ADSR envelope to apply.

        Returns:
            Enveloped FM samples including release tail.
        """
        from .envelope import ADSR  # avoid circular import at module level
        raw = self.generate(duration)
        return envelope.apply(raw, note_duration=duration)


class FMPreset:
    """Common FM synthesis presets."""

    @staticmethod
    def bellish(carrier_freq: float = 440.0, sample_rate: int = 44100) -> FMSynth:
        """Metallic bell tone — high modulation index, integer ratio."""
        return FMSynth(
            carrier_freq=carrier_freq,
            modulator_freq=carrier_freq * 2.0,
            modulation_index=3.5,
            carrier_waveform=Waveform.SINE,
            modulator_waveform=Waveform.SINE,
            amplitude=0.7,
            sample_rate=sample_rate,
        )

    @staticmethod
    def brassish(carrier_freq: float = 440.0, sample_rate: int = 44100) -> FMSynth:
        """Brass-like tone — 1:1 ratio with moderate modulation."""
        return FMSynth(
            carrier_freq=carrier_freq,
            modulator_freq=carrier_freq * 1.0,
            modulation_index=1.5,
            carrier_waveform=Waveform.SINE,
            modulator_waveform=Waveform.SINE,
            amplitude=0.8,
            sample_rate=sample_rate,
        )

    @staticmethod
    def woodwind(carrier_freq: float = 440.0, sample_rate: int = 44100) -> FMSynth:
        """Woodwind-like tone — low modulation index."""
        return FMSynth(
            carrier_freq=carrier_freq,
            modulator_freq=carrier_freq * 1.0,
            modulation_index=0.5,
            carrier_waveform=Waveform.SINE,
            modulator_waveform=Waveform.SINE,
            amplitude=0.75,
            sample_rate=sample_rate,
        )

    @staticmethod
    def bass(carrier_freq: float = 110.0, sample_rate: int = 44100) -> FMSynth:
        """Deep bass tone — low frequency, slight modulation."""
        return FMSynth(
            carrier_freq=carrier_freq,
            modulator_freq=carrier_freq * 0.5,
            modulation_index=1.0,
            carrier_waveform=Waveform.SINE,
            modulator_waveform=Waveform.SINE,
            amplitude=0.9,
            sample_rate=sample_rate,
        )

    @staticmethod
    def e_piano(carrier_freq: float = 440.0, sample_rate: int = 44100) -> FMSynth:
        """Electric piano — DX7-style FM with 1:2 ratio."""
        return FMSynth(
            carrier_freq=carrier_freq,
            modulator_freq=carrier_freq * 2.0,
            modulation_index=2.0,
            carrier_waveform=Waveform.SINE,
            modulator_waveform=Waveform.SINE,
            amplitude=0.75,
            sample_rate=sample_rate,
        )