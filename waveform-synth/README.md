# Waveform Synthesizer

A from-scratch digital audio synthesizer with waveform generation, ADSR envelopes, FM synthesis, effects processing, WAV export, and ASCII visualization.

## Features

- **5 Waveform Types**: Sine, square, sawtooth, triangle, and noise — all generated mathematically from first principles
- **Additive Harmonics**: Layer harmonics onto any waveform for rich timbral content (e.g., `(2, 0.5)` adds the 2nd harmonic at half amplitude)
- **ADSR Envelopes**: Attack-Decay-Sustain-Release envelope shaping with linear or exponential curves
- **FM Synthesis**: John Chowning-style frequency modulation with carrier and modulator oscillators — create bells, brass, electric pianos, and more
- **5 FM Presets**: Bell, brass, woodwind, bass, and electric piano
- **7 Audio Effects**: Gain, delay (with feedback), flanger, distortion (tanh soft-clipping), low-pass filter, high-pass filter, tremolo — all chainable
- **Musical Scales**: 12 scale types (major, natural/harmonic/melodic minor, dorian, phrygian, lydian, mixolydian, pentatonic, blues, chromatic, whole tone)
- **Chords**: 10 chord types (major, minor, dim, aug, dom7, maj7, min7, sus2, sus4, add9)
- **Note-to-Frequency**: Parse note names like `C4`, `F#5`, `Bb3` to Hz
- **Composition Engine**: Multi-track composition with per-track waveform, envelope, and effects
- **WAV Export**: Write 16-bit PCM WAV files; also read WAV files back for visualization
- **ASCII Visualization**: Terminal-based waveform and frequency spectrum display
- **CLI Tool**: Full command-line interface for generating, synthesizing, and visualizing audio

## How It Works

### Waveform Generation
Each waveform is computed from mathematical principles:
- **Sine**: `sin(2πft)`
- **Square**: `sign(sin(2πft))`
- **Sawtooth**: `2(fract(ft) - 0.5)`
- **Triangle**: `2|2·fract(ft) - 1| - 1`
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

### Effects Chain
Effects are applied sequentially to audio samples. Each effect processes the full sample buffer:
- **Delay**: Combines original signal with time-delayed copies and feedback
- **Flanger**: Modulated delay with LFO-controlled sweep
- **Distortion**: `tanh(drive · x)` soft-clipping
- **Low-pass/High-pass**: One-pole IIR filters with configurable cutoff
- **Tremolo**: Amplitude modulation with LFO

## Installation

```bash
cd waveform-synth
pip install -e .
```

## Usage

### Command Line

```bash
# Generate a 440Hz sine wave for 2 seconds
waveform-synth generate --waveform sine --frequency 440 --duration 2 --output sine.wav

# Generate a sawtooth with harmonics and envelope
waveform-synth generate --waveform sawtooth --frequency 220 --harmonics "2:0.5,3:0.3" \
    --envelope "0.05,0.1,0.7,0.5" --output saw.wav

# FM synthesis — bell preset
waveform-synth fm --preset bellish --duration 3 --output bell.wav

# Custom FM synthesis
waveform-synth fm --carrier 440 --modulator 880 --index 3.5 --duration 2 --output fm.wav

# Generate a C major scale
waveform-synth scale --root C --scale major --waveform triangle --output cmajor.wav

# Add effects
waveform-synth generate --waveform square --frequency 440 --duration 2 \
    --effects "distortion:3,delay:0.3:0.4:0.5,lowpass:2000" --output fx.wav

# Visualize a WAV file
waveform-synth visualize --input sine.wav
```

### Python API

```python
from waveform_synth.core import Oscillator, Waveform, normalize, mix
from waveform_synth.envelope import ADSR
from waveform_synth.fm import FMSynth, FMPreset
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.export import WavWriter
from waveform_synth.visualize import ascii_waveform
from waveform_synth.notes import generate_scale, generate_chord, note_to_freq
from waveform_synth.composition import Track, Composition, Note

# Simple sine wave
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.8)
samples = osc.generate(2.0)  # 2 seconds

# With harmonics
osc = Oscillator(Waveform.SINE, frequency=440.0, harmonics=[(2, 0.5), (3, 0.3)])
samples = osc.generate(2.0)

# Apply ADSR envelope
env = ADSR(attack=0.01, decay=0.1, sustain=0.7, release=0.3)
samples = env.apply(samples, note_duration=1.7)

# FM synthesis — electric piano
synth = FMPreset.e_piano(carrier_freq=440.0)
samples = synth.generate(2.0)
samples = env.apply(samples, note_duration=1.7)

# Effects chain
chain = EffectsChain()
chain.add(Effect(EffectType.DISTORTION, drive=2.5))
chain.add(Effect(EffectType.DELAY, time=0.3, feedback=0.4, mix=0.5))
chain.add(Effect(EffectType.LOWPASS, cutoff=2000))
processed = chain.process(samples)

# Normalize and export
processed = normalize(processed)
writer = WavWriter()
writer.write("output.wav", processed)

# Visualize
print(ascii_waveform(processed, width=80, height=20, title="My Sound"))

# Musical scale
freqs = generate_scale("C", "major", octave=4)
for freq in freqs:
    print(f"  {freq:.2f} Hz")

# Chord
chord = generate_chord("C", "maj7", octave=4)
print(f"Cmaj7: {[f'{f:.2f}' for f in chord]}")

# Multi-track composition
comp = Composition(title="My Song")
track1 = Track(waveform=Waveform.SINE, envelope=ADSR(0.05, 0.1, 0.7, 0.3))
track1.add_note("C4", 0.5)
track1.add_note("E4", 0.5)
track1.add_note("G4", 0.5)
comp.add_track(track1)
comp.export_wav("song.wav")
```

## Architecture

```
waveform_synth/
├── __init__.py        # Package entry point
├── core.py            # Oscillator, waveform types, mix, normalize, fade
├── envelope.py        # ADSR envelope generator
├── fm.py              # FM synthesis engine and presets
├── effects.py         # Effects chain and individual effect processors
├── export.py          # WAV file reader/writer
├── visualize.py       # ASCII waveform and frequency bar rendering
├── notes.py           # Note/scale/chord definitions and conversions
├── composition.py     # Multi-track composition engine
└── cli.py             # Command-line interface
```

## Requirements

- Python 3.10+
- No external dependencies — pure standard library