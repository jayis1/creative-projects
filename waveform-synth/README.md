# Waveform Synthesizer

A from-scratch digital audio synthesizer with waveform generation, ADSR envelopes, FM synthesis, effects processing, WAV export, stereo processing, audio analysis, and ASCII visualization.

## Features

- **7 Waveform Types**: Sine, square, sawtooth, triangle, noise, pulse (variable duty cycle), white noise
- **Pulse Oscillator**: Dedicated pulse wave with adjustable duty cycle (0%–100%)
- **Additive Harmonics**: Layer harmonics onto any waveform for rich timbral content
- **ADSR Envelopes**: Attack-Decay-Sustain-Release envelope shaping with linear or exponential curves
- **FM Synthesis**: John Chowning-style frequency modulation with carrier and modulator oscillators
- **5 FM Presets**: Bell, brass, woodwind, bass, and electric piano
- **9 Audio Effects**: Gain, delay, flanger, distortion, low-pass, high-pass, tremolo, **reverb** (Schroeder), **compressor** (dynamic range)
- **Effects Chain**: Chain any number of effects in sequence
- **Stereo Processing**: Mono-to-stereo panning, stereo-to-mono, stereo widening (mid-side)
- **Audio Analysis**: RMS, peak level, crest factor, zero-crossing rate, fundamental frequency estimation, spectral analysis, peak detection, comprehensive stats
- **Musical Scales**: 12 scale types (major, natural/harmonic/melodic minor, dorian, phrygian, lydian, mixolydian, pentatonic, blues, chromatic, whole tone)
- **Chords**: 10 chord types (major, minor, dim, aug, dom7, maj7, min7, sus2, sus4, add9)
- **Note-to-Frequency**: Parse note names like `C4`, `F#5`, `Bb3` to Hz, with MIDI support
- **Composition Engine**: Multi-track composition with per-track waveform, envelope, and effects
- **WAV Export/Import**: Write/read 8, 16, 24, 32-bit PCM WAV files; stereo WAV export
- **Sample Utilities**: Normalize, mix, fade, reverse, concatenate, resample, crossfade, clip, dB conversion
- **ASCII Visualization**: Terminal-based waveform rendering, frequency bars, and envelope display
- **CLI Tool**: Full command-line interface for generating, synthesizing, and visualizing audio

## How It Works

### Waveform Generation
Each waveform is computed from mathematical principles:
- **Sine**: `sin(2πft)`
- **Square**: `sign(sin(2πft))`
- **Sawtooth**: `2(fract(ft) - 0.5)`
- **Triangle**: `2|2·fract(ft) - 1| - 1`
- **Pulse**: Duty-cycle-adjustable square wave
- **Noise**: Deterministic pseudo-random from sample index

### FM Synthesis
The classic equation: `y(t) = A · carrier(2π·fc·t + I·modulator(2π·fm·t))`

The modulation index `I` controls spectral richness — higher values create more sidebands and a brighter, more complex timbre.

### ADSR Envelope
Four phases shape amplitude over time:
1. **Attack**: Linear/exponential rise from 0 to peak
2. **Decay**: Fall from peak to sustain level
3. **Sustain**: Hold at sustain level for the note's remaining duration
4. **Release**: Fall from sustain to 0 after note-off

### Effects
- **Reverb**: Schroeder reverb with 4 parallel comb filters + 2 series allpass filters, configurable room size and damping
- **Compressor**: Dynamic range compressor with threshold, ratio, attack, and release controls
- **Delay**: Combines original signal with time-delayed copies and feedback
- **Flanger**: Modulated delay with LFO-controlled sweep
- **Distortion**: `tanh(drive · x)` soft-clipping
- **Low-pass/High-pass**: One-pole IIR filters with configurable cutoff
- **Tremolo**: Amplitude modulation with LFO

### Stereo Processing
- **Panning**: Equal-power panning law for mono-to-stereo conversion
- **Stereo Widening**: Mid-side processing to increase perceived stereo width
- **Stereo WAV**: Write interleaved stereo WAV files

### Audio Analysis
- **RMS**: Root mean square level measurement
- **Peak**: Maximum absolute amplitude
- **Crest Factor**: Peak/RMS ratio (indicates dynamic range)
- **Zero-Crossing Rate**: Distinguishes tonal vs. noisy signals
- **Fundamental Frequency**: Autocorrelation-based pitch detection
- **Spectral Analysis**: DFT frequency-magnitude pairs
- **Statistics**: Comprehensive signal statistics

