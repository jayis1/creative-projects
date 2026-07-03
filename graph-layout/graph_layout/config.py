"""Configuration file support (JSON / TOML).

Allows loading a layout pipeline configuration from a file so users can
reproduce layouts without long command-line invocations.

Example JSON config::

    {
        "graph": {"generator": "petersen"},
        "layout": {"algorithm": "fr", "width": 800, "height": 600, "seed": 42},
        "render": {"format": "svg", "output": "petersen.svg"},
        "metrics": true
    }
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict


def load_config(path: str) -> Dict[str, Any]:
    """Load a JSON or TOML configuration file.

    TOML parsing uses the stdlib ``tomllib`` (Python 3.11+).  For older
    Pythons, a JSON file is expected.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".toml":
        try:
            import tomllib  # type: ignore
        except ImportError:
            raise RuntimeError(
                "TOML config requires Python 3.11+. Use JSON instead."
            )
        return tomllib.loads(text)
    # default: JSON
    return json.loads(text)


def validate_config(config: Dict[str, Any]) -> None:
    """Validate that *config* has the required structure.

    Raises ``ValueError`` with a descriptive message on failure.
    """
    if not isinstance(config, dict):
        raise ValueError("Config must be a dict")
    if "layout" not in config:
        raise ValueError("Config must contain a 'layout' section")
    layout = config["layout"]
    if not isinstance(layout, dict):
        raise ValueError("'layout' must be a dict")
    if "algorithm" not in layout:
        raise ValueError("'layout.algorithm' is required")


__all__ = ["load_config", "validate_config"]