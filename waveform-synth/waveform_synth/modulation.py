"""
Ring modulation and amplitude modulation.

Ring modulation (RM) multiplies a carrier signal by a modulator signal,
producing sum and difference frequencies. This creates metallic, inharmonic
sounds famously used for Dalek voices and avant-garde synthesis.

Amplitude modulation (AM) is similar but the modulator is unipolar
(0 to 1), so the carrier is always present — the modulator just varies
its volume. Classic AM radio sound.

Both techniques are foundational to audio synthesis and effects.
"""

import math
from typing import List, Optional

from .core import Oscillator, Waveform


def ring_modulate(
    carrier: List[float],
    modulator: List[float],
    mix: float = 1.0,
) -> List[float]:
    """
    Apply ring modulation: output = carrier × modulator.

    Ring modulation multiplies two signals together. The result contains
    frequencies at (fc + fm) and (fc - fm), but NOT the original frequencies.
    This produces characteristic metallic, bell-like, or alien sounds.

    Args:
        carrier: Carrier signal (audio to be modulated).
        modulator: Modulator signal.
        mix: Dry/wet mix (0.0 = carrier only, 1.0 = fully ring-modulated).

    Returns:
        Ring-modulated signal (same length as the shorter input).

    Raises:
        ValueError: If mix is out of range.
    """
    if not (0.0 <= mix <= 1.0):
        raise ValueError(f"Mix must be in [0.0, 1.0], got {mix}")

    min_len = min(len(carrier), len(modulator))
    result = []
    for i in range(min_len):
        ring = carrier[i] * modulator[i]
        result.append(carrier[i] * (1.0 - mix) + ring * mix)
    return result


def amplitude_modulate(
    carrier: List[float],
    modulator: List[float],
    mix: float = 1.0,
    modulator_depth: float = 1.0,
) -> List[float]:
    """
    Apply amplitude modulation: output = carrier × (1 + depth × modulator).

    Unlike ring modulation, AM keeps the carrier frequency audible and
    adds sidebands at (fc ± fm). The modulator should be in [-1, 1];
    it's made unipolar by the ``(1 + depth × mod)`` factor.

    Args:
        carrier: Carrier signal.
        modulator: Modulator signal (bipolar, [-1, 1]).
        mix: Dry/wet mix.
        modulator_depth: Modulation depth (0.0–1.0).

    Returns:
        Amplitude-modulated signal.

    Raises:
        ValueError: If parameters are out of range.
    """
    if not (0.0 <= mix <= 1.0):
        raise ValueError(f"Mix must be in [0.0, 1.0], got {mix}")
    if not (0.0 <= modulator_depth <= 1.0):
        raise ValueError(f"Depth must be in [0.0, 1.0], got {modulator_depth}")

    min_len = min(len(carrier), len(modulator))
    result = []
    for i in range(min_len):
        # Unipolar modulation: gain factor = 1 + depth * mod
        gain = 1.0 + modulator_depth * modulator[i]
        am = carrier[i] * gain
        result.append(carrier[i] * (1.0 - mix) + am * mix)
    return result


class RingModulator:
    """
    Ring modulation processor with configurable modulator frequency.

    Args:
        modulator_freq: Modulator frequency in Hz.
        modulator_waveform: Modulator waveform shape.
        amplitude: Output amplitude scaling.
        sample_rate: Audio sample rate.
        mix: Dry/wet mix (0.0 = dry, 1.0 = fully modulated).

    Raises:
        ValueError: If parameters are out of range.
    """

    def __init__(
        self,
        modulator_freq: float = 30.0,
        modulator_waveform: Waveform = Waveform.SINE,
        amplitude: float = 1.0,
        sample_rate: int = 44100,
        mix: float = 1.0,
    ):
        if modulator_freq <= 0:
            raise ValueError(f"Modulator frequency must be > 0, got {modulator_freq}")
        if not (0.0 <= amplitude <= 1.0):
            raise ValueError(f"Amplitude must be in [0.0, 1.0], got {amplitude}")
        if not (0.0 <= mix <= 1.0):
            raise ValueError(f"Mix must be in [0.0, 1.0], got {mix}")

        self.modulator_freq = modulator_freq
        self.modulator_waveform = modulator_waveform
        self.amplitude = amplitude
        self.sample_rate = sample_rate
        self.mix = mix

    def process(self, carrier: List[float]) -> List[float]:
        """
        Apply ring modulation to the carrier signal.

        Args:
            carrier: Input audio samples.

        Returns:
            Ring-modulated output.
        """
        if not carrier:
            return carrier

        mod_osc = Oscillator(
            waveform=self.modulator_waveform,
            frequency=self.modulator_freq,
            amplitude=1.0,
            sample_rate=self.sample_rate,
        )
        duration = len(carrier) / self.sample_rate
        modulator = mod_osc.generate(duration)

        result = ring_modulate(carrier, modulator, mix=self.mix)
        return [s * self.amplitude for s in result]


__all__ = ['ring_modulate', 'amplitude_modulate', 'RingModulator']