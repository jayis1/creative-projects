"""
Signal generation utilities for testing, demos, and benchmarking.

Provides parametric generation of common test signals used in wavelet
analysis: sinusoids, chirps, square/sawtooth/triangle waves, pulses,
steps, ramps, multi-tone signals, various noise types, and canonical
signals from the Donoho-Johnstone test suite (blocks, bumps, heaviSine,
Doppler).
"""

from __future__ import annotations

import math
import random
from typing import Optional

__all__ = [
    "sine",
    "multi_tone",
    "chirp",
    "square",
    "sawtooth",
    "triangle",
    "pulse",
    "step",
    "ramp",
    "gaussian_pulse",
    "white_noise",
    "brown_noise",
    "pink_noise",
    "blocks",
    "bumps",
    "heavisine",
    "doppler",
    "ecg_like",
    "add_noise",
    "generate",
]


# -------------------------------------------------------------------------
# Basic waveforms
# -------------------------------------------------------------------------
def sine(n: int, freq: float = 4.0, amplitude: float = 1.0,
         phase: float = 0.0) -> list[float]:
    """Generate a pure sine wave of ``n`` samples.

    Parameters
    ----------
    n : number of samples
    freq : frequency in cycles over the full signal (default 4 cycles)
    amplitude : peak amplitude
    phase : phase offset in radians
    """
    return [amplitude * math.sin(2 * math.pi * freq * i / n + phase) for i in range(n)]


def multi_tone(n: int, freqs: list[float], amplitudes: list[float] | None = None,
               phases: list[float] | None = None) -> list[float]:
    """Generate a multi-tone (sum of sinusoids) signal.

    Parameters
    ----------
    n : number of samples
    freqs : list of frequencies (cycles over full signal)
    amplitudes : per-tone amplitudes (default: all 1.0)
    phases : per-tone phase offsets in radians (default: all 0.0)
    """
    if amplitudes is None:
        amplitudes = [1.0] * len(freqs)
    if phases is None:
        phases = [0.0] * len(freqs)
    if len(amplitudes) != len(freqs) or len(phases) != len(freqs):
        raise ValueError("freqs, amplitudes, phases must have the same length")
    return [
        sum(a * math.sin(2 * math.pi * f * i / n + p)
            for f, a, p in zip(freqs, amplitudes, phases))
        for i in range(n)
    ]


def chirp(n: int, f0: float = 1.0, f1: float = 10.0,
          amplitude: float = 1.0) -> list[float]:
    """Generate a linear chirp signal sweeping from ``f0`` to ``f1`` cycles.

    The instantaneous frequency increases linearly from ``f0`` to ``f1``
    over the duration of the signal.
    """
    t = [i / n for i in range(n)]
    k = (f1 - f0)  # chirp rate (cycles per unit time)
    return [amplitude * math.sin(2 * math.pi * (f0 * ti + 0.5 * k * ti * ti) * n) for ti in t]


def square(n: int, freq: float = 4.0, amplitude: float = 1.0) -> list[float]:
    """Generate a square wave."""
    return [amplitude if math.sin(2 * math.pi * freq * i / n) > 0 else -amplitude
            for i in range(n)]


def sawtooth(n: int, freq: float = 4.0, amplitude: float = 1.0) -> list[float]:
    """Generate a sawtooth wave."""
    return [2 * amplitude * ((freq * i / n) % 1.0) - amplitude for i in range(n)]


def triangle(n: int, freq: float = 4.0, amplitude: float = 1.0) -> list[float]:
    """Generate a triangle wave."""
    result = []
    for i in range(n):
        phase = (freq * i / n) % 1.0
        if phase < 0.5:
            result.append(amplitude * (4 * phase - 1))
        else:
            result.append(amplitude * (3 - 4 * phase))
    return result


def pulse(n: int, start: float = 0.3, end: float = 0.7,
          amplitude: float = 1.0) -> list[float]:
    """Generate a rectangular pulse.

    Parameters
    ----------
    n : number of samples
    start : pulse start as fraction of n (0..1)
    end : pulse end as fraction of n (0..1)
    amplitude : pulse height
    """
    s, e = int(start * n), int(end * n)
    return [amplitude if s <= i < e else 0.0 for i in range(n)]


