"""
Example 5: Configuration files and reproducible workflows.

Shows how to use YAML/JSON configuration files to parameterise the
TDA pipeline reproducibly.
"""

import json
import tempfile
import os
import tda
from tda.config import load_config, save_config, validate_config, DEFAULT_CONFIG


def main():
    # Generate a default config.
    print("=" * 50)
    print("Default configuration:")
    print(json.dumps(DEFAULT_CONFIG, indent=2, default=str))

    # Customise config.
    custom = {
        "complex": {
            "type": "rips",
            "max_scale": 2.0,
            "max_dimension": 2,
        },
        "persistence": {
            "max_dimension": 2,
            "min_persistence": 0.01,
        },
        "image": {
            "resolution": 30,
            "sigma": 0.5,
        },
    }

    # Save and load.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(custom, f, indent=2)
        cfg_path = f.name

    print(f"\nConfig saved to: {cfg_path}")
    loaded = load_config(cfg_path)
    print(f"Loaded complex type: {loaded['complex']['type']}")
    print(f"Loaded max_scale:     {loaded['complex']['max_scale']}")
    print(f"Loaded image sigma:   {loaded['image']['sigma']}")

    # Validate.
    validate_config(loaded)
    print("✓ Configuration is valid")

    os.unlink(cfg_path)

    # Use config to drive computation.
    print("\n--- Using config to compute persistence ---")
    import math
    pts = [(math.cos(2*math.pi*i/6), math.sin(2*math.pi*i/6)) for i in range(6)]

    cpx_cfg = loaded["complex"]
    vr = tda.VietorisRipsComplex(
        pts,
        max_scale=cpx_cfg["max_scale"],
        max_dimension=cpx_cfg["max_dimension"],
    )
    tree = vr.build()
    pers_cfg = loaded["persistence"]
    pers = tda.compute_persistence(
        tree,
        max_dimension=pers_cfg["max_dimension"],
        min_persistence=pers_cfg["min_persistence"],
    )
    diagrams = tda.diagrams_from_persistence(pers)

    print(tda.statistics_table(diagrams))


if __name__ == "__main__":
    main()