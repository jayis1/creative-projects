# 🎵 Wave Synth — Terminal Audio Waveform Synthesizer

**Version 1.2.2** — A command-line tool for generating, visualizing, mixing, and exporting audio waveforms entirely from your terminal.

Generate sine, square, sawtooth, triangle, pulse, noise, harmonic, and chirp waveforms. Apply effects like tremolo, distortion, reverb, compressor, flanger, and more. Visualize as ASCII art or export as WAV files.

## Features

- **8 waveform types**: sine, square, sawtooth, triangle, pulse, noise, harmonic, chirp
- **17 audio effects**: tremolo, vibrato, lowpass, highpass, distortion, delay, fade-in/out, normalize, ADSR envelope, reverse, ring modulation, bitcrush, reverb, pitch shift, compressor, flanger
- **Pulse wave**: Variable duty cycle square wave
- **Dynamic compressor**: Threshold/ratio-based dynamics processing (proper dB math)
- **Flanger**: Sweeping modulated delay with feedback
- **Melody transposition**: Shift melodies up/down by semitones
- **Musical note support**: Use note names like `A4`, `C#5`, `Eb3` — sharps and flats, case-insensitive
- **13 chord types**: maj, min, dim, aug, 7, maj7, min7, sus2, sus4, 5, add9, 6, 9
- **7 melody presets**: scale, happy_birthday, ode_to_joy, twinkle, pentatonic, fur_elise, amazing_grace
- **WAV import/export**: Load 8-bit or 16-bit WAV files, apply effects, re-export
- **ASCII visualization**: Waveform and frequency spectrum display in your terminal
- **Waveform info**: Duration, peak, RMS, DC offset, crest factor, estimated frequency
- **Interactive mode**: REPL for real-time waveform experimentation with amplitude control
- **Custom harmonics**: Define your own harmonic series for rich tones
- **Note & chord reference**: `--list-notes` and `--list-chords` flags for discoverability
- **`__all__` exports**: Clean public API for programmatic use
- **Comprehensive docstrings**: All functions fully documented with Args/Returns/Raises
- **Robust error handling**: Invalid CLI parameters produce helpful messages instead of crashes
- **Minimum 1-sample guarantee**: All wave generators produce at least 1 sample for any positive duration

## Installation

No external dependencies required — uses only Python standard library modules.

```bash
# Clone or download, then run directly:
python3 wave_synth.py sine A4 2
```

## Quick Start

```bash
# Generate 2 seconds of A4 (440 Hz) sine wave
python3 wave_synth.py sine A4 2

# Square wave at 220 Hz with tremolo effect
python3 wave_synth.py square 220 1 --effect tremolo

# Pulse wave with 25% duty cycle
python3 wave_synth.py pulse A4 2 --duty 0.25

# C major chord with sawtooth wave
python3 wave_synth.py chord C4 maj 2 --wave sawtooth

# A minor 7 arpeggio
python3 wave_synth.py arp A3 min7 3

# Fur Elise melody with triangle wave
python3 wave_synth.py melody fur_elise --wave triangle

# Frequency sweep (chirp) from 200 Hz to 2000 Hz
python3 wave_synth.py chirp 200 2000 3

# Sine wave with reverb and compressor, exported to WAV
python3 wave_synth.py sine A4 2 --effect reverb:0.4 --effect compressor:0.5:4 --export output.wav

# Sine wave with flanger effect
python3 wave_synth.py sine A4 2 --effect flanger:0.5:0.002:0.3

# 4-bit crushed sine
python3 wave_synth.py sine A4 2 --effect bitcrush:4

# Import a WAV, apply effects, re-export
python3 wave_synth.py --import-wav input.wav --effect lowpass:800 --export processed.wav

# Show frequency spectrum
python3 wave_synth.py sine A4 1 --spectrum

# Show detailed waveform info
python3 wave_synth.py sine A4 1 --info

# List all note names and frequencies
python3 wave_synth.py --list-notes

# List all chord types
python3 wave_synth.py --list-chords

# Interactive mode
python3 wave_synth.py --interactive
```

## Usage

```
python3 wave_synth.py <wave_type> <note/freq> <duration> [options]
```

### Positional Arguments

| Argument     | Description                                         |
|--------------|-----------------------------------------------------|
| `wave_type`  | sine, square, sawtooth, triangle, pulse, noise, harmonic, chirp, chord, arp, melody |
| `remaining`  | Note/frequency, chord type, duration (varies)      |

