"""Load event collections from JSON or TOML configuration files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import Event


def _event_from_mapping(value: Any) -> Event:
    if not isinstance(value, dict):
        raise ValueError("each event must be an object")
    required = {"id", "start", "end"}
    missing = required - value.keys()
    if missing:
        raise ValueError(f"event missing required fields: {', '.join(sorted(missing))}")
    return Event(
        str(value["id"]),
        float(value["start"]),
        float(value["end"]),
        str(value.get("label", "")),
    )


def load_events(path: str | Path) -> list[Event]:
    """Load ``events`` from a JSON or TOML file, with clear validation errors."""
    source = Path(path)
    try:
        if source.suffix.lower() == ".toml":
            import tomllib
            data = tomllib.loads(source.read_text(encoding="utf-8"))
        elif source.suffix.lower() == ".json":
            data = json.loads(source.read_text(encoding="utf-8"))
        else:
            raise ValueError("event files must use .json or .toml")
    except FileNotFoundError as exc:
        raise ValueError(f"event file not found: {source}") from exc
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("event files"):
            raise
        raise ValueError(f"could not read event file {source}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        raise ValueError("configuration must contain an 'events' array")
    return [_event_from_mapping(item) for item in data["events"]]
