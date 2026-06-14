#!/usr/bin/env python3
"""Example: L-System pattern generation.

Demonstrates how to use L-System grammars to generate evolving
melodic and rhythmic patterns.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sequencer.lsystem import lsystem_pattern, PRESETS
from sequencer.grooves import apply_velocity_curve
from sequencer.export import pattern_to_midi
from sequencer.analysis import visualize_pattern

# Generate patterns from each built-in L-System preset
print("Available L-System presets:")
for name, preset in PRESETS.items():
    print(f"  {name}: axiom={preset['axiom']}, rules={preset['rules']}")

print("\n--- Fibonacci Melody ---")
fib = lsystem_pattern("fibonacci_melody", iterations=5, root="E", scale="minor", octave=4)
print(visualize_pattern(fib, style="block"))
pattern_to_midi(fib, "example_lsystem_fibonacci.mid", bpm=100)

print("\n--- Cantor Set ---")
cantor = lsystem_pattern("cantor", iterations=3, root="C", scale="major", octave=5)
cantor = apply_velocity_curve(cantor, "crescendo")
print(visualize_pattern(cantor, style="block"))
pattern_to_midi(cantor, "example_lsystem_cantor.mid", bpm=120)

print("\n--- Custom L-System ---")
# Define a custom L-System with your own rules
custom = lsystem_pattern(
    axiom="A",
    rules={"A": "ABH", "B": "A+R"},
    iterations=4,
    root="D",
    scale="dorian",
    octave=4,
    velocity=80,
)
print(visualize_pattern(custom, style="block"))
pattern_to_midi(custom, "example_lsystem_custom.mid", bpm=110)