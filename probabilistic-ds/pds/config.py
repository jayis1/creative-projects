"""Configuration system for the probabilistic-ds toolkit.

Supports loading structure parameters from JSON, YAML, or TOML config files.
This lets you define data-structure configurations declaratively, e.g. for
production deployments or reproducible benchmarks.

Example YAML config::

    # bloom filter for user dedup
    structure: bloom
    capacity: 1000000
    error_rate: 0.001

    # alternatively, a composite setup
    ---
    structure: hll
    precision: 14

Example JSON config::

    {
        "structure": "cms",
        "error": 0.001,
        "confidence": 0.999
    }
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .bloom import BloomFilter, CountingBloomFilter
from .blocked_bloom import BlockedBloomFilter
from .countmin import CountMinSketch
from .conservative_cms import ConservativeCountMinSketch
from .cuckoo import CuckooFilter
from .hll import HyperLogLog
from .kmv import KMV
from .minhash import MinHash
from .sampling import ReservoirSampler
from .scalable_bloom import ScalableBloomFilter
from .tdigest import TDigest
from .topk import TopK

# Registry of supported structures and their required/optional parameters
_STRUCTURE_REGISTRY: dict[str, type] = {
    "bloom": BloomFilter,
    "counting-bloom": CountingBloomFilter,
    "blocked-bloom": BlockedBloomFilter,
    "scalable-bloom": ScalableBloomFilter,
    "cuckoo": CuckooFilter,
    "cms": CountMinSketch,
    "conservative-cms": ConservativeCountMinSketch,
    "hll": HyperLogLog,
    "kmv": KMV,
    "minhash": MinHash,
    "reservoir": ReservoirSampler,
    "topk": TopK,
    "tdigest": TDigest,
}

# Which kwargs each structure's constructor accepts
_PARAM_SPECS: dict[str, list[str]] = {
    "bloom": ["capacity", "error_rate"],
    "counting-bloom": ["capacity", "error_rate"],
    "blocked-bloom": ["capacity", "error_rate", "block_bits"],
    "scalable-bloom": ["initial_capacity", "error_rate", "growth", "tighten"],
    "cuckoo": ["capacity", "bucket_size", "fingerprint_bits", "max_kicks"],
    "cms": ["width", "depth", "error", "confidence"],
    "conservative-cms": ["width", "depth", "error", "confidence"],
    "hll": ["precision"],
    "kmv": ["k"],
    "minhash": ["num_perm", "seed"],
    "reservoir": ["k"],
    "topk": ["k"],
    "tdigest": ["compression"],
}


class ConfigError(ValueError):
    """Raised when a config file is invalid or references an unknown
    structure."""
    pass


def _load_yaml(text: str) -> dict:
    """Load YAML if PyYAML is available, else raise a helpful error."""
    try:
        import yaml
    except ImportError as exc:
        raise ConfigError(
            "YAML config support requires PyYAML. Install it with: "
            "pip install pyyaml"
        ) from exc
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError("YAML config must be a mapping at the top level")
    return data


def _load_toml(text: str) -> dict:
    """Load TOML using tomllib (3.11+) or tomli."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError as exc:
            raise ConfigError(
                "TOML config support requires Python 3.11+ or the 'tomli' "
                "package."
            ) from exc
    return tomllib.loads(text)


def load_config(path: str | os.PathLike) -> dict[str, Any]:
    """Load a configuration file (JSON, YAML, or TOML) based on extension.

    Parameters
    ----------
    path : str or PathLike
        Path to the config file.  Extension determines the format:
        ``.json``, ``.yaml``/``.yml``, or ``.toml``.

    Returns
    -------
    dict
        Parsed configuration as a dictionary.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    ext = path.suffix.lower()

    if ext in (".json",):
        return json.loads(text)
    elif ext in (".yaml", ".yml"):
        return _load_yaml(text)
    elif ext in (".toml",):
        return _load_toml(text)
    else:
        raise ConfigError(
            f"Unsupported config extension '{ext}'. "
            "Use .json, .yaml, or .toml"
        )


def build_from_config(config: dict) -> Any:
    """Build a data-structure instance from a config dict.

    The dict must contain a ``structure`` key naming one of the supported
    structures (see ``list_structures()``).  Remaining keys are passed as
    keyword arguments to the constructor, filtered to only those the
    constructor accepts.

    Parameters
    ----------
    config : dict
        Configuration with at least a ``structure`` key.

    Returns
    -------
    An instance of the corresponding data structure.
    """
    if "structure" not in config:
        raise ConfigError("Config must contain a 'structure' key")

    name = config["structure"]
    if name not in _STRUCTURE_REGISTRY:
        raise ConfigError(
            f"Unknown structure '{name}'. Supported: "
            f"{', '.join(sorted(_STRUCTURE_REGISTRY))}"
        )

    cls = _STRUCTURE_REGISTRY[name]
    params = _PARAM_SPECS[name]

    # Filter the config to only accepted params
    kwargs = {}
    for key, val in config.items():
        if key == "structure":
            continue
        if key in params:
            kwargs[key] = val
        else:
            raise ConfigError(
                f"Unknown parameter '{key}' for structure '{name}'. "
                f"Accepted: {', '.join(params)}"
            )

    return cls(**kwargs)


def build_from_file(path: str | os.PathLike) -> Any:
    """Load a config file and build the structure from it."""
    return build_from_config(load_config(path))


def list_structures() -> list[str]:
    """Return a sorted list of supported structure names."""
    return sorted(_STRUCTURE_REGISTRY)


def get_param_spec(name: str) -> list[str]:
    """Return the list of accepted constructor parameters for ``name``."""
    if name not in _PARAM_SPECS:
        raise ConfigError(f"Unknown structure '{name}'")
    return list(_PARAM_SPECS[name])


def save_config(config: dict, path: str | os.PathLike) -> None:
    """Save a config dict to a file (JSON, YAML, or TOML based on extension)."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".json":
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ConfigError("YAML output requires PyYAML") from exc
        path.write_text(yaml.dump(config, default_flow_style=False),
                        encoding="utf-8")
    elif ext == ".toml":
        # Simple TOML serialization for flat dicts
        lines = []
        for k, v in config.items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, bool):
                lines.append(f"{k} = {'true' if v else 'false'}")
            elif isinstance(v, (int, float)):
                lines.append(f"{k} = {v}")
            else:
                raise ConfigError(
                    f"Cannot serialize value {v!r} to TOML")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        raise ConfigError(f"Unsupported config extension '{ext}'")