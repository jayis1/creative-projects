"""Configuration file support for KenKen generation.

Supports loading generation profiles from JSON or YAML files.  A config
file lets you specify all the parameters for puzzle generation (size,
difficulty, seed, cage options, output format) in one place.

Example JSON config::

    {
        "size": 6,
        "difficulty": "hard",
        "seed": 42,
        "max_cage_size": 4,
        "allow_singletons": false,
        "format": "json",
        "output": "puzzle.json"
    }

Example YAML config::

    size: 5
    difficulty: medium
    seed: 123
    max_cage_size: 4
    allow_singletons: true
    format: text
    output: null
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class GenerationConfig:
    """Configuration for puzzle generation.

    All fields have sensible defaults so that only the fields you want to
    override need to be set.
    """

    DEFAULTS: Dict[str, Any] = {
        "size": 5,
        "difficulty": "medium",
        "seed": None,
        "max_cage_size": 4,
        "allow_singletons": True,
        "max_attempts": 100,
        "format": "grid",
        "output": None,
    }

    def __init__(
        self,
        size: int = 5,
        difficulty: str = "medium",
        seed: Optional[int] = None,
        max_cage_size: int = 4,
        allow_singletons: bool = True,
        max_attempts: int = 100,
        format: str = "grid",
        output: Optional[str] = None,
    ) -> None:
        self.size = size
        self.difficulty = difficulty
        self.seed = seed
        self.max_cage_size = max_cage_size
        self.allow_singletons = allow_singletons
        self.max_attempts = max_attempts
        self.format = format
        self.output = output

    def to_dict(self) -> dict:
        """Serialise the config to a plain dict."""
        return {
            "size": self.size,
            "difficulty": self.difficulty,
            "seed": self.seed,
            "max_cage_size": self.max_cage_size,
            "allow_singletons": self.allow_singletons,
            "max_attempts": self.max_attempts,
            "format": self.format,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GenerationConfig":
        """Build a config from a dict, filling in defaults for missing keys."""
        merged = dict(cls.DEFAULTS)
        merged.update({k: v for k, v in d.items() if v is not None})
        return cls(
            size=int(merged["size"]),
            difficulty=str(merged["difficulty"]),
            seed=merged["seed"],
            max_cage_size=int(merged["max_cage_size"]),
            allow_singletons=bool(merged["allow_singletons"]),
            max_attempts=int(merged["max_attempts"]),
            format=str(merged["format"]),
            output=merged["output"],
        )

    @classmethod
    def from_file(cls, path: str) -> "GenerationConfig":
        """Load a config from a JSON or YAML file.

        YAML support requires ``pyyaml``; if not installed, only JSON files
        are supported (detected by the ``.yaml``/``.yml`` extension).
        """
        with open(path) as f:
            content = f.read()
        if path.endswith((".yaml", ".yml")):
            try:
                import yaml  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ImportError(
                    "YAML config support requires 'pyyaml'. "
                    "Install it with: pip install pyyaml"
                ) from exc
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        logger.debug("Loaded config from %s: %s", path, data)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return f"GenerationConfig({self.to_dict()})"


__all__ = ["GenerationConfig"]