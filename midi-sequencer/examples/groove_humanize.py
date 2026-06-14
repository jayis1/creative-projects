#!/usr/bin/env python3
"""Example: Groove and humanization.

Demonstrates how to apply groove templates and humanization
to make MIDI patterns feel more natural and less robotic.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sequencer.patterns import Song, Track
from sequencer.generators import euclidean_pattern, drum_pattern
from sequencer.grooves import apply_groove, apply_velocity_curve
from sequencer.export import song_to_midi
from sequencer.analysis import visualize_pattern

# Start with a basic pattern
base = euclidean_pattern(7, 16, root="C", scale="dorian", octave=4)

print("=== Original Pattern ===")
print(visualize_pattern(base))

# Apply different grooves
for groove_name in ["swing_16th", "shuffle", "dilla", "bossa"]:
    grooved = apply_groove(base, groove_name, intensity=0.8)
    print(f"\n=== {groove_name.title()} Groove ===")
    print(visualize_pattern(grooved, style="dot"))

    # Export each grooved version
    song = Song(
        name=f"Groove Demo - {groove_name}",
        tracks=[Track(name=groove_name, pattern=grooved, channel=0, program=81)],
        bpm=110,
    )
    song_to_midi(song, f"example_groove_{groove_name}.mid")

# Apply velocity curves
for curve in ["crescendo", "diminuendo", "swell", "heartbeat"]:
    curved = apply_velocity_curve(base, curve)
    print(f"\n=== {curve.title()} Velocity ===")
    print(visualize_pattern(curved, style="dot"))

# Full humanized track
print("\n=== Fully Humanized ===")
humanized = euclidean_pattern(5, 16, root="A", scale="minor", octave=5)
humanized = apply_groove(humanized, "shuffle", intensity=0.6)
humanized = apply_velocity_curve(humanized, "swell")

drums = drum_pattern("four_on_floor", 16)
drums = apply_groove(drums, "dilla", intensity=0.4)

song = Song(
    name="Humanized Demo",
    tracks=[
        Track(name="Melody", pattern=humanized, channel=0, program=81,
              humanize_velocity=5.0, humanize_timing=3.0),
        Track(name="Drums", pattern=drums, channel=9,
              humanize_velocity=8.0, humanize_timing=2.0),
    ],
    bpm=115,
)
song_to_midi(song, "example_humanized.mid")
print("Exported humanized track to example_humanized.mid")