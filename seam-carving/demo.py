#!/usr/bin/env python3
"""
demo.py — Generate a test image and demonstrate seam carving.

Creates a synthetic test image with a clear "object" (bright rectangle)
on a gradient background, then demonstrates:
  1. Energy map visualization (all 7 energy functions)
  2. Width reduction (carving) with seam recording
  3. Width expansion (insertion)
  4. Seam visualization (single + multiple)
  5. Object removal
  6. Quality metrics / statistics
  7. Mask protection
  8. Animation frame export (PNG)
  9. PNG output format
"""

import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seamcarving import SeamCarver, EnergyType
from seamcarving.io import write_image


def make_test_image(width: int = 120, height: int = 80) -> np.ndarray:
    """Create a test image with a gradient background, bright rectangle, and texture."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for x in range(width):
        for y in range(height):
            img[y, x] = [
                int(30 + 60 * x / width),
                int(40 + 50 * y / height),
                int(80 + 80 * (x + y) / (width + height)),
            ]
    img[20:60, 40:80] = [255, 255, 255]
    for i in range(0, height, 8):
        img[i, :40] = [200, 100, 50]
    return img


def main() -> int:
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(outdir, exist_ok=True)

    print("=== Seam Carving Demo v3.0 ===\n")

    # 1. Create test image
    print("1. Creating test image (120x80)...")
    img = make_test_image(120, 80)
    write_image(os.path.join(outdir, "original.png"), img)
    print(f"   Saved: output/original.png ({img.shape[1]}x{img.shape[0]})")

    # 2. Energy maps for all 7 energy functions
    print("\n2. Computing energy maps for all energy functions...")
    for etype in EnergyType:
        carver = SeamCarver(img, energy_type=etype)
        emap = carver.get_energy_map()
        emap_rgb = np.repeat(emap[:, :, np.newaxis], 3, axis=2)
        fname = f"energy_{etype.value}.png"
        write_image(os.path.join(outdir, fname), emap_rgb)
        print(f"   {etype.value:12s} -> {fname}")

    # 3. Seam visualization
    print("\n3. Visualizing lowest-energy seam...")
    carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
    seam = carver._find_vertical_seam()
    vis = carver.visualize_seam(seam, "vertical", color=(255, 0, 0))
    write_image(os.path.join(outdir, "seam_visualization.png"), vis)
    print(f"   Saved: output/seam_visualization.png")

    # 4. Multiple seam visualization
    print("\n4. Visualizing first 5 seams...")
    carver_multi = SeamCarver(img, energy_type=EnergyType.SOBEL)
    seams = []
    for _ in range(5):
        s = carver_multi._find_vertical_seam()
        seams.append(s)
        carver_multi._remove_vertical_seam(s)
    vis_multi = carver.visualize_multiple_seams(seams, "vertical")
    write_image(os.path.join(outdir, "multi_seam_visualization.png"), vis_multi)
    print(f"   Saved: output/multi_seam_visualization.png")

    # 5. Width reduction with seam recording
    print("\n5. Reducing width by 20 seams (120 -> 100) with recording...")
    carver2 = SeamCarver(img, energy_type=EnergyType.SOBEL)
    result = carver2.carve_vertical(20, record=True)
    write_image(os.path.join(outdir, "carved_width.png"), result)
    print(f"   Saved: output/carved_width.png ({result.shape[1]}x{result.shape[0]})")
    print(f"   Seams recorded: {len(carver2.seam_history)}")

    # 6. Width expansion
    print("\n6. Expanding width by 20 seams (120 -> 140)...")
    carver3 = SeamCarver(img, energy_type=EnergyType.SOBEL)
    result = carver3.insert_vertical(20)
    write_image(os.path.join(outdir, "expanded_width.png"), result)
    print(f"   Saved: output/expanded_width.png ({result.shape[1]}x{result.shape[0]})")

    # 7. Object removal
    print("\n7. Object removal (removing the white rectangle)...")
    carver4 = SeamCarver(img, energy_type=EnergyType.SOBEL)
    remove_mask = np.zeros((80, 120), dtype=bool)
    remove_mask[20:60, 40:80] = True
    result = carver4.remove_object(remove_mask)
    write_image(os.path.join(outdir, "object_removed.png"), result)
    print(f"   Saved: output/object_removed.png ({result.shape[1]}x{result.shape[0]})")

    # 8. Mask protection — carve around the object
    print("\n8. Protected carving (protect the white rectangle)...")
    protect_mask = np.zeros((80, 120), dtype=bool)
    protect_mask[20:60, 40:80] = True
    carver5 = SeamCarver(img, energy_type=EnergyType.SOBEL, protect_mask=protect_mask)
    result = carver5.carve_vertical(20)
    write_image(os.path.join(outdir, "protected_carve.png"), result)
    print(f"   Saved: output/protected_carve.png ({result.shape[1]}x{result.shape[0]})")

    # 9. Forward energy comparison
    print("\n9. Forward energy carving (20 seams)...")
    carver6 = SeamCarver(img, energy_type=EnergyType.FORWARD)
    result = carver6.carve_vertical(20)
    write_image(os.path.join(outdir, "forward_energy_carved.png"), result)
    print(f"   Saved: output/forward_energy_carved.png ({result.shape[1]}x{result.shape[0]})")

    # 10. Animation frame export
    print("\n10. Animation frame export (carving 15 seams)...")
    anim_dir = os.path.join(outdir, "animation_frames")
    os.makedirs(anim_dir, exist_ok=True)
    carver7 = SeamCarver(img, energy_type=EnergyType.SOBEL)
    carver7.carve_vertical(15, animation_dir=anim_dir, animation_format="png")
    frame_count = len([f for f in os.listdir(anim_dir) if f.endswith(".png")])
    print(f"   Exported {frame_count} frames to output/animation_frames/")

    # 11. Statistics
    print("\n11. Carver statistics...")
    stats_carver = SeamCarver(img, energy_type=EnergyType.SOBEL)
    stats_carver.carve_vertical(20, record=True)
    stats = stats_carver.get_stats()
    for key, val in stats.items():
        print(f"    {key}: {val}")

    # 12. New energy functions (Hofer & Entropy)
    print("\n12. Hofer & Entropy energy carving (20 seams)...")
    for etype in [EnergyType.HOFER, EnergyType.ENTROPY]:
        c = SeamCarver(img, energy_type=etype)
        result = c.carve_vertical(20)
        fname = f"carved_{etype.value}.png"
        write_image(os.path.join(outdir, fname), result)
        print(f"    {etype.value:12s} -> {fname} ({result.shape[1]}x{result.shape[0]})")

    print("\n=== Demo complete! Check the output/ directory. ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())