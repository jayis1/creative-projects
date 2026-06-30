"""Configuration example — load/save codec configuration files.

Shows how to use the CodecConfig system to persist and load codec
parameters from JSON, YAML, or TOML files.
"""
import json
import tempfile
from pathlib import Path

from reed_solomon.config import CodecConfig


def main():
    # Create a config with custom parameters
    config = CodecConfig(nsym=16, interleaving_depth=4, log_level="INFO")
    print("Default config:")
    print(config.to_json())
    print()

    # Save to JSON
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        config.save(f.name)
        json_path = f.name
    print(f"Saved to: {json_path}")

    # Load it back
    loaded = CodecConfig.load(json_path)
    print(f"Loaded nsym: {loaded.nsym}")
    print(f"Loaded depth: {loaded.interleaving_depth}")
    print(f"Loaded log_level: {loaded.log_level}")
    print()

    # Validate
    config.validate()  # raises if invalid
    print("✓ Config is valid!")

    # Serialise to different formats
    print("\n--- YAML format ---")
    try:
        print(config.to_yaml())
    except RuntimeError as e:
        print(f"  {e}")

    print("--- TOML format ---")
    try:
        print(config.to_toml())
    except RuntimeError as e:
        print(f"  {e}")


if __name__ == "__main__":
    main()