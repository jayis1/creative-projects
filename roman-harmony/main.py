#!/usr/bin/env python3
"""Analyze Roman-numeral progressions in major/minor keys."""
from __future__ import annotations
import argparse
import json
import re
from dataclasses import asdict, dataclass

PITCHES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PATTERN = re.compile(r"^([b#]?)([ivIV]+)(°|o|\+)?(7|6|64)?$")

@dataclass(frozen=True)
class Chord:
    token: str
    root: str
    quality: str
    notes: tuple[str, ...]
    function: str


def pitch_class(note: str) -> int:
    """Convert a spelled note (A-G with one optional accidental) to a pitch class."""
    match = re.fullmatch(r"([A-G])([#b]?)", note)
    if not match:
        raise ValueError(f"invalid note: {note!r}")
    letter, accidental = match.groups()
    return (NATURAL[letter] + (1 if accidental == "#" else -1 if accidental == "b" else 0)) % 12


def note_name(pc: int) -> str:
    return PITCHES[pc % 12]


def analyze(token: str, key: str = "C", mode: str = "major") -> Chord:
    """Build a diatonic triad/seventh from a Roman numeral in a major or natural-minor key."""
    if mode not in {"major", "minor"}:
        raise ValueError("mode must be 'major' or 'minor'")
    m = PATTERN.fullmatch(token)
    if not m:
        raise ValueError(f"unsupported Roman numeral: {token!r}")
    accidental, roman, marker, extension = m.groups()
    numeral = roman.upper()
    degree_map = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6}
    if numeral not in degree_map:
        raise ValueError(f"invalid Roman numeral: {roman!r}")
    degree = degree_map[numeral]
    if mode == "major":
        scale = (0, 2, 4, 5, 7, 9, 11)
        functions = ("tonic", "supertonic", "mediant", "subdominant", "dominant", "submediant", "leading-tone")
    else:
        scale = (0, 2, 3, 5, 7, 8, 10)
        functions = ("tonic", "supertonic", "mediant", "subdominant", "dominant", "submediant", "subtonic")
    root = (pitch_class(key) + scale[degree] + (1 if accidental == "#" else -1 if accidental == "b" else 0)) % 12
    # Roman-numeral case explicitly encodes chord quality; symbols take precedence.
    quality = "diminished" if marker in {"°", "o"} else "augmented" if marker == "+" else ("minor" if roman.islower() else "major")
    intervals = {"major": (0, 4, 7), "minor": (0, 3, 7), "diminished": (0, 3, 6), "augmented": (0, 4, 8)}[quality]
    notes = tuple(note_name(root + interval) for interval in intervals)
    if extension == "7":
        # Diatonic seventh quality follows the scale; dominant V7 is minor-seventh.
        seventh = 10 if numeral == "V" else {"major": 11, "minor": 10, "diminished": 9, "augmented": 10}[quality]
        notes += (note_name(root + seventh),)
    elif extension in {"6", "64"}:
        # Inversion is intentionally represented as a note ordering, not a different pitch set.
        inversion = 1 if extension == "6" else 2
        notes = notes[inversion:] + notes[:inversion]
    return Chord(token, note_name(root), quality, notes, functions[degree])


def progression(tokens: list[str], key: str = "C", mode: str = "major") -> list[Chord]:
    if not tokens:
        raise ValueError("progression must contain at least one chord")
    return [analyze(token, key, mode) for token in tokens]


def classify_cadence(chords: list[Chord]) -> str:
    """Classify a recognizable cadence from the final two scale-degree functions."""
    if len(chords) < 2:
        return "incomplete"
    penultimate, final = chords[-2:]
    if penultimate.function == "dominant" and final.function == "tonic":
        return "authentic"
    if penultimate.function == "subdominant" and final.function == "tonic":
        return "plagal"
    if penultimate.function == "dominant" and final.function == "submediant":
        return "deceptive"
    if final.function == "dominant":
        return "half"
    return "none"


def progression_report(tokens: list[str], key: str = "C", mode: str = "major") -> dict:
    """Return chord details plus a cadence label for a complete progression."""
    chords = progression(tokens, key, mode)
    return {"key": key, "mode": mode, "chords": [asdict(c) for c in chords], "cadence": classify_cadence(chords)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("numerals", nargs="+", help="e.g. I vi IV V7")
    parser.add_argument("--key", default="C")
    parser.add_argument("--mode", choices=("major", "minor"), default="major")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--report", action="store_true", help="include key, mode, and final cadence")
    args = parser.parse_args()
    try:
        chords = progression(args.numerals, args.key, args.mode)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        payload = progression_report(args.numerals, args.key, args.mode) if args.report else [asdict(c) for c in chords]
        print(json.dumps(payload, indent=2))
    else:
        for chord in chords:
            print(f"{chord.token:5} {chord.root:2} {chord.quality:11} {' '.join(chord.notes):14} {chord.function}")
        if args.report:
            print(f"Cadence: {classify_cadence(chords)}")

if __name__ == "__main__":
    main()
