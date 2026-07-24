"""Serialization: save/load filter states and full runs to JSON.

Format
------
::

    {
        "type": "KalmanFilter",
        "params": {"F": [[...]], "H": [[...]], ...},
        "state": {"x": [...], "P": [[...]]},
        "history": {                      # optional
            "x_prior": [...], "P_prior": [...],
            "x_post": [...], "P_post": [...],
            "F_list": [...]
        }
    }
"""

from __future__ import annotations

import json
import numpy as np

from .kf import KalmanFilter


def _array_to_list(arr):
    """Recursively convert ndarray / list-of-arrays to nested lists."""
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    if isinstance(arr, list):
        return [_array_to_list(a) for a in arr]
    return arr


def _list_to_array(obj):
    """Recursively convert nested lists back to ndarray where appropriate."""
    if isinstance(obj, list):
        if len(obj) > 0 and isinstance(obj[0], (int, float)):
            return np.array(obj)
        return [_list_to_array(o) for o in obj]
    return obj


def save_filter(kf, path, include_history=False, history=None):
    """Save a KalmanFilter's current state (and optionally history) to JSON.

    Parameters
    ----------
    kf : KalmanFilter
    path : str
    include_history : bool
        If True and *history* is provided (list of prior/posterior
        states/covs), save them too.
    history : dict or None
        Should contain keys 'x_prior','P_prior','x_post','P_post','F_list'
    """
    data = {
        "type": "KalmanFilter",
        "params": {
            "F": _array_to_list(kf.F),
            "H": _array_to_list(kf.H),
            "Q": _array_to_list(kf.Q),
            "R": _array_to_list(kf.R),
            "B": _array_to_list(kf.B) if kf.B is not None else None,
        },
        "state": {
            "x": _array_to_list(kf.x),
            "P": _array_to_list(kf.P),
        },
    }
    if include_history and history is not None:
        data["history"] = {k: _array_to_list(v) for k, v in history.items()}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_filter(path):
    """Load a KalmanFilter from JSON, returning (kf, history_or_None)."""
    with open(path) as f:
        data = json.load(f)
    if data["type"] != "KalmanFilter":
        raise ValueError(f"Unknown filter type: {data['type']}")
    p = data["params"]
    kf = KalmanFilter(
        F=_list_to_array(p["F"]),
        H=_list_to_array(p["H"]),
        Q=_list_to_array(p["Q"]),
        R=_list_to_array(p["R"]),
        x0=_list_to_array(data["state"]["x"]),
        P0=_list_to_array(data["state"]["P"]),
        B=_list_to_array(p["B"]) if p["B"] is not None else None,
    )
    # restore current state (x0/P0 were the initial, but save_filter stored
    # current x/P in "state", so we overwrite)
    kf.x = np.array(data["state"]["x"], dtype=float)
    kf.P = np.array(data["state"]["P"], dtype=float)
    history = None
    if "history" in data:
        history = {k: _list_to_array(v) for k, v in data["history"].items()}
    return kf, history