from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import Any

import yaml

from .model import ValidationError


def load_model(path: Path) -> dict[str, Any]:
    raw = path.read_text()
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(raw)
    if suffix == ".toml":
        return tomllib.loads(raw)
    if suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(raw)
        if not isinstance(payload, dict):
            raise ValidationError("YAML model must deserialize to a mapping")
        return payload
    raise ValidationError(f"unsupported input format: {path.suffix or '<none>'}; use .json, .toml, or .yaml")


def dump_model(path: Path, payload: dict[str, Any]) -> None:
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return
    if suffix == ".toml":
        path.write_text(_to_toml(payload).rstrip() + "\n")
        return
    if suffix in {".yaml", ".yml"}:
        path.write_text(yaml.safe_dump(payload, sort_keys=False))
        return
    raise ValidationError(f"unsupported output format: {path.suffix or '<none>'}; use .json, .toml, or .yaml")


def _to_toml(value: Any, prefix: str = "") -> str:
    lines: list[str] = []
    scalars = {k: v for k, v in value.items() if not isinstance(v, (dict, list))}
    tables = {k: v for k, v in value.items() if isinstance(v, dict)}
    arrays = {k: v for k, v in value.items() if isinstance(v, list)}

    for key, item in scalars.items():
        lines.append(f"{key} = {_toml_scalar(item)}")

    for key, item in arrays.items():
        if not item:
            lines.append(f"{key} = []")
            continue
        if all(not isinstance(entry, (dict, list)) for entry in item):
            rendered = ", ".join(_toml_scalar(entry) for entry in item)
            lines.append(f"{key} = [{rendered}]")
            continue
        if all(isinstance(entry, dict) for entry in item):
            for entry in item:
                table_name = f"{prefix}{key}" if prefix else key
                lines.append(f"[[{table_name}]]")
                nested = _to_toml(entry, prefix=f"{table_name}.")
                if nested:
                    lines.append(nested.rstrip())
            continue
        raise ValidationError(f"cannot serialize mixed array for key: {key}")

    for key, item in tables.items():
        table_name = f"{prefix}{key}" if prefix else key
        lines.append(f"[{table_name}]")
        nested = _to_toml(item, prefix=f"{table_name}.")
        if nested:
            lines.append(nested.rstrip())

    return "\n".join(lines) + ("\n" if lines else "")


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (int, float)):
        return repr(value)
    raise ValidationError(f"cannot serialize value to TOML: {value!r}")
