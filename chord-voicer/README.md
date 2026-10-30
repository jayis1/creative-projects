# Chord Voicer

A dependency-free harmony utility that finds a smooth sequence of chord inversions in a chosen MIDI register. Its twist is a global dynamic-programming search: it minimizes total movement across the whole progression rather than greedily choosing each next chord.

Useful for sketching playable keyboard parts, generating compact backing voicings, and inspecting voice-leading choices before exporting them into a DAW.

## How it works

Chord symbols map to pitch classes. The solver enumerates every distinct octave placement inside the inclusive register, then dynamic programming minimizes summed per-voice semitone travel. Ties use a deterministic lexicographic rule. MIDI notes are restricted to 0–127 (middle C = 60).

Supported qualities: major (`C`), minor (`Am`), diminished (`Bdim`), augmented (`Caug`), dominant seventh (`G7`), and minor seventh (`Dm7`). Roots support sharps and flats; slash-bass chords such as `C/E` require the bass to be a chord tone.

## Run

Requires Python 3.10+; no dependencies.

```sh
python3 chord_voicer.py C F G C
```

Exact output:

```text
C: 48 52 55
F: 48 53 57
G: 50 55 59
C: 52 55 60
```

Set inclusive bounds using `--low` and `--high`; `--stats` reports total movement:

```sh
python3 chord_voicer.py --stats C/E F G
```

For downstream tools, select JSON output. Each chord includes the original symbol, sorted MIDI notes, and note names with MIDI octave numbering; the response also includes progression motion:

```sh
python3 chord_voicer.py --format json C/E F G
```

The command prints valid JSON to standard output. Unsupported chords and invalid MIDI bounds produce a concise CLI error and exit status 2 rather than a traceback.

Run tests:

```sh
python3 -m unittest discover -s tests -v
```

## Recent improvements

- Added slash-bass inversions (for example `C/E`), constrained to put the specified chord tone in the bass.
- Added `--stats` and `total_motion()` for summed semitone travel.
- Added JSON output (`--format json`) with MIDI numbers, note names, and total motion for DAW or script integration.
- Added CLI-friendly validation errors and regression tests for invalid chords, bass notes, and MIDI bounds.

## Limitations

- Only major, minor, diminished, augmented, dominant seventh, and minor seventh chord qualities are supported.
- Slash bass must be one of the chord's existing tones; non-chord bass notes and extensions are not modeled.
- The optimizer assigns sorted pitches to voices and minimizes semitone travel; it does not model instrument-specific fingering or voice-crossing preferences.
