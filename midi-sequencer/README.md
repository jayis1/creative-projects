# 🎹 MIDI Step Sequencer

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 124](https://img.shields.io/badge/tests-124%20passing-green.svg)](#testing)

A generative music composition toolkit and MIDI file exporter built in pure Python. Create rhythmic patterns using Euclidean algorithms, Markov chains, L-systems, and probability-based generation — then export the results as standard MIDI files playable in any DAW.

```
╔══════════════════════════════════════════╗
║  MIDI Step Sequencer v3.0               ║
║  Generative music • Algorithmic rhythm   ║
║  Euclidean • Markov • L-System • More    ║
╚══════════════════════════════════════════╝
```

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Programmatic Usage](#programmatic-usage)
- [Scale Reference](#scale-reference)
- [Chord Progressions](#chord-progressions)
- [Groove Templates](#groove-templates)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Analysis & Visualization](#analysis--visualization)
- [Batch Composition](#batch-composition)
- [Extended Drum Patterns](#extended-drum-patterns)
- [Input Validation](#input-validation)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

### Core
- **15 musical scales**: major, minor, harmonic/melodic minor, dorian, phrygian, lydian, mixolydian, pentatonic, blues, whole tone, chromatic, and more
- **11 chord types**: maj, min, dim, aug, maj7, min7, dom7, dim7, sus2, sus4, add9
- **Multi-track songs**: Mix drums, bass, chords, and melody with per-track MIDI channel/program
- **MIDI export**: Standard `.mid` files compatible with all DAWs and hardware
- **CLI interface**: Compose from the command line or use preset templates
- **Configuration files**: YAML, TOML, or JSON config for default settings
- **Input validation**: Comprehensive validation for all musical parameters
- **Logging**: Configurable logging with console and file output

### Generative Algorithms
- **Euclidean rhythm generation**: Bresenham-style error diffusion for perfectly even pulse distribution
- **Markov chain melodies**: Configurable transition matrices for organic melodic generation
- **Probability-based patterns**: Control note density and randomness
- **L-System patterns**: Cantor set, Fibonacci, Koch snowflake, and other fractal-based melodies
- **Drum patterns**: Built-in styles (four_on_floor, breakbeat, hiphop, bossa, waltz) + 8 extended styles
- **Chord progressions**: Automatic voicing and arpeggiation from named progressions
- **Pattern morphing**: Smoothly blend between two patterns

### Pattern Manipulation
- **Groove templates**: swing, shuffle, dilla, bossa, reggae — apply human feel to rigid patterns
- **Velocity curves**: crescendo, diminuendo, swell, heartbeat, random dynamics
- **Pattern operations**: rotate, reverse, invert, mask, and morph between patterns
- **Humanization**: Random velocity and timing deviations for realistic feel
- **Swing timing**: Adjustable swing feel

### Song Arrangement
- **10 named progressions**: pop I-V-vi-IV, jazz ii-V-I, 12-bar blues, etc.
- **Section-based arrangement**: Chain verse/chorus sections into complete songs
- **JSON serialization**: Save and load complete songs and patterns
- **Batch composition**: Generate variations, explore parameter spaces, create albums

### Analysis & Visualization
- **Pattern statistics**: density, note range, velocity distribution
- **ASCII visualizations**: block, dot, and piano-roll views
- **Song summaries**: formatted overview of tracks and settings
- **Note & interval distributions**: understand melodic content

## Installation

### From Source (Recommended)

```bash
cd midi-sequencer
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### As a Package

```bash
pip install -e .
```

### Dependencies

- **Required**: `midiutil>=1.2` (MIDI file generation)
- **Optional**: `pyyaml>=6.0` (YAML config files)
- **Dev**: `pytest>=7.0`, `pyyaml>=6.0`

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
  -o song.mid --summary
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
python -m sequencer info drums
```

### Analyze a saved song
```bash
python -m sequencer analyze --input song.json --summary --stats
```

### Batch generate variations
```bash
python -m sequencer batch euclidean --root A --min-beats 3 --max-beats 9 -o batch/
python -m sequencer batch scales --root C -o scales/
python -m sequencer batch progressions --key C -o progs/
```

### Manage configuration
```bash
python -m sequencer config init --format yaml
python -m sequencer config show
python -m sequencer config validate --config-file my_config.yaml
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `generate <algorithm>` | Generate a pattern (euclidean, random, markov, drums, chords, lsystem, progression) |
| `compose --tracks ...` | Compose a multi-track song from track specs |
| `preset <name>` | Generate from a preset template |
| `info <type>` | Display info about scales, chords, progressions, grooves, drums, lsystems |
| `analyze --input <file>` | Analyze a saved song JSON |
| `batch <task>` | Batch composition (euclidean, scales, progressions, sweep) |
| `config <action>` | Manage configuration (show, init, validate) |

### Generate Options

| Flag | Default | Description |
|------|---------|-------------|
| `--beats` | 5 | Number of active steps (Euclidean) |
| `--length` | 16 | Pattern length in steps |
| `--root` | C | Root note |
| `--scale` | pentatonic_minor | Scale name |
| `--octave` | 4 | Starting octave |
| `--rotation` | 0 | Rotation offset |
| `--density` | 0.5 | Note density (random) |
| `--velocity` | 100 | Note velocity |
| `--drum-style` | four_on_floor | Drum pattern style |
| `--groove` | None | Apply groove template |
| `--groove-intensity` | 1.0 | Groove intensity |
| `--velocity-curve` | None | Apply velocity curve |
| `--bpm` | 120 | Tempo |
| `--channel` | 0 | MIDI channel |
| `--program` | 0 | MIDI program |
| `--visualize` | block | Visualization style (block, piano, dot) |
| `-o` | None | Output MIDI file |

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
from sequencer.config import SequencerConfig
from sequencer.validation import validate_bpm, validate_scale, ValidationError
from sequencer.analysis import pattern_stats, song_summary, visualize_pattern
from sequencer.batch import CompositionRecipe, euclidean_variations

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

# Analyze patterns
stats = pattern_stats(melody)
print(f"Density: {stats['density']:.1%}, Notes: {stats['note_count']}")

# Visualize
print(visualize_pattern(melody, style='piano'))

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

# Configure defaults
config = SequencerConfig(bpm=140, default_root='A', default_scale='minor')
config.apply_to_song(song)

# Batch composition
files = euclidean_variations(root='C', scale='major', beat_range=(3, 9))

# Validation
try:
    validate_bpm(500)  # Raises ValidationError
except ValidationError as e:
    print(f"Invalid: {e}")
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

```
sequencer/
├── __init__.py           # Package exports (v3.0.0)
├── __main__.py           # python -m sequencer entry point
├── scales.py             # Music theory: scales, chords, note utilities
├── patterns.py           # Core data structures: Step, Pattern, Track, Song
├── generators.py         # Pattern generators: Euclidean, Markov, random, drums
├── grooves.py            # Groove templates and velocity curves
├── lsystem.py            # L-System pattern generation (5 presets)
├── progressions.py       # Named chord progressions (10 progressions)
├── arrangement.py         # Multi-section song arrangement
├── presets.py            # Ready-made song templates (3 presets)
├── serialization.py      # JSON save/load for songs and patterns
├── export.py             # MIDI file export (via midiutil)
├── cli.py                # Command-line interface (7 commands)
├── config.py             # Configuration management (YAML/TOML/JSON)
├── validation.py         # Input validation with clear error messages
├── analysis.py           # Pattern/song analysis and ASCII visualization
├── batch.py              # Batch composition and parameter sweeps
├── playback.py           # MIDI playback support (optional backends)
├── extended_drums.py     # Additional drum patterns (8 styles)
└── logging_setup.py      # Centralized logging configuration
```

### Data Flow

```
Generators → Pattern → [Grooves/VelocityCurve] → Track → Song → MIDI Export
                                    ↓
                              Arrangement (Section-based)
                                    ↓
                            Serialization (JSON save/load)
                                    ↓
                           Analysis (stats, visualization)
                                    ↓
                             Batch (variations, sweeps)
```

### Core Data Model

- **`Step`**: Single sequencer step — notes, velocity, gate, probability, tie, timing_offset
- **`Pattern`**: Sequence of Steps — supports rotate, reverse, invert, mask
- **`Track`**: Pattern + instrument settings (channel, program, humanization)
- **`Song`**: Collection of Tracks + song-level settings (BPM, PPQN, time sig)

## Configuration

The sequencer supports configuration files in YAML, TOML, or JSON format:

```yaml
# midi-sequencer.yaml
bpm: 120
ppqn: 480
time_signature: [4, 4]
default_root: "C"
default_scale: "pentatonic_minor"
default_octave: 4
default_velocity: 100
default_length: 16
humanize_velocity: 0.0
humanize_timing: 0.0
add_metronome: false
logging_level: "WARNING"
```

Auto-discovery order: `.midi-sequencer.yaml` → `.midi-sequencer.toml` → `.midi-sequencer.json`

```bash
# Initialize default config
python -m sequencer config init --format yaml

# Show current config
python -m sequencer config show

# Validate a config file
python -m sequencer config validate --config-file my_config.yaml
```

## Analysis & Visualization

### Pattern Statistics
```python
from sequencer.analysis import pattern_stats
stats = pattern_stats(my_pattern)
# {'active_steps': 5, 'density': 0.31, 'note_count': 5,
#  'velocity_mean': 100, 'note_range_semitones': 12, ...}
```

### ASCII Visualizations
```python
from sequencer.analysis import visualize_pattern
print(visualize_pattern(pattern, style="block"))   # Detailed step view
print(visualize_pattern(pattern, style="piano"))   # Piano roll
print(visualize_pattern(pattern, style="dot"))     # Compact ●○ view
```

Example block view:
```
Pattern: euc_5_16 (16 steps)
──────────────────────────────────
│▓ · ▓ · · ▓ · · ▓ · · ▓ · · · ·│
│─ ↑ ─   ─ ↑ ─ ─ ↑ ─ ─ ↑     │  velocity
│ ~       ~   ~       ~        │  ties
│ 0  2  4  6  8  10 12 14 16  │  step#
```

### Song Summary
```python
from sequencer.analysis import song_summary
print(song_summary(song))
```

## Batch Composition

Generate multiple variations at once:

```python
from sequencer.batch import euclidean_variations, scale_exploration, progression_album

# Generate E(3,16) through E(9,16)
files = euclidean_variations(root='A', scale='minor', beat_range=(3, 9))

# Generate one MIDI per scale
files = scale_exploration(root='C')

# Generate one MIDI per chord progression
files = progression_album(key='C', bpm=120)
```

Or via CLI:
```bash
python -m sequencer batch euclidean --root A --min-beats 3 --max-beats 9
python -m sequencer batch scales --root C
python -m sequencer batch progressions --key C
python -m sequencer batch sweep --parameter bpm --values "80,100,120,140,160"
```

## Extended Drum Patterns

8 additional drum styles beyond the core 5:

| Style | Description |
|-------|-------------|
| jungle | Fast jungle/DnB breakbeat (160+ BPM) |
| garage | 2-step garage pattern |
| techno | 4/4 techno with offbeat hats |
| trap | Trap beat with rapid hats |
| funk | Funky drummers pattern |
| reggaeton | Reggaeton dembow rhythm |
| dub | Dub/reggae with heavy offbeats |
| samba | Samba rhythm pattern |

```python
from sequencer.extended_drums import extended_drum_pattern, list_extended_styles
pattern = extended_drum_pattern("trap", length=16)
```

## Input Validation

All musical parameters are validated before processing:

```python
from sequencer.validation import validate_bpm, validate_scale, ValidationError

try:
    validate_bpm(500)  # Raises: "BPM must be 20-300, got 500"
except ValidationError as e:
    print(e)

validate_scale("major")       # OK
validate_scale("nonexistent") # Raises ValidationError
```

Validators: `validate_note_name`, `validate_scale`, `validate_chord_quality`, `validate_midi_note`, `validate_velocity`, `validate_channel`, `validate_program`, `validate_bpm`, `validate_octave`, `validate_pattern_length`, `validate_density`, `validate_gate`, `validate_probability`, `validate_time_signature`

## Known Issues (Resolved)

The following bugs were found and fixed during earlier development phases:

1. **Euclidean rhythm algorithm produced incorrect distributions** — Replaced with Bresenham-style error diffusion algorithm.
2. **`midi_to_note`/`note_to_midi` roundtrip failure for negative octaves** — Fixed octave parsing for negative signs.
3. **Groove timing offsets silently discarded** — Added `timing_offset` field to `Step` dataclass.
4. **`scale_notes` test expectation was wrong** — Corrected to expect 8 notes (including octave root).
5. **Serialization missed `timing_offset` field** — Added with backward-compatible default.
6. **Arrangement didn't copy `timing_offset`** — Added field to Step construction.

## Testing

Run the comprehensive test suite:

```bash
cd midi-sequencer
source venv/bin/activate
python -m pytest tests/test_sequencer.py -v
```

**124 tests** covering:
- Scales (14 tests) — note conversion, roundtrip, chord notes, quantization
- Euclidean Rhythm (12 tests) — distribution, edge cases, rotation, pattern generation
- Patterns (12 tests) — step defaults, length, rotate, reverse, invert, mask, probability, track rendering
- Grooves (7 tests) — timing offsets, velocity curves, validation
- L-System (5 tests) — all presets, custom rules, growth limits
- Progressions (6 tests) — all named progressions buildable, key transposition
- Serialization (3 tests) — song/pattern roundtrip, timing_offset preservation
- MIDI Export (4 tests) — basic, multi-track, metronome, pattern-to-midi
- Drum Patterns (3 tests) — all styles, unknown style fallback
- Pattern Morph (2 tests) — position 0 and 1
- Arrangement (2 tests) — verse/chorus structure, MIDI export
- Tie Rendering (2 tests) — tied and non-tied duration
- Edge Cases (5 tests) — empty pattern, solo, clamping, octave shift
- Config (8 tests) — defaults, from dict, JSON roundtrip, validation
- Validation (14 tests) — all validators, valid and invalid inputs
- Analysis (8 tests) — stats, summary, visualizations, distributions
- Batch (4 tests) — recipe, variations, scales, progressions
- Extended Drums (5 tests) — styles, fallback, listing
- CLI (4 tests) — info, generate with/without output
- Regression (1 test) — negative octave roundtrip

## Roadmap

- [ ] **Real-time MIDI input** — Record patterns from a MIDI controller
- [ ] **MIDI file import** — Parse existing .mid files into Song objects
- [ ] **Web UI** — Flask/FastAPI interface for visual composition
- [ ] **Audio rendering** — WAV/FLAC export via fluidsynth
- [ ] **MIDI CC automation** — Control change lanes for filters, effects
- [ ] **Polyrhythmic support** — Multiple pattern lengths per song
- [ ] **Microtonal scales** — Custom tuning and non-12-TET support
- [ ] **MusicXML export** — Notation-friendly output format
- [ ] **Genetic algorithms** — Evolve patterns toward musical targets
- [ ] **Style transfer** — Neural network-based style adaptation
- [ ] **Plugin system** — Third-party generator and effect plugins

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing guidelines, and ideas for contributions.

## Changelog

### v3.0.0 — Comprehensive Improvement
- Added configuration management (YAML/TOML/JSON)
- Added input validation module with 14 validators
- Added analysis module with stats, visualizations, distributions
- Added batch composition (variations, explorations, parameter sweeps)
- Added 8 extended drum patterns (jungle, garage, techno, trap, etc.)
- Added MIDI playback support (optional backends)
- Added centralized logging system
- Added `analyze`, `batch`, `config` CLI commands
- Enhanced CLI with `--summary`, `--visualize` flags
- Added `info drums` command showing all drum styles
- Added `pyproject.toml` for pip-installable package
- Added GitHub Actions CI configuration
- Added 6 usage example scripts in `examples/`
- Added MIT LICENSE file
- Added CONTRIBUTING.md
- Added sample configuration file
- Expanded test suite from 66 to 124 tests
- Updated `__init__.py` with full public API exports

### v2.0.0 — Enhancement Phase
- Fixed Euclidean rhythm algorithm (Bresenham-style)
- Fixed negative octave roundtrip
- Fixed groove timing offset storage
- Fixed serialization of timing_offset
- Fixed arrangement timing_offset copy
- Added comprehensive test suite (66 tests)

### v1.0.0 — Initial Release
- Core sequencer with Step/Pattern/Track/Song data model
- 15 scales, 11 chord types
- 6 generative algorithms (Euclidean, Markov, random, drums, L-System, progressions)
- 6 groove templates, 5 velocity curves
- Multi-track MIDI export
- JSON serialization
- Song arrangement system
- CLI interface
- 3 preset templates

## License

MIT License — see [LICENSE](LICENSE) for details.