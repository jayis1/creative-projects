#!/usr/bin/env python3
"""
Wave Synth — Terminal Audio Waveform Synthesizer

Generate, visualize, mix, and export audio waveforms entirely from the command line.
Supports sine, square, sawtooth, triangle, noise, harmonic, chirp, and pulse waveforms
with real-time ASCII visualization, envelope shaping, filters, effects, and WAV export.
"""

__version__ = "1.2.2"

__all__ = [
    # Waveform generators
    'generate_sine', 'generate_square', 'generate_sawtooth',
    'generate_triangle', 'generate_noise', 'generate_harmonic',
    'generate_chirp', 'generate_pulse',
    # Note resolution
    'resolve_freq', 'note_to_freq', 'NOTE_FREQS',
    # Envelope
    'apply_adsr',
    # Effects
    'apply_tremolo', 'apply_vibrato', 'apply_lowpass', 'apply_highpass',
    'apply_distortion', 'apply_delay', 'apply_fade_in', 'apply_fade_out',
    'apply_reverse', 'apply_ring_mod', 'apply_bitcrush', 'apply_reverb',
    'apply_pitch_shift', 'apply_compressor', 'apply_flanger',
    'normalize',
    # Mixing
    'mix_waves',
    # Chords, arpeggios, melodies
    'generate_chord', 'generate_arpeggio', 'generate_melody',
    'transpose_melody',
    # Visualization
    'visualize_ascii', 'visualize_spectrum_ascii', 'print_waveform_info',
    # I/O
    'export_wav', 'import_wav',
    # Constants
    'SAMPLE_RATE', 'MAX_AMPLITUDE', 'TERMINAL_WIDTH', 'TERMINAL_HEIGHT',
    # Registries
    'WAVE_GENERATORS', 'EFFECTS', 'CHORD_INTERVALS', 'MELODY_PRESETS',
    # Version
    '__version__',
]

import argparse
import math
import struct
import wave
import random
import sys
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─── Constants ───────────────────────────────────────────────────────────────

SAMPLE_RATE = 44100
MAX_AMPLITUDE = 32767  # 16-bit signed
TERMINAL_WIDTH = 72
TERMINAL_HEIGHT = 16

NOTE_FREQS = {
    'C0': 16.35, 'C#0': 17.32, 'Db0': 17.32, 'D0': 18.35, 'D#0': 19.42,
    'Eb0': 19.42, 'E0': 20.60, 'F0': 21.83, 'F#0': 23.12, 'Gb0': 23.12,
    'G0': 24.50, 'G#0': 25.96, 'Ab0': 25.96, 'A0': 27.50, 'A#0': 29.14,
    'Bb0': 29.14, 'B0': 30.87,
    'C1': 32.70, 'C#1': 34.65, 'Db1': 34.65, 'D1': 36.71, 'D#1': 38.89,
    'Eb1': 38.89, 'E1': 41.20, 'F1': 43.65, 'F#1': 46.25, 'Gb1': 46.25,
    'G1': 49.00, 'G#1': 51.91, 'Ab1': 51.91, 'A1': 55.00, 'A#1': 58.27,
    'Bb1': 58.27, 'B1': 61.74,
    'C2': 65.41, 'C#2': 69.30, 'Db2': 69.30, 'D2': 73.42, 'D#2': 77.78,
    'Eb2': 77.78, 'E2': 82.41, 'F2': 87.31, 'F#2': 92.50, 'Gb2': 92.50,
    'G2': 98.00, 'G#2': 103.83, 'Ab2': 103.83, 'A2': 110.00, 'A#2': 116.54,
    'Bb2': 116.54, 'B2': 123.47,
    'C3': 130.81, 'C#3': 138.59, 'Db3': 138.59, 'D3': 146.83, 'D#3': 155.56,
    'Eb3': 155.56, 'E3': 164.81, 'F3': 174.61, 'F#3': 185.00, 'Gb3': 185.00,
    'G3': 196.00, 'G#3': 207.65, 'Ab3': 207.65, 'A3': 220.00, 'A#3': 233.08,
    'Bb3': 233.08, 'B3': 246.94,
    'C4': 261.63, 'C#4': 277.18, 'Db4': 277.18, 'D4': 293.66, 'D#4': 311.13,
    'Eb4': 311.13, 'E4': 329.63, 'F4': 349.23, 'F#4': 369.99, 'Gb4': 369.99,
    'G4': 392.00, 'G#4': 415.30, 'Ab4': 415.30, 'A4': 440.00, 'A#4': 466.16,
    'Bb4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'C#5': 554.37, 'Db5': 554.37, 'D5': 587.33, 'D#5': 622.25,
    'Eb5': 622.25, 'E5': 659.25, 'F5': 698.46, 'F#5': 739.99, 'Gb5': 739.99,
    'G5': 783.99, 'G#5': 830.61, 'Ab5': 830.61, 'A5': 880.00, 'A#5': 932.33,
    'Bb5': 932.33, 'B5': 987.77,
    'C6': 1046.50, 'C#6': 1108.73, 'Db6': 1108.73, 'D6': 1174.66, 'D#6': 1244.51,
    'Eb6': 1244.51, 'E6': 1318.51, 'F6': 1396.91, 'F#6': 1479.98, 'Gb6': 1479.98,
    'G6': 1567.98, 'G#6': 1661.22, 'Ab6': 1661.22, 'A6': 1760.00, 'A#6': 1864.92,
    'Bb6': 1864.92, 'B6': 1975.53,
    'C7': 2093.00, 'C#7': 2217.46, 'Db7': 2217.46, 'D7': 2349.32, 'D#7': 2489.02,
    'Eb7': 2489.02, 'E7': 2637.02, 'F7': 2793.83, 'F#7': 2959.96, 'Gb7': 2959.96,
    'G7': 3135.96, 'G#7': 3322.44, 'Ab7': 3322.44, 'A7': 3520.00, 'A#7': 3729.81,
    'Bb7': 3729.81, 'B7': 3951.07,
    'C8': 4186.01,
}


# ─── Waveform Generation ────────────────────────────────────────────────────

