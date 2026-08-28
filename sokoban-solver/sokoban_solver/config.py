"""Configuration loading for CLI defaults and batch jobs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import Any


@dataclass(frozen=True)
class RuntimeConfig:
    max_states: int = 200_000
    json_output: bool = False
    show_frames: bool = False
    log_level: str = "WARNING"

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RuntimeConfig":
        solver = data.get("solver", {}) if isinstance(data.get("solver", {}), dict) else {}
        output = data.get("output", {}) if isinstance(data.get("output", {}), dict) else {}
        logging_cfg = data.get("logging", {}) if isinstance(data.get("logging", {}), dict) else {}
        return cls(
            max_states=int(solver.get("max_states", cls.max_states)),
            json_output=bool(output.get("json", cls.json_output)),
            show_frames=bool(output.get("show_frames", cls.show_frames)),
            log_level=str(logging_cfg.get("level", cls.log_level)).upper(),
        )


def load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")
    suffix = config_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".toml", ".tml"}:
        payload = tomllib.loads(text)
    else:
        raise ValueError(f"unsupported config format for {config_path.name}; use .json or .toml")
    if not isinstance(payload, dict):
        raise ValueError("config root must be a mapping/object")
    return payload
