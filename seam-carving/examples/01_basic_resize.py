"""
Example 1: Basic resize — reduce image width by 30 pixels.

Demonstrates the simplest usage: load an image, carve 30 vertical seams,
and save the result.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seamcarving import SeamCarver, EnergyType
from seamcarving.io import read_image, write_image


def main() -> None:
    # Create a synthetic test image (gradient + bright rectangle)
    img = np.zeros((80, 120, 3), dtype=np.uint8)
    for x in range(120):
        for y in range(80):
            img[y, x] = [int(30 + 60 * x / 120), int(40 + 50 * y / 80), 100]
    img[20:60, 40:80] = [255, 255, 255]

    # Save original
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(outdir, exist_ok=True)
    write_image(os.path.join(outdir, "ex1_original.png"), img)

    # Reduce width by 30 seams
    carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
    result = carver.carve_vertical(30)
    write_image(os.path.join(outdir, "ex1_carved.png"), result)
    print(f"Original: {img.shape[1]}x{img.shape[0]}")
    print(f"Carved:   {result.shape[1]}x{result.shape[0]}")


if __name__ == "__main__":
    main()