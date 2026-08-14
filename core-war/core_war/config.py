"""
Configuration management for Core War battles and tournaments.

Supports loading configuration from YAML or JSON files, with full
validation, defaults, and programmatic access.

Example YAML config file::

    core_size: 8000
    max_cycles: 80000
    max_processes: 8000
    min_separation: 100
    rounds: 10
    seed: 42
    warriors:
      - warriors/imp.red
      - warriors/dwarf.red
    log_level: INFO
    output_format: table
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


logger = logging.getLogger("core_war.config")


@dataclass
class BattleConfig:
    """
    Configuration for a Core War battle or tournament.

    Attributes:
        core_size: Size of the circular memory array.
        max_cycles: Maximum cycles before a draw is declared.
        max_processes: Maximum processes per warrior.
        min_separation: Minimum distance between warrior load positions.
        rounds: Number of rounds per battle pair.
        seed: Random seed for reproducibility (None = random).
        warriors: List of warrior file paths.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        output_format: Output format for results (table, json, csv).
        trace: Whether to enable execution trace.
        heatmap: Whether to show heatmap in core-dump.
    """

    core_size: int = 8000
    max_cycles: int = 80000
    max_processes: int = 8000
    min_separation: int = 100
    rounds: int = 10
    seed: Optional[int] = None
    warriors: List[str] = field(default_factory=list)
    log_level: str = "INFO"
    output_format: str = "table"
    trace: bool = False
    heatmap: bool = False

    def __post_init__(self) -> None:
        """Validate configuration values."""
        self.validate()

    def validate(self) -> None:
        """Validate all configuration values and raise ValueError on invalid."""
        if self.core_size <= 0:
            raise ValueError(f"core_size must be positive, got {self.core_size}")
        if self.core_size > 1_000_000:
            raise ValueError(f"core_size unreasonably large: {self.core_size}")
        if self.max_cycles <= 0:
            raise ValueError(f"max_cycles must be positive, got {self.max_cycles}")
        if self.max_processes <= 0:
            raise ValueError(f"max_processes must be positive, got {self.max_processes}")
        if self.min_separation < 0:
            raise ValueError(f"min_separation must be non-negative, got {self.min_separation}")
        if self.rounds <= 0:
            raise ValueError(f"rounds must be positive, got {self.rounds}")
        if self.log_level.upper() not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"Invalid log_level: {self.log_level!r}")
        if self.output_format not in ("table", "json", "csv"):
            raise ValueError(f"Invalid output_format: {self.output_format!r}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to a dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize config to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_yaml(self) -> str:
        """Serialize config to YAML string."""
        if not _HAS_YAML:
            raise ImportError("PyYAML is required for YAML output. Install with: pip install pyyaml")
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def save(self, path: Union[str, Path]) -> None:
        """Save configuration to a file. Format determined by extension."""
        path = Path(path)
        ext = path.suffix.lower()
        if ext == ".json":
            path.write_text(self.to_json())
        elif ext in (".yaml", ".yml"):
            path.write_text(self.to_yaml())
        else:
            raise ValueError(f"Unsupported config format: {ext} (use .json, .yaml, or .yml)")
        logger.info("Saved configuration to %s", path)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BattleConfig":
        """Create a BattleConfig from a dictionary, ignoring unknown keys."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "BattleConfig":
        """Load configuration from a YAML or JSON file.

        Args:
            path: Path to the config file (.json, .yaml, or .yml).

        Returns:
            BattleConfig instance.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file format is unsupported or invalid.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        ext = path.suffix.lower()
        text = path.read_text()

        if ext == ".json":
            data = json.loads(text)
        elif ext in (".yaml", ".yml"):
            if not _HAS_YAML:
                raise ImportError("PyYAML is required for YAML config. Install with: pip install pyyaml")
            data = yaml.safe_load(text)
        else:
            raise ValueError(f"Unsupported config format: {ext} (use .json, .yaml, or .yml)")

        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a mapping, got {type(data).__name__}")

        logger.info("Loaded configuration from %s", path)
        return cls.from_dict(data)

    @classmethod
    def create_template(cls, path: Union[str, Path]) -> "BattleConfig":
        """Create a template config file with defaults and comments."""
        path = Path(path)
        config = cls()
        ext = path.suffix.lower()

        if ext == ".json":
            path.write_text(json.dumps(config.to_dict(), indent=2))
        elif ext in (".yaml", ".yml"):
            if not _HAS_YAML:
                raise ImportError("PyYAML is required for YAML. Install with: pip install pyyaml")
            template = """# Core War Battle Configuration
# ===========================
# This file configures battles and tournaments.

# Core memory size (circular array)
core_size: 8000

# Maximum cycles before a draw is declared
max_cycles: 80000

# Maximum processes per warrior
max_processes: 8000

# Minimum distance between warrior load positions
min_separation: 100

# Number of rounds per battle pair
rounds: 10

# Random seed (null for random)
seed: 42

# Warrior files to load
warriors:
  - warriors/imp.red
  - warriors/dwarf.red

# Logging level: DEBUG, INFO, WARNING, ERROR
log_level: INFO

# Output format: table, json, csv
output_format: table

# Enable execution trace
trace: false

# Show heatmap in core-dump
heatmap: false
"""
            path.write_text(template)
        else:
            raise ValueError(f"Unsupported format: {ext}")

        logger.info("Created template config at %s", path)
        return config


def load_config(path: Union[str, Path]) -> BattleConfig:
    """Convenience function to load a BattleConfig from a file."""
    return BattleConfig.from_file(path)