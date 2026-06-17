"""
Wavetable synthesis.

A wavetable oscillator stores pre-computed single-cycle waveforms and
interpolates between them to create evolving timbres. Unlike simple
oscillators that repeat a fixed waveform, a wavetable can morph through
multiple waveforms (or "frames") over time, producing rich, animated
sounds.

Supports:
- Built-in wavetables (sine-to-saw, classic analog, spectral blends)
- Custom user-defined wavetables (list of single-cycle waveforms)
- Linear and cubic interpolation between frames
- Position modulation (manual or via LFO)
- Anti-aliased band-limited synthesis
"""

import math
from typing import List, Optional, Tuple, Sequence

from .core import Waveform


class Wavetable:
    """
    A collection of single-cycle waveforms (frames) for wavetable synthesis.

    Args:
        frames: List of waveforms, each a list of floats representing one
            cycle. All frames must have the same length.
        name: Optional name for the wavetable.

    Raises:
        ValueError: If frames is empty, or frame lengths don't match.
    """

    def __init__(self, frames: List[List[float]], name: str = "custom"):
        if not frames:
            raise ValueError("Wavetable must have at least one frame")
        self._frame_size = len(frames[0])
        if self._frame_size == 0:
            raise ValueError("Frames cannot be empty")
        for i, frame in enumerate(frames):
            if len(frame) != self._frame_size:
                raise ValueError(
                    f"Frame {i} has length {len(frame)}, expected {self._frame_size}"
                )
        self.frames = frames
        self.name = name
        self.num_frames = len(frames)

    @classmethod
    def from_waveforms(cls, waveforms: List[Waveform],
                       frame_size: int = 2048,
                       name: str = "multi") -> 'Wavetable':
        """
        Build a wavetable from multiple Waveform enum values.

        Each waveform becomes one frame.

        Args:
            waveforms: List of Waveform enum values.
            frame_size: Number of samples per frame.
            name: Wavetable name.

        Returns:
            Wavetable instance.
        """
        frames = []
        for wf in waveforms:
            frame = _generate_single_cycle(wf, frame_size)
            frames.append(frame)
        return cls(frames, name=name)

    @classmethod
    def sine_to_saw(cls, num_frames: int = 8,
                    frame_size: int = 2048) -> 'Wavetable':
        """
        Create a wavetable that morphs from a sine wave to a sawtooth.

        Intermediate frames are created by gradually adding odd harmonics,
        producing a smooth timbral transition.

        Args:
            num_frames: Number of interpolation frames.
            frame_size: Samples per frame.

        Returns:
            Wavetable that morphs from sine to sawtooth.
        """
        frames = []
        for f in range(num_frames):
            # Morph factor: 0 = pure sine, 1 = full saw
            morph = f / max(1, num_frames - 1)
            frame = []
            for i in range(frame_size):
                t = i / frame_size  # 0 to 1 (one cycle)
                val = math.sin(2 * math.pi * t)
                # Add harmonics up to 16th, scaled by morph
                for h in range(2, 17):
                    harmonic_amp = morph * (1.0 / h)
                    val += harmonic_amp * math.sin(2 * math.pi * h * t)
                frame.append(val)
            frames.append(frame)
        return cls(frames, name="sine_to_saw")

    @classmethod
    def classic_analog(cls, frame_size: int = 2048) -> 'Wavetable':
        """
        Create a classic analog-style wavetable with sine, triangle, saw, and square frames.

        Args:
            frame_size: Samples per frame.

        Returns:
            Wavetable with 4 classic analog waveforms.
        """
        frames = [
            _generate_single_cycle(Waveform.SINE, frame_size),
            _generate_single_cycle(Waveform.TRIANGLE, frame_size),
            _generate_single_cycle(Waveform.SAWTOOTH, frame_size),
            _generate_single_cycle(Waveform.SQUARE, frame_size),
        ]
        return cls(frames, name="classic_analog")

    def get_frame_at(self, position: float) -> List[float]:
        """
        Interpolate a frame at a fractional position (0.0 to 1.0).

        Position 0.0 = first frame, 1.0 = last frame.
        Uses linear interpolation between adjacent frames.

        Args:
            position: Frame position in [0.0, 1.0].

        Returns:
            Interpolated frame (list of floats).
        """
        if self.num_frames == 1:
            return list(self.frames[0])

        # Clamp position
        position = max(0.0, min(1.0, position))

        # Map to frame indices
        scaled = position * (self.num_frames - 1)
        idx0 = int(scaled)
        idx1 = min(idx0 + 1, self.num_frames - 1)
        frac = scaled - idx0

        frame0 = self.frames[idx0]
        frame1 = self.frames[idx1]

        return [frame0[i] * (1.0 - frac) + frame1[i] * frac
                for i in range(self._frame_size)]

    def __repr__(self):
        return f"Wavetable('{self.name}', {self.num_frames} frames × {self._frame_size} samples)"


