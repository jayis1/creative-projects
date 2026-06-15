"""Configuration management for compression engine.

Supports loading codec presets and defaults from JSON or YAML
configuration files, as well as programmatic configuration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "default_codec": "deflate",
    "codecs": {
        "huffman": {},
        "lz77": {"window_size": 4096, "min_match": 3, "max_match": 258},
        "bwt": {},
        "deflate": {"window_size": 32768},
        "rle": {},
        "delta": {"mode": "auto"},
        "lzw": {"max_bits": 16},
        "arithmetic": {},
    },
    "pipelines": {
        "fast": "rle+lz77",
        "balanced": "rle+deflate",
        "best": "bwt+huffman",
        "numeric": "delta+deflate",
    },
    "benchmark": {
        "include_pipelines": True,
        "repeat": 1,
    },
    "logging": {
        "level": "WARNING",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
}


def load_config(path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load configuration from a JSON file.

    If path is None, searches for config files in order:
    1. ./compression_engine.json
    2. ~/.compression_engine.json
    3. /etc/compression_engine/config.json

    If no config file is found, returns DEFAULT_CONFIG.

    Args:
        path: Path to config file, or None to auto-discover.

    Returns:
        Configuration dictionary.
    """
    if path is not None:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r") as f:
            user_config = json.load(f)
        return _deep_merge(DEFAULT_CONFIG.copy(), user_config)

    # Auto-discover config files
    search_paths = [
        Path.cwd() / "compression_engine.json",
        Path.home() / ".compression_engine.json",
        Path("/etc/compression_engine/config.json"),
    ]

    for config_path in search_paths:
        if config_path.exists():
            with open(config_path, "r") as f:
                user_config = json.load(f)
            return _deep_merge(DEFAULT_CONFIG.copy(), user_config)

    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any], path: Union[str, Path]) -> None:
    """Save configuration to a JSON file.

    Args:
        config: Configuration dictionary to save.
        path: Path to save the config file.
    """
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries. Override values take precedence.

    Args:
        base: Base dictionary.
        override: Override dictionary.

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_codec_config(config: Dict[str, Any], codec_name: str) -> Dict[str, Any]:
    """Get codec-specific configuration.

    Args:
        config: Full configuration dictionary.
        codec_name: Name of the codec.

    Returns:
        Codec configuration dictionary.
    """
    return config.get("codecs", {}).get(codec_name, {})


def resolve_pipeline(config: Dict[str, Any], name: str) -> str:
    """Resolve a pipeline name to its specification string.

    If name is a known pipeline name (e.g. 'fast', 'balanced'), return
    the pipeline spec (e.g. 'rle+deflate'). Otherwise return name as-is
    (it may already be a pipeline spec like 'rle+huffman').

    Args:
        config: Full configuration dictionary.
        name: Pipeline name or spec string.

    Returns:
        Pipeline specification string.
    """
    pipelines = config.get("pipelines", {})
    return pipelines.get(name, name)