### Options

| Flag                     | Description                                        |
|--------------------------|----------------------------------------------------|
| `--interactive`, `-i`    | Start interactive mode                              |
| `--version`, `-V`        | Show version                                       |
| `--wave`, `-w`           | Wave type for chord/arp/melody (default: sine)     |
| `--amplitude`, `-a`      | Amplitude 0–1 (default: 0.8)                        |
| `--export`, `-e`         | Export to WAV file                                  |
| `--import-wav`           | Import WAV file and apply effects                   |
| `--effect`, `-f`         | Apply effect (can be used multiple times)           |
| `--adsr`                 | Apply ADSR envelope (e.g. `0.01,0.1,0.7,0.2`)       |
| `--chord-type`, `-c`     | Chord type for chord/arp (default: maj)             |
| `--harmonics`            | Custom harmonics (e.g. `"1,1 2,0.5 3,0.25"`)        |
| `--duty`                 | Duty cycle for pulse wave (0.0–1.0, default: 0.5)   |
| `--sweep-method`         | Chirp method: linear or exponential (default: linear) |
| `--spectrum`, `-s`       | Show frequency spectrum instead of waveform         |
| `--info`                 | Show waveform info (duration, peak, RMS, etc.)       |
| `--quiet`, `-q`          | Suppress visualization output                        |
| `--seed`                 | Random seed for noise generation                    |
| `--width`                | Visualization width (default: 72)                   |
| `--height`               | Visualization height (default: 16)                  |
| `--list-notes`           | List all note names and frequencies                 |
| `--list-chords`          | List all chord types and intervals                  |

### Effect Parameters

Effects can be specified with parameters using colons:

```
--effect tremolo:5:0.5          Tremolo (rate Hz, depth 0-1)
--effect vibrato:5:0.002        Vibrato (rate Hz, depth seconds)
--effect lowpass:1000            Low-pass filter (cutoff Hz)
--effect highpass:1000           High-pass filter (cutoff Hz)
--effect distortion:3            Distortion (drive 0+)
--effect delay:0.3:0.4          Delay (time seconds, feedback 0-1)
--effect fadein:0.05            Fade in (duration seconds)
--effect fadeout:0.05           Fade out (duration seconds)
--effect normalize               Normalize to peak 0.95
--effect reverse                 Reverse waveform
--effect ringmod:100             Ring modulation (carrier Hz)
--effect bitcrush:4             Bit crush (1–16 bits)
--effect reverb:0.3              Reverb (decay 0-1)
--effect pitchshift:5            Pitch shift (semitones)
--effect compressor:0.5:4       Compressor (threshold 0-1, ratio 1+)
--effect flanger:0.5:0.002:0.3  Flanger (rate Hz, depth s, feedback 0-1)
```

### Note Names

Supports standard scientific pitch notation:
- Sharps: `C#4`, `A#3`, `F#5`
- Flats: `Eb3`, `Bb4`, `Ab5`
- Case-insensitive: `eb3`, `bb4`, `c#5` all work
- Numeric frequencies: `440`, `261.63`

### Chord Types

`maj`, `min`, `dim`, `aug`, `7`, `maj7`, `min7`, `sus2`, `sus4`, `5`, `add9`, `6`, `9`

### Melody Presets

`scale`, `happy_birthday`, `ode_to_joy`, `twinkle`, `pentatonic`, `fur_elise`, `amazing_grace`

### Pulse Wave Duty Cycle

The `pulse` wave type generates a rectangular wave with configurable duty cycle:
- `--duty 0.5` → standard square wave (default)
- `--duty 0.25` → narrow pulse, buzzy sound
- `--duty 0.1` → very narrow click-like pulse

## Interactive Mode

Run `python3 wave_synth.py --interactive` for a REPL:

```
wave> gen sine A4 2 0.8       # Generate with amplitude 0.8
wave> effect tremolo:5:0.5
wave> effect reverb:0.3
wave> effect compressor:0.5:4
wave> viz
wave> export output.wav
wave> quit
```

Interactive mode also supports:
- `gen <wave> <freq> <dur> [amp]` — Generate waveform with optional amplitude (default 0.8)
- `pulse <freq> <dur> [duty] [amp]` — Generate pulse wave with optional amplitude
- `chirp <start> <end> <dur> [amp] [method]` — Generate chirp with optional amplitude
- `transpose <semitones>` — Transpose the last melody by semitones
- `info` — Show detailed waveform statistics

