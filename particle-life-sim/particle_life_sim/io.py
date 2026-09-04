"""Config, report, and snapshot I/O helpers for Particle Life."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import tomllib
from typing import Any, Iterable

import yaml


def load_mapping(path: str | Path) -> dict[str, Any]:
    """Load a JSON, TOML, or YAML mapping from disk."""

    path = Path(path)
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        data = json.loads(text)
    elif suffix == ".toml":
        data = tomllib.loads(text)
    elif suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        raise ValueError(f"unsupported config format {suffix!r}; expected .json, .toml, .yaml, or .yml")
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping at {path}, got {type(data).__name__}")
    return data


def dump_json(path: str | Path, data: Any) -> None:
    """Write JSON with stable formatting."""

    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def dump_mapping(path: str | Path, data: Any) -> None:
    """Write a mapping using the file extension format."""

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        dump_json(path, data)
        return
    if suffix in {".yaml", ".yml"}:
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return
    raise ValueError(f"unsupported output format {suffix!r}; expected .json, .yaml, or .yml")


def dump_csv(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    """Write a list of mapping rows as CSV."""

    materialized = list(rows)
    headers = sorted({key for row in materialized for key in row})
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in materialized:
            writer.writerow(row)
