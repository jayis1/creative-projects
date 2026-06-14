# MIDI Step Sequencer

A generative music composition toolkit and MIDI file exporter built in pure Python. Create rhythmic patterns using Euclidean algorithms, Markov chains, and probability-based generation — then export the results as standard MIDI files playable in any DAW.

## Features

- **15 musical scales**: major, minor, harmonic/melodic minor, dorian, phrygian, lydian, mixolydian, pentatonic, blues, whole tone, chromatic, and more
- **11 chord types**: maj, min, dim, aug, maj7, min7, dom7, dim7, sus2, sus4, add9
- **Euclidean rhythm generation**: Björklund's algorithm for perfectly even pulse distribution
- **Markov chain melodies**: Configurable transition matrices for organic melodic generation
- **Probability-based patterns**: Control note density and randomness
- **Drum patterns**: Built-in styles (four_on_floor, breakbeat, hiphop, bossa, waltz)
- **Chord progressions**: Automatic voicing and arpeggiation
- **Humanization**: Random velocity and timing deviations for realistic feel
- **Pattern operations**: Rotate, reverse, invert, mask, and morph between patterns
- **Multi-track songs**: Mix drums, bass, chords, and melody with per-track MIDI channel/program
- **Swing timing**: Adjustable swing feel
- **MIDI export**: Standard `.mid` files compatible with all DAWs and hardware
- **CLI interface**: Compose from the command line or use preset templates

## Installation

```bash
cd midi-sequencer
python3 -m venv venv
source venv/bin/activate
pip install midiutil
```

## Quick Start

### Generate a Euclidean rhythm pattern
```bash
python -m sequencer generate euclidean --beats 5 --length 16 --root C --scale pentatonic_minor -o euc.mid
```

### Generate a drum pattern
```bash
python -m sequencer generate drums --drum-style four_on_floor -o drums.mid
```

### Compose a multi-track song
```bash
python -m sequencer compose \
  --tracks "drums:four_on_floor" "euclidean:5:16:C:pentatonic_minor:4" \
  --bpm 128 -o song.mid
```

### Use a preset template
```bash
python -m sequencer preset euclidean_jam --key A --bpm 110 -o jam.mid
```

### View available scales
```bash
python -m sequencer info scales
```

## Programmatic Usage

```python
from sequencer.scales import scale_notes, chord_notes
from sequencer.patterns import Pattern, Step, Track, Song
from sequencer.generators import euclidean_pattern, drum_pattern, markov_pattern
from sequencer.export import song_to_midi

# Create a Euclidean melody pattern
melody = euclidean_pattern(5, 16, root='A', scale='pentatonic_minor', octave=5, velocity=90)

# Create a drum track
drums = drum_pattern('four_on_floor', 16)

# Assemble a song
song = Song(
    name='My Song',
    tracks=[
        Track(name='Drums', pattern=drums, channel=9),
        Track(name='Melody', pattern=melody, channel=0, program=81),
    ],
    bpm=120,
)

# Export to MIDI
song_to_midi(song, 'my_song.mid')
```

## Scale Reference

| Scale | Intervals |
|-------|-----------|
| major | 0 2 4 5 7 9 11 |
| minor (natural_minor) | 0 2 3 5 7 8 10 |
| harmonic_minor | 0 2 3 5 7 8 11 |
| melodic_minor | 0 2 3 5 7 9 11 |
| dorian | 0 2 3 5 7 9 10 |
| phrygian | 0 1 3 5 7 8 10 |
| lydian | 0 2 4 6 7 9 11 |
| mixolydian | 0 2 4 5 7 9 10 |
| phrygian_dominant | 0 1 3 5 7 8 10 |
| whole_tone | 0 2 4 6 8 10 |
| pentatonic_major | 0 2 4 7 9 |
| pentatonic_minor | 0 3 5 7 10 |
| blues | 0 3 5 6 7 10 |
| chromatic | 0 1 2 3 4 5 6 7 8 9 10 11 |

## Architecture

- **`sequencer/scales.py`** — Note/scale/chord utilities and music theory
- **`sequencer/patterns.py`** — Step, Pattern, Track, Song data structures
- **`sequencer/generators.py`** — Euclidean, random, Markov, chord, bass, drum generators
- **`sequencer/presets.py`** — Ready-made song templates
- **`sequencer/export.py`** — MIDI file export
- **`sequencer/cli.py`** — Command-line interface