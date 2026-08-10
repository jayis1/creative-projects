#!/usr/bin/env python3
"""
demo.py — Generate a test image and demonstrate seam carving.

Creates a synthetic test image with a clear "object" (bright rectangle)
on a gradient background, then demonstrates:
  1. Energy map visualization
  2. Width reduction (carving)
  3. Width expansion (insertion)
  4. Seam visualization
"""

import sys
import os

import numpy as np

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seamcarving import SeamCarver, EnergyType, resize
from seamcarving.core import write_ppm, read_ppm


def make_test_image(width: int = 120, height: int = 80) -> np.ndarray:
    """
    Create a test image with:
    - A smooth horizontal gradient background (blue-ish)
    - A bright white rectangle "object" in the center
    - Some diagonal texture for energy variation
    """
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Gradient background
    for x in range(width):
        for y in range(height):
            img[y, x] = [
                int(30 + 60 * x / width),
                int(40 + 50 * y / height),
                int(80 + 80 * (x + y) / (width + height)),
            ]
    # Bright rectangle (the "object" we want to preserve)
    img[20:60, 40:80] = [255, 255, 255]
    # Some texture lines
    for i in range(0, height, 8):
        img[i, :40] = [200, 100, 50]
    return img


def main() -> int:
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(outdir, exist_ok=True)

    print("=== Seam Carving Demo ===\n")

    # 1. Create test image
    print("1. Creating test image (120x80)...")
    img = make_test_image(120, 80)
    write_ppm(os.path.join(outdir, "original.ppm"), img)
    print(f"   Saved: output/original.ppm ({img.shape[1]}x{img.shape[0]})")

    # 2. Energy map
    print("\n2. Computing energy map (Sobel)...")
    carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
    emap = carver.get_energy_map()
    emap_rgb = np.repeat(emap[:, :, np.newaxis], 3, axis=2)
    write_ppm(os.path.join(outdir, "energy_map.ppm"), emap_rgb)
    print(f"   Saved: output/energy_map.ppm")

    # 3. Seam visualization
    print("\n3. Visualizing lowest-energy seam...")
    seam = carver._find_vertical_seam()
    vis = carver.visualize_seam(seam, "vertical")
    write_ppm(os.path.join(outdir, "seam_visualization.ppm"), vis)
    print(f"   Saved: output/seam_visualization.ppm")

    # 4. Width reduction — carve 20 vertical seams
    print("\n4. Reducing width by 20 seams (120 -> 100)...")
    carver2 = SeamCarver(img, energy_type=EnergyType.SOBEL)
    result = carver2.carve_vertical(20)
    write_ppm(os.path.join(outdir, "carved_width.ppm"), result)
    print(f"   Saved: output/carved_width.ppm ({result.shape[1]}x{result.shape[0]})")

    # 5. Width expansion — insert 20 vertical seams
    print("\n5. Expanding width by 20 seams (120 -> 140)...")
    carver3 = SeamCarver(img, energy_type=EnergyType.SOBEL)
    result = carver3.insert_vertical(20)
    write_ppm(os.path.join(outdir, "expanded_width.ppm"), result)
    print(f"   Saved: output/expanded_width.ppm ({result.shape[1]}x{result.shape[0]})")

    # 6. Object removal demo
    print("\n6. Object removal (removing the white rectangle)...")
    carver4 = SeamCarver(img, energy_type=EnergyType.SOBEL)
    remove_mask = np.zeros((80, 120), dtype=bool)
    remove_mask[20:60, 40:80] = True
    result = carver4.remove_object(remove_mask)
    write_ppm(os.path.join(outdir, "object_removed.ppm"), result)
    print(f"   Saved: output/object_removed.ppm ({result.shape[1]}x{result.shape[0]})")

    # 7. Forward energy comparison
    print("\n7. Forward energy carving (20 seams)...")
    carver5 = SeamCarver(img, energy_type=EnergyType.FORWARD)
    result = carver5.carve_vertical(20)
    write_ppm(os.path.join(outdir, "forward_energy_carved.ppm"), result)
    print(f"   Saved: output/forward_energy_carved.ppm ({result.shape[1]}x{result.shape[0]})")

    print("\n=== Demo complete! Check the output/ directory. ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())