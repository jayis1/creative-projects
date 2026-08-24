"""Configuration loading for CLI automation."""

from __future__ import annotations

import json
import pathlib
import tomllib
from typing import Any


class ConfigError(ValueError):
    """Raised when a configuration file is malformed."""


def load_config(path: str) -> dict[str, Any]:
    config_path = pathlib.Path(path)
    suffix = config_path.suffix.lower()
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"could not read config file {config_path}: {exc}") from exc

    try:
        if suffix == ".json":
            data = json.loads(raw)
        elif suffix in {".toml", ".tml"}:
            data = tomllib.loads(raw)
        else:
            raise ConfigError("config files must use .json or .toml")
    except (json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"failed to parse config file {config_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("top-level config must be a mapping/object")
    return data
