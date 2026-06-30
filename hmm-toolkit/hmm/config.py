"""Configuration support for hmm-toolkit.

Loads model and training parameters from JSON or YAML files (YAML is
parsed with a tiny hand-rolled parser when PyYAML is not available).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


def load_config(path: str) -> Dict[str, Any]:
    """Load a configuration file.

    Supports ``.json`` natively and ``.yaml``/``.yml`` if PyYAML is
    installed (falls back to a minimal parser for simple flat configs).
    """
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if ext == ".json":
        return json.loads(text)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except ImportError:
            return _simple_yaml_parse(text)
    elif ext == ".toml":
        try:
            import tomllib  # py311+
            import io
            return tomllib.loads(text)
        except ImportError:
            try:
                import tomli  # type: ignore
                return tomli.loads(text)
            except ImportError:
                raise ImportError(
                    "TOML config requires Python 3.11+ (tomllib) or the 'tomli' package"
                )
    else:
        # Try JSON as fallback
        return json.loads(text)


def save_config(config: Dict[str, Any], path: str) -> None:
    """Save a configuration dict to JSON or YAML."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config, f, default_flow_style=False)
        except ImportError:
            # Fall back to JSON
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)


# ---------------------------------------------------------------------------
# Minimal YAML parser (handles simple flat key: value configs)
# ---------------------------------------------------------------------------

def _simple_yaml_parse(text: str) -> Dict[str, Any]:
    """Parse a very simple flat YAML file (key: value, no nesting).

    Values are coerced to int, float, bool, or string.  This is a fallback
    when PyYAML is not installed — for complex configs install PyYAML.
    """
    result: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        # Try to coerce
        if val.lower() in ("true", "yes"):
            result[key] = True
        elif val.lower() in ("false", "no"):
            result[key] = False
        elif val.lower() in ("null", "none", "~"):
            result[key] = None
        else:
            try:
                result[key] = int(val)
            except ValueError:
                try:
                    result[key] = float(val)
                except ValueError:
                    result[key] = val
    return result