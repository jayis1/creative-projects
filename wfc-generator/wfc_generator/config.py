"""Configuration system for WFC generation runs.

A :class:`WFCConfig` describes all the parameters needed for a single
generation run (mode, dimensions, seed, periodicity, selection strategy,
backtrack limit, output options).  It can be loaded from / saved to JSON,
YAML or TOML, and merged with CLI overrides.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from .grid import SelectionStrategy

logger = logging.getLogger(__name__)


@dataclass
class WFCConfig:
    """Parameters for a WFC generation run.

    Attributes
    ----------
    mode:
        Generation mode (e.g. ``terrain``, ``dungeon``, ``overlap``,
        ``custom``, ``village``, ``islands``).
    width, height:
        Grid dimensions.
    seed:
        Optional random seed.
    periodic:
        Use toroidal boundaries.
    backtrack_limit:
        Maximum full restarts on contradiction.
    selection:
        :class:`SelectionStrategy` name.
    cache_entropy:
        Whether to maintain an entropy cache.
    output:
        Optional output file path.
    cell_size:
        Cell size in pixels for visual output.
    stats:
        Whether to print generation statistics.
    sample:
        Path to a sample JSON file (overlap mode only).
    n:
        Pattern size for overlap mode.
    tileset:
        Path to a custom tileset JSON file (custom mode only).
    symmetrize:
        Whether to auto-symmetrize a custom tileset's constraints.
    """

    mode: str = "terrain"
    width: int = 30
    height: int = 20
    seed: Optional[int] = None
    periodic: bool = False
    backtrack_limit: int = 10
    selection: str = SelectionStrategy.MIN_ENTROPY.value
    cache_entropy: bool = False
    output: Optional[str] = None
    cell_size: int = 16
    stats: bool = False
    sample: Optional[str] = None
    n: int = 2
    tileset: Optional[str] = None
    symmetrize: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate(self) -> None:
        """Validate the configuration; raise ``ValueError`` on problems."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"width and height must be positive, got {self.width}x{self.height}"
            )
        if self.backtrack_limit < 0:
            raise ValueError(
                f"backtrack_limit must be non-negative, got {self.backtrack_limit}"
            )
        if self.n < 1:
            raise ValueError(f"overlap n must be >= 1, got {self.n}")
        if self.mode == "overlap" and not self.sample:
            raise ValueError("overlap mode requires a 'sample' file path")
        if self.mode == "custom" and not self.tileset:
            raise ValueError("custom mode requires a 'tileset' file path")
        try:
            SelectionStrategy(self.selection)
        except ValueError as e:
            raise ValueError(
                f"selection must be one of {[s.value for s in SelectionStrategy]}, "
                f"got {self.selection!r}"
            ) from e

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Drop empty 'extra' to keep output tidy
        if not d.get("extra"):
            d.pop("extra", None)
        return d

    def to_json(self, path: Optional[str] = None) -> str:
        text = json.dumps(self.to_dict(), indent=2)
        if path:
            Path(path).write_text(text, encoding="utf-8")
        return text

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WFCConfig":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        clean = {k: v for k, v in data.items() if k in known}
        extra = {k: v for k, v in data.items() if k not in known}
        cfg = cls(**clean)
        if extra:
            cfg.extra = extra
        return cfg

    @classmethod
    def from_json(cls, path: str) -> "WFCConfig":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def from_yaml(cls, path: str) -> "WFCConfig":
        try:
            import yaml
        except ImportError as e:  # pragma: no cover - optional dep
            raise ImportError(
                "YAML support requires PyYAML: pip install pyyaml"
            ) from e
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(yaml.safe_load(f))

    @classmethod
    def from_toml(cls, path: str) -> "WFCConfig":
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        with open(path, "rb") as f:
            return cls.from_dict(tomllib.load(f))

    @classmethod
    def from_file(cls, path: str) -> "WFCConfig":
        """Load a config from a file, inferring the format from the extension."""
        ext = Path(path).suffix.lower()
        if ext == ".json":
            return cls.from_json(path)
        if ext in (".yaml", ".yml"):
            return cls.from_yaml(path)
        if ext == ".toml":
            return cls.from_toml(path)
        # Fall back to JSON
        return cls.from_json(path)

    # ------------------------------------------------------------------ #
    # Merging
    # ------------------------------------------------------------------ #
    def override(self, **changes: Any) -> "WFCConfig":
        """Return a new config with the given fields overridden."""
        data = self.to_dict()
        for k, v in changes.items():
            if v is None:
                continue
            data[k] = v
        return WFCConfig.from_dict(data)