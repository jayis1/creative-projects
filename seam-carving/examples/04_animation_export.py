"""
Example 4: Animation frame export.

Exports each carving step as a PNG frame, which can be combined into
a GIF or video using external tools (e.g., ffmpeg).
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seamcarving import SeamCarver, EnergyType
from seamcarving.io import write_image


def main() -> None:
    # Create a test image
    img = np.zeros((60, 100, 3), dtype=np.uint8)
    for x in range(100):
        for y in range(60):
            img[y, x] = [int(40 + 60 * x / 100), int(50 + 40 * y / 60), 110]
    img[15:45, 30:70] = [255, 255, 255]

    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    anim_dir = os.path.join(outdir, "ex4_frames")
    os.makedirs(anim_dir, exist_ok=True)

    # Save original
    write_image(os.path.join(outdir, "ex4_original.png"), img)

    # Carve 30 seams with animation export
    carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
    carver.carve_vertical(
        30,
        record=True,
        animation_dir=anim_dir,
        animation_format="png",
    )

    print(f"Original: 100x60")
    print(f"Carved:   {carver.w}x{carver.h}")
    print(f"Frames exported to: {anim_dir}")
    print(f"Seams recorded: {len(carver.seam_history)}")

    # Also save the final result
    write_image(os.path.join(outdir, "ex4_final.png"), carver.image)

    # Print stats
    stats = carver.get_stats()
    print(f"\nStatistics:")
    for key, val in stats.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()