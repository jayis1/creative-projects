#!/usr/bin/env python3
"""Example: Basic Euclidean rhythm generation and export.

Demonstrates the simplest way to create a Euclidean rhythm pattern
and export it to a MIDI file.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sequencer.generators import euclidean_pattern
from sequencer.export import pattern_to_midi

# Generate E(5,16) — 5 pulses evenly distributed across 16 steps
pattern = euclidean_pattern(
    beats=5,
    length=16,
    root="A",
    scale="pentatonic_minor",
    octave=4,
)

# Export to MIDI
output = "example_euclidean.mid"
pattern_to_midi(pattern, output, bpm=120)
print(f"Exported E(5,16) pattern to {output}")

# Print a visualization
print(f"\nPattern: {pattern.name} ({pattern.length} steps)")
for i, step in enumerate(pattern.steps):
    if step.notes:
        print(f"  Step {i:2d}: ▓ vel={step.velocity:3d} note={step.notes[0]}")
    else:
        print(f"  Step {i:2d}: · (rest)")