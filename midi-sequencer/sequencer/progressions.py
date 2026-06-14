"""Common chord progressions and progression builder."""

from __future__ import annotations
from typing import List, Tuple, Dict
from sequencer.scales import SCALE_INTERVALS, note_to_midi, chord_notes


# Common chord progressions as (degree, quality) tuples
# Degree is 1-based: 1=I, 2=ii, 3=iii, etc.
# These return lists of (root_note_name, chord_quality) given a key

def _degree_to_note(root: str, degree: int, scale: str = "major") -> str:
    """Convert a scale degree (1-based) to a note name in the given key.

    Args:
        root: Root note name (e.g. 'C', 'F#')
        degree: Scale degree 1-7
        scale: Scale type

    Returns:
        Note name string
    """
    chromatic = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    root_idx = chromatic.index(root) if root in chromatic else 0
    intervals = SCALE_INTERVALS[scale]
    degree_idx = (degree - 1) % len(intervals)
    note_idx = (root_idx + intervals[degree_idx]) % 12
    return chromatic[note_idx]


def _degree_quality(degree: int, scale: str = "major") -> str:
    """Determine the default chord quality for a scale degree.

    In major: I-ii-iii-IV-V-vi-vii°
    In minor: i-ii°-III-iv-v-VI-VII (natural minor)
    """
    if scale in ("major", "ionian"):
        qualities = {1: "maj7", 2: "min7", 3: "min7", 4: "maj7", 5: "dom7", 6: "min7", 7: "dim"}
    elif scale in ("minor", "natural_minor", "aeolian"):
        qualities = {1: "min7", 2: "dim", 3: "maj7", 4: "min7", 5: "min7", 6: "maj7", 7: "dom7"}
    elif scale == "dorian":
        qualities = {1: "min7", 2: "min7", 3: "maj7", 4: "dom7", 5: "min7", 6: "dim", 7: "maj7"}
    elif scale == "mixolydian":
        qualities = {1: "dom7", 2: "min7", 3: "dim", 4: "maj7", 5: "min7", 6: "min7", 7: "maj7"}
    else:
        qualities = {1: "maj7", 2: "min7", 3: "min7", 4: "maj7", 5: "dom7", 6: "min7", 7: "dim"}

    return qualities.get(degree, "maj7")


# Named progressions: list of (degree, optional_quality_override)
PROGRESSIONS: Dict[str, List[Tuple[int, str]]] = {
    # Pop/rock
    "pop_I_V_vi_IV": [(1, "maj"), (5, "maj"), (6, "min"), (4, "maj")],
    "pop_vi_IV_I_V": [(6, "min"), (4, "maj"), (1, "maj"), (5, "maj")],
    "50s_I_vi_IV_V": [(1, "maj"), (6, "min"), (4, "maj"), (5, "maj")],

    # Jazz
    "jazz_ii_V_I": [(2, "min7"), (5, "dom7"), (1, "maj7")],
    "jazz_i_vi_ii_V": [(1, "maj7"), (6, "min7"), (2, "min7"), (5, "dom7")],
    "rhythm_changes": [(1, "maj7"), (6, "min7"), (2, "min7"), (5, "dom7")],

    # Blues
    "blues_12bar": [(1, "dom7"), (1, "dom7"), (1, "dom7"), (1, "dom7"),
                    (4, "dom7"), (4, "dom7"), (1, "dom7"), (1, "dom7"),
                    (5, "dom7"), (4, "dom7"), (1, "dom7"), (5, "dom7")],

    # Classical
    "classical_I_IV_V_I": [(1, "maj"), (4, "maj"), (5, "maj"), (1, "maj")],
    "classical_i_iv_V_i": [(1, "min"), (4, "min"), (5, "maj"), (1, "min")],
    "andalusian": [(6, "min"), (5, "maj"), (4, "maj"), (3, "maj")],
}


def build_progression(
    prog_name: str,
    key: str = "C",
    scale: str = "major",
) -> List[Tuple[str, str]]:
    """Build a chord progression by name in a given key.

    Args:
        prog_name: Name from PROGRESSIONS dict
        key: Root key
        scale: Scale for degree resolution

    Returns:
        List of (root_note, chord_quality) tuples
    """
    if prog_name not in PROGRESSIONS:
        raise ValueError(f"Unknown progression: {prog_name!r}. Choose from: {list(PROGRESSIONS)}")

    result = []
    for degree, quality in PROGRESSIONS[prog_name]:
        root_note = _degree_to_note(key, degree, scale)
        result.append((root_note, quality))

    return result


def list_progressions() -> Dict[str, List[Tuple[int, str]]]:
    """Return all available named chord progressions."""
    return dict(PROGRESSIONS)