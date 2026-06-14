#!/usr/bin/env python3
"""Example: Multi-track song composition.

Shows how to build a complete song with drums, bass, chords, and melody.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sequencer.patterns import Song, Track
from sequencer.generators import (
    euclidean_pattern, drum_pattern, bassline_from_chords, chord_pattern,
)
from sequencer.grooves import apply_groove, apply_velocity_curve
from sequencer.progressions import build_progression
from sequencer.export import song_to_midi

# Build a chord progression
chords = build_progression("pop_I_V_vi_IV", key="C")
print(f"Chord progression: {chords}")

# Drum track — four on the floor
drums = Track(
    name="Drums",
    pattern=drum_pattern("four_on_floor", 16),
    channel=9,
    program=0,
    volume=110,
)

# Chord track — arpeggiated progression
chord_pat = chord_pattern(
    chords=chords,
    length_per_chord=16,
    octave=3,
    arpeggiate=True,
    velocity=70,
)
chord_track = Track(
    name="Chords",
    pattern=chord_pat,
    channel=1,
    program=4,  # Electric piano
    volume=85,
)

# Bass track — walking bass
bass = bassline_from_chords(
    chords=chords,
    length_per_chord=16,
    octave=2,
    pattern_type="walking",
)
bass_track = Track(
    name="Bass",
    pattern=bass,
    channel=2,
    program=34,  # Electric bass
    volume=100,
)

# Melody track — Euclidean pattern with groove
melody = euclidean_pattern(5, 16, root="C", scale="pentatonic_minor", octave=5, velocity=90)
melody = apply_groove(melody, "shuffle")
melody = apply_velocity_curve(melody, "swell")
melody_track = Track(
    name="Melody",
    pattern=melody,
    channel=3,
    program=81,  # Lead synth
    volume=90,
    humanize_velocity=5.0,
)

# Assemble song
song = Song(
    name="Pop Song in C",
    tracks=[drums, chord_track, bass_track, melody_track],
    bpm=120,
)

# Export
output = "example_multitrack.mid"
song_to_midi(song, output)
print(f"\nExported multi-track song to {output}")
print(f"  Tracks: {len(song.tracks)}")
print(f"  BPM: {song.bpm}")
for track in song.tracks:
    print(f"  - {track.name}: {track.pattern.length} steps, ch={track.channel}")