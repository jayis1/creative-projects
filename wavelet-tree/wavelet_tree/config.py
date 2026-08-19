"""Configuration system for the wavelet tree library.

Supports JSON, TOML, and YAML config files.
"""

from __future__ import annotations

import json
import os
from typing import Any


class Config:
    """Configuration for wavelet tree operations.

    Attributes:
        structure: Which structure to use ("tree", "matrix",
            "huffman-tree", "huffman-matrix").
        use_blocked: Whether to use BlockedBitVector for O(1) rank.
        log_level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR").
        log_format: Log format ("text", "json").
    """

    DEFAULTS: dict[str, Any] = {
        "structure": "tree",
        "use_blocked": True,
        "log_level": "INFO",
        "log_format": "text",
    }

    VALID_STRUCTURES = {"tree", "matrix", "huffman-tree", "huffman-matrix"}
    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    VALID_LOG_FORMATS = {"text", "json"}

    def __init__(self, **kwargs: Any):
        """Create a Config from keyword arguments, applying defaults."""
        self.structure: str = kwargs.get("structure", self.DEFAULTS["structure"])
        self.use_blocked: bool = kwargs.get("use_blocked", self.DEFAULTS["use_blocked"])
        self.log_level: str = kwargs.get("log_level", self.DEFAULTS["log_level"])
        self.log_format: str = kwargs.get("log_format", self.DEFAULTS["log_format"])
        self.validate()

    def validate(self) -> None:
        """Validate configuration values. Raises ValueError on invalid config."""
        if self.structure not in self.VALID_STRUCTURES:
            raise ValueError(
                f"Invalid structure '{self.structure}'. "
                f"Must be one of {sorted(self.VALID_STRUCTURES)}"
            )
        if not isinstance(self.use_blocked, bool):
            raise ValueError(
                f"use_blocked must be a boolean, got {type(self.use_blocked)}"
            )
        if self.log_level not in self.VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log_level '{self.log_level}'. "
                f"Must be one of {sorted(self.VALID_LOG_LEVELS)}"
            )
        if self.log_format not in self.VALID_LOG_FORMATS:
            raise ValueError(
                f"Invalid log_format '{self.log_format}'. "
                f"Must be one of {sorted(self.VALID_LOG_FORMATS)}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return config as a dictionary."""
        return {
            "structure": self.structure,
            "use_blocked": self.use_blocked,
            "log_level": self.log_level,
            "log_format": self.log_format,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create a Config from a dictionary."""
        return cls(**{**cls.DEFAULTS, **data})

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load a Config from a JSON, TOML, or YAML file.

        The format is auto-detected from the file extension.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")

        ext = os.path.splitext(path)[1].lower()

        if ext == ".json":
            with open(path) as f:
                data = json.load(f)
        elif ext == ".toml":
            data = _load_toml(path)
        elif ext in (".yaml", ".yml"):
            data = _load_yaml(path)
        else:
            raise ValueError(
                f"Unsupported config format '{ext}'. Use .json, .toml, or .yaml"
            )

        return cls.from_dict(data)

    def save(self, path: str) -> None:
        """Save the config to a file (format auto-detected from extension)."""
        ext = os.path.splitext(path)[1].lower()
        data = self.to_dict()

        if ext == ".json":
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        elif ext == ".toml":
            _save_toml(path, data)
        elif ext in (".yaml", ".yml"):
            _save_yaml(path, data)
        else:
            raise ValueError(
                f"Unsupported config format '{ext}'. Use .json, .toml, or .yaml"
            )

    def __repr__(self) -> str:
        return f"Config(structure={self.structure!r}, use_blocked={self.use_blocked})"


def _load_toml(path: str) -> dict:
    """Load a TOML file using tomllib (3.11+) or a simple fallback parser."""
    try:
        import tomllib  # type: ignore[import-not-found]

        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        # Fallback: try the tomli package
        try:
            import tomli  # type: ignore[import-not-found]

            with open(path, "rb") as f:
                return tomli.load(f)
        except ImportError:
            # Very simple TOML parser for flat key=value configs
            return _simple_toml_load(path)


def _simple_toml_load(path: str) -> dict:
    """Minimal TOML parser for flat key=value pairs (fallback only)."""
    result: dict = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Parse basic types
            if value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            elif value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
            else:
                try:
                    result[key] = int(value)
                except ValueError:
                    try:
                        result[key] = float(value)
                    except ValueError:
                        result[key] = value
    return result


def _save_toml(path: str, data: dict) -> None:
    """Save a dict as a simple TOML file."""
    with open(path, "w") as f:
        for key, value in data.items():
            if isinstance(value, bool):
                f.write(f"{key} = {str(value).lower()}\n")
            elif isinstance(value, str):
                f.write(f'{key} = "{value}"\n')
            elif isinstance(value, (int, float)):
                f.write(f"{key} = {value}\n")
            else:
                f.write(f'{key} = "{value}"\n')


def _load_yaml(path: str) -> dict:
    """Load a YAML file using a simple fallback parser."""
    try:
        import yaml  # type: ignore[import-not-found]

        with open(path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return _simple_yaml_load(path)


def _simple_yaml_load(path: str) -> dict:
    """Minimal YAML parser for flat key: value pairs (fallback only)."""
    result: dict = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            elif value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
            else:
                try:
                    result[key] = int(value)
                except ValueError:
                    try:
                        result[key] = float(value)
                    except ValueError:
                        result[key] = value
    return result


def _save_yaml(path: str, data: dict) -> None:
    """Save a dict as a simple YAML file."""
    with open(path, "w") as f:
        for key, value in data.items():
            if isinstance(value, bool):
                f.write(f"{key}: {str(value).lower()}\n")
            elif isinstance(value, str):
                f.write(f'{key}: "{value}"\n')
            elif isinstance(value, (int, float)):
                f.write(f"{key}: {value}\n")
            else:
                f.write(f'{key}: "{value}"\n')