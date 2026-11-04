# Roman Harmony

A dependency-free Python toolkit and CLI for converting Roman-numeral harmony into named chords in major and natural-minor keys.

## How it works

The analyzer maps the key tonic to a pitch class, applies the selected diatonic scale's degree offset, and constructs a triad or seventh chord from its quality. Numeral case supplies the conventional minor/major alteration; `°`, `o`, and `+` explicitly select diminished or augmented triads. The optional `6` and `64` suffixes reorder triad tones to show first and second inversion. Notes use sharp pitch names for unambiguous output.

Supported tokens: I through VII (upper- or lowercase), one optional leading `b`/`#`, optional `°`/`o`/`+`, and optional `6`, `64`, or `7`. This is a deliberately bounded notation subset, not a full figured-bass parser.

## Usage

Requires Python 3.10+; no third-party packages.

```sh
cd roman-harmony
python3 main.py I vi IV V7
python3 main.py --key G --mode major I ii V7
python3 main.py --key A --mode minor i iv V --json
python3 -m unittest -v
```

The text view prints token, root, chord quality, ordered note names, and scale-degree function. `--json` emits the chord list for scripts. Add `--report` to classify the final cadence as authentic, plagal, deceptive, half, none, or incomplete; with `--json --report` the output is an object containing key, mode, chords, and cadence. The classifier is intentionally a simple final-two-function heuristic, not a full tonal-analysis engine. Invalid tokens, keys, and modes are rejected with a CLI usage error.

```sh
python3 main.py I V7 I --report
python3 main.py --key G V I --json --report
```

Library example:

```python
from main import progression, classify_cadence
chords = progression(["I", "IV", "V7", "I"], key="C")
print(classify_cadence(chords))  # authentic
```

## Phase 1 implementation

Includes pure-Python note parsing, major/natural-minor diatonic chord construction, triad quality alterations, seventh chords, inversions, validation, JSON/text CLI, and unit tests.