def step(n: int, position: float = 0.5, amplitude: float = 1.0) -> list[float]:
    """Generate a Heaviside step function."""
    pos = int(position * n)
    return [0.0 if i < pos else amplitude for i in range(n)]


def ramp(n: int, start: float = 0.0, end: float = 1.0) -> list[float]:
    """Generate a linear ramp from ``start`` to ``end``."""
    if n <= 1:
        return [start]
    return [start + (end - start) * i / (n - 1) for i in range(n)]


def gaussian_pulse(n: int, center: float = 0.5, sigma: float = 0.1,
                   amplitude: float = 1.0) -> list[float]:
    """Generate a Gaussian-modulated pulse."""
    return [amplitude * math.exp(-((i / n - center) ** 2) / (2 * sigma * sigma))
            for i in range(n)]


# -------------------------------------------------------------------------
# Noise generators
# -------------------------------------------------------------------------
def white_noise(n: int, sigma: float = 1.0, seed: int | None = None) -> list[float]:
    """Generate white (Gaussian) noise with std dev ``sigma``."""
    rng = random.Random(seed)
    return [rng.gauss(0, sigma) for _ in range(n)]


def brown_noise(n: int, sigma: float = 1.0, seed: int | None = None) -> list[float]:
    """Generate brown (integrated white) noise — random walk."""
    rng = random.Random(seed)
    result = [0.0] * n
    val = 0.0
    for i in range(n):
        val += rng.gauss(0, sigma)
        result[i] = val
    # Normalize to zero mean
    mean = sum(result) / n
    return [v - mean for v in result]


def pink_noise(n: int, sigma: float = 1.0, alpha: float = 1.0,
               seed: int | None = None) -> list[float]:
    """Generate pink (1/f^alpha) noise via the Voss-McCartney algorithm.

    Parameters
    ----------
    n : number of samples
    sigma : desired standard deviation of the output
    alpha : spectral exponent (1.0 = standard pink, 0 ≈ white, 2 ≈ brown)
    seed : random seed for reproducibility
    """
    rng = random.Random(seed)
    result = [0.0] * n
    # Use several octaves and sum
    n_octaves = max(1, int(math.log2(n)) + 1)
    octaves = []
    for _ in range(n_octaves):
        octaves.append(rng.gauss(0, 1))
    for i in range(n):
        # Update some octaves based on bit pattern of i
        for b in range(n_octaves):
            if (i >> b) & 1:
                octaves[b] = rng.gauss(0, 1)
        result[i] = sum(octaves) / math.sqrt(n_octaves)
    # Scale to desired std dev
    if result:
        m = sum(result) / n
        std = math.sqrt(sum((v - m) ** 2 for v in result) / n)
        if std > 0:
            result = [(v - m) * sigma / std for v in result]
    return result


# -------------------------------------------------------------------------
# Donoho-Johnstone test signals
# -------------------------------------------------------------------------
def blocks(n: int) -> list[float]:
    """Donoho-Johnstone 'blocks' test signal."""
    tjumps = [0.1, 0.13, 0.15, 0.23, 0.25, 0.40, 0.44, 0.65, 0.66, 0.77, 0.81, 0.87, 0.89]
    hjumps = [4.0, -5.0, 3.0, -4.0, 5.0, -4.2, 2.1, 4.3, -3.1, 2.1, -4.2, 2.4, -1.1]
    result = [0.0] * n
    for i in range(n):
        t = (i + 1) / n
        val = 0.0
        for tj, hj in zip(tjumps, hjumps):
            if t >= tj:
                val += hj
        result[i] = val
    # Normalize
    mx = max(abs(v) for v in result) or 1.0
    return [v / mx * 3.0 for v in result]


def bumps(n: int) -> list[float]:
    """Donoho-Johnstone 'bumps' test signal."""
    tjumps = [0.1, 0.13, 0.15, 0.23, 0.25, 0.40, 0.44, 0.65, 0.66, 0.77, 0.81, 0.87, 0.89]
    hjumps = [4.0, 5.0, 3.0, 4.0, 5.0, 4.2, 2.1, 4.3, 3.1, 2.1, 4.2, 2.4, 1.1]
    wjumps = [0.005, 0.005, 0.006, 0.01, 0.01, 0.03, 0.01, 0.01, 0.005, 0.008, 0.005, 0.005, 0.005]
    result = [0.0] * n
    for i in range(n):
        t = (i + 1) / n
        val = 0.0
        for tj, hj, wj in zip(tjumps, hjumps, wjumps):
            val += hj / (1 + abs((t - tj) / wj) ** 4)
        result[i] = val
    mx = max(abs(v) for v in result) or 1.0
    return [v / mx * 3.0 for v in result]


