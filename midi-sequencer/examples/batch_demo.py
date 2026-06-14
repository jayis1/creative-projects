#!/usr/bin/env python3
"""Example: Batch composition — generate multiple variations at once.

Demonstrates the batch module for generating albums, parameter sweeps,
and systematic explorations.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sequencer.batch import (
    CompositionRecipe,
    parameter_sweep,
    euclidean_variations,
    scale_exploration,
    progression_album,
)

output_base = "example_batch_output"

# 1. Generate Euclidean variations
print("Generating Euclidean rhythm variations...")
files = euclidean_variations(
    root="A",
    scale="pentatonic_minor",
    bpm=110,
    beat_range=(3, 9),
    length=16,
    output_dir=f"{output_base}/euclidean",
)
print(f"  Generated {len(files)} files")

# 2. Explore all scales
print("Exploring all scales...")
files = scale_exploration(
    root="C",
    bpm=120,
    output_dir=f"{output_base}/scales",
)
print(f"  Generated {len(files)} files")

# 3. Generate a progression album
print("Generating progression album...")
files = progression_album(
    key="C",
    bpm=120,
    output_dir=f"{output_base}/progressions",
)
print(f"  Generated {len(files)} files")

# 4. Parameter sweep over BPM
recipe = CompositionRecipe(
    name="sweep_song",
    bpm=120,
    root="C",
    scale="pentatonic_minor",
    tracks=[
        {"type": "euclidean", "beats": 5, "length": 16, "channel": 0, "program": 81},
        {"type": "drums", "style": "four_on_floor", "length": 16, "channel": 9},
    ],
)

print("Running BPM sweep...")
files = parameter_sweep(
    base_recipe=recipe,
    parameter="bpm",
    values=[80, 100, 120, 140, 160],
    output_dir=f"{output_base}/bpm_sweep",
)
print(f"  Generated {len(files)} files")

# 5. Parameter sweep over roots
print("Running root note sweep...")
files = parameter_sweep(
    base_recipe=recipe,
    parameter="root",
    values=["C", "D", "E", "F", "G", "A", "Bb"],
    output_dir=f"{output_base}/root_sweep",
)
print(f"  Generated {len(files)} files")

print(f"\nAll outputs in ./{output_base}/")