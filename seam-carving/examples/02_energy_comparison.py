"""
Example 2: Energy function comparison.

Compares all 7 energy functions by carving the same number of seams
from the same image and showing the resulting dimensions and stats.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seamcarving import SeamCarver, EnergyType
from seamcarving.io import write_image


def make_test_image() -> np.ndarray:
    """Create a synthetic image with distinct features."""
    img = np.zeros((60, 100, 3), dtype=np.uint8)
    for x in range(100):
        for y in range(60):
            img[y, x] = [int(20 + 50 * x / 100), int(30 + 40 * y / 60), 90]
    # Add a bright square
    img[15:45, 30:70] = [255, 255, 255]
    # Add some texture
    for i in range(0, 60, 6):
        img[i, :30] = [200, 100, 50]
    return img


def main() -> None:
    img = make_test_image()
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(outdir, exist_ok=True)

    print(f"{'Energy':<12} {'Output WxH':<12} {'Avg Cost':<10} {'Preservation':<12}")
    print("-" * 50)

    for etype in EnergyType:
        carver = SeamCarver(img, energy_type=etype)
        result = carver.carve_vertical(20)
        stats = carver.get_stats()
        fname = f"ex2_{etype.value}.png"
        write_image(os.path.join(outdir, fname), result)
        print(
            f"{etype.value:<12} {result.shape[1]}x{result.shape[0]:<6} "
            f"{stats['avg_seam_cost']:<10.2f} "
            f"{stats['energy_preservation_ratio']:<12.4f}"
        )


if __name__ == "__main__":
    main()