## Programmatic Use

```python
from wave_synth import generate_sine, apply_reverb, apply_compressor, export_wav

# Generate a sine wave
samples = generate_sine(440.0, 2.0, amplitude=0.8)

# Apply effects chain
samples = apply_compressor(samples, threshold=0.5, ratio=4.0)
samples = apply_reverb(samples, decay=0.3)

# Export to WAV (status message printed to stderr)
export_wav(samples, 'output.wav')
```

Note: `export_wav()` prints its status message to **stderr** (not stdout), so it won't interfere with piped output.

All public functions are exported via `__all__`.

## Changelog

### v1.2.2 — Bug Fix Release

**Bugs fixed:**
- **Wave generators now produce at least 1 sample for very short durations**: Previously, `generate_sine(440, 0.00001)` returned an empty list because `int(0.00001 * 44100) = 0`. All 8 wave generators (sine, square, sawtooth, triangle, pulse, noise, harmonic, chirp) now use `max(1, int(duration * sample_rate))` to guarantee at least 1 sample for any positive duration.
- **Fade-in/out on single-sample input no longer silences the signal**: `apply_fade_in([0.8], 0.01)` and `apply_fade_out([0.8], 0.01)` previously returned `[0.0]` because the fade formula `i/n` yields 0 for i=0 when n=1. Now, when the fade covers 0 or 1 samples, the functions return a copy of the input unchanged.
- **Visualization scale labels no longer overwrite waveform data**: The `+1.0`, `0.0`, and `-1.0` labels were inserted at column 2 inside the waveform frame, corrupting the displayed waveform. Now the labels appear as a left-side column *outside* the frame, preserving the waveform integrity.
- **ADSR on empty input now returns empty list explicitly**: Added early return for empty samples in `apply_adsr()` for clarity, though the existing `[0.0] * n` pattern already handled this.
- **Fixed duplicate `unittest.main()` call** in test file.

**Tests:** 133 tests (up from 124), adding 9 new tests:
- `test_fade_in_single_sample` — fade-in on 1 sample preserves the value
- `test_fade_out_single_sample` — fade-out on 1 sample preserves the value
- `test_fade_in_two_samples` — fade-in on 2 samples starts quiet
- `test_fade_out_two_samples` — fade-out on 2 samples ends quiet
- `test_generator_minimum_one_sample` — very short duration sine produces ≥1 sample
- `test_generator_all_minimum_one_sample` — all generators produce ≥1 sample
- `test_pulse_minimum_one_sample` — pulse wave produces ≥1 sample for short durations
- `test_visualize_scale_labels_dont_corrupt_data` — labels appear as prefix, not inside frame
- `test_adsr_empty_samples` — ADSR on empty input returns empty

### v1.2.1 — Bug Fix Release

- **Compressor math corrected**: Proper dB conversion (`20 * log10`) for gain computation; `ratio=1.0` passes signal through unchanged.
- **`generate_noise()` no longer mutates global random state**: Global state saved/restored around seeding.
- **`apply_delay()` performance fix**: Replaced `copy.deepcopy(samples)` with `list(samples)`.
- **`export_wav()` prints to stderr**: Won't interfere with piped output.
- **CLI crash on invalid effect/ADSR parameters**: Non-numeric values produce helpful error messages.
- **Interactive mode amplitude**: `gen`, `pulse`, `chirp` commands accept optional amplitude (default 0.8).
- **Spectrum visualization performance**: Downsampling for signals >16384 samples.

### v1.2.0 — Feature Release

- Pulse wave, compressor, flanger, melody transposition, `--list-notes`, `--list-chords`, `--duty`, 3 chord types, 2 melody presets, `__all__` exports, enhanced `print_waveform_info`, comprehensive docstrings.

### v1.1.1 — Bug Fix Release

- Fixed `note_to_freq` corrupted B notes, `resolve_freq` lowercase flats, chord/harmonic/chirp crashes, empty-sample crashes, distortion drive=0, mix zero-weight division, visualization scale label row shift.

### v1.1.0 — Feature Release

- Chirp/sweep, 5 effects (reverse, ring mod, bitcrush, reverb, pitch shift), WAV import, `--version`, `--quiet`, interactive mode enhancements.

### v1.0.0 — Initial Release

- Basic waveform generation, effects, visualization, WAV export.

## License

MIT