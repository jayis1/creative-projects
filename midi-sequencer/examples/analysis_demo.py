#!/usr/bin/env python3
"""Example: Song analysis and statistics.

Shows how to use the analysis module to understand the musical
content of generated songs.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sequencer.patterns import Song, Track
from sequencer.generators import euclidean_pattern, drum_pattern, bassline_from_chords
from sequencer.grooves import apply_groove
from sequencer.analysis import (
    pattern_stats, track_stats, song_stats, song_summary,
    visualize_pattern, note_distribution, interval_distribution,
)
import json

# Build a song to analyze
drums = Track(name="Drums", pattern=drum_pattern("four_on_floor", 16), channel=9)
melody = euclidean_pattern(5, 16, root="A", scale="minor", octave=5)
melody = apply_groove(melody, "shuffle")
melody_track = Track(name="Melody", pattern=melody, channel=0, program=81)
bass = bassline_from_chords([("A", "min7")], 16, octave=2, pattern_type="walking")
bass_track = Track(name="Bass", pattern=bass, channel=1, program=34)

song = Song(name="Analysis Demo", tracks=[drums, melody_track, bass_track], bpm=120)

# Song summary
print(song_summary(song))

# Pattern-level stats
print("\n--- Melody Pattern Stats ---")
melody_stats = pattern_stats(melody)
print(json.dumps(melody_stats, indent=2))

# Track-level stats
print("\n--- Track Stats ---")
for track in song.tracks:
    stats = track_stats(track)
    print(f"  {track.name}: density={stats['density']:.1%}, "
          f"notes={stats['note_count']}, vel_mean={stats['velocity_mean']:.0f}")

# Note distribution
print("\n--- Melody Note Distribution ---")
dist = note_distribution(melody)
for note, count in dist.items():
    bar = "█" * count
    print(f"  MIDI {note:3d}: {bar} ({count})")

# Interval distribution
print("\n--- Melody Interval Distribution ---")
intervals = interval_distribution(melody)
for interval, count in sorted(intervals.items()):
    direction = "↑" if interval > 0 else "↓" if interval < 0 else "─"
    bar = "█" * count
    print(f"  {interval:+3d} semitones {direction}: {bar} ({count})")

# Visualizations
print("\n--- Piano Roll View ---")
print(visualize_pattern(melody, style="piano"))

print("\n--- Block View ---")
print(visualize_pattern(melody, style="block"))

# Song-level stats
print("\n--- Full Song Stats ---")
full_stats = song_stats(song)
# Don't print nested track stats again
summary_stats = {k: v for k, v in full_stats.items() if k != "tracks"}
print(json.dumps(summary_stats, indent=2, default=str))