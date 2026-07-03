"""Configuration system and serialization for rl-solver.

Supports JSON, TOML, and YAML config files for MDP construction,
planner/learner hyperparameters, and experiment definitions.  Also
provides serialization of value functions and policies.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .mdp import MDP, GridWorld
from .planners import Policy


# ---- format detection ------------------------------------------------- #

def _load_json(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _dump_json(obj: Dict[str, Any], path: str) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _load_toml(path: str) -> Dict[str, Any]:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            raise ImportError("No TOML parser available (need Python 3.11+ or tomli)")
    with open(path, "rb") as f:
        return tomllib.load(f)


def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        raise ImportError("PyYAML not installed for YAML config support")
    with open(path) as f:
        return yaml.safe_load(f)


def load_config(path: str) -> Dict[str, Any]:
    """Load a config file (JSON/TOML/YAML) based on extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return _load_json(path)
    elif ext == ".toml":
        return _load_toml(path)
    elif ext in (".yaml", ".yml"):
        return _load_yaml(path)
    else:
        raise ValueError(f"Unsupported config format: {ext}")


def save_config(config: Dict[str, Any], path: str) -> None:
    """Save a config dict to JSON/TOML/YAML based on extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        _dump_json(config, path)
    elif ext == ".toml":
        # Python stdlib has no TOML writer; fall back to JSON
        _dump_json(config, path + ".json")
    elif ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
            with open(path, "w") as f:
                yaml.safe_dump(config, f, sort_keys=True)
        except ImportError:
            _dump_json(config, path + ".json")
    else:
        raise ValueError(f"Unsupported config format: {ext}")


# ---- experiment config schema ----------------------------------------- #

DEFAULT_EXPERIMENT_CONFIG: Dict[str, Any] = {
    "env": {"preset": "russell_norvig", "gamma": 0.99, "slip": 0.0},
    "planner": {"method": "value_iteration", "theta": 1e-8},
    "learner": {
        "algo": "q",
        "alpha": 0.1,
        "epsilon": 0.1,
        "epsilon_decay": 0.999,
        "epsilon_min": 0.01,
        "episodes": 5000,
        "max_steps": 1000,
    },
    "simulation": {"episodes": 500, "seed": 42},
}


def validate_config(config: Dict[str, Any]) -> bool:
    """Check that a config dict has the required keys."""
    required = ["env"]
    for key in required:
        if key not in config:
            raise ValueError(f"Config missing required key: {key}")
    env = config["env"]
    if "preset" not in env and "grid" not in env:
        raise ValueError("Config env must specify 'preset' or 'grid'")
    return True


# ---- serialization ---------------------------------------------------- #

def serialize_value_function(V: Dict[Any, float], path: str) -> None:
    """Save a value function to JSON (states are stringified)."""
    data = {str(k): v for k, v in V.items()}
    _dump_json(data, path)


def deserialize_value_function(path: str) -> Dict[str, float]:
    """Load a value function from JSON (keys remain strings)."""
    with open(path) as f:
        return json.load(f)


def serialize_policy(policy: Policy, path: str) -> None:
    """Save a policy to JSON."""
    _dump_json(policy.to_dict(), path)


def deserialize_policy(path: str) -> Dict[str, Any]:
    """Load a policy from JSON (keys and values are strings)."""
    with open(path) as f:
        return json.load(f)


__all__ = [
    "load_config",
    "save_config",
    "validate_config",
    "DEFAULT_EXPERIMENT_CONFIG",
    "serialize_value_function",
    "deserialize_value_function",
    "serialize_policy",
    "deserialize_policy",
]