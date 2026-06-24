"""Example: Config file — run Game of Life from a JSON config.

Demonstrates loading a CA configuration from a JSON file and running it.
"""
import json
import tempfile
import os

from cellular_automaton import CAConfig


CONFIG_JSON = """{
  "rule": "GameOfLife",
  "width": 40,
  "height": 20,
  "boundary": "periodic",
  "initial": {
    "random": 0.3,
    "seed": 42
  },
  "steps": 50,
  "output": {
    "format": "ascii"
  },
  "logging": {
    "level": "INFO"
  }
}"""


def main():
    # Write config to a temp file.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(CONFIG_JSON)
        config_path = f.name

    try:
        # Load and run.
        cfg = CAConfig.from_file(config_path)
        print(f"Config loaded: rule={cfg.rule}, {cfg.width}x{cfg.height}, steps={cfg.steps}")

        ca, result = cfg.run()
        print(f"\nAfter {ca.step_count} steps — alive: {ca.alive_count()}")
        if result:
            print(result)
    finally:
        os.unlink(config_path)


if __name__ == "__main__":
    main()