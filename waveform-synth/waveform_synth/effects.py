"""
Audio effects processing.

Provides a chainable effects pipeline with individual effect processors:
- Gain
- Delay (with feedback)
- Flanger
- Distortion
- Low-pass filter (simple one-pole)
- High-pass filter (simple one-pole)
- Tremolo
"""

import math
from typing import List, Optional
from enum import Enum


class EffectType(Enum):
    """Available effect types."""
    GAIN = "gain"
    DELAY = "delay"
    FLANGER = "flanger"
    DISTORTION = "distortion"
    LOWPASS = "lowpass"
    HIGHPASS = "highpass"
    TREMOLO = "tremolo"


class Effect:
    """
    A single audio effect with configurable parameters.

    Args:
        effect_type: The type of effect.
        **kwargs: Effect-specific parameters (see below).

    Parameters by type:
        gain: amount (float, default 1.0) — linear gain multiplier
        delay: time (float, default 0.3, seconds), feedback (float, default 0.3, [0,1]), mix (float, default 0.5, [0,1])
        flanger: rate (float, default 0.5, Hz), depth (float, default 0.002, seconds), feedback (float, default 0.5, [0,1]), mix (float, default 0.5, [0,1])
        distortion: drive (float, default 2.0) — higher = more clipping
        lowpass: cutoff (float, default 1000.0, Hz)
        highpass: cutoff (float, default 200.0, Hz)
        tremolo: rate (float, default 5.0, Hz), depth (float, default 0.5, [0,1])
    """

    def __init__(self, effect_type: EffectType, **kwargs):
        self.effect_type = effect_type
        self.params = kwargs

        # Validate and set defaults
        if effect_type == EffectType.GAIN:
            self.params.setdefault("amount", 1.0)
        elif effect_type == EffectType.DELAY:
            self.params.setdefault("time", 0.3)
            self.params.setdefault("feedback", 0.3)
            self.params.setdefault("mix", 0.5)
        elif effect_type == EffectType.FLANGER:
            self.params.setdefault("rate", 0.5)
            self.params.setdefault("depth", 0.002)
            self.params.setdefault("feedback", 0.5)
            self.params.setdefault("mix", 0.5)
        elif effect_type == EffectType.DISTORTION:
            self.params.setdefault("drive", 2.0)
        elif effect_type == EffectType.LOWPASS:
            self.params.setdefault("cutoff", 1000.0)
        elif effect_type == EffectType.HIGHPASS:
            self.params.setdefault("cutoff", 200.0)
        elif effect_type == EffectType.TREMOLO:
            self.params.setdefault("rate", 5.0)
            self.params.setdefault("depth", 0.5)

    def process(self, samples: List[float], sample_rate: int = 44100) -> List[float]:
        """
        Apply this effect to a list of audio samples.

        Args:
            samples: Input audio samples.
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples.
        """
        if not samples:
            return samples

        if self.effect_type == EffectType.GAIN:
            return self._apply_gain(samples)
        elif self.effect_type == EffectType.DELAY:
            return self._apply_delay(samples, sample_rate)
        elif self.effect_type == EffectType.FLANGER:
            return self._apply_flanger(samples, sample_rate)
        elif self.effect_type == EffectType.DISTORTION:
            return self._apply_distortion(samples)
        elif self.effect_type == EffectType.LOWPASS:
            return self._apply_lowpass(samples, sample_rate)
        elif self.effect_type == EffectType.HIGHPASS:
            return self._apply_highpass(samples, sample_rate)
        elif self.effect_type == EffectType.TREMOLO:
            return self._apply_tremolo(samples, sample_rate)
        else:
            return samples

    def _apply_gain(self, samples: List[float]) -> List[float]:
        """Apply gain."""
        amount = self.params["amount"]
        return [s * amount for s in samples]

    def _apply_delay(self, samples: List[float], sample_rate: int) -> List[float]:
        """Apply delay effect with feedback."""
        delay_time = self.params["time"]
        feedback = self.params["feedback"]
        mix = self.params["mix"]

        delay_samples = int(delay_time * sample_rate)
        # Output buffer is extended to include delay tail
        output = list(samples) + [0.0] * (delay_samples * 4)

        for i in range(len(samples)):
            delayed_idx = i + delay_samples
            if delayed_idx < len(output):
                output[delayed_idx] += samples[i] * feedback * mix

        # Mix dry and wet
        result = []
        for i in range(len(samples)):
            dry = samples[i]
            wet_idx = i + delay_samples
            wet = output[wet_idx] if wet_idx < len(output) else 0.0
            result.append(dry * (1.0 - mix) + wet * mix)

        return result

    def _apply_flanger(self, samples: List[float], sample_rate: int) -> List[float]:
        """Apply flanger effect (modulated delay)."""
        rate = self.params["rate"]
        depth = self.params["depth"]
        feedback = self.params["feedback"]
        mix = self.params["mix"]

        max_delay = int(depth * sample_rate) + 1
        buffer = [0.0] * (len(samples) + max_delay * 2)
        result = [0.0] * len(samples)

        for i in range(len(samples)):
            # Modulated delay time
            mod_delay = depth * sample_rate * (0.5 + 0.5 * math.sin(2 * math.pi * rate * i / sample_rate))
            delay_int = int(mod_delay)

            # Read from buffer with linear interpolation
            read_pos = i + max_delay - delay_int
            frac = mod_delay - delay_int

            if read_pos + 1 < len(buffer):
                delayed = buffer[read_pos] * (1.0 - frac) + buffer[read_pos + 1] * frac
            elif read_pos < len(buffer):
                delayed = buffer[read_pos]
            else:
                delayed = 0.0

            # Write input + feedback to buffer
            buffer[i + max_delay] = samples[i] + delayed * feedback

            # Mix dry and wet
            result[i] = samples[i] * (1.0 - mix) + delayed * mix

        return result

    def _apply_distortion(self, samples: List[float]) -> List[float]:
        """Apply soft-clipping distortion using tanh."""
        drive = self.params["drive"]
        return [math.tanh(s * drive) for s in samples]

    def _apply_lowpass(self, samples: List[float], sample_rate: int) -> List[float]:
        """Apply one-pole low-pass filter."""
        cutoff = self.params["cutoff"]
        # RC filter coefficient
        rc = 1.0 / (2.0 * math.pi * cutoff)
        dt = 1.0 / sample_rate
        alpha = dt / (rc + dt)

        result = [0.0] * len(samples)
        result[0] = alpha * samples[0]
        for i in range(1, len(samples)):
            result[i] = result[i - 1] + alpha * (samples[i] - result[i - 1])
        return result

    def _apply_highpass(self, samples: List[float], sample_rate: int) -> List[float]:
        """Apply one-pole high-pass filter."""
        cutoff = self.params["cutoff"]
        rc = 1.0 / (2.0 * math.pi * cutoff)
        dt = 1.0 / sample_rate
        alpha = rc / (rc + dt)

        result = [0.0] * len(samples)
        result[0] = samples[0]
        for i in range(1, len(samples)):
            result[i] = alpha * result[i - 1] + alpha * (samples[i] - samples[i - 1])
        return result

    def _apply_tremolo(self, samples: List[float], sample_rate: int) -> List[float]:
        """Apply tremolo (amplitude modulation)."""
        rate = self.params["rate"]
        depth = self.params["depth"]

        result = []
        for i in range(len(samples)):
            # Tremolo: modulate amplitude with LFO
            lfo = 1.0 - depth * (0.5 + 0.5 * math.sin(2.0 * math.pi * rate * i / sample_rate))
            result.append(samples[i] * lfo)
        return result


class EffectsChain:
    """
    Chain of effects applied sequentially to audio samples.

    Args:
        effects: List of Effect objects to apply in order.
    """

    def __init__(self, effects: Optional[List[Effect]] = None):
        self.effects = effects or []

    def add(self, effect: Effect) -> 'EffectsChain':
        """Add an effect to the chain. Returns self for fluent API."""
        self.effects.append(effect)
        return self

    def process(self, samples: List[float], sample_rate: int = 44100) -> List[float]:
        """
        Apply all effects in sequence.

        Args:
            samples: Input audio samples.
            sample_rate: Sample rate in Hz.

        Returns:
            Processed audio samples after all effects.
        """
        result = list(samples)
        for effect in self.effects:
            result = effect.process(result, sample_rate)
        return result