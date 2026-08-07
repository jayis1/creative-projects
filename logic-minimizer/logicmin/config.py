"""
Configuration system for logicmin.

Supports JSON, TOML, and YAML config files.  Pure stdlib — YAML support uses
a minimal hand-rolled parser (no PyYAML dependency) that handles the subset of
YAML used in config files.

Example config (JSON)::

    {
        "minimizer": "qm",
        "n_vars": 4,
        "use_petrick": true,
        "espresso_max_iter": 50,
        "output_format": "text",
        "log_level": "INFO"
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class Config:
    """Configuration for logicmin."""

    minimizer: str = "qm"           # "qm" | "espresso" | "pos" | "multi"
    n_vars: int = 4
    use_petrick: bool = True
    espresso_max_iter: int = 50
    espresso_strategy: str = "guarded"
    output_format: str = "text"     # "text" | "json"
    log_level: str = "WARNING"
    show_primes: bool = False
    petrick_max_products: int = 100_000

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Config":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid}
        return cls(**filtered)

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load config from a JSON, TOML, or YAML file."""
        with open(path) as fh:
            text = fh.read()
        ext = os.path.splitext(path)[1].lower()
        if ext == ".json":
            return cls.from_dict(json.loads(text))
        if ext == ".toml":
            return cls.from_dict(_parse_toml(text))
        if ext in (".yaml", ".yml"):
            return cls.from_dict(_parse_yaml(text))
        # try to auto-detect
        stripped = text.strip()
        if stripped.startswith("{"):
            return cls.from_dict(json.loads(stripped))
        if "=" in stripped and "{" not in stripped:
            return cls.from_dict(_parse_toml(stripped))
        return cls.from_dict(_parse_yaml(stripped))

    def save(self, path: str) -> None:
        """Save config to a file (format inferred from extension)."""
        ext = os.path.splitext(path)[1].lower()
        d = self.to_dict()
        with open(path, "w") as fh:
            if ext == ".json":
                json.dump(d, fh, indent=2)
            elif ext == ".toml":
                fh.write(_dict_to_toml(d))
            elif ext in (".yaml", ".yml"):
                fh.write(_dict_to_yaml(d))
            else:
                json.dump(d, fh, indent=2)


# ---------------------------------------------------------------------------
# Minimal TOML parser (key = value, # comments, strings/ints/bools/floats)
# ---------------------------------------------------------------------------

def _parse_toml(text: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # strip inline comments
        if "#" in val and not val.startswith('"'):
            val = val.split("#")[0].strip()
        # type inference
        if val.lower() in ("true", "false"):
            result[key] = val.lower() == "true"
        else:
            try:
                result[key] = int(val)
            except ValueError:
                try:
                    result[key] = float(val)
                except ValueError:
                    result[key] = val
    return result


def _dict_to_toml(d: Dict[str, Any]) -> str:
    lines = []
    for k, v in d.items():
        if isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        else:
            lines.append(f"{k} = {v}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Minimal YAML parser (key: value, # comments, indentation-based nesting)
# ---------------------------------------------------------------------------

def _parse_yaml(text: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.split("#")[0].rstrip()
        if not line.strip():
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not val:
            continue
        # remove quotes
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        if val.lower() in ("true", "false"):
            result[key] = val.lower() == "true"
        else:
            try:
                result[key] = int(val)
            except ValueError:
                try:
                    result[key] = float(val)
                except ValueError:
                    result[key] = val
    return result


def _dict_to_yaml(d: Dict[str, Any]) -> str:
    lines = []
    for k, v in d.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, str):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines) + "\n"