# MIDI Step Sequencer

A generative music composition toolkit and MIDI file exporter built in pure Python. Create rhythmic patterns using Euclidean algorithms, Markov chains, L-systems, and probability-based generation — then export the results as standard MIDI files playable in any DAW.

## Features

### Core
- **15 musical scales**: major, minor, harmonic/melodic minor, dorian, phrygian, lydian, mixolydian, pentatonic, blues, whole tone, chromatic, and more
- **11 chord types**: maj, min, dim, aug, maj7, min7, dom7, dim7, sus2, sus4, add9
- **Multi-track songs**: Mix drums, bass, chords, and melody with per-track MIDI channel/program
- **MIDI export**: Standard `.mid` files compatible with all DAWs and hardware
- **CLI interface**: Compose from the command line or use preset templates

### Generative Algorithms
- **Euclidean rhythm generation**: Björklund's algorithm for perfectly even pulse distribution
- **Markov chain melodies**: Configurable transition matrices for organic melodic generation
- **Probability-based patterns**: Control note density and randomness
- **L-System patterns**: Cantor set, Fibonacci, Koch snowflake, and other fractal-based melodies
- **Drum patterns**: Built-in styles (four_on_floor, breakbeat, hiphop, bossa, waltz)
- **Chord progressions**: Automatic voicing and arpeggiation from named progressions

### Pattern Manipulation
- **Groove templates**: swing, shuffle, dilla, bossa, reggae — apply human feel to rigid patterns
- **Velocity curves**: crescendo, diminuendo, swell, heartbeat, random dynamics
- **Pattern operations**: rotate, reverse, invert, mask, and morph between patterns
- **Humanization**: Random velocity and timing deviations for realistic feel
- **Swing timing**: Adjustable swing feel

### Song Arrangement
- **Named progressions**: 10 built-in chord progressions (pop I-V-vi-IV, jazz ii-V-I, 12-bar blues, etc.)
- **Section-based arrangement**: Chain verse/chorus sections into complete songs
- **JSON serialization**: Save and load complete songs and patterns

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

### Generate an L-System melody
```bash
python -m sequencer generate lsystem --lsystem-preset fibonacci_melody --iterations 4 -o lsystem.mid
```

### Generate a chord progression
```bash
python -m sequencer generate progression --progression jazz_ii_V_I --root D -o jazz.mid
```

### Apply groove and velocity curve
```bash
python -m sequencer generate euclidean --beats 7 --length 16 --groove dilla --velocity-curve swell -o grooved.mid
```

### Compose a multi-track song
```bash
python -m sequencer compose \
  --tracks "drums:four_on_floor" "euclidean:5:16:C:pentatonic_minor:4" "progression:pop_I_V_vi_IV" \
  -o song.mid
```

### Use a preset template
```bash
python -m sequencer preset euclidean_jam --key A --bpm 110 -o jam.mid
```

### View available options
```bash
python -m sequencer info scales
python -m sequencer info progressions
python -m sequencer info grooves
python -m sequencer info lsystems
```

## Programmatic Usage

