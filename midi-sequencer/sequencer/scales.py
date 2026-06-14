"""Musical scales, chords, and note utilities."""

from __future__ import annotations
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

# Semitone offsets from root for each scale type
SCALE_INTERVALS: Dict[str, Tuple[int, ...]] = {
    "major":             (0, 2, 4, 5, 7, 9, 11),
    "minor":             (0, 2, 3, 5, 7, 8, 10),        # alias for natural_minor
    "natural_minor":     (0, 2, 3, 5, 7, 8, 10),
    "harmonic_minor":    (0, 2, 3, 5, 7, 8, 11),
    "melodic_minor":     (0, 2, 3, 5, 7, 9, 11),
    "dorian":            (0, 2, 3, 5, 7, 9, 10),
    "phrygian":          (0, 1, 3, 5, 7, 8, 10),
    "lydian":            (0, 2, 4, 6, 7, 9, 11),
    "mixolydian":        (0, 2, 4, 5, 7, 9, 10),
    "phrygian_dominant": (0, 1, 3, 5, 7, 8, 10),
    "whole_tone":        (0, 2, 4, 6, 8, 10),
    "pentatonic_major":  (0, 2, 4, 7, 9),
    "pentatonic_minor":  (0, 3, 5, 7, 10),
    "blues":             (0, 3, 5, 6, 7, 10),
    "chromatic":         tuple(range(12)),
}

# Note name -> MIDI offset within octave (C4 = 60)
NOTE_OFFSETS: Dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

# Chord quality -> semitone offsets from root
CHORD_INTERVALS: Dict[str, Tuple[int, ...]] = {
    "maj":   (0, 4, 7),
    "min":   (0, 3, 7),
    "dim":   (0, 3, 6),
    "aug":   (0, 4, 8),
    "maj7":  (0, 4, 7, 11),
    "min7":  (0, 3, 7, 10),
    "dom7":  (0, 4, 7, 10),
    "dim7":  (0, 3, 6, 9),
    "sus2":  (0, 2, 7),
    "sus4":  (0, 5, 7),
    "add9":  (0, 4, 7, 14),
}


def note_to_midi(note: str) -> int:
    """Convert a note name like 'C4', 'F#3', 'Bb5' to a MIDI note number.

    C4 = 60 (middle C). Supports negative octaves: 'C-1' = 0.
    """
    note = note.strip()
    # Find where the octave starts — look for the last digit sequence,
    # which may be preceded by a minus sign for negative octaves.
    i = len(note) - 1
    while i >= 0 and note[i].isdigit():
        i -= 1
    # Check for negative octave sign
    if i >= 0 and note[i] == '-':
        i -= 1
    name = note[:i + 1]
    octave_str = note[i + 1:]
    octave = int(octave_str) if octave_str else 4
    if name not in NOTE_OFFSETS:
        raise ValueError(f"Unknown note name: {name!r}")
    return NOTE_OFFSETS[name] + (octave + 1) * 12


def midi_to_note(midi: int) -> str:
    """Convert MIDI note number to note name like 'C4'.

    Uses sharps by default for enharmonic equivalents.
    """
    octave = midi // 12 - 1
    offset = midi % 12
    # Prefer sharp names for simplicity; avoid flat names that contain 'b'
    # which conflicts with the letter 'B'
    sharp_names = {0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5: "F",
                   6: "F#", 7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B"}
    name = sharp_names.get(offset, "C")
    return f"{name}{octave}"


def scale_notes(root: str, scale: str, octaves: int = 2, start_octave: int = 3) -> List[int]:
    """Return a list of MIDI note numbers for the given scale.

    Args:
        root: Root note name without octave, e.g. 'C', 'F#', 'Bb'
        scale: Scale type name from SCALE_INTERVALS
        octaves: Number of octaves to span
        start_octave: First octave number
    """
    if scale not in SCALE_INTERVALS:
        raise ValueError(f"Unknown scale: {scale!r}. Choose from: {list(SCALE_INTERVALS)}")
    root_midi = note_to_midi(f"{root}{start_octave}")
    intervals = SCALE_INTERVALS[scale]
    notes = []
    for oct_offset in range(octaves):
        for interval in intervals:
            notes.append(root_midi + oct_offset * 12 + interval)
    # Include top root
    notes.append(root_midi + octaves * 12)
    return notes


def chord_notes(root: str, quality: str, octave: int = 4) -> List[int]:
    """Return MIDI note numbers for a chord.

    Args:
        root: Root note name without octave, e.g. 'C', 'Eb'
        quality: Chord quality from CHORD_INTERVALS
        octave: Octave number
    """
    if quality not in CHORD_INTERVALS:
        raise ValueError(f"Unknown chord quality: {quality!r}. Choose from: {list(CHORD_INTERVALS)}")
    root_midi = note_to_midi(f"{root}{octave}")
    return [root_midi + interval for interval in CHORD_INTERVALS[quality]]


def degree_to_note(root: str, scale: str, degree: int, octave: int = 4) -> int:
    """Convert a scale degree (1-based) to a MIDI note number.

    degree=1 is the root, degree=2 is the second, etc.
    Degrees > 7 go up octaves (8 = root + octave).
    """
    notes = scale_notes(root, scale, 2, octave)
    idx = degree - 1
    if idx < 0 or idx >= len(notes):
        raise ValueError(f"Degree {degree} out of range for scale with {len(notes)} notes")
    return notes[idx]


def quantize_to_scale(note: int, root: str, scale: str) -> int:
    """Snap a MIDI note to the nearest note in the given scale."""
    scale_pitches = set(n % 12 for n in scale_notes(root, scale, 1, 4))
    note_class = note % 12
    if note_class in scale_pitches:
        return note
    # Search up and down for nearest scale tone
    for offset in range(1, 6):
        up = (note_class + offset) % 12
        down = (note_class - offset) % 12
        if up in scale_pitches:
            return note + offset
        if down in scale_pitches:
            return note - offset
    return note