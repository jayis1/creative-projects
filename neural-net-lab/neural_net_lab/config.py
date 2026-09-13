"""Validated TOML/JSON experiment configuration."""
from __future__ import annotations
import json, tomllib
from pathlib import Path
from typing import Any

DEFAULTS = {"sizes": [2, 4, 1], "activations": ["tanh", "sigmoid"], "seed": 7, "epochs": 2000, "lr": 0.08, "batch_size": 4, "optimizer": "adam", "loss": "mse", "clip": 5.0, "patience": None}

def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        with p.open("rb") as f: raw = tomllib.load(f) if p.suffix.lower() == ".toml" else json.load(f)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as e:
        raise ValueError(f"invalid configuration {p}: {e}") from e
    if not isinstance(raw, dict): raise ValueError("configuration must be an object/table")
    cfg = {**DEFAULTS, **raw}
    if not isinstance(cfg["sizes"], list) or not all(isinstance(n, int) and n > 0 for n in cfg["sizes"]): raise ValueError("sizes must be positive integers")
    if cfg["optimizer"] not in {"adam", "sgd"}: raise ValueError("optimizer must be adam or sgd")
    return cfg
