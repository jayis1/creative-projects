"""
Configuration system for the diff_merge toolkit.

Supports JSON, TOML, and YAML config files.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

__all__ = ["Config", "load_config", "save_config"]


@dataclass
class Config:
    """Configuration for diff/patch/merge operations."""
    algorithm: str = "myers"
    format: str = "unified"
    context: int = 3
    fuzz: int = 0
    max_offset: int = 100
    conflict_marker_size: int = 7
    ignore_whitespace: bool = False
    ignore_blank_lines: bool = False
    color: bool = False
    reject_file: bool = False
    inline_diff: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create a Config from a dictionary."""
        known_fields = {
            "algorithm", "format", "context", "fuzz", "max_offset",
            "conflict_marker_size", "ignore_whitespace", "ignore_blank_lines",
            "color", "reject_file", "inline_diff",
        }
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return {
            "algorithm": self.algorithm,
            "format": self.format,
            "context": self.context,
            "fuzz": self.fuzz,
            "max_offset": self.max_offset,
            "conflict_marker_size": self.conflict_marker_size,
            "ignore_whitespace": self.ignore_whitespace,
            "ignore_blank_lines": self.ignore_blank_lines,
            "color": self.color,
            "reject_file": self.reject_file,
            "inline_diff": self.inline_diff,
        }


def load_config(filepath: str) -> Config:
    """Load configuration from a JSON, TOML, or YAML file.

    The format is determined by the file extension.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")

    if suffix == ".json":
        data = json.loads(text)
    elif suffix == ".toml":
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        data = tomllib.loads(text)
    elif suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            # Fallback: minimal YAML parser for simple key: value configs
            data = _parse_simple_yaml(text)
        else:
            data = yaml.safe_load(text)
    else:
        raise ValueError(f"Unknown config format: {suffix}")

    return Config.from_dict(data)


def save_config(config: Config, filepath: str) -> None:
    """Save configuration to a JSON, TOML, or YAML file."""
    path = Path(filepath)
    suffix = path.suffix.lower()
    data = config.to_dict()

    if suffix == ".json":
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    elif suffix == ".toml":
        lines = []
        for key, value in data.items():
            if isinstance(value, bool):
                lines.append(f'{key} = {str(value).lower()}')
            elif isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            else:
                lines.append(f'{key} = {value}')
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            lines = []
            for key, value in data.items():
                if isinstance(value, bool):
                    lines.append(f"{key}: {str(value).lower()}")
                else:
                    lines.append(f"{key}: {value}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    else:
        raise ValueError(f"Unknown config format: {suffix}")


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Minimal YAML parser for simple key: value configs (no nesting)."""
    result: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Parse common types
        if value.lower() in ("true", "false"):
            result[key] = value.lower() == "true"
        elif value.startswith('"') and value.endswith('"'):
            result[key] = value[1:-1]
        elif value.isdigit():
            result[key] = int(value)
        else:
            result[key] = value
    return result