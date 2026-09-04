"""Config and snapshot I/O helpers for Particle Life."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import Any


def load_mapping(path: str | Path) -> dict[str, Any]:
    """Load a JSON or TOML mapping from disk."""

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text())
    if suffix == ".toml":
        return tomllib.loads(path.read_text())
    raise ValueError(f"unsupported config format {suffix!r}; expected .json or .toml")


def dump_json(path: str | Path, data: Any) -> None:
    """Write JSON with stable formatting."""

    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
