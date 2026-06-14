"""Preset song templates for quick-start compositions."""

from sequencer.patterns import Song, Track, Pattern, Step
from sequencer.generators import (
    drum_pattern, euclidean_pattern, chord_pattern, bassline_from_chords,
    markov_pattern, random_pattern,
)
from sequencer.scales import chord_notes


def preset_four_on_floor(key: str = "C", bpm: int = 128) -> Song:
    """Classic 4/4 dance pattern: kick + snare + hi-hat + bass + chords.

    Args:
        key: Root key (e.g., 'C', 'Eb')
        bpm: Tempo in BPM
    """
    drums = Track(
        name="Drums",
        pattern=drum_pattern("four_on_floor", 16),
        channel=9,
        program=0,
        volume=110,
    )

    chords = chord_pattern(
        chords=[(key, "min7"), (f"{key}m" if len(key) == 1 else key, "min7")],
        length_per_chord=16,
        octave=4,
        arpeggiate=True,
        velocity=70,
    )
    chord_track = Track(
        name="Chords",
        pattern=chords,
        channel=1,
        program=4,  # Electric piano
        volume=85,
    )

    bass = bassline_from_chords(
        chords=[(key, "min7")],
        length_per_chord=16,
        octave=2,
        pattern_type="steady",
    )
    bass_track = Track(
        name="Bass",
        pattern=bass,
        channel=2,
        program=34,  # Electric bass
        volume=100,
    )

    melody = euclidean_pattern(5, 16, root=key, scale="pentatonic_minor", octave=5, velocity=90)
    melody_track = Track(
        name="Melody",
        pattern=melody,
        channel=3,
        program=81,  # Lead synth
        volume=90,
        humanize_velocity=5.0,
    )

    return Song(
        name=f"Four on Floor in {key}",
        tracks=[drums, chord_track, bass_track, melody_track],
        bpm=bpm,
    )


def preset_euclidean_jam(key: str = "A", bpm: int = 110) -> Song:
    """Multi-layer Euclidean rhythm composition.

    Args:
        key: Root key
        bpm: Tempo
    """
    drums = Track(
        name="Drums",
        pattern=drum_pattern("breakbeat", 16),
        channel=9,
        volume=100,
    )

    # Multiple Euclidean layers with different densities
    pat1 = euclidean_pattern(3, 8, root=key, scale="minor", octave=4, velocity=80)
    track1 = Track(name="Euc 3:8", pattern=pat1, channel=1, program=11, volume=85)

    pat2 = euclidean_pattern(5, 16, root=key, scale="pentatonic_minor", octave=5, velocity=75)
    track2 = Track(name="Euc 5:16", pattern=pat2, channel=2, program=81, volume=80)

    pat3 = euclidean_pattern(7, 16, root=key, scale="dorian", octave=3, velocity=70)
    track3 = Track(name="Euc 7:16", pattern=pat3, channel=3, program=33, volume=75)

    return Song(
        name=f"Euclidean Jam in {key}",
        tracks=[drums, track1, track2, track3],
        bpm=bpm,
    )


def preset_ambient_pad(key: str = "D", bpm: int = 72) -> Song:
    """Slow ambient pad with evolving chord changes.

    Args:
        key: Root key
        bpm: Slow tempo
    """
    # Chord progression: I - vi - IV - V
    from sequencer.scales import NOTE_OFFSETS
    # Build diatonic chords
    chord_progression = [
        (key, "maj7"),
        (_relative_minor(key), "min7"),
        (_fourth(key), "maj7"),
        (_fifth(key), "dom7"),
    ]

    chords = chord_pattern(chord_progression, length_per_chord=16, octave=3, velocity=60)
    pad_track = Track(
        name="Pad",
        pattern=chords,
        channel=0,
        program=89,  # Pad synth
        volume=75,
        humanize_velocity=3.0,
    )

    melody = markov_pattern(64, root=key, scale="major", octave=5, velocity=70)
    melody_track = Track(
        name="Melody",
        pattern=melody,
        channel=1,
        program=74,  # Flute
        volume=65,
        humanize_velocity=4.0,
        humanize_timing=2.0,
    )

    return Song(
        name=f"Ambient Pad in {key}",
        tracks=[pad_track, melody_track],
        bpm=bpm,
    )


def _relative_minor(key: str) -> str:
    """Get the relative minor root note."""
    intervals = {"C": "A", "C#": "A#", "D": "B", "Eb": "C", "E": "C#",
                 "F": "D", "F#": "D#", "G": "E", "Ab": "F", "A": "F#", "Bb": "G", "B": "G#"}
    return intervals.get(key, "A")


def _fourth(key: str) -> str:
    """Get the perfect fourth above."""
    order = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    idx = order.index(key) if key in order else 0
    return order[(idx + 5) % 12]


def _fifth(key: str) -> str:
    """Get the perfect fifth above."""
    order = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    idx = order.index(key) if key in order else 0
    return order[(idx + 7) % 12]


PRESETS = {
    "four_on_floor": preset_four_on_floor,
    "euclidean_jam": preset_euclidean_jam,
    "ambient_pad": preset_ambient_pad,
}