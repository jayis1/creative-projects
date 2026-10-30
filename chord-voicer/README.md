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

Run tests:

```sh
python3 -m unittest discover -s tests -v
```

## Phase 2 enhancements

- Slash-bass inversions (for example `C/E`) are constrained to put the specified chord tone in the bass.
- `--stats` and `total_motion()` report summed semitone travel.
- Added strict slash-bass validation and regression tests.

## Known Issues (Resolved)

- The initial register validation allowed negative and above-127 note numbers, although output is labeled as MIDI. A regression test first reproduced both invalid bounds being accepted; the solver now rejects values outside the MIDI note domain (0–127).
