# Spectral Music Lab

A dependency-free Python toolkit for inspecting PCM audio spectra. It implements a radix-2 Cooley–Tukey FFT, applies a Hann window, and reports RMS level, spectral centroid, and strongest frequency bins.

## How it works

The analyzer converts multichannel integer WAV frames to mono, normalizes supported 8-, 16-, 24-, and 32-bit PCM, windows a bounded frame to reduce leakage, zero-pads when needed, and computes a one-sided spectrum. DC is excluded from pitch and centroid calculations. A radix-2 transform runs in O(N log N).

## Usage

Requires Python 3.10+; no third-party dependencies.

```sh
python3 main.py recording.wav
python3 main.py recording.wav --peaks 10 --json
python3 main.py recording.wav --frame-size 2048
python3 main.py recording.wav --spectrogram-csv features.csv --frame-size 1024 --hop-size 256
python3 -m unittest -v
```

The default analyzes up to the first 4096 samples, selected as a power-of-two frame; `--frame-size` sets a power-of-two window up to 65536. WAV reading is capped at ten million frames. Frequency resolution is sample_rate / frame_size, and peaks are FFT bins (not interpolated pitch estimates). This is an educational offline analyzer, not real-time production DSP.

## Frame-by-frame CSV analysis

Use `--spectrogram-csv features.csv` to write time-indexed RMS, spectral centroid, and dominant-bin features for overlapping frames. The default frame is 1024 samples with a half-frame hop; `--frame-size` and `--hop-size` control resolution and overlap. A final short frame is zero-padded for FFT analysis, while its reported sample count and RMS use only real samples. CSV output is suitable for plotting or downstream analysis without extra dependencies.

## Enhancements

Added overlapping, time-indexed CSV spectrogram export with configurable hop size. Also includes bounded WAV decoding for four PCM widths, multichannel-to-mono conversion, configurable frames and peak count, JSON output, invalid-input checks, and regression tests.

## Known Issues (Resolved)

- Empty WAV input previously proceeded toward an invalid zero-length transform; it now raises a clear `ValueError`, covered by a regression test.
- Negative sample limits were not rejected; they now fail explicitly. (Verified by inspection of the input validation path.)

## Remaining limitations

Only uncompressed PCM WAV is supported; compressed WAV codecs and other containers are not. Peak ranking can report neighboring bins around one tone, and no sub-bin frequency interpolation is applied.
