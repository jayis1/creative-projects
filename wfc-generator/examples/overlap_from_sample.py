"""Learn constraints from a sample pattern and generate a new one.

Run with:  python3 examples/overlap_from_sample.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wfc_generator import OverlapModel

# A small "cave-like" sample: ~ = water, . = sand, # = grass, T = tree, ^ = rock
SAMPLE = [
    ["~", "~", "~", ".", "#", "#"],
    ["~", "~", ".", "#", "#", "T"],
    ["~", ".", "#", "#", "T", "T"],
    [".", "#", "#", "T", "T", "^"],
    ["#", "#", "T", "T", "^", "^"],
]


def main():
    model = OverlapModel(SAMPLE, n=3)
    print(f"Extracted {len(model.patterns)} unique 3x3 patterns.\n")
    # Use periodic boundaries so the constrained pattern is easier to satisfy.
    result = model.generate(width=20, height=10, seed=7, periodic=True)
    if result is None:
        # Fall back to a smaller window / n=2 which is much easier to solve.
        print("(3x3 periodic failed; retrying with n=2, non-periodic, smaller grid)")
        model2 = OverlapModel(SAMPLE, n=2)
        result = model2.generate(width=16, height=8, seed=7, periodic=True)
    if result is None:
        print("Generation failed!", file=sys.stderr)
        sys.exit(1)
    for row in result:
        print("".join(row))


if __name__ == "__main__":
    main()