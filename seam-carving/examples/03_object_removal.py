"""
Example 3: Object removal.

Removes a rectangular object from an image by specifying a mask,
then restores the original dimensions via seam insertion.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seamcarving import SeamCarver, EnergyType
from seamcarving.io import write_image


def main() -> None:
    # Create an image with a "person" (bright rectangle) we want to remove
    img = np.zeros((80, 120, 3), dtype=np.uint8)
    for x in range(120):
        for y in range(80):
            img[y, x] = [int(50 + 40 * x / 120), int(60 + 30 * y / 80), 120]
    # The "person" standing in the scene
    img[20:60, 50:70] = [255, 200, 100]

    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(outdir, exist_ok=True)
    write_image(os.path.join(outdir, "ex3_original.png"), img)

    # Define the removal mask
    mask = np.zeros((80, 120), dtype=bool)
    mask[20:60, 50:70] = True

    # Remove the object
    carver = SeamCarver(img, energy_type=EnergyType.FORWARD)
    carver.remove_object(mask)
    removed = carver.image
    write_image(os.path.join(outdir, "ex3_object_removed.png"), removed)
    print(f"After removal: {removed.shape[1]}x{removed.shape[0]}")

    # Restore original width by inserting seams
    carver.insert_vertical(120 - carver.w)
    carver.insert_horizontal(80 - carver.h)
    restored = carver.image
    write_image(os.path.join(outdir, "ex3_restored.png"), restored)
    print(f"After restore: {restored.shape[1]}x{restored.shape[0]}")
    print(f"Seams carved: {carver.num_seams_carved}")


if __name__ == "__main__":
    main()