```python
from sequencer.scales import scale_notes, chord_notes
from sequencer.patterns import Pattern, Step, Track, Song
from sequencer.generators import euclidean_pattern, drum_pattern, markov_pattern
from sequencer.grooves import apply_groove, apply_velocity_curve
from sequencer.lsystem import lsystem_pattern
from sequencer.progressions import build_progression
from sequencer.arrangement import Arrangement, Section, verse_chorus_verse
from sequencer.serialization import save_song, load_song
from sequencer.export import song_to_midi

# Create patterns
melody = euclidean_pattern(5, 16, root='A', scale='pentatonic_minor', octave=5)
melody = apply_groove(melody, 'shuffle')
melody = apply_velocity_curve(melody, 'swell')
drums = drum_pattern('four_on_floor', 16)

# Build a chord progression
chords = build_progression('pop_I_V_vi_IV', key='C')
# Returns: [('C', 'maj'), ('G', 'maj'), ('A', 'min'), ('F', 'maj')]

# L-System patterns
ls = lsystem_pattern('fibonacci_melody', iterations=3, root='E', scale='minor')

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

# Save/load as JSON
save_song(song, 'my_song.json')
loaded = load_song('my_song.json')

# Arrange verse/chorus structure
arr = verse_chorus_verse(verse_melody, chorus_melody, verse_bass, chorus_bass, verse_drums, chorus_drums)
arr.export_midi('arrangement.mid')
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

## Chord Progressions

| Name | Degrees |
|------|---------|
| pop_I_V_vi_IV | I-V-vi-IV |
| pop_vi_IV_I_V | vi-IV-I-V |
| 50s_I_vi_IV_V | I-vi-IV-V |
| jazz_ii_V_I | ii-V-I |
| jazz_i_vi_ii_V | I-vi-ii-V |
| rhythm_changes | I-vi-ii-V |
| blues_12bar | 12-bar blues |
| classical_I_IV_V_I | I-IV-V-I |
| classical_i_iv_V_i | i-iv-V-i |
| andalusian | vi-V-IV-III |

## Groove Templates

- `straight` — No groove, metronomic timing
- `swing_16th` — Classic swung 16th notes
- `shuffle` — Heavy shuffle feel
- `dilla` — J Dilla-style loose timing
- `bossa` — Bossa nova syncopation
- `reggae` — Offbeat reggae feel

## Architecture

- **`sequencer/scales.py`** — Note/scale/chord utilities and music theory
- **`sequencer/patterns.py`** — Step, Pattern, Track, Song data structures
- **`sequencer/generators.py`** — Euclidean, random, Markov, chord, bass, drum generators
- **`sequencer/grooves.py`** — Groove templates and velocity curves
- **`sequencer/lsystem.py`** — L-System pattern generation
- **`sequencer/progressions.py`** — Named chord progressions
- **`sequencer/arrangement.py`** — Multi-section song arrangement
- **`sequencer/presets.py`** — Ready-made song templates
- **`sequencer/serialization.py`** — JSON save/load for songs and patterns
- **`sequencer/export.py`** — MIDI file export
- **`sequencer/cli.py`** — Command-line interface

## Known Issues (Resolved)

The following bugs were found and fixed during the bug hunt phase:

1. **Euclidean rhythm algorithm produced incorrect distributions** — The original Björklund algorithm implementation had a termination condition bug that caused `short_count >= remaining` to fire prematurely, resulting in clumped rather than evenly distributed pulses (e.g., E(8,13) produced all-then-none instead of evenly spaced). **Fix:** Replaced with a correct Bresenham-style error diffusion algorithm that guarantees even distribution and exact pulse counts.

2. **`midi_to_note`/`note_to_midi` roundtrip failure for negative octaves** — `midi_to_note(0)` returned `"C-1"` but `note_to_midi("C-1")` crashed with `ValueError: Unknown note name: 'C-'` because the negative sign wasn't handled during octave parsing. **Fix:** Updated `note_to_midi` to detect and handle the `-` sign in negative octaves. Also rewrote `midi_to_note` to use an explicit mapping dict for clarity.

3. **Groove timing offsets were silently discarded** — The `apply_groove()` function computed timing offsets per step but never stored them, so groove timing had no effect on the exported MIDI. **Fix:** Added a `timing_offset` field to the `Step` dataclass and updated `apply_groove()` to write timing offsets into steps. Updated `Track.render_notes()` to combine step-level groove offsets with track-level humanization.

4. **`scale_notes` test expectation was wrong** — The test for `scale_notes("C", "major", 1, 4)` expected 7 notes but the function correctly returns 8 (including the octave root). **Fix:** Corrected the test expectation. The function's behavior of including the top root note is intentional and musically correct.

5. **Serialization missed `timing_offset` field** — The `step_to_dict` and `dict_to_step` functions didn't include the new `timing_offset` field, causing data loss on round-trip. **Fix:** Added `timing_offset` to both serialization functions with a default of 0.0 for backward compatibility.

6. **Arrangement didn't copy `timing_offset`** — The `render_to_song()` method in `arrangement.py` manually constructed `Step` objects but omitted `timing_offset`. **Fix:** Added `timing_offset` to the Step construction in arrangement.

## Testing

Run the comprehensive test suite:

```bash
cd midi-sequencer
source venv/bin/activate
python -m pytest tests/test_sequencer.py -v
```

66 tests covering scales, Euclidean rhythms, patterns, grooves, L-systems, progressions, serialization, MIDI export, arrangements, ties, and edge cases.