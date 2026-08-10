"""
seamcarving/config.py — Configuration file support.

Loads configuration from JSON, YAML, or TOML files.  Provides a
``CarverConfig`` dataclass with sensible defaults.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union

if sys.version_info >= (3, 11):
    import tomllib
    _HAS_TOMLLIB = True
else:
    _HAS_TOMLLIB = False

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

from .exceptions import InvalidConfigError
from .energy import EnergyType

PathLike = Union[str, Path]


@dataclass
class CarverConfig:
    """Configuration for seam carving operations.

    Attributes
    ----------
    energy_type : str
        Energy function name (sobel, prewitt, laplacian, gradient, forward,
        hofer, entropy).
    target_width : Optional[int]
        Target image width (None = no width change).
    target_height : Optional[int]
        Target image height (None = no height change).
    protect_mask_path : Optional[str]
        Path to a PGM mask file for region protection.
    remove_mask_path : Optional[str]
        Path to a PGM mask file for object removal.
    energy_map_path : Optional[str]
        If set, save the energy map visualization to this path.
    seam_vis_path : Optional[str]
        If set, save a seam visualization to this path.
    animation_dir : Optional[str]
        If set, export animation frames to this directory.
    animation_format : str
        Output format for animation frames (ppm, png).
    output_format : str
        Output image format (ppm, pgm, png).
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    log_file : Optional[str]
        If set, write logs to this file.
    json_logs : bool
        If True, format logs as JSON.
    max_iterations : int
        Maximum iterations for object removal.
    record_seams : bool
        If True, record seam history for animation/debugging.
    """

    energy_type: str = "sobel"
    target_width: Optional[int] = None
    target_height: Optional[int] = None
    protect_mask_path: Optional[str] = None
    remove_mask_path: Optional[str] = None
    energy_map_path: Optional[str] = None
    seam_vis_path: Optional[str] = None
    animation_dir: Optional[str] = None
    animation_format: str = "png"
    output_format: str = "ppm"
    log_level: str = "INFO"
    log_file: Optional[str] = None
    json_logs: bool = False
    max_iterations: int = 500
    record_seams: bool = False

    def validate(self) -> None:
        """Validate configuration values. Raises InvalidConfigError on failure."""
        valid_energies = {e.value for e in EnergyType}
        if self.energy_type not in valid_energies:
            raise InvalidConfigError(
                f"energy_type must be one of {valid_energies}, got '{self.energy_type}'"
            )
        if self.target_width is not None and self.target_width <= 0:
            raise InvalidConfigError("target_width must be positive")
        if self.target_height is not None and self.target_height <= 0:
            raise InvalidConfigError("target_height must be positive")
        if self.max_iterations <= 0:
            raise InvalidConfigError("max_iterations must be positive")
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_log_levels:
            raise InvalidConfigError(
                f"log_level must be one of {valid_log_levels}, got '{self.log_level}'"
            )
        valid_formats = {"ppm", "pgm", "png"}
        if self.output_format not in valid_formats:
            raise InvalidConfigError(
                f"output_format must be one of {valid_formats}, got '{self.output_format}'"
            )
        if self.animation_format not in valid_formats:
            raise InvalidConfigError(
                f"animation_format must be one of {valid_formats}, got '{self.animation_format}'"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_yaml(self) -> str:
        """Serialize to YAML string (requires PyYAML)."""
        if not _HAS_YAML:
            raise InvalidConfigError("PyYAML is required for YAML output")
        return yaml.dump(self.to_dict(), default_flow_style=False)

    def save(self, path: PathLike) -> None:
        """Save configuration to a file (format determined by extension)."""
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            path.write_text(self.to_json())
        elif suffix in (".yaml", ".yml"):
            path.write_text(self.to_yaml())
        elif suffix == ".toml":
            # Simple TOML writer (no dependency on toml library)
            lines = []
            for key, val in self.to_dict().items():
                if val is None:
                    continue  # skip None values in TOML
                elif isinstance(val, bool):
                    lines.append(f"{key} = {str(val).lower()}")
                elif isinstance(val, (int, float)):
                    lines.append(f"{key} = {val}")
                else:
                    lines.append(f'{key} = "{val}"')
            path.write_text("\n".join(lines) + "\n")
        else:
            raise InvalidConfigError(f"Unsupported config format: {suffix}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CarverConfig":
        """Create from a dictionary, ignoring unknown keys."""
        valid_keys = {
            "energy_type", "target_width", "target_height",
            "protect_mask_path", "remove_mask_path", "energy_map_path",
            "seam_vis_path", "animation_dir", "animation_format",
            "output_format", "log_level", "log_file", "json_logs",
            "max_iterations", "record_seams",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        config = cls(**filtered)
        config.validate()
        return config

    @classmethod
    def load(cls, path: PathLike) -> "CarverConfig":
        """Load configuration from a JSON, YAML, or TOML file.

        Format is auto-detected from the file extension.
        """
        path = Path(path)
        if not path.exists():
            raise InvalidConfigError(f"Config file not found: {path}")

        text = path.read_text()
        suffix = path.suffix.lower()

        if suffix == ".json":
            data = json.loads(text)
        elif suffix in (".yaml", ".yml"):
            if not _HAS_YAML:
                raise InvalidConfigError("PyYAML is required to load YAML config files")
            data = yaml.safe_load(text)
        elif suffix == ".toml":
            if not _HAS_TOMLLIB:
                raise InvalidConfigError(
                    "TOML support requires Python 3.11+ or the 'tomli' package"
                )
            with open(path, "rb") as f:
                data = tomllib.load(f)
        else:
            raise InvalidConfigError(f"Unsupported config format: {suffix}")

        return cls.from_dict(data)


# Default config instance
DEFAULT_CONFIG = CarverConfig()