def heavisine(n: int) -> list[float]:
    """Donoho-Johnstone 'heaviSine' test signal."""
    result = []
    for i in range(n):
        t = (i + 1) / n
        val = 4 * math.sin(4 * math.pi * t)
        if t >= 0.6:
            val -= 6.0
        result.append(val)
    mx = max(abs(v) for v in result) or 1.0
    return [v / mx * 3.0 for v in result]


def doppler(n: int) -> list[float]:
    """Donoho-Johnstone 'Doppler' test signal."""
    result = []
    for i in range(n):
        t = (i + 1) / n
        val = math.sqrt(t * (1 - t)) * math.sin(2 * math.pi * 1.05 / (t + 0.05))
        result.append(val)
    mx = max(abs(v) for v in result) or 1.0
    return [v / mx * 3.0 for v in result]


def ecg_like(n: int, heart_rate: float = 72.0,
             amplitude: float = 1.0) -> list[float]:
    """Generate a synthetic ECG-like signal with periodic QRS complexes."""
    beats_per_signal = heart_rate / 60 * n / 1000  # assume 1000 Hz rate conceptually
    period = max(1, n / max(1, beats_per_signal))
    result = []
    for i in range(n):
        phase = (i % period) / period  # 0..1 within one beat
        # QRS complex around phase=0.1
        qrs = -0.1 * math.exp(-((phase - 0.08) ** 2) / 0.0001)
        r_wave = 1.0 * math.exp(-((phase - 0.10) ** 2) / 0.00005)
        s_wave = -0.25 * math.exp(-((phase - 0.12) ** 2) / 0.0001)
        # P wave
        p_wave = 0.15 * math.exp(-((phase - 0.05) ** 2) / 0.0008)
        # T wave
        t_wave = 0.3 * math.exp(-((phase - 0.25) ** 2) / 0.005)
        result.append(amplitude * (p_wave + qrs + r_wave + s_wave + t_wave))
    return result


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def add_noise(signal: list[float], sigma: float = 0.3,
              seed: int | None = None) -> list[float]:
    """Add Gaussian white noise to a signal."""
    noise = white_noise(len(signal), sigma, seed)
    return [s + nz for s, nz in zip(signal, noise)]


_GENERATORS = {
    "sine": sine,
    "multi": lambda n: multi_tone(n, [4.0, 16.0], [1.0, 0.3]),
    "chirp": chirp,
    "square": square,
    "sawtooth": sawtooth,
    "triangle": triangle,
    "pulse": pulse,
    "step": step,
    "ramp": ramp,
    "gaussian": gaussian_pulse,
    "white_noise": lambda n: white_noise(n, 1.0, seed=42),
    "brown_noise": lambda n: brown_noise(n, 1.0, seed=42),
    "pink_noise": lambda n: pink_noise(n, 1.0, seed=42),
    "blocks": blocks,
    "bumps": bumps,
    "heavisine": heavisine,
    "doppler": doppler,
    "ecg": ecg_like,
}


def generate(kind: str, n: int, noise: float = 0.0,
             seed: int | None = None) -> list[float]:
    """Generate a named test signal, optionally with additive noise.

    Parameters
    ----------
    kind : signal name (see ``list_signals()``)
    n : number of samples
    noise : std dev of additive Gaussian noise (default: 0)
    seed : random seed for reproducible noise
    """
    kind = kind.lower().strip()
    if kind not in _GENERATORS:
        raise ValueError(f"Unknown signal '{kind}'. Available: {sorted(_GENERATORS.keys())}")
    sig = _GENERATORS[kind](n)
    if noise > 0:
        sig = add_noise(sig, noise, seed)
    return sig


def list_signals() -> list[str]:
    """Return a sorted list of available signal names."""
    return sorted(_GENERATORS.keys())