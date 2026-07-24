"""Configuration loader for kalman-estimator filters.

Supports JSON and TOML configuration files describing filter model
parameters (F, H, Q, R, x0, P0, B) and optional filter-type selection.

Example JSON config::

    {
        "filter": "kalman",
        "F": [[1, 1], [0, 1]],
        "H": [[1, 0]],
        "Q": [[0.01, 0], [0, 0.01]],
        "R": [[2.0]],
        "x0": [0.0, 0.0],
        "P0": [[10, 0], [0, 10]]
    }

Example usage::

    from kalman_estimator.config import load_filter_from_config
    kf = load_filter_from_config("config.json")
    kf.predict()
    kf.update([5.0])
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import numpy as np

from .kf import KalmanFilter


def _load_toml(path: str) -> Dict[str, Any]:
    """Load a TOML file (using tomllib on Python ≥ 3.11, else tomli)."""
    try:
        import tomllib  # type: ignore[attr-defined]
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_config(path: str) -> Dict[str, Any]:
    """Load a filter configuration from JSON or TOML.

    The file format is auto-detected from the extension:
    ``.json`` → JSON, ``.toml`` → TOML.

    Parameters
    ----------
    path : str
        Path to the configuration file.

    Returns
    -------
    config : dict
        Parsed configuration dictionary.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path) as f:
            return json.load(f)
    elif ext == ".toml":
        return _load_toml(path)
    else:
        # try JSON first, then TOML
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return _load_toml(path)


def load_filter_from_config(path: str) -> KalmanFilter:
    """Build a :class:`KalmanFilter` from a JSON/TOML config file.

    The config must contain keys: ``F``, ``H``, ``Q``, ``R``, ``x0``,
    ``P0``, and optionally ``B``.

    The optional ``filter`` key selects the filter type:
    ``"kalman"`` (default) or ``"information"``.
    """
    cfg = load_config(path)
    filter_type = cfg.pop("filter", "kalman").lower()

    # Convert lists to numpy arrays
    arrays = {}
    for key in ("F", "H", "Q", "R", "x0", "P0", "B"):
        if key in cfg:
            arrays[key] = np.array(cfg[key], dtype=float)
    if "B" not in arrays or arrays.get("B") is None:
        arrays.pop("B", None)

    if filter_type == "kalman":
        return KalmanFilter(**arrays)
    elif filter_type == "information":
        from .info_filter import InformationFilter

        # InformationFilter needs y0 = P0^{-1} x0, Y0 = P0^{-1}
        P0 = arrays.pop("P0")
        x0 = arrays.pop("x0")
        Y0 = np.linalg.inv(P0)
        y0 = Y0 @ x0
        arrays["y0"] = y0
        arrays["Y0"] = Y0
        return InformationFilter(**arrays)  # type: ignore[arg-type]
    else:
        raise ValueError(f"Unknown filter type '{filter_type}' in config")


def save_config(config: Dict[str, Any], path: str) -> None:
    """Save a configuration dict to JSON."""
    def _to_list(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: _to_list(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_to_list(v) for v in obj]
        return obj

    with open(path, "w") as f:
        json.dump(_to_list(config), f, indent=2)