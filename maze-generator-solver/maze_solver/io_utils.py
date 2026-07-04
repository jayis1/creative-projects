"""
I/O utilities: configuration loading and maze batch serialization.

Supports JSON, TOML, and YAML configuration files for declarative
maze generation.  Also provides batch save/load for multiple mazes.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .core import Maze


# --------------------------------------------------------------------------- #
# Config defaults
# --------------------------------------------------------------------------- #

DEFAULT_CONFIG: Dict[str, Any] = {
    "width": 20,
    "height": 10,
    "seed": None,
    "generator": "recursive_backtracking",
    "solver": "bfs",
    "heuristic": "manhattan",
    "braid": None,
    "start": None,
    "end": None,
}


# --------------------------------------------------------------------------- #
# JSON config
# --------------------------------------------------------------------------- #


def load_config_json(path: str) -> Dict[str, Any]:
    """Load a JSON configuration file.

    The config is merged over :data:`DEFAULT_CONFIG`.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {**DEFAULT_CONFIG, **data}


def save_config_json(config: Dict[str, Any], path: str) -> None:
    """Save a configuration dictionary as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


# --------------------------------------------------------------------------- #
# TOML config
# --------------------------------------------------------------------------- #


def load_config_toml(path: str) -> Dict[str, Any]:
    """Load a TOML configuration file.

    Uses ``tomllib`` (Python 3.11+) or ``tomli`` if available.
    """
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            raise ImportError(
                "TOML support requires Python 3.11+ (tomllib) or the "
                "'tomli' package."
            )
    with open(path, "rb") as f:
        data = tomllib.load(f)
    # Flatten single-table TOML into our config schema.
    flat: Dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, dict):
            flat.update(val)
        else:
            flat[key] = val
    return {**DEFAULT_CONFIG, **flat}


# --------------------------------------------------------------------------- #
# YAML config
# --------------------------------------------------------------------------- #


def load_config_yaml(path: str) -> Dict[str, Any]:
    """Load a YAML configuration file.

    Requires the ``pyyaml`` package.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("YAML support requires the 'pyyaml' package.")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {}
    return {**DEFAULT_CONFIG, **data}


# --------------------------------------------------------------------------- #
# Unified config loader (auto-detects format by extension)
# --------------------------------------------------------------------------- #


def load_config(path: str) -> Dict[str, Any]:
    """Load a configuration file, auto-detecting format by extension.

    Supported extensions: ``.json``, ``.toml``, ``.yaml``, ``.yml``.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return load_config_json(path)
    elif ext == ".toml":
        return load_config_toml(path)
    elif ext in (".yaml", ".yml"):
        return load_config_yaml(path)
    else:
        raise ValueError(
            f"Unsupported config format '{ext}'. "
            f"Supported: .json, .toml, .yaml, .yml"
        )


# --------------------------------------------------------------------------- #
# Maze from config
# --------------------------------------------------------------------------- #


def maze_from_config(config: Dict[str, Any]) -> Maze:
    """Create and generate a maze from a configuration dictionary.

    Parameters
    ----------
    config : dict
        Configuration with keys: ``width``, ``height``, ``seed``,
        ``generator``, ``braid``, ``start``, ``end``.

    Returns
    -------
    Maze
        A generated maze ready for solving/analysis.
    """
    maze = Maze(
        width=config.get("width", 20),
        height=config.get("height", 10),
        seed=config.get("seed"),
    )
    maze.generate(config.get("generator", "recursive_backtracking"))
    # Braid if specified.
    braid_prob = config.get("braid")
    if braid_prob is not None:
        maze.braid(braid_prob)
    # Set custom start/end if specified.
    start = config.get("start")
    if start is not None:
        maze.set_start(start[0], start[1])
    end = config.get("end")
    if end is not None:
        maze.set_end(end[0], end[1])
    return maze


# --------------------------------------------------------------------------- #
# Batch save/load
# --------------------------------------------------------------------------- #


def save_batch(mazes: List[Maze], path: str) -> None:
    """Save multiple mazes to a single JSON file."""
    data = {"mazes": [m.to_dict() for m in mazes]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_batch(path: str) -> List[Maze]:
    """Load multiple mazes from a JSON file created by :func:`save_batch`."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Maze.from_dict(d) for d in data["mazes"]]