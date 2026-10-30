# Chord Voicer

A dependency-free harmony utility that finds a smooth sequence of chord inversions in a chosen MIDI register. Its twist is a global dynamic-programming search: it minimizes total movement across the whole progression rather than greedily choosing each next chord.

Useful for sketching playable keyboard parts, generating compact backing voicings, and inspecting voice-leading choices before exporting them into a DAW.

## How it works

Chord symbols map to pitch classes. The solver enumerates every distinct octave placement inside the inclusive note range, then dynamic programming minimizes the sum of per-voice semitone travel. Equal-cost paths use a deterministic lexicographic tie-break. MIDI note numbers are printed (middle C = 60).

Supported qualities: major (for example `C`), minor (`Am`), diminished (`Bdim`), augmented (`Caug`), dominant seventh (`G7`), and minor seventh (`Dm7`). Roots support sharps and flats.

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

Set the inclusive register with `--low` and `--high`:

```sh
python3 chord_voicer.py --low 55 --high 76 Am Dm7 G7 C
```

Run tests from this folder:

```sh
python3 -m unittest discover -s tests -v
```
