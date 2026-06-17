# 🎵 Waveform Synthesizer

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 160](https://img.shields.io/badge/tests-160%20passing-brightgreen.svg)](tests/)
[![Version: 3.0.0](https://img.shields.io/badge/version-3.0.0-orange.svg)](pyproject.toml)

A comprehensive from-scratch digital audio synthesizer built in pure Python with NumPy. Generate waveforms, sculpt sounds with ADSR envelopes and effects chains, create FM synthesis patches, compose multi-track music, analyze audio signals, and export to WAV/MIDI — all without external audio libraries.

```
                         440Hz Sine                         
┌────────────────────────────────────────────────────────────┐
│▓   █   █   ▓  ▓   █   █   █  ▓   █   █   ▓  ▓   █   █   █  │
│██          █  █▓  ▓       ▓  ██          █  █▓  ▓       ▓  │
│ ▓   ▓     █    █         █    ▓   ▓     █    █         █   │
│     █ █            █ █            █ █            █ █       │
│   ▓   ▓ █        ▓   ▓ █        ▓   ▓ █        ▓   ▓ █     │
│   █     ▓   ▓    █     ▓   ▓    █     ▓   ▓    █     ▓   ▓ │
│  ▓       ▓  ██  ▓       ▓  ██  ▓       ▓  ██  ▓       ▓  ██│
│  █   █   █      █   █   █      █   █   █      █   █   █    │
└────────────────────────────────────────────────────────────┘
                                                         +1.00
                                                         -1.00
```

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Architecture](#architecture)
- [Module Reference](#module-reference)
  - [Core — Oscillators & Signals](#core--oscillators--signals)
  - [ADSR Envelopes](#adsr-envelopes)
  - [FM Synthesis](#fm-synthesis)
  - [Effects Chain](#effects-chain)
  - [Stereo Processing](#stereo-processing)
  - [Audio Analysis](#audio-analysis)
  - [DSP Utilities](#dsp-utilities)
  - [Audio I/O](#audio-io)
  - [MIDI Export](#midi-export)
  - [Configuration System](#configuration-system)
  - [Composition Engine](#composition-engine)
  - [Visualization](#visualization)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

- **7 Waveform Types** — sine, square, sawtooth, triangle, pulse (variable duty cycle), white noise
- **ADSR Envelopes** — attack, decay, sustain, release with linear & exponential curves
- **FM Synthesis** — carrier/modulator pair with 5 built-in presets (bell, brass, woodwind, bass, e-piano)
- **Effects Chain** — 10 effects: gain, distortion, lowpass/highpass filter, delay, flanger, tremolo, reverb (Schroeder), compressor, echo
- **Stereo Processing** — panning, stereo widening, mid/side processing, stereo WAV export
- **Audio Analysis** — RMS, peak, crest factor, ZCR, fundamental frequency (YIN algorithm), spectral analysis
- **DSP Utilities** — FFT, Butterworth filters (LP/HP/BP), windowing (Hann/Hamming/Blackman), convolution, correlation, onset detection
- **Multi-format Export** — WAV (8/16/24/32-bit, mono/stereo), MIDI (Format 0), AIFF import, raw PCM
- **Configuration System** — JSON/TOML config files, 5 built-in presets, reproducible sound design
- **Composition Engine** — multi-track sequencing with per-note ADSR and waveform selection
- **Note/Scale/Chord Library** — 12 scale types, 8 chord types, MIDI note mapping
- **ASCII Visualization** — terminal waveform & envelope display
- **CLI Interface** — full command-line access with subcommands: generate, fm, scale, chord, analyze, visualize, preset, config

## Installation

### From Source

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/waveform-synth
pip install -e ".[dev]"
```

### Dependencies

- **Python 3.10+**
- **NumPy** (required, core signal generation)
- **Click** (optional, for CLI — included with install)
- **pytest + pytest-cov** (optional, for development)

## Quick Start

### Python API

```python
from waveform_synth.core import Oscillator, Waveform, normalize
from waveform_synth.envelope import ADSR
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.export import WavWriter

# Generate a sine wave
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.8)
samples = osc.generate(2.0)  # 2 seconds

# Apply ADSR envelope
env = ADSR(attack=0.05, decay=0.1, sustain=0.7, release=0.3)
shaped = env.apply(samples, note_duration=0.5)

# Add effects
chain = EffectsChain()
chain.add(Effect(EffectType.REVERB, room_size=0.6, damping=0.4, wet=0.25))
chain.add(Effect(EffectType.COMPRESSOR, threshold=0.5, ratio=4.0))
processed = chain.process(shaped)

# Normalize and export
processed = normalize(processed)
WavWriter().write("output.wav", processed)
```

### CLI

```bash
# Generate a sine wave
waveform-synth generate --waveform sine --frequency 440 --duration 2 --output out.wav

# FM synthesis with a preset
waveform-synth fm --preset bellish --duration 2 --output bell.wav

# Generate a chord
waveform-synth chord --root C --chord major --duration 2 --output chord.wav

# Generate a scale
waveform-synth scale --root C --scale major --output scale.wav

# Analyze a WAV file
waveform-synth analyze --input out.wav

# Use a built-in preset
waveform-synth preset --name ambient_pad --output pad.wav

# Generate from a config file
waveform-synth config --file my_sound.json --output output.wav
```

## Architecture

```
waveform_synth/
├── __init__.py          # Package exports, version info
├── core.py              # Oscillator, Waveform enum, normalize, mix, crossfade, resample, clip
├── envelope.py          # ADSR envelope generation (linear & exponential curves)
├── fm.py                # FM synthesis engine with 5 presets
├── effects.py           # EffectsChain with 10 effect types
├── stereo.py            # Stereo processing: panning, widening, mid/side
├── analysis.py          # Audio analysis: RMS, peak, ZCR, YIN pitch detection, spectrum
├── dsp.py               # DSP primitives: FFT, filters, windows, convolution, correlation
├── audio_io.py          # Multi-format audio I/O: AIFF, raw PCM, format detection
├── midi.py              # MIDI Format 0 export with tempo & program change
├── config.py            # Configuration system: JSON/TOML, 5 presets
├── composition.py        # Multi-track composition engine
├── notes.py             # Note/frequency mapping, scales, chords
├── visualize.py         # ASCII waveform & envelope visualization
├── export.py            # WAV export (8/16/24/32-bit, mono/stereo)
└── cli.py               # Command-line interface (8 subcommands)

tests/
├── conftest.py          # Pytest configuration
├── test_waveform.py     # Core test suite (95 tests)
├── test_dsp.py          # DSP module tests
├── test_midi.py         # MIDI module tests
├── test_config.py       # Config module tests
└── test_audio_io.py     # Audio I/O module tests

examples/
├── quickstart.py        # 10 beginner examples
└── advanced.py          # 10 advanced examples (DSP, MIDI, config)
```

### Signal Flow

```
Oscillator → ADSR Envelope → Effects Chain → Stereo Processing → Normalization → WAV Export
     │                                                              │
     └── FM Synthesis (carrier × modulator)                        └── MIDI Export
```

## Module Reference

### Core — Oscillators & Signals

```python
from waveform_synth.core import Oscillator, Waveform, PulseOscillator, normalize, mix, crossfade

# Basic oscillators
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.8)
osc = Oscillator(Waveform.SAWTOOTH, frequency=220.0, harmonics=[(2, 0.5), (3, 0.3)])
samples = osc.generate(duration=2.0)

# Pulse oscillator (variable duty cycle)
pulse = PulseOscillator(frequency=440.0, duty_cycle=0.25)
samples = pulse.generate(1.0)

# Signal mixing
mixed = mix([signal1, signal2, signal3])

# Crossfading between signals
xf = crossfade(signal1, signal2, overlap_samples=4410)
```

### ADSR Envelopes

```python
from waveform_synth.envelope import ADSR

# Linear curve (default)
env = ADSR(attack=0.01, decay=0.1, sustain=0.7, release=0.3)
shaped = env.apply(samples, note_duration=0.5)

# Exponential curve
env = ADSR(attack=0.01, decay=0.1, sustain=0.7, release=0.3, curve="exponential")
```

### FM Synthesis

```python
from waveform_synth.fm import FMSynth, FMPreset

# Manual FM
synth = FMSynth(carrier_freq=440, modulator_freq=880, modulation_index=2.0)
samples = synth.generate(2.0)

# Presets
synth = FMPreset.bellish(carrier_freq=440)    # Bell-like tones
synth = FMPreset.brassish(carrier_freq=220)   # Brass-like tones
synth = FMPreset.e_piano(carrier_freq=440)    # Electric piano
```

### Effects Chain

```python
from waveform_synth.effects import EffectsChain, Effect, EffectType

chain = EffectsChain()
chain.add(Effect(EffectType.DISTORTION, drive=2.5))
chain.add(Effect(EffectType.LOWPASS, cutoff=3000.0))
chain.add(Effect(EffectType.REVERB, room_size=0.6, damping=0.4, wet=0.25))
chain.add(Effect(EffectType.COMPRESSOR, threshold=0.5, ratio=4.0))
chain.add(Effect(EffectType.DELAY, time=0.3, feedback=0.3, mix=0.5))
processed = chain.process(samples)
```

### Stereo Processing

```python
from waveform_synth.stereo import mono_to_stereo, stereo_to_mono, StereoWidener

# Panning
left, right = mono_to_stereo(samples, pan=0.3)  # 0=left, 0.5=center, 1=right

# Widening
widener = StereoWidener(width=1.5)
wide_left, wide_right = widener.process(left, right)

# Export stereo
writer.write_stereo("stereo.wav", wide_left, wide_right)
```

### Audio Analysis

```python
from waveform_synth.analysis import rms, peak_level, compute_stats, fundamental_frequency

stats = compute_stats(samples)
# {'num_samples': 88200, 'rms': 0.5, 'peak': 1.0, 'crest_factor': 2.0,
#  'zero_crossing_rate': 0.1, 'mean': 0.0, 'variance': 0.25, 'min': -1.0, 'max': 1.0}

freq = fundamental_frequency(samples)  # Uses YIN algorithm
```

### DSP Utilities

```python
from waveform_synth.dsp import (
    fft, fft_magnitude,
    lowpass_filter, highpass_filter, bandpass_filter,
    window_hann, window_hamming, window_blackman,
    convolve, autocorrelate, amplitude_envelope, onset_detection,
)

# FFT analysis
spectrum = fft_magnitude(samples[:8192], sample_rate=44100)

# Butterworth filters
filtered = lowpass_filter(samples, cutoff=500, sample_rate=44100)
filtered = highpass_filter(samples, cutoff=2000, sample_rate=44100)
filtered = bandpass_filter(samples, low_cutoff=500, high_cutoff=2000, sample_rate=44100)

# Windowing
window = window_hann(1024)
window = window_blackman(512)
```

### Audio I/O

```python
from waveform_synth.audio_io import read_aiff, write_raw_pcm, detect_audio_format

# Read AIFF files
samples, sample_rate = read_aiff("input.aiff")

# Write raw PCM
write_raw_pcm("output.pcm", samples, bits_per_sample=16)

# Detect file format
fmt = detect_audio_format("file.wav")  # 'wav', 'aiff', or 'unknown'
```

### MIDI Export

```python
from waveform_synth.midi import MidiWriter

midi = MidiWriter(tempo_bpm=120, channel=0, program=0)
midi.add_note_by_name('C4', duration_beats=1.0, velocity=100)
midi.add_note_by_name('E4', duration_beats=1.0, velocity=90)
midi.add_note_by_name('G4', duration_beats=1.0, velocity=80)
midi.write("melody.mid")
```

### Configuration System

```python
from waveform_synth.config import SynthConfig, get_preset

# Built-in presets
config = get_preset('ambient_pad')    # Long sine pad with reverb
config = get_preset('harsh_lead')    # Distorted sawtooth lead
config = get_preset('deep_bass')     # Low sub-bass

# Custom configuration
config = SynthConfig({
    'waveform': 'triangle',
    'frequency': 330.0,
    'duration': 3.0,
    'attack': 0.1, 'decay': 0.2, 'sustain': 0.6, 'release': 0.8,
    'effects': [
        {'type': 'reverb', 'room_size': 0.8, 'damping': 0.3, 'wet': 0.35},
    ],
})
config.to_json("my_sound.json")  # Save config

# Load from file
loaded = SynthConfig.from_file("my_sound.json")
```

### Composition Engine

```python
from waveform_synth.composition import Track, Composition

comp = Composition(title="My Song")
track = Track(waveform=Waveform.SINE, envelope=env)
track.add_note('C4', duration=0.5)
track.add_note('E4', duration=0.5)
track.add_note('G4', duration=1.0)
comp.add_track(track)
comp.export_wav("song.wav")
```

### Visualization

```python
from waveform_synth.visualize import ascii_waveform

print(ascii_waveform(samples, width=80, height=20, title="440Hz Sine"))
```

## Examples

See the `examples/` directory for complete scripts:

- **`quickstart.py`** — 10 beginner examples covering oscillators, envelopes, FM, effects, scales, chords, stereo, analysis, and crossfading
- **`advanced.py`** — 10 advanced examples covering DSP utilities, FFT, filters, MIDI export, and configuration system

## Testing

```bash
# Run all 160 tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=waveform_synth

# Run specific test modules
python -m pytest tests/test_dsp.py -v
python -m pytest tests/test_midi.py -v
python -m pytest tests/test_config.py -v
```

## Known Issues (Resolved)

| # | Issue | Fix | Test |
|---|-------|-----|------|
| 1 | Fundamental frequency returned wrong octave (110Hz for 440Hz input) | Replaced broken autocorrelation with YIN algorithm | `test_fundamental_frequency` |
| 2 | `Waveform.PULSE` and `WHITE_NOISE` crashed Oscillator | Added handlers in `_base_wave()` | `test_pulse_waveform_in_oscillator`, `test_white_noise_waveform_in_oscillator` |
| 3 | Reverb damping was dead code (`if False else`) | Changed to proper one-pole low-pass filter on feedback | `test_reverb_damping_is_applied` |
| 4 | Compressor amplified instead of compressing | Sign error: `(1 - 1/ratio)` → `(1/ratio - 1)` | `test_compressor_envelope_follows_signal` |
| 5 | Compressor envelope follower had duplicated logic | Redundant ternary was immediately overwritten | Code review |
| 6 | Spectral analysis had wrong frequency labels | DFT computed on truncated samples but used full length for freq calc | `test_spectral_analysis_frequency_labels` |
| 7 | `read_aiff` had unbound variable `num_frames` | Initialized to 0 before conditional | `test_audio_io` |
| 8 | `get_audio_info` had unbound variables for AIFF | Initialized before conditional branches | `test_audio_io` |

## Roadmap

- [ ] **Ogg/Vorbis export** — Add OGG container format support
- [ ] **Real-time audio playback** — PortAudio or sounddevice integration
- [ ] **LFO modulation** — Low-frequency oscillator for vibrato, tremolo automation
- [ ] **Sampler** — Load and trigger audio samples at different pitches
- [ ] **Spectral processing** — FFT-based effects (pitch shifting, time stretching)
- [ ] **Vorbis/FLAC import** — Decode compressed audio formats
- [ ] **MIDI import** — Read Standard MIDI Files
- [ ] **Web UI** — Browser-based waveform editor with WebAudio playback
- [ ] **Plugin API** — Extensible effect and oscillator plugin system
- [ ] **Multi-channel output** — Support for 5.1, 7.1 surround configurations

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

## License

[MIT License](LICENSE) — free for personal and commercial use.