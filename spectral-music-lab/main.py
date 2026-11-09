#!/usr/bin/env python3
"""Analyze short audio with a dependency-free radix-2 FFT and spectral features."""
from __future__ import annotations
import argparse
import cmath
import json
import math
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Peak:
    frequency_hz: float
    magnitude: float


@dataclass(frozen=True)
class Analysis:
    sample_rate: int
    samples: int
    rms: float
    spectral_centroid_hz: float
    dominant_frequency_hz: float | None
    peaks: list[Peak]


def fft(values: Sequence[complex]) -> list[complex]:
    """Return the forward radix-2 FFT; reject empty or non-power-of-two inputs."""
    n = len(values)
    if n == 0 or n & (n - 1):
        raise ValueError("FFT length must be a positive power of two")
    out = list(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            out[i], out[j] = out[j], out[i]
    size = 2
    while size <= n:
        root = cmath.exp(-2j * math.pi / size)
        half = size // 2
        for start in range(0, n, size):
            factor = 1 + 0j
            for k in range(half):
                even = out[start + k]
                odd = factor * out[start + k + half]
                out[start + k] = even + odd
                out[start + k + half] = even - odd
                factor *= root
        size <<= 1
    return out


def analyze(samples: Sequence[float], sample_rate: int, *, peak_count: int = 5,
            frame_size: int | None = None) -> Analysis:
    """Analyze a real-valued sample frame using a Hann window and one-sided spectrum."""
    if sample_rate <= 0:
        raise ValueError("sample rate must be positive")
    if peak_count < 0:
        raise ValueError("peak count cannot be negative")
    if not samples:
        raise ValueError("at least one sample is required")
    if any(not math.isfinite(float(x)) for x in samples):
        raise ValueError("samples must be finite")
    n = frame_size or min(4096, 1 << (len(samples) - 1).bit_length())
    if n <= 0 or n & (n - 1) or n > 65536:
        raise ValueError("frame size must be a power of two no larger than 65536")
    if len(samples) > n:
        raise ValueError("frame size cannot be shorter than the sample sequence")
    padded = list(map(float, samples)) + [0.0] * (n - len(samples))
    windowed = [x * (0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)))
                for i, x in enumerate(padded)] if n > 1 else padded
    spectrum = fft(windowed)
    mags = [abs(spectrum[i]) for i in range(n // 2 + 1)]
    # Drop DC from pitch and centroid calculations: offset is not a pitched component.
    weighted = sum(i * sample_rate / n * mags[i] for i in range(1, len(mags)))
    total = sum(mags[1:])
    centroid = weighted / total if total else 0.0
    candidates = sorted(range(1, len(mags)), key=lambda i: (-mags[i], i))[:peak_count]
    peaks = [Peak(i * sample_rate / n, mags[i] * 2 / n) for i in candidates if mags[i] > 0]
    return Analysis(sample_rate, len(samples), math.sqrt(sum(float(x)**2 for x in samples) / len(samples)),
                    centroid, peaks[0].frequency_hz if peaks else None, peaks)


def read_wav(path: str | Path, *, max_samples: int = 10_000_000) -> tuple[list[float], int]:
    """Read bounded mono or multichannel PCM WAV and average channels to mono."""
    if max_samples < 0:
        raise ValueError("sample limit cannot be negative")
    with wave.open(str(path), "rb") as src:
        channels, width, rate, frames = src.getnchannels(), src.getsampwidth(), src.getframerate(), src.getnframes()
        if channels < 1 or width not in (1, 2, 3, 4) or rate <= 0:
            raise ValueError("unsupported WAV format")
        if frames > max_samples:
            raise ValueError(f"WAV exceeds sample limit ({max_samples})")
        raw = src.readframes(frames)
    stride = channels * width
    if len(raw) != frames * stride:
        raise ValueError("truncated WAV data")

    def decode(chunk: bytes) -> int:
        if width == 1:
            return chunk[0] - 128
        if width == 3:
            value = int.from_bytes(chunk, "little", signed=False)
            return value - (1 << 24) if value & (1 << 23) else value
        return int.from_bytes(chunk, "little", signed=True)

    scale = float(1 << (8 * width - 1))
    values = []
    for frame in range(frames):
        start = frame * stride
        values.append(sum(decode(raw[start + c*width:start + (c+1)*width]) for c in range(channels)) / channels / scale)
    return values, rate


def analyze_wav(path: str | Path, *, peak_count: int = 5, frame_size: int | None = None) -> Analysis:
    samples, rate = read_wav(path)
    size = frame_size or min(4096, 1 << (min(len(samples), 4096) - 1).bit_length()) if samples else frame_size
    frame = samples[:size] if size else samples
    return analyze(frame, rate, peak_count=peak_count, frame_size=size)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path, help="PCM WAV input")
    parser.add_argument("--peaks", type=int, default=5, help="number of spectral peaks (default: 5)")
    parser.add_argument("--frame-size", type=int, help="power-of-two analysis frame, up to 65536")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a text summary")
    args = parser.parse_args(argv)
    try:
        result = analyze_wav(args.wav, peak_count=args.peaks, frame_size=args.frame_size)
    except (OSError, wave.Error, ValueError) as exc:
        parser.error(str(exc))
    data = asdict(result)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Samples: {result.samples} at {result.sample_rate} Hz; RMS: {result.rms:.6f}")
        print(f"Spectral centroid: {result.spectral_centroid_hz:.2f} Hz")
        print(f"Dominant frequency: {result.dominant_frequency_hz if result.dominant_frequency_hz is not None else 'none'} Hz")
        for peak in result.peaks:
            print(f"  {peak.frequency_hz:9.2f} Hz  magnitude {peak.magnitude:.6f}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