def generate_sine(freq: float, duration: float, amplitude: float = 1.0,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a sine wave.

    Args:
        freq: Frequency in Hz (must be positive).
        duration: Duration in seconds (must be positive).
        amplitude: Peak amplitude (0.0 to 1.0 typical).
        sample_rate: Samples per second.

    Returns:
        List of floating-point samples in the range [-amplitude, amplitude].
    """
    if freq <= 0:
        raise ValueError(f"Frequency must be positive, got {freq}")
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")
    n_samples = max(1, int(duration * sample_rate))
    return [amplitude * math.sin(2 * math.pi * freq * i / sample_rate)
            for i in range(n_samples)]


def generate_square(freq: float, duration: float, amplitude: float = 1.0,
                    sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a square wave (50% duty cycle).

    Args:
        freq: Frequency in Hz (must be positive).
        duration: Duration in seconds (must be positive).
        amplitude: Peak amplitude.
        sample_rate: Samples per second.

    Returns:
        List of samples alternating between +amplitude and -amplitude.
    """
    if freq <= 0:
        raise ValueError(f"Frequency must be positive, got {freq}")
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")
    n_samples = max(1, int(duration * sample_rate))
    return [amplitude * (1.0 if math.sin(2 * math.pi * freq * i / sample_rate) >= 0 else -1.0)
            for i in range(n_samples)]


def generate_sawtooth(freq: float, duration: float, amplitude: float = 1.0,
                     sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a sawtooth wave.

    Args:
        freq: Frequency in Hz (must be positive).
        duration: Duration in seconds (must be positive).
        amplitude: Peak amplitude.
        sample_rate: Samples per second.

    Returns:
        List of samples forming a ramp from -amplitude to +amplitude each cycle.
    """
    if freq <= 0:
        raise ValueError(f"Frequency must be positive, got {freq}")
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")
    n_samples = max(1, int(duration * sample_rate))
    return [amplitude * (2.0 * ((freq * i / sample_rate) % 1.0) - 1.0)
            for i in range(n_samples)]


def generate_triangle(freq: float, duration: float, amplitude: float = 1.0,
                     sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a triangle wave.

    Args:
        freq: Frequency in Hz (must be positive).
        duration: Duration in seconds (must be positive).
        amplitude: Peak amplitude.
        sample_rate: Samples per second.

    Returns:
        List of samples forming a triangular waveform.
    """
    if freq <= 0:
        raise ValueError(f"Frequency must be positive, got {freq}")
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")
    n_samples = max(1, int(duration * sample_rate))
    result = []
    for i in range(n_samples):
        phase = (freq * i / sample_rate) % 1.0
        if phase < 0.5:
            result.append(amplitude * (4.0 * phase - 1.0))
        else:
            result.append(amplitude * (3.0 - 4.0 * phase))
    return result


def generate_pulse(freq: float, duration: float, amplitude: float = 1.0,
                   duty_cycle: float = 0.5,
                   sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a pulse wave with configurable duty cycle.

    A pulse wave is similar to a square wave but allows the "on" portion
    to be any fraction of the cycle (duty_cycle), not just 50%.

    Args:
        freq: Frequency in Hz (must be positive).
        duration: Duration in seconds (must be positive).
        amplitude: Peak amplitude.
        duty_cycle: Fraction of each cycle that is "on" (0.0 to 1.0).
            0.5 produces a square wave. Values near 0 or 1 produce narrow pulses.
        sample_rate: Samples per second.

    Returns:
        List of samples forming a pulse waveform.

    Raises:
        ValueError: If freq or duration is not positive, or duty_cycle is out of range.
    """
    if freq <= 0:
        raise ValueError(f"Frequency must be positive, got {freq}")
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")
    if not 0.0 < duty_cycle < 1.0:
        raise ValueError(f"Duty cycle must be between 0.0 and 1.0 (exclusive), got {duty_cycle}")
    n_samples = max(1, int(duration * sample_rate))
    result = []
    for i in range(n_samples):
        phase = (freq * i / sample_rate) % 1.0
        if phase < duty_cycle:
            result.append(amplitude)
        else:
            result.append(-amplitude)
    return result


def generate_noise(duration: float, amplitude: float = 1.0,
                  sample_rate: int = SAMPLE_RATE,
                  seed: Optional[int] = None) -> List[float]:
    """Generate white noise.

    Args:
        duration: Duration in seconds (must be positive).
        amplitude: Peak amplitude.
        sample_rate: Samples per second.
        seed: Random seed for reproducible noise. If None, uses system randomness.
            The global random state is preserved after generation.

    Returns:
        List of random samples uniformly distributed in [-amplitude, amplitude].
    """
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")
    # Save global random state only when using a seed, to avoid side effects
    saved_state = None
    if seed is not None:
        saved_state = random.getstate()
        random.seed(seed)
    n_samples = max(1, int(duration * sample_rate))
    result = [amplitude * (random.random() * 2.0 - 1.0) for _ in range(n_samples)]
    if saved_state is not None:
        random.setstate(saved_state)
    return result


def generate_harmonic(freq: float, duration: float, amplitude: float = 1.0,
                      harmonics: Optional[List[Tuple[int, float]]] = None,
                      sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a wave with harmonic overtones.

    Args:
        freq: Fundamental frequency in Hz (must be positive).
        duration: Duration in seconds (must be positive).
        amplitude: Peak amplitude.
        harmonics: List of (harmonic_number, relative_amplitude) tuples.
            e.g. [(1, 1.0), (2, 0.5), (3, 0.25)] for fundamental + 2 overtones.
            Defaults to [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.125)].
        sample_rate: Samples per second.

    Returns:
        List of samples forming the summed harmonic waveform.

    Note:
        Harmonics above the Nyquist frequency (sample_rate / 2) are silently
        skipped to prevent aliasing.
    """
    if freq <= 0:
        raise ValueError(f"Frequency must be positive, got {freq}")
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")
    if harmonics is None:
        harmonics = [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.125)]
    n_samples = max(1, int(duration * sample_rate))
    result = [0.0] * n_samples
    total_amp = sum(a for _, a in harmonics)
    if total_amp == 0:
        total_amp = 1.0  # Avoid division by zero
    for h_num, h_amp in harmonics:
        h_freq = freq * h_num
        if h_freq > sample_rate / 2:
            continue  # Skip above Nyquist
        for i in range(n_samples):
            result[i] += (amplitude * h_amp / total_amp) * math.sin(2 * math.pi * h_freq * i / sample_rate)
    return result


def generate_chirp(start_freq: float, end_freq: float, duration: float,
                   amplitude: float = 1.0, sample_rate: int = SAMPLE_RATE,
                   method: str = 'linear') -> List[float]:
    """Generate a chirp (frequency sweep) from start_freq to end_freq.

    Args:
        start_freq: Starting frequency in Hz (must be positive).
        end_freq: Ending frequency in Hz (must be positive).
        duration: Duration in seconds (must be positive).
        amplitude: Peak amplitude.
        sample_rate: Samples per second.
        method: 'linear' for linear frequency sweep, 'exponential' for exponential sweep.

    Returns:
        List of samples forming the chirp waveform.

    Raises:
        ValueError: If frequencies or duration are not positive.
    """
    if start_freq <= 0 or end_freq <= 0:
        raise ValueError(f"Frequencies must be positive, got start={start_freq}, end={end_freq}")
    if duration <= 0:
        raise ValueError(f"Duration must be positive, got {duration}")
    n_samples = max(1, int(duration * sample_rate))
    result = []
    for i in range(n_samples):
        t = i / sample_rate
        frac = i / max(n_samples - 1, 1)
        if method == 'exponential':
            ratio = end_freq / start_freq
            if ratio != 1.0:
                phase = 2 * math.pi * start_freq * duration * (
                    ratio ** (t / duration) - 1
                ) / (math.log(ratio) * duration)
            else:
                phase = 2 * math.pi * start_freq * t
        else:
            # Linear sweep
            phase = 2 * math.pi * (start_freq * t + (end_freq - start_freq) * t * t / (2 * duration))
        result.append(amplitude * math.sin(phase))
    return result


WAVE_GENERATORS = {
    'sine': generate_sine,
    'square': generate_square,
    'sawtooth': generate_sawtooth,
    'triangle': generate_triangle,
    'pulse': generate_pulse,
    'noise': lambda f, d, a, sr=SAMPLE_RATE: generate_noise(d, a, sr),
    'harmonic': generate_harmonic,
    'chirp': None,  # Handled specially — needs start/end freq
}

# Wave types that don't need a frequency parameter
NO_FREQ_WAVES = {'noise'}

# Wave types that accept extra parameters
WAVE_EXTRA_PARAMS = {
    'pulse': 'duty_cycle',
    'harmonic': 'harmonics',
    'noise': 'seed',
    'chirp': 'start_freq,end_freq,method',
}


def resolve_freq(note_or_freq: str) -> float:
    """Resolve a note name (e.g. 'A4', 'C#5', 'Eb3') or frequency string to a float.

    Supports sharps (#) and flats (b) in note names. Case-insensitive: 'eb3' and 'Eb3' both work.
    Numeric frequencies are also accepted: '440' → 440.0, '261.63' → 261.63.

    Args:
        note_or_freq: A note name or numeric frequency string.

    Returns:
        The frequency in Hz as a float.

    Raises:
        ValueError: If the input is not a recognized note or valid number.
    """
    raw = note_or_freq.strip()
    # Try direct lookup first (preserves case-sensitive keys like 'Eb3')
    if raw in NOTE_FREQS:
        return NOTE_FREQS[raw]

    # Normalize for case-insensitive lookup:
    normalized = _normalize_note_name(raw)
    if normalized in NOTE_FREQS:
        return NOTE_FREQS[normalized]

    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"Unknown note or frequency: {raw!r}. "
                         f"Examples: 'A4', 'C#5', 'Eb3', '440', '261.63'")


def _normalize_note_name(name: str) -> str:
    """Normalize a note name to the format used in NOTE_FREQS.

    Converts 'eb3' -> 'Eb3', 'bb4' -> 'Bb4', 'c#5' -> 'C#5', 'a4' -> 'A4'.
    """
    if not name:
        return name
    letter = name[0].upper()
    rest = name[1:]
    accidental = ''
    i = 0
    while i < len(rest) and rest[i] in '#b':
        accidental += rest[i]
        i += 1
    octave = rest[i:]
    return letter + accidental + octave


# ─── Envelope ────────────────────────────────────────────────────────────────

def apply_adsr(samples: List[float], attack: float = 0.01, decay: float = 0.01,
               sustain: float = 0.7, release: float = 0.1,
               sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply an ADSR (Attack-Decay-Sustain-Release) envelope to samples.

    Args:
        samples: Input audio samples.
        attack: Attack time in seconds (ramp from 0 to 1).
        decay: Decay time in seconds (ramp from 1 to sustain level).
        sustain: Sustain level (0.0 to 1.0).
        release: Release time in seconds (ramp from sustain to 0).
        sample_rate: Samples per second.

    Returns:
        Samples with the ADSR envelope applied.
    """
    if not samples:
        return []
    n = len(samples)
    result = [0.0] * n

    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    release_samples = int(release * sample_rate)
    sustain_start = attack_samples + decay_samples
    sustain_end = n - release_samples

    if sustain_end < sustain_start:
        sustain_end = sustain_start

    for i in range(n):
        if i < attack_samples and attack_samples > 0:
            env = i / attack_samples
        elif i < sustain_start and decay_samples > 0:
            env = 1.0 - (1.0 - sustain) * (i - attack_samples) / decay_samples
        elif i < sustain_end:
            env = sustain
        elif release_samples > 0 and i < n:
            remaining = n - i
            env = sustain * remaining / release_samples if remaining < release_samples else sustain
        else:
            env = 0.0
        result[i] = samples[i] * max(0.0, min(1.0, env))

    return result


# ─── Effects ─────────────────────────────────────────────────────────────────

def apply_tremolo(samples: List[float], rate: float = 5.0, depth: float = 0.5,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply tremolo (amplitude modulation).

    Args:
        samples: Input audio samples.
        rate: Tremolo rate in Hz (cycles per second).
        depth: Tremolo depth (0.0 = no effect, 1.0 = full).
        sample_rate: Samples per second.

    Returns:
        Samples with tremolo applied.
    """
    if not samples:
        return []
    result = []
    for i, s in enumerate(samples):
        mod = 1.0 - depth * (0.5 + 0.5 * math.sin(2 * math.pi * rate * i / sample_rate))
        result.append(s * mod)
    return result


def apply_vibrato(samples: List[float], rate: float = 5.0, depth: float = 0.002,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply vibrato (frequency modulation via delay modulation).

    Args:
        samples: Input audio samples.
        rate: Vibrato rate in Hz.
        depth: Vibrato depth in seconds (delay variation).
        sample_rate: Samples per second.

    Returns:
        Samples with vibrato applied.
    """
    if not samples:
        return []
    n = len(samples)
    max_delay = int(depth * sample_rate)
    if max_delay < 1:
        max_delay = 1
    padded = [0.0] * max_delay + samples
    result = []
    for i in range(n):
        delay = int(max_delay * math.sin(2 * math.pi * rate * i / sample_rate))
        idx = i + max_delay + delay
        idx = max(0, min(len(padded) - 1, idx))
        result.append(padded[idx])
    return result


def apply_lowpass(samples: List[float], cutoff: float = 1000.0,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a simple one-pole low-pass filter.

    Args:
        samples: Input audio samples.
        cutoff: Cutoff frequency in Hz (must be positive).
        sample_rate: Samples per second.

    Returns:
        Filtered samples.
    """
    if not samples:
        return []
    if cutoff <= 0:
        raise ValueError(f"Cutoff frequency must be positive, got {cutoff}")
    rc = 1.0 / (2.0 * math.pi * cutoff)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)
    result = [0.0] * len(samples)
    result[0] = samples[0]
    for i in range(1, len(samples)):
        result[i] = result[i - 1] + alpha * (samples[i] - result[i - 1])
    return result


def apply_highpass(samples: List[float], cutoff: float = 1000.0,
                   sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a simple one-pole high-pass filter.

    Args:
        samples: Input audio samples.
        cutoff: Cutoff frequency in Hz (must be positive).
        sample_rate: Samples per second.

    Returns:
        Filtered samples.
    """
    if not samples:
        return []
    if cutoff <= 0:
        raise ValueError(f"Cutoff frequency must be positive, got {cutoff}")
    rc = 1.0 / (2.0 * math.pi * cutoff)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)
    result = [0.0] * len(samples)
    result[0] = samples[0]
    for i in range(1, len(samples)):
        result[i] = alpha * (result[i - 1] + samples[i] - samples[i - 1])
    return result


def apply_distortion(samples: List[float], drive: float = 2.0) -> List[float]:
    """Apply distortion (soft clipping using tanh).

    Args:
        samples: Input audio samples.
        drive: Distortion drive amount (0.0 = no effect, higher = more distortion).
            Must be non-negative.

    Returns:
        Distorted samples with soft clipping.

    Raises:
        ValueError: If drive is negative.
    """
    if drive < 0:
        raise ValueError(f"Drive must be non-negative, got {drive}")
    if drive == 0:
        return list(samples)
    result = []
    for s in samples:
        driven = s * drive
        clipped = math.tanh(driven) / math.tanh(drive)
        result.append(clipped)
    return result


def apply_delay(samples: List[float], delay_time: float = 0.3, feedback: float = 0.4,
                mix: float = 0.5, sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a delay/echo effect.

    Args:
        samples: Input audio samples.
        delay_time: Delay time in seconds (must be positive).
        feedback: Feedback amount 0.0 to <1.0 (higher = more echoes).
        mix: Wet/dry mix (0.0 = dry only, 1.0 = wet only).
        sample_rate: Samples per second.

    Returns:
        Samples with delay effect applied.

    Raises:
        ValueError: If delay_time is not positive or feedback is out of range.
    """
    if delay_time <= 0:
        raise ValueError(f"Delay time must be positive, got {delay_time}")
    if not 0 <= feedback < 1.0:
        raise ValueError(f"Feedback must be in [0, 1), got {feedback}")
    if not samples:
        return []
    n = len(samples)
    delay_samples = int(delay_time * sample_rate)
    result = [0.0] * (n + delay_samples * 3)

    for i in range(n):
        result[i] += samples[i] * (1.0 - mix)

    # Copy samples for echo buffer (shallow copy suffices for float list)
    echo = list(samples)
    fb = feedback
    current_delay = delay_samples
    while fb > 0.01:
        for i in range(len(echo)):
            idx = i + current_delay
            if idx < len(result):
                result[idx] += echo[i] * fb * mix
        current_delay += delay_samples
        fb *= feedback

    return result[:n]


def apply_fade_in(samples: List[float], duration: float = 0.05,
                 sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a fade-in envelope.

    Args:
        samples: Input audio samples.
        duration: Fade-in duration in seconds.
        sample_rate: Samples per second.

    Returns:
        Samples with fade-in applied.
    """
    if not samples:
        return []
    n = min(int(duration * sample_rate), len(samples))
    if n <= 1:
        # If fade covers 0 or 1 samples, no fade is needed — return copy.
        # A 1-sample fade would zero the first sample (i/n = 0/1 = 0),
        # which is worse than no fade at all.
        return list(samples)
    result = list(samples)
    for i in range(n):
        result[i] *= i / n
    return result


def apply_fade_out(samples: List[float], duration: float = 0.05,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a fade-out envelope.

    Args:
        samples: Input audio samples.
        duration: Fade-out duration in seconds.
        sample_rate: Samples per second.

    Returns:
        Samples with fade-out applied.
    """
    if not samples:
        return []
    n = min(int(duration * sample_rate), len(samples))
    if n <= 1:
        # If fade covers 0 or 1 samples, no fade is needed — return copy.
        # A 1-sample fade would zero the last sample (0/n = 0),
        # which is worse than no fade at all.
        return list(samples)
    result = list(samples)
    for i in range(n):
        result[len(result) - 1 - i] *= i / n
    return result


def normalize(samples: List[float], target_peak: float = 0.95) -> List[float]:
    """Normalize samples to a target peak amplitude.

    Args:
        samples: Input audio samples.
        target_peak: Target peak amplitude (e.g. 0.95).

    Returns:
        Normalized samples. If input is silence, returns unchanged.
    """
    if not samples:
        return samples
    peak = max(abs(s) for s in samples)
    if peak == 0:
        return samples
    scale = target_peak / peak
    return [s * scale for s in samples]


def apply_reverse(samples: List[float]) -> List[float]:
    """Reverse the waveform (backwards playback).

    Args:
        samples: Input audio samples.

    Returns:
        Samples in reverse order.
    """
    return list(reversed(samples))


def apply_ring_mod(samples: List[float], freq: float = 100.0,
                   sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply ring modulation with a carrier frequency.

    Args:
        samples: Input audio samples.
        freq: Carrier frequency in Hz (must be positive).
        sample_rate: Samples per second.

    Returns:
        Ring-modulated samples.

    Raises:
        ValueError: If freq is not positive.
    """
    if freq <= 0:
        raise ValueError(f"Carrier frequency must be positive, got {freq}")
    if not samples:
        return []
    return [s * math.sin(2 * math.pi * freq * i / sample_rate)
            for i, s in enumerate(samples)]


def apply_bitcrush(samples: List[float], bits: int = 8) -> List[float]:
    """Reduce bit depth for a lo-fi crunchy sound.

    Args:
        samples: Input audio samples.
        bits: Target bit depth (1–16). Lower = more crushed.

    Returns:
        Bit-crushed samples with reduced resolution.
    """
    if not samples:
        return []
    bits = max(1, min(16, int(bits)))
    levels = 2 ** bits
    return [round(s * levels / 2) / (levels / 2) for s in samples]


def apply_reverb(samples: List[float], decay: float = 0.3,
                 delays: Optional[List[float]] = None,
                 sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a simple multi-tap reverb effect.

    Args:
        samples: Input audio samples.
        decay: Reverb decay (0.0 = dry, approaching 1.0 = infinite tail).
        delays: List of delay times in seconds (default: simulated room reflections).
        sample_rate: Samples per second.

    Returns:
        Samples with reverb applied.
    """
    if not samples:
        return []
    if delays is None:
        delays = [0.023, 0.037, 0.041, 0.053, 0.067, 0.079]

    result = list(samples)
    for delay_s in delays:
        delay_samples = int(delay_s * sample_rate)
        for i in range(delay_samples, len(result)):
            result[i] += result[i - delay_samples] * decay

    peak = max(abs(s) for s in result) if result else 0
    if peak > 1.0:
        result = [s / peak for s in result]
    return result


def apply_pitch_shift(samples: List[float], semitones: float = 0.0,
                      sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Simple pitch shift by resampling (changes duration as a side effect).

    Positive semitones shift up, negative shifts down.
    Uses linear interpolation for resampling.

    Args:
        samples: Input audio samples.
        semitones: Number of semitones to shift (0 = no change).
        sample_rate: Samples per second.

    Returns:
        Pitch-shifted samples (length differs from input).
    """
    if not samples:
        return []
    if semitones == 0:
        return list(samples)

    ratio = 2.0 ** (semitones / 12.0)
    new_length = int(len(samples) / ratio)
    if new_length == 0:
        return [0.0]

    result = []
    for i in range(new_length):
        src_pos = i * ratio
        idx = int(src_pos)
        frac = src_pos - idx
        if idx + 1 < len(samples):
            val = samples[idx] * (1.0 - frac) + samples[idx + 1] * frac
        elif idx < len(samples):
            val = samples[idx]
        else:
            val = 0.0
        result.append(val)
    return result


def apply_compressor(samples: List[float], threshold: float = 0.5,
                     ratio: float = 4.0, attack: float = 0.005,
                     release: float = 0.05,
                     sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a simple dynamics compressor.

    Reduces the volume of samples that exceed the threshold, making the
    overall sound louder and more even. Common in music production to
    even out volume differences.

    Uses proper dB conversion for gain computation: signals above the
    threshold are reduced so that their dB level is compressed by the
    given ratio.

    Args:
        samples: Input audio samples.
        threshold: Level above which compression starts (0.0 to 1.0).
        ratio: Compression ratio (e.g. 4.0 means 4:1 compression).
            Higher values = more aggressive compression. ratio=1.0 is a no-op.
        attack: Attack time in seconds (how quickly compression kicks in).
        release: Release time in seconds (how quickly compression fades out).
        sample_rate: Samples per second.

    Returns:
        Compressed samples.

    Raises:
        ValueError: If threshold or ratio are out of valid range.
    """
    if not samples:
        return []
    if not 0.0 < threshold <= 1.0:
        raise ValueError(f"Threshold must be in (0, 1], got {threshold}")
    if ratio < 1.0:
        raise ValueError(f"Ratio must be >= 1.0, got {ratio}")

    # Fast path: ratio=1 means no compression
    if ratio == 1.0:
        return list(samples)

    attack_samples = max(1, int(attack * sample_rate))
    release_samples = max(1, int(release * sample_rate))

    # Compute gain for each sample using envelope follower
    gain = [1.0] * len(samples)
    env_level = 0.0

    for i in range(len(samples)):
        input_level = abs(samples[i])

        # Smooth envelope follower
        if input_level > env_level:
            coeff = 1.0 / attack_samples
            env_level += coeff * (input_level - env_level)
        else:
            coeff = 1.0 / release_samples
            env_level += coeff * (input_level - env_level)

        # Compute gain reduction in dB
        if env_level > threshold:
            # Convert to dB, compress, convert back
            level_db = 20.0 * math.log10(env_level) if env_level > 0 else -120.0
            threshold_db = 20.0 * math.log10(threshold) if threshold > 0 else -120.0
            over_db = level_db - threshold_db
            compressed_db = threshold_db + over_db / ratio
            # Gain in dB = compressed_db - level_db
            gain_db = compressed_db - level_db
            gain[i] = 10.0 ** (gain_db / 20.0)
        # else gain[i] stays 1.0 (no compression)

    # Apply gain
    result = [s * g for s, g in zip(samples, gain)]
    return result


def apply_flanger(samples: List[float], rate: float = 0.5, depth: float = 0.002,
                  feedback: float = 0.3,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a flanger effect (short modulated delay with feedback).

    Creates a sweeping, jet-like sound by mixing the signal with a
    delayed, modulated copy of itself.

    Args:
        samples: Input audio samples.
        rate: Flanger sweep rate in Hz (typical: 0.1–2.0).
        depth: Maximum delay in seconds (typical: 0.001–0.005).
        feedback: Feedback amount 0.0 to <1.0 (typical: 0.2–0.5).
        sample_rate: Samples per second.

    Returns:
        Samples with flanger effect applied.

    Raises:
        ValueError: If feedback is out of range.
    """
    if not samples:
        return []
    if not 0 <= feedback < 1.0:
        raise ValueError(f"Feedback must be in [0, 1), got {feedback}")

    max_delay = int(depth * sample_rate)
    if max_delay < 1:
        max_delay = 1

    result = [0.0] * len(samples)
    delay_buffer = [0.0] * (max_delay + 1)
    buf_idx = 0

    for i in range(len(samples)):
        # Modulated delay time
        delay = int(max_delay * 0.5 * (1.0 + math.sin(2 * math.pi * rate * i / sample_rate)))
        delay = max(0, min(delay, max_delay))

        # Read from delay buffer with feedback
        read_idx = (buf_idx - delay) % (max_delay + 1)
        delayed = delay_buffer[read_idx]

        # Output = original + delayed
        result[i] = samples[i] + delayed * 0.7

        # Write to delay buffer with feedback
        delay_buffer[buf_idx] = samples[i] + delayed * feedback
        buf_idx = (buf_idx + 1) % (max_delay + 1)

    return result


EFFECTS = {
    'tremolo': apply_tremolo,
    'vibrato': apply_vibrato,
    'lowpass': apply_lowpass,
    'highpass': apply_highpass,
    'distortion': apply_distortion,
    'delay': apply_delay,
    'fadein': apply_fade_in,
    'fadeout': apply_fade_out,
    'normalize': normalize,
    'adsr': apply_adsr,
    'reverse': apply_reverse,
    'ringmod': apply_ring_mod,
    'bitcrush': apply_bitcrush,
    'reverb': apply_reverb,
    'pitchshift': apply_pitch_shift,
    'compressor': apply_compressor,
    'flanger': apply_flanger,
}

# Effect descriptions for help text and discoverability
EFFECT_DESCRIPTIONS = {
    'tremolo':    'Amplitude modulation (rate:Hz, depth:0-1)',
    'vibrato':    'Frequency modulation via delay (rate:Hz, depth:s)',
    'lowpass':    'Low-pass filter (cutoff:Hz)',
    'highpass':   'High-pass filter (cutoff:Hz)',
    'distortion': 'Soft clipping distortion (drive:0+)',
    'delay':      'Echo/delay effect (time:s, feedback:0-1)',
    'fadein':     'Fade in from silence (duration:s)',
    'fadeout':    'Fade out to silence (duration:s)',
    'normalize':  'Normalize peak amplitude to 0.95',
    'adsr':       'ADSR envelope (attack,decay,sustain,release in s)',
    'reverse':    'Reverse the waveform',
    'ringmod':    'Ring modulation (carrier:Hz)',
    'bitcrush':   'Reduce bit depth (bits:1-16)',
    'reverb':     'Multi-tap reverb (decay:0-1)',
    'pitchshift': 'Pitch shift via resampling (semitones)',
    'compressor': 'Dynamic compression (threshold:0-1, ratio:1+)',
    'flanger':    'Sweeping modulated delay (rate:Hz, depth:s, feedback:0-1)',
}


# ─── Mixing ──────────────────────────────────────────────────────────────────

def mix_waves(waves: List[List[float]], weights: Optional[List[float]] = None) -> List[float]:
    """Mix multiple wave arrays. Weights default to equal.

    Args:
        waves: List of sample arrays to mix.
        weights: Optional per-wave weights. If None, uses equal weights.

    Returns:
        Mixed sample array with length equal to the longest input.
        If all weights are zero, returns silence.
    """
    if not waves:
        return []
    max_len = max(len(w) for w in waves)
    if weights is None:
        weights = [1.0 / len(waves)] * len(waves)
    total_weight = sum(weights)
    if total_weight == 0:
        return [0.0] * max_len
    weights = [w / total_weight for w in weights]

    result = [0.0] * max_len
    for wave, weight in zip(waves, weights):
        for i in range(len(wave)):
            result[i] += wave[i] * weight
    return result


# ─── ASCII Visualization ─────────────────────────────────────────────────────

def visualize_ascii(samples: List[float], width: int = TERMINAL_WIDTH,
                   height: int = TERMINAL_HEIGHT) -> str:
    """Render an ASCII art waveform visualization.

    Args:
        samples: Audio samples to visualize.
        width: Display width in characters.
        height: Display height in rows.

    Returns:
        String containing the ASCII art waveform display.
    """
    if not samples:
        return "(empty waveform)"

    # Downsample to width points
    step = max(1, len(samples) // width)
    points = []
    for i in range(0, min(len(samples), width * step), step):
        points.append(samples[i])
    if not points:
        points = [0.0]

    # Create canvas
    canvas = [[' '] * len(points) for _ in range(height)]

    for col, val in enumerate(points):
        normalized = (val + 1.0) / 2.0  # [0, 1]
        normalized = max(0.0, min(1.0, normalized))
        row = int((1.0 - normalized) * (height - 1))

        center_row = height // 2
        min_row = min(row, center_row)
        max_row = max(row, center_row)

        for r in range(min_row, max_row + 1):
            canvas[r][col] = '│'

        if 0 <= row < height:
            if val >= 0:
                canvas[row][col] = '╮' if col > 0 and canvas[row][col-1] == '│' else '⌐'
            else:
                canvas[row][col] = '╯' if col > 0 and canvas[row][col-1] == '│' else '¬'

    # Add center line
    for col in range(len(points)):
        center_row = height // 2
        if canvas[center_row][col] == ' ':
            canvas[center_row][col] = '─'

    # Build frame with scale labels as a left-side column (outside the waveform)
    label_width = 5  # width for labels like "+1.0"
    top_label = '+1.0'
    mid_label = ' 0.0'
    bot_label = '-1.0'
    center_row = height // 2

    top_line = '┌' + '─' * len(points) + '┐'
    bottom_line = '└' + '─' * len(points) + '┘'

    lines = [top_line]
    for r, row in enumerate(canvas):
        row_str = '│' + ''.join(row) + '│'
        # Add scale label on the appropriate rows
        if r == 0:
            row_str = top_label + row_str
        elif r == center_row:
            row_str = mid_label + row_str
        elif r == height - 1:
            row_str = bot_label + row_str
        else:
            row_str = ' ' * label_width + row_str
        lines.append(row_str)
    lines.append(' ' * label_width + bottom_line)

    return '\n'.join(lines)


def visualize_spectrum_ascii(samples: List[float], width: int = TERMINAL_WIDTH,
                            height: int = 10) -> str:
    """Render a simple ASCII frequency spectrum approximation using DFT.

    Args:
        samples: Audio samples to analyze.
        width: Display width in characters.
        height: Display height in rows.

    Returns:
        String containing the ASCII spectrum display.
    """
    if len(samples) < 2:
        return "(not enough samples for spectrum)"

    n = len(samples)

    # Downsample long signals to keep computation reasonable
    # Use at most 16384 samples for the DFT (about 0.37s at 44100Hz)
    MAX_DFT_SAMPLES = 16384
    if n > MAX_DFT_SAMPLES:
        step = n / MAX_DFT_SAMPLES
        samples = [samples[int(i * step)] for i in range(MAX_DFT_SAMPLES)]
        n = MAX_DFT_SAMPLES

    # Pick logarithmically spaced frequency bins
    bins = []
    min_freq = 20
    max_freq = SAMPLE_RATE / 2
    num_bins = width

    for i in range(num_bins):
        freq = min_freq * (max_freq / min_freq) ** (i / num_bins)
        bins.append(freq)

    # Compute magnitude for each bin
    magnitudes = []
    for freq in bins:
        real_part = 0.0
        imag_part = 0.0
        for j in range(n):
            angle = 2 * math.pi * freq * j / SAMPLE_RATE
            real_part += samples[j] * math.cos(angle)
            imag_part -= samples[j] * math.sin(angle)
        mag = math.sqrt(real_part ** 2 + imag_part ** 2) / n
        magnitudes.append(mag)

    # Normalize
    max_mag = max(magnitudes) if magnitudes else 1.0
    if max_mag == 0:
        max_mag = 1.0
    magnitudes = [m / max_mag for m in magnitudes]

    # Build bar chart
    lines = []
    lines.append(f'  {"─" * width}')
    for row in range(height, 0, -1):
        threshold = row / height
        bar_line = ''
        for m in magnitudes:
            if m >= threshold:
                bar_line += '█'
            elif m >= threshold - 0.15:
                bar_line += '▓'
            elif m >= threshold - 0.3:
                bar_line += '░'
            else:
                bar_line += ' '
        lines.append(f'  │{bar_line}│')
    lines.append(f'  {"─" * width}')
    lines.append(f'  20Hz{" " * (width - 14)}{int(max_freq/1000)}kHz')

    return '\n'.join(lines)


def print_waveform_info(samples: List[float], name: str = "Waveform",
                       sample_rate: int = SAMPLE_RATE) -> str:
    """Print summary info about a waveform.

    Args:
        samples: Audio samples to analyze.
        name: Display name for the waveform.
        sample_rate: Samples per second.

    Returns:
        Multi-line string with waveform statistics.
    """
    if not samples:
        return f"{name}: (empty)"
    duration = len(samples) / sample_rate
    peak = max(abs(s) for s in samples)
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    zero_crossings = sum(1 for i in range(1, len(samples)) if samples[i] * samples[i-1] < 0)
    est_freq = zero_crossings / (2 * duration) if duration > 0 else 0

    # Compute DC offset
    dc_offset = sum(samples) / len(samples)

    # Compute crest factor (peak / RMS)
    crest_factor = peak / rms if rms > 0 else 0.0

    info = [
        f"  Name:         {name}",
        f"  Duration:     {duration:.3f}s",
        f"  Samples:      {len(samples):,}",
        f"  Sample Rate:  {sample_rate} Hz",
        f"  Peak:         {peak:.4f}",
        f"  RMS:          {rms:.4f}",
        f"  DC Offset:    {dc_offset:+.6f}",
        f"  Crest Factor: {crest_factor:.2f}",
        f"  Est. Freq:    {est_freq:.1f} Hz",
    ]
    return '\n'.join(info)


# ─── WAV Export ──────────────────────────────────────────────────────────────

def export_wav(samples: List[float], filename: str,
              sample_rate: int = SAMPLE_RATE) -> None:
    """Export samples as a 16-bit mono WAV file.

    Automatically normalizes if peak exceeds 1.0 to prevent clipping.

    Args:
        samples: Audio samples (float, typically -1.0 to 1.0).
        filename: Output WAV file path.
        sample_rate: Samples per second.

    Raises:
        ValueError: If samples is empty.
    """
    if not samples:
        raise ValueError("Cannot export empty samples to WAV")

    # Normalize to prevent clipping
    peak = max(abs(s) for s in samples) if samples else 0
    if peak > 1.0:
        samples = [s / peak for s in samples]

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        data = b''
        for s in samples:
            val = int(s * MAX_AMPLITUDE)
            val = max(-MAX_AMPLITUDE, min(MAX_AMPLITUDE, val))
            data += struct.pack('<h', val)

        wf.writeframes(data)

    # Report file size (using stderr to avoid polluting stdout in library usage)
    size = os.path.getsize(filename)
    print(f"  Exported: {filename} ({size:,} bytes, {len(samples)/sample_rate:.2f}s)", file=sys.stderr)


def import_wav(filename: str) -> Tuple[List[float], int]:
    """Import samples from a WAV file.

    Supports 8-bit and 16-bit mono or stereo WAV files.
    Stereo files are automatically mixed down to mono.

    Args:
        filename: Path to the WAV file.

    Returns:
        Tuple of (samples, sample_rate).

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the sample width is unsupported.
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"WAV file not found: {filename}")

    with wave.open(filename, 'r') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_data = wf.readframes(n_frames)

    if sampwidth == 2:
        # 16-bit
        samples = []
        for i in range(0, len(raw_data), sampwidth * n_channels):
            if n_channels == 1:
                val = struct.unpack('<h', raw_data[i:i+2])[0]
                samples.append(val / MAX_AMPLITUDE)
            else:
                # Mix down to mono by averaging channels
                frame_vals = []
                for ch in range(n_channels):
                    offset = i + ch * 2
                    val = struct.unpack('<h', raw_data[offset:offset+2])[0]
                    frame_vals.append(val)
                samples.append(sum(frame_vals) / (len(frame_vals) * MAX_AMPLITUDE))
    elif sampwidth == 1:
        # 8-bit unsigned
        samples = []
        for i in range(0, len(raw_data), n_channels):
            if n_channels == 1:
                val = raw_data[i]
                samples.append((val - 128) / 128.0)
            else:
                frame_vals = []
                for ch in range(n_channels):
                    val = raw_data[i + ch]
                    frame_vals.append((val - 128) / 128.0)
                samples.append(sum(frame_vals) / len(frame_vals))
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth} bits. Only 8 and 16-bit WAV files are supported.")

    return samples, sample_rate


# ─── Chord / Arpeggio Generation ────────────────────────────────────────────

CHORD_INTERVALS = {
    'maj': [0, 4, 7],
    'min': [0, 3, 7],
    'dim': [0, 3, 6],
    'aug': [0, 4, 8],
    '7': [0, 4, 7, 10],
    'maj7': [0, 4, 7, 11],
    'min7': [0, 3, 7, 10],
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    '5': [0, 7],
    'add9': [0, 4, 7, 14],
    '6': [0, 4, 7, 9],
    '9': [0, 4, 7, 10, 14],
}

NOTE_ORDER = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_to_freq(note_name: str) -> float:
    """Convert a note name like 'C4' to frequency.

    Supports sharps (#) and flats (b), e.g. 'C#4', 'Eb3', 'Bb4'.
    Delegates to resolve_freq for accurate lookups.

    Args:
        note_name: Note name string (e.g. 'A4', 'C#5', 'Eb3').

    Returns:
        Frequency in Hz.

    Raises:
        ValueError: If the note name is unrecognized.
    """
    note = note_name.strip()
    if not note:
        raise ValueError("Empty note name")
    try:
        return resolve_freq(note)
    except ValueError:
        try:
            return float(note)
        except ValueError:
            raise ValueError(f"Unknown note or frequency: {note!r}")


def _generate_wave_for_type(wave_type: str, freq: float, duration: float,
                            amplitude: float, sample_rate: int) -> List[float]:
    """Generate a waveform of the given type, handling special cases.

    Args:
        wave_type: Wave type string (sine, square, sawtooth, triangle, pulse,
            noise, harmonic, chirp).
        freq: Frequency in Hz.
        duration: Duration in seconds.
        amplitude: Peak amplitude.
        sample_rate: Samples per second.

    Returns:
        List of generated samples.
    """
    if wave_type == 'noise':
        return generate_noise(duration, amplitude, sample_rate)
    elif wave_type == 'harmonic':
        return generate_harmonic(freq, duration, amplitude, sample_rate=sample_rate)
    elif wave_type == 'chirp':
        # For chords/arps, chirp does a fixed-frequency "sine-like" tone
        return generate_chirp(freq, freq, duration, amplitude, sample_rate)
    elif wave_type == 'pulse':
        return generate_pulse(freq, duration, amplitude, duty_cycle=0.5, sample_rate=sample_rate)
    elif wave_type in WAVE_GENERATORS and WAVE_GENERATORS[wave_type] is not None:
        return WAVE_GENERATORS[wave_type](freq, duration, amplitude, sample_rate)
    else:
        return generate_sine(freq, duration, amplitude, sample_rate)


def generate_chord(root_freq: float, chord_type: str, duration: float,
                   wave_type: str = 'sine', amplitude: float = 1.0,
                   sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a chord by mixing multiple notes.

    Args:
        root_freq: Root note frequency in Hz.
        chord_type: Chord type (see CHORD_INTERVALS for options).
        duration: Duration in seconds.
        wave_type: Wave type for each note.
        amplitude: Peak amplitude.
        sample_rate: Samples per second.

    Returns:
        Mixed chord samples.
    """
    intervals = CHORD_INTERVALS.get(chord_type, CHORD_INTERVALS['maj'])
    waves = []
    for interval in intervals:
        freq = root_freq * (2.0 ** (interval / 12.0))
        w = _generate_wave_for_type(wave_type, freq, duration,
                                     amplitude / len(intervals), sample_rate)
        waves.append(w)
    return mix_waves(waves)


def generate_arpeggio(root_freq: float, chord_type: str, duration: float,
                     wave_type: str = 'sine', amplitude: float = 1.0,
                     sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate an arpeggio — each note played sequentially.

    Args:
        root_freq: Root note frequency in Hz.
        chord_type: Chord type (see CHORD_INTERVALS for options).
        duration: Total duration in seconds.
        wave_type: Wave type for each note.
        amplitude: Peak amplitude.
        sample_rate: Samples per second.

    Returns:
        Arpeggio samples (notes played one after another).
    """
    intervals = CHORD_INTERVALS.get(chord_type, CHORD_INTERVALS['maj'])
    note_duration = duration / len(intervals)
    result = []
    for interval in intervals:
        freq = root_freq * (2.0 ** (interval / 12.0))
        w = _generate_wave_for_type(wave_type, freq, note_duration,
                                     amplitude, sample_rate)
        result.extend(w)
    return result


# ─── Melody from Notes ──────────────────────────────────────────────────────

def generate_melody(notes: List[Tuple[str, float]], wave_type: str = 'sine',
                    amplitude: float = 0.8, sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a melody from a list of (note, duration) tuples.

    Args:
        notes: List of (note_name, duration_in_seconds) tuples.
            Note names like 'C4', 'A#3', or 'R'/'rest' for rests.
        wave_type: Wave type for each note.
        amplitude: Peak amplitude.
        sample_rate: Samples per second.

    Returns:
        Concatenated melody samples.
    """
    result = []
    for note, dur in notes:
        if note.upper() in ('R', 'REST', ''):
            result.extend([0.0] * int(dur * sample_rate))
        else:
            freq = resolve_freq(note)
            w = _generate_wave_for_type(wave_type, freq, dur, amplitude, sample_rate)
            result.extend(w)
    return result


def transpose_melody(notes: List[Tuple[str, float]], semitones: int) -> List[Tuple[str, float]]:
    """Transpose a melody by a given number of semitones.

    Notes specified as note names (e.g. 'C4') are shifted by the given
    number of semitones. Rests ('R') are left unchanged. Notes specified
    as numeric frequency strings are converted to the transposed frequency.

    Args:
        notes: List of (note_name, duration) tuples.
        semitones: Number of semitones to shift (positive = up, negative = down).

    Returns:
        New list of (note_or_freq, duration) tuples with transposed pitches.

    Example:
        >>> transpose_melody([('C4', 0.5), ('E4', 0.5)], 2)
        [('D4', 0.5), ('F#4', 0.5)]
    """
    result = []
    for note, dur in notes:
        if note.upper() in ('R', 'REST', ''):
            result.append((note, dur))
            continue

        # Check if it's a note name (contains a letter)
        is_note = note[0].isalpha()

        if is_note:
            freq = resolve_freq(note)
            new_freq = freq * (2.0 ** (semitones / 12.0))
            # Try to find the nearest note name for the new frequency
            new_note = _freq_to_note(new_freq)
            result.append((new_note, dur))
        else:
            # Numeric frequency
            freq = float(note)
            new_freq = freq * (2.0 ** (semitones / 12.0))
            result.append((f"{new_freq:.2f}", dur))
    return result


def _freq_to_note(freq: float) -> str:
    """Convert a frequency to the nearest note name.

    Args:
        freq: Frequency in Hz.

    Returns:
        Nearest note name (e.g. 'A4', 'C#5').
    """
    if freq <= 0:
        return f"{freq:.2f}"

    # Find the closest note
    best_note = None
    best_diff = float('inf')
    for note_name, note_freq in NOTE_FREQS.items():
        diff = abs(note_freq - freq)
        if diff < best_diff:
            best_diff = diff
            best_note = note_name

    # Prefer sharp names over flat names for readability
    if best_note and best_note.startswith(('D', 'G', 'A', 'B')):
        # Check if a sharp name exists with same frequency
        for note_name, note_freq in NOTE_FREQS.items():
            if abs(note_freq - freq) < 0.5 and '#' in note_name:
                return note_name
    return best_note if best_note else f"{freq:.2f}"


# ─── Preset Melodies ────────────────────────────────────────────────────────

MELODY_PRESETS = {
    'scale': [('C4', 0.3), ('D4', 0.3), ('E4', 0.3), ('F4', 0.3),
              ('G4', 0.3), ('A4', 0.3), ('B4', 0.3), ('C5', 0.5)],
    'happy_birthday': [('C4', 0.25), ('C4', 0.25), ('D4', 0.5), ('C4', 0.5),
                       ('F4', 0.5), ('E4', 1.0), ('R', 0.25),
                       ('C4', 0.25), ('C4', 0.25), ('D4', 0.5), ('C4', 0.5),
                       ('G4', 0.5), ('F4', 1.0)],
    'ode_to_joy': [('E4', 0.4), ('E4', 0.4), ('F4', 0.4), ('G4', 0.4),
                   ('G4', 0.4), ('F4', 0.4), ('E4', 0.4), ('D4', 0.4),
                   ('C4', 0.4), ('C4', 0.4), ('D4', 0.4), ('E4', 0.4),
                   ('E4', 0.6), ('D4', 0.2), ('D4', 0.8)],
    'twinkle': [('C4', 0.4), ('C4', 0.4), ('G4', 0.4), ('G4', 0.4),
                ('A4', 0.4), ('A4', 0.4), ('G4', 0.8),
                ('F4', 0.4), ('F4', 0.4), ('E4', 0.4), ('E4', 0.4),
                ('D4', 0.4), ('D4', 0.4), ('C4', 0.8)],
    'pentatonic': [('C4', 0.25), ('D4', 0.25), ('E4', 0.25), ('G4', 0.25),
                   ('A4', 0.25), ('C5', 0.25), ('A4', 0.25), ('G4', 0.25),
                   ('E4', 0.25), ('D4', 0.25), ('C4', 0.5)],
    'fur_elise': [('E5', 0.2), ('D#5', 0.2), ('E5', 0.2), ('D#5', 0.2),
                  ('E5', 0.2), ('B4', 0.2), ('D5', 0.2), ('C5', 0.2),
                  ('A4', 0.4), ('R', 0.1),
                  ('C4', 0.2), ('E4', 0.2), ('A4', 0.2), ('B4', 0.4),
                  ('R', 0.1),
                  ('E4', 0.2), ('G#4', 0.2), ('B4', 0.2), ('C5', 0.4)],
    'amazing_grace': [('G4', 0.6), ('B4', 0.3), ('D5', 0.3), ('E5', 0.6),
                      ('D5', 0.3), ('B4', 0.6), ('G4', 0.3),
                      ('A4', 0.6), ('G4', 0.3), ('E4', 0.6),
                      ('G4', 0.6), ('B4', 0.3), ('D5', 0.6)],
}


# ─── Interactive Mode ────────────────────────────────────────────────────────

def interactive_mode():
    """Run an interactive wave synthesizer session."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              🎵  WAVE SYNTH — Interactive Mode  🎵          ║")
    print(f"║                    version {__version__:<24}            ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Commands:")
    print("  gen <wave> <freq/note> <dur> [amp] — Generate waveform")
    print("  chirp <start> <end> <dur> [amp] [method] — Generate chirp/sweep")
    print("  pulse <freq> <duration> [duty] [amp] — Generate pulse wave (duty 0.0-1.0)")
    print("  effect <name> [params]             — Apply effect to current wave")
    print("  adsr <a> <d> <s> <r>               — Apply ADSR envelope")
    print("  mix <idx1> <idx2> [w1] [w2]        — Mix two stored waves")
    print("  chord <root> <type> <duration>     — Generate chord")
    print("  arp <root> <type> <duration>        — Generate arpeggio")
    print("  melody <preset>                     — Generate preset melody")
    print("  transpose <semitones>               — Transpose current melody by semitones")
    print("  import <filename>                  — Import WAV file")
    print("  viz                                 — Visualize current waveform")
    print("  spectrum                            — Show frequency spectrum")
    print("  info                                — Show waveform info")
    print("  export <filename>                  — Export as WAV")
    print("  play                                — Show current waveform")
    print("  list                                — List stored waveforms")
    print("  help                                 — Show this help")
    print("  quit                                 — Exit")
    print()
    print(f"  Wave types: sine, square, sawtooth, triangle, pulse, noise, harmonic, chirp")
    print(f"  Effects: {', '.join(EFFECTS.keys())}")
    print(f"  Chord types: {', '.join(CHORD_INTERVALS.keys())}")
    print(f"  Melody presets: {', '.join(MELODY_PRESETS.keys())}")
    print()

    current = None
    waves = []  # List of (name, samples) tuples
    current_melody_notes = None  # Store melody notes for transposition

    while True:
        try:
            cmd = input("wave> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not cmd:
            continue

        parts = cmd.split()
        action = parts[0].lower()

        try:
            if action == 'quit' or action == 'exit':
                print("Bye!")
                break

            elif action == 'help':
                print("See the command list above, or use 'gen sine A4 2' to get started!")

            elif action == 'gen':
                if len(parts) < 4:
                    print("Usage: gen <wave_type> <freq_or_note> <duration> [amplitude]")
                    continue
                wave_type = parts[1].lower()
                freq = resolve_freq(parts[2])
                duration = float(parts[3])
                amplitude = float(parts[4]) if len(parts) > 4 else 0.8
                if wave_type not in WAVE_GENERATORS or WAVE_GENERATORS[wave_type] is None:
                    print(f"Unknown wave type: {wave_type}. Available: {', '.join(k for k,v in WAVE_GENERATORS.items() if v is not None)}")
                    continue
                gen = WAVE_GENERATORS[wave_type]
                if wave_type == 'noise':
                    samples = generate_noise(duration, amplitude, SAMPLE_RATE)
                else:
                    samples = gen(freq, duration, amplitude, SAMPLE_RATE)
                name = f"{wave_type}_{parts[2]}_{duration}s"
                current = samples
                waves.append((name, samples))
                current_melody_notes = None
                print(f"  Generated {name} ({len(samples)} samples, amp={amplitude})")

            elif action == 'pulse':
                if len(parts) < 4:
                    print("Usage: pulse <freq_or_note> <duration> [duty_cycle] [amplitude]")
                    continue
                freq = resolve_freq(parts[1])
                duration = float(parts[2])
                duty = float(parts[3]) if len(parts) > 3 else 0.5
                amplitude = float(parts[4]) if len(parts) > 4 else 0.8
                samples = generate_pulse(freq, duration, amplitude, duty, SAMPLE_RATE)
                name = f"pulse_{parts[1]}_{duration}s_d{duty}"
                current = samples
                waves.append((name, samples))
                current_melody_notes = None
                print(f"  Generated {name} ({len(samples)} samples, amp={amplitude})")

            elif action == 'chirp':
                if len(parts) < 4:
                    print("Usage: chirp <start_freq> <end_freq> <duration> [amplitude] [linear|exponential]")
                    continue
                start_freq = resolve_freq(parts[1])
                end_freq = resolve_freq(parts[2])
                duration = float(parts[3])
                amplitude = 0.8
                method = 'linear'
                for p in parts[4:]:
                    if p.lower() in ('linear', 'exponential'):
                        method = p.lower()
                    else:
                        try:
                            amplitude = float(p)
                        except ValueError:
                            pass
                samples = generate_chirp(start_freq, end_freq, duration, amplitude, SAMPLE_RATE, method)
                name = f"chirp_{parts[1]}_{parts[2]}_{duration}s"
                current = samples
                waves.append((name, samples))
                current_melody_notes = None
                print(f"  Generated {name} ({len(samples)} samples)")

            elif action == 'effect':
                if current is None:
                    print("No current waveform. Use 'gen' first.")
                    continue
                if len(parts) < 2:
                    print(f"Available effects: {', '.join(EFFECTS.keys())}")
                    continue
                effect_name = parts[1].lower()
                if effect_name not in EFFECTS:
                    print(f"Unknown effect: {effect_name}. Available: {', '.join(EFFECTS.keys())}")
                    continue

                if effect_name == 'tremolo':
                    rate = float(parts[2]) if len(parts) > 2 else 5.0
                    depth = float(parts[3]) if len(parts) > 3 else 0.5
                    current = apply_tremolo(current, rate, depth)
                    print(f"  Applied tremolo (rate={rate}, depth={depth})")
                elif effect_name == 'vibrato':
                    rate = float(parts[2]) if len(parts) > 2 else 5.0
                    depth = float(parts[3]) if len(parts) > 3 else 0.002
                    current = apply_vibrato(current, rate, depth)
                    print(f"  Applied vibrato (rate={rate}, depth={depth})")
                elif effect_name == 'lowpass':
                    cutoff = float(parts[2]) if len(parts) > 2 else 1000.0
                    current = apply_lowpass(current, cutoff)
                    print(f"  Applied lowpass (cutoff={cutoff}Hz)")
                elif effect_name == 'highpass':
                    cutoff = float(parts[2]) if len(parts) > 2 else 1000.0
                    current = apply_highpass(current, cutoff)
                    print(f"  Applied highpass (cutoff={cutoff}Hz)")
                elif effect_name == 'distortion':
                    drive = float(parts[2]) if len(parts) > 2 else 2.0
                    current = apply_distortion(current, drive)
                    print(f"  Applied distortion (drive={drive})")
                elif effect_name == 'delay':
                    delay_time = float(parts[2]) if len(parts) > 2 else 0.3
                    feedback = float(parts[3]) if len(parts) > 3 else 0.4
                    current = apply_delay(current, delay_time, feedback)
                    print(f"  Applied delay (time={delay_time}s, feedback={feedback})")
                elif effect_name == 'fadein':
                    dur = float(parts[2]) if len(parts) > 2 else 0.05
                    current = apply_fade_in(current, dur)
                    print(f"  Applied fade-in ({dur}s)")
                elif effect_name == 'fadeout':
                    dur = float(parts[2]) if len(parts) > 2 else 0.05
                    current = apply_fade_out(current, dur)
                    print(f"  Applied fade-out ({dur}s)")
                elif effect_name == 'normalize':
                    current = normalize(current)
                    print("  Normalized waveform")
                elif effect_name == 'adsr':
                    a = float(parts[2]) if len(parts) > 2 else 0.01
                    d = float(parts[3]) if len(parts) > 3 else 0.01
                    s = float(parts[4]) if len(parts) > 4 else 0.7
                    r = float(parts[5]) if len(parts) > 5 else 0.1
                    current = apply_adsr(current, a, d, s, r)
                    print(f"  Applied ADSR (A={a}, D={d}, S={s}, R={r})")
                elif effect_name == 'reverse':
                    current = apply_reverse(current)
                    print("  Reversed waveform")
                elif effect_name == 'ringmod':
                    freq = float(parts[2]) if len(parts) > 2 else 100.0
                    current = apply_ring_mod(current, freq)
                    print(f"  Applied ring modulation (carrier={freq}Hz)")
                elif effect_name == 'bitcrush':
                    bits = int(parts[2]) if len(parts) > 2 else 8
                    current = apply_bitcrush(current, bits)
                    print(f"  Applied bitcrush ({bits}-bit)")
                elif effect_name == 'reverb':
                    decay = float(parts[2]) if len(parts) > 2 else 0.3
                    current = apply_reverb(current, decay)
                    print(f"  Applied reverb (decay={decay})")
                elif effect_name == 'pitchshift':
                    semitones = float(parts[2]) if len(parts) > 2 else 0.0
                    current = apply_pitch_shift(current, semitones)
                    print(f"  Applied pitch shift ({semitones:+.1f} semitones)")
                elif effect_name == 'compressor':
                    threshold = float(parts[2]) if len(parts) > 2 else 0.5
                    ratio = float(parts[3]) if len(parts) > 3 else 4.0
                    current = apply_compressor(current, threshold, ratio)
                    print(f"  Applied compressor (threshold={threshold}, ratio={ratio})")
                elif effect_name == 'flanger':
                    rate = float(parts[2]) if len(parts) > 2 else 0.5
                    depth = float(parts[3]) if len(parts) > 3 else 0.002
                    feedback = float(parts[4]) if len(parts) > 4 else 0.3
                    current = apply_flanger(current, rate, depth, feedback)
                    print(f"  Applied flanger (rate={rate}Hz, depth={depth}s, feedback={feedback})")

                waves.append((f"effect_{effect_name}", current))

            elif action == 'mix':
                if len(parts) < 3:
                    print("Usage: mix <idx1> <idx2> [weight1] [weight2]")
                    continue
                idx1 = int(parts[1])
                idx2 = int(parts[2])
                w1 = float(parts[3]) if len(parts) > 3 else 1.0
                w2 = float(parts[4]) if len(parts) > 4 else 1.0
                if idx1 >= len(waves) or idx2 >= len(waves):
                    print(f"Index out of range. Available: 0-{len(waves)-1}")
                    continue
                current = mix_waves([waves[idx1][1], waves[idx2][1]], [w1, w2])
                name = f"mix_{idx1}_{idx2}"
                waves.append((name, current))
                print(f"  Mixed waves {idx1} and {idx2} (weights: {w1}, {w2})")

            elif action == 'chord':
                if len(parts) < 4:
                    print("Usage: chord <root_note> <type> <duration> [wave]")
                    continue
                root = resolve_freq(parts[1])
                chord_type = parts[2].lower()
                duration = float(parts[3])
                wave_type = parts[4].lower() if len(parts) > 4 else 'sine'
                current = generate_chord(root, chord_type, duration, wave_type)
                name = f"chord_{parts[1]}_{chord_type}"
                waves.append((name, current))
                current_melody_notes = None
                print(f"  Generated {name} ({len(current)} samples)")

            elif action == 'arp':
                if len(parts) < 4:
                    print("Usage: arp <root_note> <type> <duration> [wave]")
                    continue
                root = resolve_freq(parts[1])
                chord_type = parts[2].lower()
                duration = float(parts[3])
                wave_type = parts[4].lower() if len(parts) > 4 else 'sine'
                current = generate_arpeggio(root, chord_type, duration, wave_type)
                name = f"arp_{parts[1]}_{chord_type}"
                waves.append((name, current))
                current_melody_notes = None
                print(f"  Generated {name} ({len(current)} samples)")

            elif action == 'melody':
                if len(parts) < 2:
                    print(f"Available presets: {', '.join(MELODY_PRESETS.keys())}")
                    continue
                preset = parts[1].lower()
                if preset not in MELODY_PRESETS:
                    print(f"Unknown preset: {preset}. Available: {', '.join(MELODY_PRESETS.keys())}")
                    continue
                wave_type = parts[2].lower() if len(parts) > 2 else 'sine'
                notes = MELODY_PRESETS[preset]
                current = generate_melody(notes, wave_type)
                name = f"melody_{preset}"
                waves.append((name, current))
                current_melody_notes = list(notes)
                print(f"  Generated {name} ({len(current)} samples)")

            elif action == 'transpose':
                if len(parts) < 2:
                    print("Usage: transpose <semitones>")
                    continue
                semitones = int(parts[1])
                if current_melody_notes is None:
                    print("No melody to transpose. Generate a melody first with 'melody <preset>'.")
                    continue
                current_melody_notes = transpose_melody(current_melody_notes, semitones)
                wave_type = parts[2].lower() if len(parts) > 2 else 'sine'
                current = generate_melody(current_melody_notes, wave_type)
                name = f"transposed_{semitones:+d}"
                waves.append((name, current))
                print(f"  Transposed melody by {semitones:+d} semitones ({len(current)} samples)")

            elif action == 'import':
                if len(parts) < 2:
                    print("Usage: import <filename.wav>")
                    continue
                filename = parts[1]
                try:
                    samples, sr = import_wav(filename)
                    name = os.path.basename(filename).replace('.wav', '')
                    current = samples
                    waves.append((name, samples))
                    current_melody_notes = None
                    print(f"  Imported {filename} ({len(samples)} samples, {sr}Hz)")
                except Exception as e:
                    print(f"  Import error: {e}")

            elif action == 'viz' or action == 'visualize':
                if current is None:
                    print("No current waveform.")
                    continue
                print(visualize_ascii(current))

            elif action == 'spectrum':
                if current is None:
                    print("No current waveform.")
                    continue
                print(visualize_spectrum_ascii(current))

            elif action == 'info':
                if current is None:
                    print("No current waveform.")
                    continue
                name = waves[-1][0] if waves else "unknown"
                print(print_waveform_info(current, name))

            elif action == 'export':
                if current is None:
                    print("No current waveform to export.")
                    continue
                filename = parts[1] if len(parts) > 1 else "output.wav"
                if not filename.endswith('.wav'):
                    filename += '.wav'
                export_wav(current, filename)

            elif action == 'play':
                if current is None:
                    print("No current waveform.")
                    continue
                name = waves[-1][0] if waves else "unknown"
                print(f"Current: {name} ({len(current)} samples)")
                print(visualize_ascii(current))

            elif action == 'list':
                if not waves:
                    print("No waveforms stored yet.")
                    continue
                for i, (name, s) in enumerate(waves):
                    dur = len(s) / SAMPLE_RATE
                    marker = " ◀" if s is current else ""
                    print(f"  [{i}] {name} ({dur:.2f}s){marker}")

            else:
                print(f"Unknown command: {action}. Type 'help' for commands.")

        except Exception as e:
            print(f"Error: {e}")


# ─── CLI Mode ────────────────────────────────────────────────────────────────

def _list_notes():
    """Print a table of all available note names and their frequencies."""
    print("\n  Note   Frequency (Hz)")
    print("  " + "─" * 25)
    for octave in range(0, 9):
        for note in ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']:
            key = f"{note}{octave}"
            if key in NOTE_FREQS:
                print(f"  {key:<6} {NOTE_FREQS[key]:>8.2f}")
    print()


def _list_chords():
    """Print a table of all available chord types and their intervals."""
    print("\n  Chord Type   Intervals (semitones)")
    print("  " + "─" * 40)
    for name, intervals in CHORD_INTERVALS.items():
        print(f"  {name:<12} {intervals}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Wave Synth — Terminal Audio Waveform Synthesizer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sine A4 2                          Generate 2s sine at A4 (440Hz)
  %(prog)s square 220 1 --effect tremolo       Square wave with tremolo
  %(prog)s triangle C4 3 --export output.wav   Export triangle wave to WAV
  %(prog)s pulse A4 2 --duty 0.25               25%% duty cycle pulse wave
  %(prog)s harmonic E4 2 --harmonics "1,1 2,0.5 3,0.25"  Custom harmonics
  %(prog)s chord C4 maj 2 --wave sawtooth     C major chord (sawtooth)
  %(prog)s arp A3 min7 3                       A minor 7 arpeggio
  %(prog)s melody twinkle --wave triangle      Twinkle Twinkle melody
  %(prog)s chirp 200 2000 3                    Frequency sweep 200-2000Hz
  %(prog)s sine A4 2 --effect reverb:0.4       Sine with reverb
  %(prog)s sine A4 2 --effect compressor:0.5:4  Compressed sine
  %(prog)s sine A4 2 --effect flanger:0.5:0.002:0.3  Flanged sine
  %(prog)s --import-wav input.wav --effect lowpass:800 --export processed.wav
  %(prog)s --interactive                       Start interactive mode
  %(prog)s --list-notes                        Show all note names and frequencies
  %(prog)s --list-chords                       Show all chord types

Effects: tremolo, vibrato, lowpass, highpass, distortion, delay, fadein,
         fadeout, normalize, reverse, ringmod, bitcrush, reverb, pitchshift,
         compressor, flanger

Effect parameters:
  tremolo:RATE:DEPTH     vibrato:RATE:DEPTH      lowpass:CUTOFF
  highpass:CUTOFF       distortion:DRIVE         delay:TIME:FEEDBACK
  fadein:DURATION       fadeout:DURATION          ringmod:FREQ
  bitcrush:BITS         reverb:DECAY              pitchshift:SEMITONES
  compressor:THRESHOLD:RATIO   flanger:RATE:DEPTH:FEEDBACK
        """)

    parser.add_argument('wave_type', nargs='?', choices=list(WAVE_GENERATORS.keys()) + ['chord', 'arp', 'melody'],
                        help='Type of waveform to generate')
    parser.add_argument('remaining', nargs='*', help='Note, chord-type, and/or duration (varies by wave type)')

    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Start interactive mode')
    parser.add_argument('--version', '-V', action='version',
                        version=f'Wave Synth v{__version__}')
    parser.add_argument('--wave', '-w', default='sine',
                        choices=[k for k in WAVE_GENERATORS.keys() if WAVE_GENERATORS[k] is not None],
                        help='Wave type for chord/arp/melody (default: sine)')
    parser.add_argument('--amplitude', '-a', type=float, default=0.8,
                        help='Amplitude 0-1 (default: 0.8)')
    parser.add_argument('--export', '-e', metavar='FILE',
                        help='Export to WAV file')
    parser.add_argument('--import-wav', metavar='FILE',
                        help='Import WAV file and apply effects/visualize')
    parser.add_argument('--effect', '-f', action='append',
                        help='Apply effect (e.g. tremolo, lowpass:1000, distortion:3, reverb:0.4)')
    parser.add_argument('--adsr', metavar='A,D,S,R',
                        help='Apply ADSR envelope (e.g. 0.01,0.1,0.7,0.2)')
    parser.add_argument('--chord-type', '-c', default='maj',
                        choices=list(CHORD_INTERVALS.keys()),
                        help='Chord type (for chord/arp commands)')
    parser.add_argument('--harmonics', metavar='N,A ...',
                        help='Custom harmonics for harmonic wave (e.g. "1,1 2,0.5 3,0.25")')
    parser.add_argument('--duty', type=float, default=0.5,
                        help='Duty cycle for pulse wave (0.0-1.0, default: 0.5)')
    parser.add_argument('--sweep-method', choices=['linear', 'exponential'], default='linear',
                        help='Chirp sweep method: linear or exponential (default: linear)')
    parser.add_argument('--spectrum', '-s', action='store_true',
                        help='Show frequency spectrum instead of waveform')
    parser.add_argument('--info', action='store_true',
                        help='Show waveform info')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress visualization output')
    parser.add_argument('--seed', type=int,
                        help='Random seed for noise generation')
    parser.add_argument('--width', type=int, default=TERMINAL_WIDTH,
                        help='Visualization width')
    parser.add_argument('--height', type=int, default=TERMINAL_HEIGHT,
                        help='Visualization height')
    parser.add_argument('--list-notes', action='store_true',
                        help='List all available note names and frequencies')
    parser.add_argument('--list-chords', action='store_true',
                        help='List all available chord types and intervals')

    args = parser.parse_args()

    if args.list_notes:
        _list_notes()
        return

    if args.list_chords:
        _list_chords()
        return

    if args.interactive:
        interactive_mode()
        return

    if not args.wave_type and not args.import_wav:
        parser.print_help()
        return

    # Parse positional args based on wave type
    remaining = args.remaining or []

    # Parse effect parameters
    effects_to_apply = []
    if args.effect:
        for eff_str in args.effect:
            parts = eff_str.split(':')
            name = parts[0].lower()
            try:
                params = [float(p) for p in parts[1:]] if len(parts) > 1 else []
            except ValueError:
                print(f"  Invalid effect parameter for '{name}': expected numbers, got '{':'.join(parts[1:])}'")
                return
            effects_to_apply.append((name, params))

    # Parse ADSR
    adsr_params = None
    if args.adsr:
        parts = args.adsr.split(',')
        if len(parts) == 4:
            try:
                adsr_params = tuple(float(p) for p in parts)
            except ValueError:
                print("ADSR parameters must be numbers. Format: A,D,S,R (e.g. 0.01,0.1,0.7,0.2)")
                return
        else:
            print("ADSR format: A,D,S,R (e.g. 0.01,0.1,0.7,0.2)")
            return

    # Generate waveform
    samples = None

    # Handle WAV import
    if args.import_wav:
        try:
            samples, imported_sr = import_wav(args.import_wav)
            print(f"  Imported: {args.import_wav} ({len(samples)} samples, {imported_sr}Hz)")
        except Exception as e:
            print(f"  Import error: {e}")
            return

    elif args.wave_type in ('chord', 'arp'):
        note = remaining[0] if len(remaining) >= 1 else None
        if not note:
            print(f"{args.wave_type} requires note and duration. Usage: {args.wave_type} <note> [chord_type] <duration>")
            return
        if len(remaining) == 3:
            chord_type = remaining[1]
            duration = float(remaining[2])
        elif len(remaining) == 2:
            try:
                duration = float(remaining[1])
                chord_type = args.chord_type
            except ValueError:
                chord_type = remaining[1]
                print(f"{args.wave_type} requires a duration. Usage: {args.wave_type} <note> [chord_type] <duration>")
                return
        else:
            print(f"{args.wave_type} requires note and duration. Usage: {args.wave_type} <note> [chord_type] <duration>")
            return
        freq = resolve_freq(note)
        if args.wave_type == 'chord':
            samples = generate_chord(freq, chord_type, duration, args.wave, args.amplitude)
        else:
            samples = generate_arpeggio(freq, chord_type, duration, args.wave, args.amplitude)

    elif args.wave_type == 'melody':
        preset = remaining[0] if remaining else None
        if preset and preset.lower() in MELODY_PRESETS:
            samples = generate_melody(MELODY_PRESETS[preset.lower()], args.wave, args.amplitude)
        else:
            print(f"Melody presets: {', '.join(MELODY_PRESETS.keys())}")
            return

    elif args.wave_type == 'chirp':
        if len(remaining) < 3:
            print("Chirp requires start_freq, end_freq, and duration. Usage: chirp <start_freq> <end_freq> <duration>")
            return
        start_freq = resolve_freq(remaining[0])
        end_freq = resolve_freq(remaining[1])
        duration = float(remaining[2])
        samples = generate_chirp(start_freq, end_freq, duration, args.amplitude, SAMPLE_RATE, args.sweep_method)

    elif args.wave_type == 'pulse':
        if len(remaining) < 2:
            print("Pulse wave requires note/frequency and duration. Usage: pulse <note/freq> <duration> [--duty D]")
            return
        note = remaining[0]
        duration = float(remaining[1])
        freq = resolve_freq(note)
        duty = max(0.01, min(0.99, args.duty))  # Clamp duty cycle to valid range
        samples = generate_pulse(freq, duration, args.amplitude, duty, SAMPLE_RATE)

    else:
        # Standard wave: sine A4 2 | noise 1 | harmonic C4 2
        if len(remaining) < 1:
            print("Generation requires note/frequency. For noise, provide duration.")
            return
        note = remaining[0]
        if len(remaining) >= 2:
            duration = float(remaining[1])
        else:
            if args.wave_type == 'noise':
                duration = float(note)
                note = None
            else:
                print("Generation requires note/frequency and duration")
                return

        if args.wave_type == 'noise':
            samples = generate_noise(duration, args.amplitude, SAMPLE_RATE, args.seed)
        elif args.wave_type == 'harmonic':
            freq = resolve_freq(note)
            harmonics = None
            if args.harmonics:
                harmonics = []
                for h_str in args.harmonics.split():
                    n, a = h_str.split(',')
                    harmonics.append((int(n), float(a)))
            samples = generate_harmonic(freq, duration, args.amplitude, harmonics)
        else:
            freq = resolve_freq(note)
            gen = WAVE_GENERATORS[args.wave_type]
            samples = gen(freq, duration, args.amplitude)

    # Apply ADSR
    if adsr_params and samples:
        samples = apply_adsr(samples, *adsr_params)

    # Apply effects
    if samples:
        for eff_name, params in effects_to_apply:
            if eff_name in EFFECTS:
                func = EFFECTS[eff_name]
                try:
                    samples = func(samples, *params)
                except TypeError:
                    samples = func(samples)
                print(f"  Applied: {eff_name}")
            else:
                print(f"  Unknown effect: {eff_name}")

    # Normalize before export
    if args.export and samples:
        samples = normalize(samples, 0.95)

    # Output
    label = args.wave_type or "imported"
    if remaining:
        label += '_' + '_'.join(str(r) for r in remaining)

    if args.info and samples:
        print(print_waveform_info(samples, label))
        print()

    if not args.quiet and samples:
        if args.spectrum:
            print(visualize_spectrum_ascii(samples, args.width, args.height))
        else:
            print(visualize_ascii(samples, args.width, args.height))

    if args.export and samples:
        export_wav(samples, args.export)


if __name__ == '__main__':
    main()