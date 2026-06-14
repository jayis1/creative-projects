#!/usr/bin/env python3
"""Example: Arrangement — build verse/chorus/verse song structure.

Shows how to use the Arrangement system to create a song with
multiple sections, each with different patterns.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sequencer.generators import euclidean_pattern, drum_pattern, bassline_from_chords
from sequencer.arrangement import Arrangement, Section
from sequencer.export import song_to_midi
from sequencer.analysis import song_summary

# Create verse patterns
verse_melody = euclidean_pattern(3, 16, root="A", scale="minor", octave=5, velocity=80)
verse_drums = drum_pattern("four_on_floor", 16)
verse_bass = bassline_from_chords([("A", "min7")], 16, octave=2, pattern_type="steady")

# Create chorus patterns (more energetic)
chorus_melody = euclidean_pattern(7, 16, root="A", scale="minor", octave=5, velocity=110)
chorus_drums = drum_pattern("breakbeat", 16)
chorus_bass = bassline_from_chords([("A", "min7")], 16, octave=2, pattern_type="walking")

# Build the arrangement
arr = Arrangement(name="Dark Minor Song", bpm=125)

verse = Section(
    name="Verse",
    tracks={
        "Lead": (verse_melody, 0, 81),
        "Bass": (verse_bass, 1, 34),
        "Drums": (verse_drums, 9, 0),
    },
    repeats=2,
)

chorus = Section(
    name="Chorus",
    tracks={
        "Lead": (chorus_melody, 0, 81),
        "Bass": (chorus_bass, 1, 34),
        "Drums": (chorus_drums, 9, 0),
    },
    repeats=2,
)

# Structure: Verse -> Chorus -> Verse -> Chorus
arr.add_section(verse).add_section(chorus).add_section(verse).add_section(chorus)

# Render and export
song = arr.render_to_song()
output = "example_arrangement.mid"
arr.export_midi(output)

print(song_summary(song))
print(f"\nExported arrangement to {output}")