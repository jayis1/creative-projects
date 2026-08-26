from __future__ import annotations

import json
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .generator import VALID_MODES

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class GenerationConfig:
    """Validated generator settings shared across CLI commands."""

    width: int = 41
    height: int = 25
    seed: int | None = None
    mode: str = "grid"
    iterations: int = 45
    landmarks: int = 4
    zone_weights: dict[str, float] = field(default_factory=dict)
    seeds: list[int] = field(default_factory=list)
    cell_size: int = 18
    title: str = "Shape Grammar City Report"

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "GenerationConfig":
        zone_weights = payload.get("zone_weights") or payload.get("zone-weights") or {}
        if zone_weights is None:
            zone_weights = {}
        if not isinstance(zone_weights, dict):
            raise ValueError("zone_weights must be a mapping of tile names to numeric weights")
        seeds = payload.get("seeds", [])
        if seeds is None:
            seeds = []
        if not isinstance(seeds, list):
            raise ValueError("seeds must be a list of integers")
        config = cls(
            width=int(payload.get("width", 41)),
            height=int(payload.get("height", 25)),
            seed=None if payload.get("seed") is None else int(payload["seed"]),
            mode=str(payload.get("mode", "grid")),
            iterations=int(payload.get("iterations", 45)),
            landmarks=int(payload.get("landmarks", payload.get("landmark_count", 4))),
            zone_weights={str(name): float(value) for name, value in zone_weights.items()},
            seeds=[int(seed) for seed in seeds],
            cell_size=int(payload.get("cell_size", payload.get("cell-size", 18))),
            title=str(payload.get("title", "Shape Grammar City Report")),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.width < 9 or self.height < 9:
            raise ValueError("width and height must both be at least 9")
        if self.iterations < 1:
            raise ValueError("iterations must be at least 1")
        if self.landmarks < 0:
            raise ValueError("landmarks cannot be negative")
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(VALID_MODES)}")
        if self.cell_size < 4:
            raise ValueError("cell_size must be at least 4")


def load_config(path: Path) -> GenerationConfig:
    """Load a generation config from JSON or TOML."""

    suffix = path.suffix.lower()
    LOGGER.debug("Loading config from %s", path)
    if suffix == ".json":
        payload = json.loads(path.read_text())
    elif suffix == ".toml":
        payload = tomllib.loads(path.read_text())
    else:
        raise ValueError(f"unsupported config format {suffix!r}; use .json or .toml")
    if not isinstance(payload, dict):
        raise ValueError("configuration root must be a mapping/object")
    nested = payload.get("city")
    if nested is not None:
        if not isinstance(nested, dict):
            raise ValueError("configuration key 'city' must contain a mapping/object")
        payload = nested
    return GenerationConfig.from_mapping(payload)


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")
