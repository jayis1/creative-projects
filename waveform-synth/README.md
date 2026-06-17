# 🎵 Waveform Synthesizer

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 258](https://img.shields.io/badge/tests-258%20passing-brightgreen.svg)](tests/)
[![Version: 4.0.0](https://img.shields.io/badge/version-4.0.0-orange.svg)](pyproject.toml)
[![CI](https://img.shields.io/badge/CI-github%20actions-blue.svg)](.github/workflows/waveform-synth-ci.yml)

> A comprehensive from-scratch digital audio synthesizer built in pure Python — no external audio libraries.

Generate waveforms, sculpt sounds with ADSR envelopes and effects chains, create FM synthesis patches, morph wavetables, build granular textures, shift pitch, stretch time, modulate with LFOs, import MIDI files, compose multi-track music, analyze audio signals, and export to WAV/MIDI — all from a single pip-installable package.

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
  - [LFO Modulation](#lfo-modulation-new-in-v40)
  - [Wavetable Synthesis](#wavetable-synthesis-new-in-v40)
  - [Noise Generators](#noise-generators-new-in-v40)
  - [Ring & Amplitude Modulation](#ring--amplitude-modulation-new-in-v40)
  - [Spectral Processing](#spectral-processing-new-in-v40)
  - [Granular Synthesis](#granular-synthesis-new-in-v40)
  - [MIDI Import](#midi-import-new-in-v40)
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
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

### Synthesis Engines
- **7 Waveform Types** — sine, square, sawtooth, triangle, pulse (variable duty cycle), white noise
- **Wavetable Synthesis** — multi-cycle waveform blending with linear/cubic interpolation, position morphing, built-in wavetables (sine-to-saw, classic analog), custom user-defined tables
- **FM Synthesis** — carrier/modulator pair with 5 built-in presets (bell, brass, woodwind, bass, e-piano)
- **Granular Synthesis** — grain-based texture generation with pitch spread, position spread, random panning, multiple window types, stereo output
- **Noise Generators** — 5 noise colors: white, pink (1/f), brown (1/f²), blue (+3dB/oct), violet (+6dB/oct), with seeded reproducibility

### Modulation
- **LFO** — low-frequency oscillator with 4 waveforms, tempo sync, amplitude modulation (tremolo), pitch modulation (vibrato)
- **Ring Modulation** — multiply carrier × modulator for metallic, inharmonic sounds
- **Amplitude Modulation** — classic AM with configurable depth and mix

### Effects (13 types)
- Gain, Distortion (tanh), Lowpass, Highpass, Delay, Flanger, Tremolo, Reverb (Schroeder), Compressor
- **Chorus** — multi-voice modulated delay for ensemble effects (new)
- **Bitcrusher** — bit depth and sample rate reduction for lo-fi sounds (new)
- **Echo** — pronounced delay with long feedback tail (new)

### Processing
- **Pitch Shifting** — phase vocoder-based, ±36 semitones, fractional shifts
- **Time Stretching** — phase vocoder, any stretch factor, pitch-preserving
- **DSP Utilities** — FFT (Cooley-Tukey), Butterworth filters (LP/HP/BP), windowing (Hann/Hamming/Blackman/rectangle), convolution, correlation, onset detection

### Audio I/O
- **WAV Export** — 8/16/24/32-bit, mono/stereo
- **WAV Import** — multi-bit-depth PCM reader
- **MIDI Export** — Standard MIDI File Format 0 with tempo & program change
- **MIDI Import** — read SMF Format 0 & 1, extract notes, tempo, program changes (new)
- **AIFF Import** — AIFF/AIFC file reader
- **Raw PCM** — headerless PCM read/write

### Composition & Analysis
- **Composition Engine** — multi-track sequencing with per-note ADSR and waveform selection
- **Audio Analysis** — RMS, peak, crest factor, ZCR, fundamental frequency (YIN algorithm), spectral analysis
- **Note/Scale/Chord Library** — 12 scale types, 10 chord types, MIDI note mapping
- **Configuration System** — JSON/TOML config files, 5 built-in presets, reproducible sound design
- **ASCII Visualization** — terminal waveform, frequency bars, and envelope display
- **CLI Interface** — 15 subcommands with full argument parsing

## Installation

### From Source (Recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/waveform-synth
pip install -e ".[dev]"
```

### Dependencies

- **Python 3.10+**
- **NumPy** (optional, for performance — falls back to pure Python)
- **pytest + pytest-cov** (optional, for development)

After installation, the `waveform-synth` command is available system-wide.

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

### Wavetable Synthesis (v4.0)

```python
from waveform_synth.wavetable import Wavetable, WavetableOscillator

# Built-in wavetable: morphs from sine to sawtooth
wt = Wavetable.sine_to_saw(num_frames=16, frame_size=2048)
osc = WavetableOscillator(wt, frequency=220.0, position=0.0)

# Morph through the wavetable over 2 seconds
n = int(44100 * 2.0)
position_sweep = [i / n for i in range(n)]  # 0.0 → 1.0
samples = osc.generate_with_modulation(2.0, position_modulation=position_sweep)
```

### LFO Modulation (v4.0)

```python
from waveform_synth.lfo import LFO

# Vibrato: 5 Hz pitch modulation
lfo = LFO(waveform=Waveform.SINE, rate=5.0, depth=0.03)
vibrato = lfo.apply_to_pitch(samples, base_freq=440.0)

# Tremolo: 6 Hz amplitude modulation
lfo = LFO(waveform=Waveform.SINE, rate=6.0, depth=0.7)
tremolo = lfo.apply_to_amplitude(samples)

# Tempo-synced LFO
lfo = LFO.synced(bpm=120, beats_per_cycle=1.0)  # 2 Hz
```

### Granular Synthesis (v4.0)

```python
from waveform_synth.granular import GranularSynth

source = Oscillator(Waveform.SINE, frequency=440.0).generate(0.5)
gran = GranularSynth(
    source=source,
    grain_size=0.03,
    density=30,
    pitch_spread=0.5,
    position_spread=0.8,
    seed=42,
)
texture = gran.generate(2.0)
```

### CLI

```bash
# Generate a sine wave
waveform-synth generate --waveform sine --frequency 440 --duration 2 --output out.wav

# FM synthesis with a preset
waveform-synth fm --preset bellish --duration 2 --output bell.wav

# Generate a chord
waveform-synth chord --root C --chord major --duration 2 --output chord.wav

# Generate colored noise
waveform-synth noise --color pink --duration 3 --output noise.wav

# Wavetable synthesis
waveform-synth wavetable --table classic_analog --frequency 220 --duration 2 --output wt.wav

# Pitch shift a WAV file
waveform-synth pitchshift --input input.wav --semitones 7 --output shifted.wav

# Time stretch a WAV file
waveform-synth timestretch --input input.wav --factor 1.5 --output stretched.wav

# Granular synthesis from a source WAV
waveform-synth granular --input source.wav --duration 5 --grain-size 0.03 --output granular.wav

# Ring modulation
waveform-synth ringmod --input input.wav --modulator-freq 35 --output ring.wav

# Import and analyze a MIDI file
waveform-synth midi-import --input song.mid --output rendered.wav

# Analyze a WAV file
waveform-synth analyze --input out.wav

# Use a built-in preset
waveform-synth preset --name ambient_pad --output pad.wav

# Generate from a config file
waveform-synth config --file my_sound.json --output output.wav
```

## CLI Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `generate` | Generate a single waveform | `--waveform`, `--frequency`, `--duration`, `--output`, `--envelope`, `--effects`, `--visualize`, `--analyze` |
| `fm` | FM synthesis | `--carrier`, `--modulator`, `--index`, `--preset`, `--output` |
| `scale` | Generate a musical scale | `--root`, `--scale`, `--octave`, `--note-duration`, `--output` |
| `chord` | Generate a chord | `--root`, `--chord`, `--octave`, `--duration`, `--output` |
| `analyze` | Analyze a WAV file | `--input`, `--verbose-analysis` |
| `visualize` | Visualize a WAV file | `--input`, `--width`, `--height` |
| `preset` | Generate from built-in preset | `--name`, `--frequency`, `--duration`, `--output` |
| `config` | Generate from config file | `--file`, `--output`, `--visualize` |
| `wavetable` | Wavetable synthesis | `--table`, `--frequency`, `--position`, `--interpolation`, `--output` |
| `noise` | Generate colored noise | `--color`, `--duration`, `--amplitude`, `--seed`, `--output` |
| `ringmod` | Ring modulation | `--input`, `--modulator-freq`, `--mix`, `--output` |
| `pitchshift` | Pitch shift a WAV | `--input`, `--semitones`, `--output` |
| `timestretch` | Time-stretch a WAV | `--input`, `--factor`, `--output` |
| `granular` | Granular synthesis | `--input`, `--duration`, `--grain-size`, `--density`, `--pitch-spread`, `--output` |
| `midi-import` | Import & analyze MIDI | `--input`, `--output`, `--waveform`, `--visualize` |

## Architecture

```
waveform_synth/
├── __init__.py          # Package exports, version info
├── core.py              # Oscillator, Waveform enum, normalize, mix, crossfade, resample, clip
├── envelope.py          # ADSR envelope generation (linear & exponential curves)
├── fm.py                # FM synthesis engine with 5 presets
├── effects.py           # EffectsChain with 13 effect types
├── lfo.py               # LFO modulation (vibrato, tremolo, tempo sync) ★
├── wavetable.py         # Wavetable synthesis (morphing, interpolation) ★
├── noise.py             # Multi-color noise generators (5 colors) ★
├── modulation.py        # Ring & amplitude modulation ★
├── spectral.py          # Pitch shifting & time stretching (phase vocoder) ★
├── granular.py          # Granular synthesis (grain-based textures) ★
├── midi_reader.py       # Standard MIDI File import (Format 0 & 1) ★
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
└── cli.py               # Command-line interface (15 subcommands)

tests/
├── conftest.py              # Pytest configuration
├── test_waveform.py         # Core test suite
├── test_dsp.py              # DSP module tests
├── test_midi.py            # MIDI module tests
├── test_config.py          # Config module tests
├── test_audio_io.py        # Audio I/O module tests
└── test_new_features.py    # New v4.0 features tests ★

examples/
├── quickstart.py           # 10 beginner examples
├── advanced.py             # 10 advanced examples (DSP, MIDI, config)
└── advanced_v4.py          # 12 v4.0 feature examples ★

★ = New in v4.0
```

### Signal Flow

```
                    ┌──────────────────────────────────────────────────┐
                    │                                                  │
Oscillator ────────►│  ┌─────────┐  ┌──────────┐  ┌────────────┐       │
                    │  │   ADSR  │─►│ Effects  │─►│  Stereo    │───► WAV
Wavetable ─────────►│  │Envelope │  │  Chain    │  │ Processing │───► MIDI
                    │  └─────────┘  └──────────┘  └────────────┘       │
FM Synth ──────────►│         ▲          ▲                              │
                    │         │          │                              │
Granular ──────────►│    LFO Modulation  │                              │
                    │    (vibrato/       │                              │
Noise Gen ─────────►│     tremolo)       │                              │
                    │                    │                              │
                    │            Spectral Processing                    │
                    │            (pitch shift, time stretch)            │
                    └──────────────────────────────────────────────────┘
                              │
                    MIDI Import ──► Composition Engine ──► WAV/MIDI Export
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
chain.add(Effect(EffectType.CHORUS, rate=0.5, depth=0.003, voices=4))  # v4.0
chain.add(Effect(EffectType.BITCRUSHER, bits=8, downsample=2))         # v4.0
chain.add(Effect(EffectType.ECHO, time=0.15, feedback=0.4, mix=0.5))  # v4.0
chain.add(Effect(EffectType.REVERB, room_size=0.6, damping=0.4, wet=0.25))
chain.add(Effect(EffectType.COMPRESSOR, threshold=0.5, ratio=4.0))
processed = chain.process(samples)
```

### LFO Modulation (New in v4.0)

```python
from waveform_synth.lfo import LFO

# Create an LFO
lfo = LFO(waveform=Waveform.SINE, rate=5.0, depth=0.5)

# Apply vibrato (pitch modulation)
vibrato = lfo.apply_to_pitch(samples, base_freq=440.0)

# Apply tremolo (amplitude modulation)
tremolo = lfo.apply_to_amplitude(samples)

# Tempo-synced LFO (1 cycle per beat at 120 BPM)
lfo = LFO.synced(bpm=120, beats_per_cycle=1.0)

# Generate raw LFO values
lfo_values = lfo.generate(2.0)
modulation = lfo.generate_modulation(2.0)  # depth-scaled
```

### Wavetable Synthesis (New in v4.0)

```python
from waveform_synth.wavetable import Wavetable, WavetableOscillator

# Built-in wavetables
wt = Wavetable.sine_to_saw(num_frames=16, frame_size=2048)  # Morphs sine→saw
wt = Wavetable.classic_analog(frame_size=2048)              # Sine, tri, saw, square

# Custom wavetable from waveforms
wt = Wavetable.from_waveforms([Waveform.SINE, Waveform.SAWTOOTH], frame_size=512)

# Oscillator with position morphing
osc = WavetableOscillator(wt, frequency=440.0, position=0.5, interpolation="cubic")
samples = osc.generate(2.0)

# Position modulation (e.g. via LFO)
lfo = LFO(waveform=Waveform.TRIANGLE, rate=0.5, depth=0.5)
pos_mod = [0.5 + 0.5 * lfo.value_at(i / 44100) for i in range(88200)]
samples = osc.generate_with_modulation(2.0, position_modulation=pos_mod)
```

### Noise Generators (New in v4.0)

```python
from waveform_synth.noise import NoiseColor, NoiseGenerator

# White noise
ng = NoiseGenerator(color=NoiseColor.WHITE, seed=42)
white = ng.generate(2.0)

# Pink noise (1/f spectrum — equal energy per octave)
ng = NoiseGenerator(color=NoiseColor.PINK, seed=42)
pink = ng.generate(2.0)

# Brown noise (1/f² — low rumble)
ng = NoiseGenerator(color=NoiseColor.BROWN, seed=42)
brown = ng.generate(2.0)

# Blue noise (+3 dB/octave — inverted pink)
ng = NoiseGenerator(color=NoiseColor.BLUE, seed=42)
blue = ng.generate(2.0)

# Violet noise (+6 dB/octave — differentiated white)
ng = NoiseGenerator(color=NoiseColor.VIOLET, seed=42)
violet = ng.generate(2.0)
```

### Ring & Amplitude Modulation (New in v4.0)

```python
from waveform_synth.modulation import ring_modulate, amplitude_modulate, RingModulator

# Ring modulation: output = carrier × modulator
carrier = Oscillator(Waveform.SINE, frequency=440.0).generate(1.0)
modulator = Oscillator(Waveform.SINE, frequency=35.0).generate(1.0)
ring = ring_modulate(carrier, modulator, mix=1.0)

# Amplitude modulation: output = carrier × (1 + depth × modulator)
am = amplitude_modulate(carrier, modulator, mix=1.0, modulator_depth=0.5)

# RingModulator class
rm = RingModulator(modulator_freq=30.0, mix=1.0)
result = rm.process(carrier)
```

### Spectral Processing (New in v4.0)

```python
from waveform_synth.spectral import pitch_shift, time_stretch

# Pitch shift by +7 semitones (a perfect fifth)
osc = Oscillator(Waveform.SINE, frequency=440.0)
samples = osc.generate(1.0)
shifted = pitch_shift(samples[:8192], semitones=7.0, fft_size=2048, hop_size=512)

# Time stretch by 1.5x (slower, same pitch)
stretched = time_stretch(samples[:8192], stretch_factor=1.5, fft_size=2048, hop_size=512)
```

### Granular Synthesis (New in v4.0)

```python
from waveform_synth.granular import GranularSynth

source = Oscillator(Waveform.SINE, frequency=440.0).generate(0.5)
gran = GranularSynth(
    source=source,
    grain_size=0.03,        # 30ms grains
    density=30,              # 30 grains per second
    pitch_spread=0.5,       # ±0.5 octave randomization
    position_spread=0.8,    # randomize read position
    random_pan=True,        # random stereo placement
    window_type="hann",     # grain envelope
    seed=42,                # reproducible
)
texture = gran.generate(3.0)

# Stereo granular output
left, right = gran.generate_stereo(3.0)
```

### MIDI Import (New in v4.0)

```python
from waveform_synth.midi_reader import read_midi_file

# Read a Standard MIDI File
midi = read_midi_file("song.mid")

print(f"Format: {midi.format}")
print(f"Tracks: {midi.num_tracks}")
print(f"Duration: {midi.duration:.2f}s")
print(f"Notes: {len(midi.notes)}")

for note in midi.notes:
    print(f"  {note.note_name} at {note.start_time:.2f}s, "
          f"duration={note.duration:.2f}s, velocity={note.velocity}")

# Filter notes by time range or channel
first_bar = midi.get_notes_in_range(0.0, 1.0)
channel_0 = midi.get_notes_on_channel(0)
```

### Stereo Processing

```python
from waveform_synth.stereo import mono_to_stereo, stereo_to_mono, StereoWidener

# Panning
left, right = mono_to_stereo(samples, pan=0.3)  # -1=left, 0=center, 1=right

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
filtered = bandpass_filter(samples, low_cutoff=500, high_cutoff=2000, sample_rate=44100)
```

### Audio I/O

```python
from waveform_synth.audio_io import read_aiff, write_raw_pcm, detect_audio_format

samples, sample_rate = read_aiff("input.aiff")
write_raw_pcm("output.pcm", samples, bits_per_sample=16)
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
config = get_preset('harsh_lead')      # Distorted sawtooth lead
config = get_preset('deep_bass')       # Low sub-bass

# Custom configuration
config = SynthConfig({
    'waveform': 'triangle',
    'frequency': 330.0,
    'duration': 3.0,
    'effects': [
        {'type': 'chorus', 'rate': 0.5, 'depth': 0.003, 'voices': 4},  # v4.0
        {'type': 'reverb', 'room_size': 0.8, 'damping': 0.3, 'wet': 0.35},
    ],
})
config.to_json("my_sound.json")
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
from waveform_synth.visualize import ascii_waveform, ascii_frequency_bars, ascii_envelope

print(ascii_waveform(samples, width=80, height=20, title="440Hz Sine"))
print(ascii_frequency_bars(samples, num_bars=32, title="Spectrum"))
print(ascii_envelope(env.generate(0.5), title="ADSR"))
```

## Examples

See the `examples/` directory for complete scripts:

- **`quickstart.py`** — 10 beginner examples covering oscillators, envelopes, FM, effects, scales, chords, stereo, analysis, and crossfading
- **`advanced.py`** — 10 advanced examples covering DSP utilities, FFT, filters, MIDI export, and configuration system
- **`advanced_v4.py`** — 12 examples of new v4.0 features: LFO, wavetable, noise, ring mod, pitch shift, time stretch, granular, MIDI import, chorus, bitcrusher, echo, and a full pipeline ★

## Testing

```bash
# Run all 258 tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=waveform_synth

# Run specific test modules
python -m pytest tests/test_new_features.py -v   # v4.0 feature tests
python -m pytest tests/test_dsp.py -v
python -m pytest tests/test_midi.py -v
python -m pytest tests/test_config.py -v
```

### Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| Core (oscillators, utilities) | 49 | Full |
| ADSR envelopes | 8 | Full |
| FM synthesis | 3 | Full |
| Effects (13 types) | 22 | Full |
| LFO modulation ★ | 14 | Full |
| Wavetable synthesis ★ | 17 | Full |
| Noise generators ★ | 11 | Full |
| Ring/AM modulation ★ | 14 | Full |
| Spectral processing ★ | 11 | Full |
| Granular synthesis ★ | 11 | Full |
| MIDI import ★ | 10 | Full |
| DSP utilities | 25 | Full |
| MIDI export | 16 | Full |
| Config system | 15 | Full |
| Audio I/O | 9 | Full |
| **Total** | **258** | **Full** |

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
| 9 | MIDI writer missing header length field ★ | Added 4-byte header length (6) to MThd chunk | `test_midi_round_trip` |

★ = Fixed in v4.0

## Changelog

### v4.0.0 — Major Feature Release

**New Modules (6):**
- `lfo.py` — LFO modulation (vibrato, tremolo, tempo sync, 4 waveforms)
- `wavetable.py` — Wavetable synthesis (morphing, linear/cubic interpolation, 3 built-in tables)
- `noise.py` — Multi-color noise generators (white, pink, brown, blue, violet)
- `modulation.py` — Ring & amplitude modulation
- `spectral.py` — Pitch shifting & time stretching (phase vocoder)
- `granular.py` — Granular synthesis (grain-based textures, stereo, pitch spread)
- `midi_reader.py` — Standard MIDI File import (Format 0 & 1)

**New Effects (3):**
- Chorus — multi-voice modulated delay
- Bitcrusher — bit depth & sample rate reduction
- Echo — pronounced delay with long feedback tail

**New CLI Subcommands (7):**
- `wavetable`, `noise`, `ringmod`, `pitchshift`, `timestretch`, `granular`, `midi-import`

**Other Improvements:**
- Fixed MIDI writer missing header length field (bug #9)
- Added 98 new tests (258 total, all passing)
- Added GitHub Actions CI workflow (Python 3.10–3.13)
- Added `examples/advanced_v4.py` with 12 feature demonstrations
- Updated all documentation

### v3.0.0 — Architecture & Quality Release

- Split monolithic code into 15 modules
- Added stereo processing, audio analysis, DSP utilities, MIDI export
- Added configuration system with JSON/TOML support
- Added multi-format audio I/O (AIFF, raw PCM)
- Added CLI with 8 subcommands
- Bug hunt: fixed 8 bugs (YIN pitch detection, reverb damping, compressor, etc.)

### v2.0.0 — Initial Enhancement

- Added pulse oscillator, Schroeder reverb, dynamic range compressor
- Added crossfade, resample, clip, dB conversion
- Added multi-bit-depth WAV support
- Added WavReader for import

### v1.0.0 — Initial Release

- 7 waveform types, ADSR envelopes, FM synthesis with 5 presets
- 7 effects, WAV export, ASCII visualization
- Note/scale/chord library, composition engine

## Roadmap

- [ ] **Ogg/Vorbis export** — Add OGG container format support
- [ ] **Real-time audio playback** — PortAudio or sounddevice integration
- [ ] **Sampler** — Load and trigger audio samples at different pitches
- [ ] **Vorbis/FLAC import** — Decode compressed audio formats
- [ ] **Web UI** — Browser-based waveform editor with WebAudio playback
- [ ] **Plugin API** — Extensible effect and oscillator plugin system
- [ ] **Multi-channel output** — Support for 5.1, 7.1 surround configurations
- [ ] **Phase vocoder improvements** — higher-quality pitch shifting with formant preservation
- [ ] **MIDI Format 2 support** — Read multi-track MIDI with song structure
- [x] ~~**LFO modulation**~~ ✓ Done in v4.0
- [x] ~~**Spectral processing**~~ ✓ Done in v4.0
- [x] ~~**MIDI import**~~ ✓ Done in v4.0

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

### Adding New Features

**New Waveform Types:** Add the enum value to `Waveform` in `core.py`, then implement in `Oscillator._base_wave()`.

**New Effects:**
1. Add the enum value to `EffectType` in `effects.py`
2. Add default parameters in `Effect.__init__`
3. Implement `_apply_<effect>` method
4. Add to the `process()` dispatch
5. Add tests in `tests/test_new_features.py`

**New Synthesis Modules:**
1. Create a new module file in `waveform_synth/`
2. Export from `__init__.py`
3. Add CLI subcommand in `cli.py`
4. Add comprehensive tests
5. Add example in `examples/`

## License

[MIT License](LICENSE) — free for personal and commercial use.