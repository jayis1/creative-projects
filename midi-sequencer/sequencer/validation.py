"""Input validation utilities for the MIDI Step Sequencer.

Provides validation functions for musical parameters, ensuring
all inputs are within valid ranges before processing.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from sequencer.scales import SCALE_INTERVALS, CHORD_INTERVALS, NOTE_OFFSETS


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def validate_note_name(note: str) -> str:
    """Validate and normalize a note name.

    Args:
        note: Note name string (e.g. 'C', 'F#', 'Bb')

    Returns:
        Normalized note name

    Raises:
        ValidationError: If note name is invalid
    """
    note = note.strip()
    if not note:
        raise ValidationError("Note name cannot be empty")

    # Extract the base note name (before octave digits)
    i = len(note) - 1
    while i >= 0 and note[i].isdigit():
        i -= 1
    if i >= 0 and note[i] == '-':
        i -= 1
    base = note[:i + 1]

    if base not in NOTE_OFFSETS:
        raise ValidationError(
            f"Invalid note name: {base!r}. "
            f"Valid note names: {sorted(NOTE_OFFSETS.keys())}"
        )
    return note


def validate_scale(scale: str) -> str:
    """Validate a scale name.

    Args:
        scale: Scale name string

    Returns:
        The validated scale name

    Raises:
        ValidationError: If scale name is not recognized
    """
    if scale not in SCALE_INTERVALS:
        raise ValidationError(
            f"Unknown scale: {scale!r}. "
            f"Available scales: {sorted(SCALE_INTERVALS.keys())}"
        )
    return scale


def validate_chord_quality(quality: str) -> str:
    """Validate a chord quality name.

    Args:
        quality: Chord quality string

    Returns:
        The validated quality name

    Raises:
        ValidationError: If chord quality is not recognized
    """
    if quality not in CHORD_INTERVALS:
        raise ValidationError(
            f"Unknown chord quality: {quality!r}. "
            f"Available qualities: {sorted(CHORD_INTERVALS.keys())}"
        )
    return quality


def validate_midi_note(note: int) -> int:
    """Validate a MIDI note number.

    Args:
        note: MIDI note number

    Returns:
        The validated note number, clamped to 0-127

    Raises:
        ValidationError: If note is wildly out of range
    """
    if note < -100 or note > 300:
        raise ValidationError(f"MIDI note {note} is far out of range (0-127)")
    return max(0, min(127, note))


def validate_velocity(velocity: int) -> int:
    """Validate and clamp a MIDI velocity value.

    Args:
        velocity: Velocity value

    Returns:
        Clamped velocity (1-127)

    Raises:
        ValidationError: If velocity is wildly out of range
    """
    if velocity < -50 or velocity > 300:
        raise ValidationError(f"Velocity {velocity} is far out of range (1-127)")
    return max(1, min(127, velocity))


def validate_channel(channel: int) -> int:
    """Validate a MIDI channel number.

    Args:
        channel: MIDI channel (0-15)

    Returns:
        The validated channel

    Raises:
        ValidationError: If channel is out of range
    """
    if not 0 <= channel <= 15:
        raise ValidationError(f"MIDI channel must be 0-15, got {channel}")
    return channel


def validate_program(program: int) -> int:
    """Validate a MIDI program number.

    Args:
        program: MIDI program (0-127)

    Returns:
        The validated program

    Raises:
        ValidationError: If program is out of range
    """
    if not 0 <= program <= 127:
        raise ValidationError(f"MIDI program must be 0-127, got {program}")
    return program


def validate_bpm(bpm: int) -> int:
    """Validate a BPM value.

    Args:
        bpm: Beats per minute

    Returns:
        The validated BPM

    Raises:
        ValidationError: If BPM is out of reasonable range
    """
    if not 20 <= bpm <= 300:
        raise ValidationError(f"BPM must be 20-300, got {bpm}")
    return bpm


def validate_octave(octave: int) -> int:
    """Validate an octave number.

    Args:
        octave: Octave number (typically -1 to 9)

    Returns:
        The validated octave

    Raises:
        ValidationError: If octave is wildly out of range
    """
    if not -2 <= octave <= 10:
        raise ValidationError(f"Octave must be -2 to 10, got {octave}")
    return octave


def validate_pattern_length(length: int) -> int:
    """Validate a pattern length.

    Args:
        length: Pattern length in steps

    Returns:
        The validated length

    Raises:
        ValidationError: If length is invalid
    """
    if length < 1:
        raise ValidationError(f"Pattern length must be >= 1, got {length}")
    if length > 1024:
        raise ValidationError(f"Pattern length > 1024 is impractical, got {length}")
    return length


def validate_density(density: float) -> float:
    """Validate a density value.

    Args:
        density: Note density (0.0-1.0)

    Returns:
        The validated density

    Raises:
        ValidationError: If density is out of range
    """
    if not 0.0 <= density <= 1.0:
        raise ValidationError(f"Density must be 0.0-1.0, got {density}")
    return density


def validate_gate(gate: float) -> float:
    """Validate a gate value.

    Args:
        gate: Gate length (0.0-1.0)

    Returns:
        The validated gate

    Raises:
        ValidationError: If gate is out of range
    """
    if not 0.0 <= gate <= 1.0:
        raise ValidationError(f"Gate must be 0.0-1.0, got {gate}")
    return gate


def validate_probability(probability: float) -> float:
    """Validate a probability value.

    Args:
        probability: Step probability (0.0-1.0)

    Returns:
        The validated probability

    Raises:
        ValidationError: If probability is out of range
    """
    if not 0.0 <= probability <= 1.0:
        raise ValidationError(f"Probability must be 0.0-1.0, got {probability}")
    return probability


def validate_time_signature(ts: Tuple[int, int]) -> Tuple[int, int]:
    """Validate a time signature.

    Args:
        ts: (beats_per_bar, beat_unit)

    Returns:
        The validated time signature

    Raises:
        ValidationError: If time signature is invalid
    """
    beats, unit = ts
    if beats < 1 or beats > 32:
        raise ValidationError(f"Beats per bar must be 1-32, got {beats}")
    if unit not in (1, 2, 4, 8, 16, 32):
        raise ValidationError(f"Beat unit must be a power of 2 (1,2,4,8,16,32), got {unit}")
    return ts