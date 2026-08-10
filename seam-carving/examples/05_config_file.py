"""
Example 5: Config file usage.

Demonstrates loading a configuration file and using it to drive
the seam carving process.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from seamcarving import SeamCarver, EnergyType, CarverConfig
from seamcarving.io import write_image


def main() -> None:
    # Create a config
    config = CarverConfig(
        energy_type="forward",
        target_width=80,
        target_height=60,
        output_format="png",
        log_level="DEBUG",
        record_seams=True,
    )

    # Save it
    config_path = os.path.join(tempfile.gettempdir(), "seam_config.json")
    config.save(config_path)
    print(f"Config saved to: {config_path}")
    print(f"Config contents:\n{config.to_json()}\n")

    # Load it back
    loaded = CarverConfig.load(config_path)
    print(f"Loaded energy_type: {loaded.energy_type}")
    print(f"Loaded target: {loaded.target_width}x{loaded.target_height}")

    # Use it
    img = np.zeros((80, 120, 3), dtype=np.uint8)
    for x in range(120):
        for y in range(80):
            img[y, x] = [int(30 + 60 * x / 120), int(40 + 50 * y / 80), 100]
    img[20:60, 40:80] = [255, 255, 255]

    from seamcarving import resize
    assert loaded.target_width is not None
    assert loaded.target_height is not None
    result = resize(img, loaded.target_width, loaded.target_height,
                    EnergyType(loaded.energy_type))

    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    os.makedirs(outdir, exist_ok=True)
    write_image(os.path.join(outdir, "ex5_config_result.png"), result)
    print(f"\nResult: {result.shape[1]}x{result.shape[0]}")


if __name__ == "__main__":
    main()