"""Example: using a config file to define and run a Kalman filter.

Demonstrates the JSON config-file interface.

Usage::

    python examples/config_example.py
"""

import json
import os
import tempfile

import numpy as np

from kalman_estimator.config import load_filter_from_config, save_config


def main():
    # Create a config dict
    config = {
        "filter": "kalman",
        "F": [[1, 1], [0, 1]],
        "H": [[1, 0]],
        "Q": [[0.01, 0], [0, 0.01]],
        "R": [[4.0]],
        "x0": [0.0, 0.0],
        "P0": [[10, 0], [0, 10]],
    }

    # Save to a temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_path = f.name
    save_config(config, config_path)

    print(f"Config saved to: {config_path}")
    with open(config_path) as f:
        print(f"Config contents:\n{f.read()}")

    # Load the filter from config
    kf = load_filter_from_config(config_path)
    print(f"\nFilter loaded: {type(kf).__name__}")
    print(f"  F = {kf.F.tolist()}")
    print(f"  H = {kf.H.tolist()}")
    print(f"  R = {kf.R.tolist()}")

    # Run a quick tracking simulation
    rng = np.random.default_rng(42)
    true_pos = 0.0
    for step in range(20):
        true_pos += 1.0
        z = true_pos + rng.normal(0, 2.0)
        kf.predict()
        kf.update([z])

    print(f"\nAfter 20 steps:")
    print(f"  True position:      {true_pos:.2f}")
    print(f"  Estimated position: {kf.state[0]:.2f}")
    print(f"  Estimated velocity: {kf.state[1]:.2f}")

    os.unlink(config_path)
    print(f"\nConfig file cleaned up.")


if __name__ == "__main__":
    main()