## Installation

```bash
cd waveform-synth
pip install -e .
```

## Usage

### Command Line

```bash
# Generate a 440Hz sine wave for 2 seconds
waveform-synth generate --waveform sine --frequency 440 --duration 2 --output out.wav

# Generate a sawtooth with harmonics and envelope
waveform-synth generate --waveform sawtooth --frequency 220 --harmonics "2:0.5,3:0.3" \
    --envelope "0.05,0.1,0.7,0.5" --output saw.wav

# FM synthesis — bell preset
waveform-synth fm --preset bellish --duration 3 --output bell.wav

# Custom FM synthesis with effects
waveform-synth fm --carrier 440 --modulator 880 --index 3.5 --duration 2 \
    --effects "distortion:3,delay:0.3:0.4:0.5" --output fm.wav

# Generate a C major scale
waveform-synth scale --root C --scale major --waveform triangle --output cmajor.wav

# Visualize a WAV file
waveform-synth visualize --input sine.wav
```

### Python API

```python
from waveform_synth.core import Oscillator, Waveform, PulseOscillator, normalize, mix, crossfade
from waveform_synth.envelope import ADSR
from waveform_synth.fm import FMSynth, FMPreset
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.export import WavWriter
from waveform_synth.visualize import ascii_waveform, ascii_frequency_bars
from waveform_synth.notes import generate_scale, generate_chord, note_to_freq
from waveform_synth.composition import Track, Composition, Note
from waveform_synth.stereo import mono_to_stereo, StereoWidener
from waveform_synth.analysis import rms, peak_level, fundamental_frequency, compute_stats

# Simple sine wave
osc = Oscillator(Waveform.SINE, frequency=440.0)
samples = osc.generate(2.0)

# Pulse wave with 25% duty cycle
pulse = PulseOscillator(frequency=440.0, duty_cycle=0.25)
samples = pulse.generate(2.0)

# FM synthesis — electric piano
synth = FMPreset.e_piano(carrier_freq=440.0)
samples = synth.generate(2.0)

# Effects chain with reverb and compressor
chain = EffectsChain()
chain.add(Effect(EffectType.DISTORTION, drive=2.5))
chain.add(Effect(EffectType.REVERB, room_size=0.7, damping=0.5, wet=0.3))
chain.add(Effect(EffectType.COMPRESSOR, threshold=0.5, ratio=4.0))
processed = chain.process(samples)

# Stereo panning
left, right = mono_to_stereo(samples, pan=0.3)

# Audio analysis
stats = compute_stats(samples)
print(f"RMS: {stats['rms']:.4f}, Peak: {stats['peak']:.4f}")

# Stereo WAV export
writer = WavWriter()
writer.write_stereo("stereo.wav", left, right)

# Multi-track composition
comp = Composition(title="My Song")
track = Track(waveform=Waveform.SINE, envelope=ADSR(0.05, 0.1, 0.7, 0.3))
track.add_note("C4", 0.5).add_note("E4", 0.5).add_note("G4", 0.5)
comp.add_track(track)
comp.export_wav("song.wav")
```

## Architecture

```
waveform_synth/
├── __init__.py        # Package entry point
├── core.py            # Oscillator, PulseOscillator, waveform types, mix, normalize, fade, crossfade, resample, clip, dB
├── envelope.py        # ADSR envelope generator (linear/exponential curves)
├── fm.py              # FM synthesis engine and 5 presets
├── effects.py         # Effects chain, 9 effects (gain, delay, flanger, distortion, LP, HP, tremolo, reverb, compressor)
├── export.py          # WAV file reader/writer (mono & stereo, 8/16/24/32-bit)
├── visualize.py       # ASCII waveform, frequency bars, envelope rendering
├── notes.py           # Note/scale/chord definitions and conversions
├── composition.py     # Multi-track composition engine
├── stereo.py          # Stereo panning, widening, channel conversion
├── analysis.py        # RMS, peak, crest factor, ZCR, pitch detection, spectral analysis, stats
└── cli.py             # Command-line interface
```

## Requirements

- Python 3.10+
- No external dependencies — pure standard library