"""Validated TOML/JSON experiment configuration."""
from __future__ import annotations
import json, tomllib
from pathlib import Path
from typing import Any

DEFAULTS = {"sizes": [2, 4, 1], "activations": ["tanh", "sigmoid"], "seed": 7, "epochs": 2000, "lr": 0.08, "batch_size": 4, "optimizer": "adam", "loss": "mse", "clip": 5.0, "patience": None}


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate an experiment configuration and return it for fluent use."""
    required = {"sizes", "activations", "seed", "epochs", "lr", "batch_size", "optimizer", "loss"}
    missing = required - config.keys()
    if missing:
        raise ValueError(f"configuration missing keys: {', '.join(sorted(missing))}")
    sizes = config["sizes"]
    activations = config["activations"]
    if (not isinstance(sizes, list) or len(sizes) < 2
            or not all(isinstance(n, int) and n > 0 for n in sizes)):
        raise ValueError("sizes must contain at least two positive integers")
    if (not isinstance(activations, list) or len(activations) != len(sizes) - 1
            or not all(isinstance(name, str) for name in activations)):
        raise ValueError("activations must contain one name per layer")
    if not isinstance(config["seed"], int):
        raise ValueError("seed must be an integer")
    if not isinstance(config["epochs"], int) or config["epochs"] < 1:
        raise ValueError("epochs must be a positive integer")
    if not isinstance(config["lr"], (int, float)) or config["lr"] <= 0:
        raise ValueError("lr must be positive")
    if not isinstance(config["batch_size"], int) or config["batch_size"] < 1:
        raise ValueError("batch_size must be a positive integer")
    if config["optimizer"] not in {"adam", "sgd"}:
        raise ValueError("optimizer must be adam or sgd")
    if config["loss"] not in {"mse", "bce", "cross_entropy"}:
        raise ValueError("loss must be mse, bce, or cross_entropy")
    if config.get("clip") is not None and (not isinstance(config["clip"], (int, float)) or config["clip"] <= 0):
        raise ValueError("clip must be positive or null")
    if config.get("patience") is not None and (not isinstance(config["patience"], int) or config["patience"] < 1):
        raise ValueError("patience must be a positive integer or null")
    return config


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        with p.open("rb") as f: raw = tomllib.load(f) if p.suffix.lower() == ".toml" else json.load(f)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as e:
        raise ValueError(f"invalid configuration {p}: {e}") from e
    if not isinstance(raw, dict): raise ValueError("configuration must be an object/table")
    return validate_config({**DEFAULTS, **raw})
