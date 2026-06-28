"""Configuration system for typeinfer.

Supports loading/saving configuration in JSON, TOML, and YAML formats
(YAML requires the ``pyyaml`` package; otherwise it falls back to JSON).

Configuration options:

* ``builtins`` (bool) — load built-in primitives by default
* ``explain`` (bool) — print inference trace by default
* ``log_level`` (str) — logging level ("DEBUG", "INFO", "WARNING", "ERROR")
* ``data_types`` (dict) — user-defined data type names for annotation resolution
* ``initial_env`` (dict) — custom type environment entries (name -> scheme)
* ``max_type_vars`` (int) — safety limit on fresh variable generation
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or is invalid."""


@dataclass
class Config:
    """Configuration for the typeinfer engine."""

    builtins: bool = True
    explain: bool = False
    log_level: str = "WARNING"
    data_types: Dict[str, Any] = field(default_factory=dict)
    initial_env: Dict[str, Any] = field(default_factory=dict)
    max_type_vars: int = 10000

    def apply_logging(self) -> None:
        """Apply the configured log level to the root logger."""
        level = getattr(logging, self.log_level.upper(), logging.WARNING)
        logging.getLogger("typeinfer").setLevel(level)

    def validate(self) -> None:
        """Validate the configuration, raising ConfigError on problems."""
        if not isinstance(self.builtins, bool):
            raise ConfigError("builtins must be a boolean")
        if not isinstance(self.explain, bool):
            raise ConfigError("explain must be a boolean")
        if self.log_level.upper() not in (
            "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        ):
            raise ConfigError(
                f"log_level must be one of DEBUG/INFO/WARNING/ERROR/CRITICAL, "
                f"got {self.log_level!r}"
            )
        if not isinstance(self.max_type_vars, int) or self.max_type_vars < 1:
            raise ConfigError("max_type_vars must be a positive integer")


def default_config() -> Config:
    """Return the default configuration."""
    return Config()


def _detect_format(path: str) -> str:
    """Detect the config format from the file extension."""
    ext = Path(path).suffix.lower()
    if ext in (".json",):
        return "json"
    if ext in (".toml",):
        return "toml"
    if ext in (".yaml", ".yml"):
        return "yaml"
    raise ConfigError(f"Cannot determine config format from extension: {ext}")


def load_config(path: str) -> Config:
    """Load configuration from a file (JSON, TOML, or YAML).

    The format is detected from the file extension.
    """
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")

    fmt = _detect_format(path)
    with open(path, "r") as f:
        content = f.read()

    if fmt == "json":
        data = json.loads(content)
    elif fmt == "toml":
        # Use tomllib (3.11+) or fallback to tomli
        try:
            import tomllib  # type: ignore
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                raise ConfigError(
                    "TOML config requires Python 3.11+ or the 'tomli' package"
                )
        data = tomllib.loads(content)
    elif fmt == "yaml":
        try:
            import yaml  # type: ignore
        except ImportError:
            raise ConfigError(
                "YAML config requires the 'pyyaml' package: pip install pyyaml"
            )
        data = yaml.safe_load(content)
    else:
        raise ConfigError(f"Unsupported config format: {fmt}")

    return _from_dict(data)


def _from_dict(data: Dict[str, Any]) -> Config:
    """Build a Config from a dictionary."""
    if not isinstance(data, dict):
        raise ConfigError("Config root must be a mapping/dict")
    known = {"builtins", "explain", "log_level", "data_types",
             "initial_env", "max_type_vars"}
    unknown = set(data.keys()) - known
    if unknown:
        logger.warning("Unknown config keys ignored: %s", unknown)
    cfg = Config(
        builtins=data.get("builtins", True),
        explain=data.get("explain", False),
        log_level=data.get("log_level", "WARNING"),
        data_types=data.get("data_types", {}),
        initial_env=data.get("initial_env", {}),
        max_type_vars=data.get("max_type_vars", 10000),
    )
    cfg.validate()
    return cfg


def save_config(path: str, config: Config) -> None:
    """Save configuration to a file (JSON, TOML, or YAML)."""
    fmt = _detect_format(path)
    data = {
        "builtins": config.builtins,
        "explain": config.explain,
        "log_level": config.log_level,
        "data_types": config.data_types,
        "initial_env": config.initial_env,
        "max_type_vars": config.max_type_vars,
    }
    if fmt == "json":
        content = json.dumps(data, indent=2, sort_keys=True)
    elif fmt == "toml":
        # Simple TOML serialization (no nested tables needed here)
        lines = []
        for k, v in data.items():
            if isinstance(v, bool):
                lines.append(f"{k} = {str(v).lower()}")
            elif isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, int):
                lines.append(f"{k} = {v}")
            elif isinstance(v, dict):
                # Simple inline table for dicts
                inner = ", ".join(
                    f'{dk} = {json.dumps(dv)}' for dk, dv in v.items()
                )
                lines.append(f"{k} = {{ {inner} }}")
        content = "\n".join(lines) + "\n"
    elif fmt == "yaml":
        try:
            import yaml  # type: ignore
        except ImportError:
            raise ConfigError(
                "YAML config requires the 'pyyaml' package: pip install pyyaml"
            )
        content = yaml.dump(data, default_flow_style=False, sort_keys=True)
    else:
        raise ConfigError(f"Unsupported config format: {fmt}")

    with open(path, "w") as f:
        f.write(content)


def from_dict(data: Dict[str, Any]) -> Config:
    """Public alias for building a Config from a dict."""
    return _from_dict(data)