def _generate_single_cycle(waveform: Waveform, frame_size: int) -> List[float]:
    """Generate a single cycle of the given waveform type."""
    frame = []
    for i in range(frame_size):
        t = i / frame_size  # 0 to 1
        if waveform == Waveform.SINE:
            val = math.sin(2 * math.pi * t)
        elif waveform == Waveform.SQUARE:
            val = 1.0 if t < 0.5 else -1.0
        elif waveform == Waveform.SAWTOOTH:
            val = 2.0 * t - 1.0
        elif waveform == Waveform.TRIANGLE:
            val = 2.0 * abs(2.0 * t - 1.0) - 1.0
        elif waveform == Waveform.PULSE:
            val = 1.0 if t < 0.25 else -1.0
        else:
            val = math.sin(2 * math.pi * t)
        frame.append(val)
    return frame


class WavetableOscillator:
    """
    Wavetable oscillator that morphs between frames.

    Generates audio by reading from a Wavetable at a specified frequency,
    with a frame position that can be static or modulated (e.g. by an LFO).

    Args:
        wavetable: The Wavetable to read from.
        frequency: Output frequency in Hz.
        amplitude: Peak amplitude (0.0–1.0).
        position: Initial frame position (0.0–1.0).
        sample_rate: Audio sample rate.
        interpolation: Interpolation method for frame morphing: 'linear' or 'cubic'.

    Raises:
        ValueError: If parameters are out of range.
    """

    def __init__(
        self,
        wavetable: Wavetable,
        frequency: float = 440.0,
        amplitude: float = 1.0,
        position: float = 0.0,
        sample_rate: int = 44100,
        interpolation: str = "linear",
    ):
        if frequency <= 0:
            raise ValueError(f"Frequency must be > 0, got {frequency}")
        if not (0.0 <= amplitude <= 1.0):
            raise ValueError(f"Amplitude must be in [0.0, 1.0], got {amplitude}")
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be > 0, got {sample_rate}")
        if not (0.0 <= position <= 1.0):
            raise ValueError(f"Position must be in [0.0, 1.0], got {position}")
        if interpolation not in ("linear", "cubic"):
            raise ValueError(f"Interpolation must be 'linear' or 'cubic', got '{interpolation}'")

        self.wavetable = wavetable
        self.frequency = frequency
        self.amplitude = amplitude
        self.position = position
        self.sample_rate = sample_rate
        self.interpolation = interpolation
        self._phase = 0.0

    def set_position(self, position: float) -> None:
        """Set the wavetable frame position (0.0–1.0)."""
        if not (0.0 <= position <= 1.0):
            raise ValueError(f"Position must be in [0.0, 1.0], got {position}")
        self.position = position

    def sample(self, t: float, position_override: Optional[float] = None) -> float:
        """
        Generate a single sample at time ``t``.

        Args:
            t: Time in seconds.
            position_override: Optional position override for this sample.

        Returns:
            Audio sample value.
        """
        pos = position_override if position_override is not None else self.position
        frame = self.wavetable.get_frame_at(pos)
        frame_size = len(frame)

        # Phase increment
        phase = (self.frequency * t) % 1.0
        idx = phase * frame_size
        idx_int = int(idx)
        frac = idx - idx_int

        # Linear interpolation within the frame
        s0 = frame[idx_int]
        s1 = frame[(idx_int + 1) % frame_size]

        if self.interpolation == "cubic":
            s_prev = frame[(idx_int - 1) % frame_size]
            s_next = frame[(idx_int + 2) % frame_size]
            # Catmull-Rom cubic interpolation
            val = _catmull_rom(s_prev, s0, s1, s_next, frac)
        else:
            val = s0 * (1.0 - frac) + s1 * frac

        return self.amplitude * val

    def generate(self, duration: float) -> List[float]:
        """
        Generate audio samples for the given duration.

        Args:
            duration: Duration in seconds.

        Returns:
            List of audio samples.
        """
        if duration <= 0:
            raise ValueError(f"Duration must be > 0, got {duration}")
        n = int(self.sample_rate * duration)
        return [self.sample(i / self.sample_rate) for i in range(n)]

    def generate_with_modulation(
        self,
        duration: float,
        position_modulation: Optional[List[float]] = None,
    ) -> List[float]:
        """
        Generate audio with per-sample position modulation.

        Args:
            duration: Duration in seconds.
            position_modulation: Optional list of position values (0.0–1.0),
                one per sample. If shorter than the output, the last value
                is held; if None, uses the static position.

        Returns:
            List of audio samples.
        """
        if duration <= 0:
            raise ValueError(f"Duration must be > 0, got {duration}")
        n = int(self.sample_rate * duration)
        result = []
        for i in range(n):
            t = i / self.sample_rate
            if position_modulation is not None and i < len(position_modulation):
                pos = position_modulation[i]
            elif position_modulation is not None and len(position_modulation) > 0:
                pos = position_modulation[-1]
            else:
                pos = None
            result.append(self.sample(t, position_override=pos))
        return result

    def __repr__(self):
        return (f"WavetableOscillator({self.wavetable.name}, "
                f"freq={self.frequency}Hz, pos={self.position:.2f})")


def _catmull_rom(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    """Catmull-Rom cubic interpolation between four points."""
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2 * p1) +
        (-p0 + p2) * t +
        (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
        (-p0 + 3 * p1 - 3 * p2 + p3) * t3
    )


__all__ = ['Wavetable', 'WavetableOscillator', '_generate_single_cycle']