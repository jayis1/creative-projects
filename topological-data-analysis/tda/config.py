"""
Configuration file support for the TDA toolkit.

Load and validate YAML or JSON configuration files that specify
parameters for complex construction, persistence computation, and
distance/vectorization options.

Example YAML config::

    complex:
      type: rips
      max_scale: 2.0
      max_dimension: 2
    persistence:
      max_dimension: 2
      min_persistence: 0.01
    output:
      format: json
      file: diagrams.json

Example JSON config::

    {
      "complex": {"type": "rips", "max_scale": 2.0, "max_dimension": 2},
      "persistence": {"max_dimension": 2, "min_persistence": 0.01}
    }
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .exceptions import FileFormatError, InvalidParameterError


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    "complex": {
        "type": "rips",
        "max_scale": float("inf"),
        "max_dimension": 1,
        "metric": "euclidean",
    },
    "persistence": {
        "max_dimension": 1,
        "min_persistence": 0.0,
    },
    "output": {
        "format": "summary",
        "file": None,
    },
    "distance": {
        "metric": "bottleneck",
        "p": 2.0,
    },
    "image": {
        "resolution": 50,
        "sigma": 1.0,
    },
    "landscape": {
        "resolution": 100,
        "max_functions": 5,
    },
}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_config(path: str) -> Dict[str, Any]:
    """Load a configuration file (JSON or YAML).

    If the file has a ``.yaml`` or ``.yml`` extension, a YAML parser is
    used.  If PyYAML is not installed, a :class:`~tda.exceptions.FileFormatError`
    is raised with a helpful message.

    Parameters
    ----------
    path : str
        Path to the config file.

    Returns
    -------
    dict
        Parsed configuration, merged over :data:`DEFAULT_CONFIG`.

    Raises
    ------
    FileFormatError
        If the file cannot be parsed or the format is unsupported.
    """
    if not os.path.exists(path):
        raise FileFormatError(f"Config file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as f:
        text = f.read()
    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            raise FileFormatError(
                "PyYAML is required to load YAML config files. "
                "Install with: pip install pyyaml"
            )
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:  # type: ignore
            raise FileFormatError(f"Invalid YAML in {path}: {exc}")
    elif ext == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise FileFormatError(f"Invalid JSON in {path}: {exc}")
    else:
        raise FileFormatError(
            f"Unsupported config format '{ext}'. Use .json, .yaml, or .yml"
        )
    if not isinstance(data, dict):
        raise FileFormatError(f"Config root must be a mapping, got {type(data)}")
    return merge_config(DEFAULT_CONFIG, data)


# ---------------------------------------------------------------------------
# Merging / validation
# ---------------------------------------------------------------------------

def merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge *override* into *base*, returning a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = merge_config(result[key], val)
        else:
            result[key] = val
    return result


def validate_config(cfg: Dict[str, Any]) -> None:
    """Validate a configuration dict, raising ``InvalidParameterError`` on
    out-of-range or inconsistent values."""
    cpx = cfg.get("complex", {})
    if cpx.get("type") not in ("rips", "weighted", "cech", "alpha", "sublevel"):
        raise InvalidParameterError(
            f"Unknown complex type: {cpx.get('type')!r}")
    if cpx.get("max_scale") is not None:
        ms = cpx["max_scale"]
        if not isinstance(ms, (int, float)) or ms < 0:
            raise InvalidParameterError("complex.max_scale must be a non-negative number")
    md = cpx.get("max_dimension")
    if md is not None and (not isinstance(md, int) or md < 0):
        raise InvalidParameterError("complex.max_dimension must be a non-negative integer")

    pers = cfg.get("persistence", {})
    mp = pers.get("min_persistence")
    if mp is not None and mp < 0:
        raise InvalidParameterError("persistence.min_persistence must be >= 0")

    dist = cfg.get("distance", {})
    p_val = dist.get("p")
    if p_val is not None and p_val < 1:
        raise InvalidParameterError("distance.p must be >= 1")

    img = cfg.get("image", {})
    res = img.get("resolution")
    if res is not None and (not isinstance(res, int) or res < 1):
        raise InvalidParameterError("image.resolution must be a positive integer")
    sigma = img.get("sigma")
    if sigma is not None and sigma <= 0:
        raise InvalidParameterError("image.sigma must be positive")


def save_config(cfg: Dict[str, Any], path: str) -> None:
    """Save a configuration dict to a JSON or YAML file."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            raise FileFormatError("PyYAML required to write YAML config files.")
        with open(path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
    else:
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)