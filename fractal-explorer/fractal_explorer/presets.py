"""Preset management — named, reusable render configurations.

A preset is a JSON file that stores all the parameters for a render (fractal
kind, viewport, coloring, palette, etc.) so it can be reproduced exactly.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional


class PresetManager:
    """Manage named render presets stored as JSON files.

    Parameters
    ----------
    directory : str
        Directory to store preset files. Created on demand.
    """

    def __init__(self, directory: str = "presets"):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def save(self, name: str, params: dict) -> str:
        """Save a preset to ``<directory>/<name>.json``."""
        path = os.path.join(self.directory, f"{name}.json")
        with open(path, "w") as f:
            json.dump(params, f, indent=2)
        return path

    def load(self, name: str) -> dict:
        """Load a preset by name."""
        path = os.path.join(self.directory, f"{name}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"No preset named {name!r} in {self.directory}")
        with open(path) as f:
            return json.load(f)

    def list(self) -> Dict[str, str]:
        """Return ``{name: path}`` for all presets in the directory."""
        result = {}
        if os.path.isdir(self.directory):
            for fn in os.listdir(self.directory):
                if fn.endswith(".json"):
                    result[fn[:-5]] = os.path.join(self.directory, fn)
        return result

    def delete(self, name: str) -> bool:
        """Delete a preset. Returns True if it existed."""
        path = os.path.join(self.directory, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


# Built-in presets — classic fractal viewpoints --------------------------------- #

PRESETS = {
    "mandelbrot-classic": {
        "kind": "mandelbrot", "center": "-0.5,0", "viewport_width": 3.0,
        "max_iter": 512, "palette": "fire", "coloring": "smooth",
    },
    "seahorse-valley": {
        "kind": "mandelbrot", "center": "-0.745,0.105",
        "viewport_width": 0.01, "max_iter": 1000, "palette": "magma",
        "coloring": "smooth", "supersample": 2,
    },
    "elephant-valley": {
        "kind": "mandelbrot", "center": "0.275,0.0",
        "viewport_width": 0.05, "max_iter": 800, "palette": "electric",
        "coloring": "smooth",
    },
    "julia-dendrite": {
        "kind": "julia", "julia_c": "-0.4,0.6", "center": "0,0",
        "viewport_width": 3.0, "max_iter": 300, "palette": "ice",
        "coloring": "smooth",
    },
    "julia-dragon": {
        "kind": "julia", "julia_c": "-0.8,0.156", "center": "0,0",
        "viewport_width": 3.0, "max_iter": 300, "palette": "neon",
        "coloring": "smooth",
    },
    "burning-ship": {
        "kind": "burning_ship", "center": "-0.5,-0.5",
        "viewport_width": 3.5, "max_iter": 400, "palette": "fire",
        "coloring": "smooth",
    },
    "newton-cubic": {
        "kind": "newton", "center": "0,0", "viewport_width": 4.0,
        "max_iter": 80, "palette": "rainbow", "coloring": "root",
        "newton_power": 3,
    },
    "multibrot-5": {
        "kind": "mandelbrot", "power": 5.0, "center": "0,0",
        "viewport_width": 3.0, "max_iter": 400, "palette": "sunset",
        "coloring": "smooth",
    },
    "tricorn": {
        "kind": "tricorn", "center": "0,0", "viewport_width": 3.0,
        "max_iter": 300, "palette": "ocean", "coloring": "smooth",
    },
    "phoenix": {
        "kind": "phoenix", "phoenix_c": "-0.5", "center": "0,0",
        "viewport_width": 3.0, "max_iter": 300, "palette": "magma",
        "coloring": "smooth",
    },
}


def save_preset(name: str, params: dict, directory: str = "presets") -> str:
    """Convenience: save a preset to the given directory."""
    return PresetManager(directory).save(name, params)


def load_preset(name: str, directory: str = "presets") -> dict:
    """Convenience: load a preset from the given directory."""
    return PresetManager(directory).load(name)