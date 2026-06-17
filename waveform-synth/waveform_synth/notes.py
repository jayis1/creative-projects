"""
Musical scale and note definitions.

Provides note-to-frequency conversion, scale definitions, and
chord generation for use in compositions.
"""

import math
from typing import List, Dict, Optional


# A4 = 440 Hz, reference pitch
A4_FREQ = 440.0

# Note names
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# MIDI note number for A4
A4_MIDI = 69


def midi_to_freq(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return A4_FREQ * (2.0 ** ((midi_note - A4_MIDI) / 12.0))


def note_to_midi(note_name: str) -> int:
    """
    Convert a note name like 'C4', 'A#3', 'Bb5' to a MIDI note number.

    Supports sharps (#) and flats (b).

    Args:
        note_name: Note name with octave, e.g. 'C4', 'F#5', 'Bb3'.

    Returns:
        MIDI note number.

    Raises:
        ValueError: If the note name is invalid.
    """
    note_name = note_name.strip()

    # Parse the note letter
    if len(note_name) < 2:
        raise ValueError(f"Invalid note name: '{note_name}'")

    letter = note_name[0].upper()
    if letter not in NOTE_NAMES:
        raise ValueError(f"Invalid note letter: '{letter}'")

    note_idx = NOTE_NAMES.index(letter)

    # Parse accidental and octave
    rest = note_name[1:]
    accidental = 0

    if rest.startswith('#'):
        accidental = 1
        rest = rest[1:]
    elif rest.startswith('b'):
        # Don't confuse B-natural with flat
        # 'b' is flat only if followed by a digit
        if len(rest) > 1 and rest[1:].lstrip('-').isdigit():
            accidental = -1
            rest = rest[1:]

    # Parse octave
    try:
        octave = int(rest)
    except ValueError:
        raise ValueError(f"Invalid octave in note name: '{note_name}'")

    # MIDI note calculation: C4 = 60
    midi = (octave + 1) * 12 + note_idx + accidental
    return midi


def note_to_freq(note_name: str) -> float:
    """Convert a note name to frequency in Hz."""
    return midi_to_freq(note_to_midi(note_name))


# Scale definitions (intervals in semitones from root)
SCALES: Dict[str, List[int]] = {
    "major":            [0, 2, 4, 5, 7, 9, 11],
    "natural_minor":    [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor":   [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor":    [0, 2, 3, 5, 7, 9, 11],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "lydian":           [0, 2, 4, 6, 7, 9, 11],
    "mixolydian":       [0, 2, 4, 5, 7, 9, 10],
    "pentatonic":       [0, 2, 4, 7, 9],
    "blues":            [0, 3, 5, 6, 7, 10],
    "chromatic":        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "whole_tone":       [0, 2, 4, 6, 8, 10],
}

# Chord definitions (intervals in semitones from root)
CHORDS: Dict[str, List[int]] = {
    "major":      [0, 4, 7],
    "minor":      [0, 3, 7],
    "diminished": [0, 3, 6],
    "augmented":  [0, 4, 8],
    "dom7":       [0, 4, 7, 10],
    "maj7":       [0, 4, 7, 11],
    "min7":       [0, 3, 7, 10],
    "sus2":       [0, 2, 7],
    "sus4":       [0, 5, 7],
    "add9":       [0, 4, 7, 14],
}


def generate_scale(root: str, scale_name: str, octave: int = 4, num_octaves: int = 1) -> List[float]:
    """
    Generate frequencies for a musical scale.

    Args:
        root: Root note name (e.g. 'C', 'A').
        scale_name: Scale name from SCALES dict.
        octave: Starting octave.
        num_octaves: Number of octaves to generate.

    Returns:
        List of frequencies in Hz.
    """
    if scale_name not in SCALES:
        raise ValueError(f"Unknown scale '{scale_name}'. Available: {list(SCALES.keys())}")

    intervals = SCALES[scale_name]
    root_midi = note_to_midi(f"{root}{octave}")

    frequencies = []
    for octave_offset in range(num_octaves):
        for interval in intervals:
            midi = root_midi + interval + octave_offset * 12
            frequencies.append(midi_to_freq(midi))

    # Add the root an octave up
    frequencies.append(midi_to_freq(root_midi + num_octaves * 12))

    return frequencies


def generate_chord(root: str, chord_name: str, octave: int = 4) -> List[float]:
    """
    Generate frequencies for a chord.

    Args:
        root: Root note name (e.g. 'C', 'A').
        chord_name: Chord name from CHORDS dict.
        octave: Octave for the root.

    Returns:
        List of frequencies in Hz.
    """
    if chord_name not in CHORDS:
        raise ValueError(f"Unknown chord '{chord_name}'. Available: {list(CHORDS.keys())}")

    intervals = CHORDS[chord_name]
    root_midi = note_to_midi(f"{root}{octave}")

    return [midi_to_freq(root_midi + interval) for interval in intervals]