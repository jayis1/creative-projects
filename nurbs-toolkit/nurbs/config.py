"""Configuration management for the NURBS toolkit.

Supports loading configuration from JSON, TOML, and YAML files,
as well as programmatic construction via a dataclass.

The config controls tessellation quality, export formats, logging,
curvature thresholds, fitting defaults, and more.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


@dataclass
class TessellationConfig:
    """Tessellation sampling defaults."""
    curve_samples: int = 100
    surface_samples_u: int = 50
    surface_samples_v: int = 50


@dataclass
class ExportConfig:
    """Export format options."""
    format: str = "obj"          # obj, ply, stl_ascii, stl_binary
    precision: int = 6           # decimal places for text formats
    flip_faces: bool = False


@dataclass
class FittingConfig:
    """Curve fitting defaults."""
    degree: int = 3
    num_control_points: int = 8
    method: str = "least_squares"  # least_squares or interpolation


@dataclass
class ProjectionConfig:
    """Point projection defaults."""
    coarse_samples: int = 100
    tolerance: float = 1e-8
    max_iterations: int = 50


@dataclass
class ArcLengthConfig:
    """Arc length computation defaults."""
    samples: int = 1000
    method: str = "simpson"   # simpson or gaussian


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "WARNING"    # DEBUG, INFO, WARNING, ERROR
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file: Optional[str] = None


@dataclass
class NURBSConfig:
    """Top-level configuration for the NURBS toolkit.

    Can be loaded from JSON, TOML, or YAML files.
    """
    tessellation: TessellationConfig = field(default_factory=TessellationConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    fitting: FittingConfig = field(default_factory=FittingConfig)
    projection: ProjectionConfig = field(default_factory=ProjectionConfig)
    arc_length: ArcLengthConfig = field(default_factory=ArcLengthConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # -- serialization ------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to a dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize config to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NURBSConfig":
        """Create a config from a dictionary."""
        cfg = cls()
        if "tessellation" in d:
            cfg.tessellation = TessellationConfig(**d["tessellation"])
        if "export" in d:
            cfg.export = ExportConfig(**d["export"])
        if "fitting" in d:
            cfg.fitting = FittingConfig(**d["fitting"])
        if "projection" in d:
            cfg.projection = ProjectionConfig(**d["projection"])
        if "arc_length" in d:
            cfg.arc_length = ArcLengthConfig(**d["arc_length"])
        if "logging" in d:
            cfg.logging = LoggingConfig(**d["logging"])
        return cfg

    @classmethod
    def from_json(cls, s: str) -> "NURBSConfig":
        """Load config from a JSON string."""
        return cls.from_dict(json.loads(s))

    @classmethod
    def from_file(cls, path: str) -> "NURBSConfig":
        """Load config from a file.

        Supports ``.json``, ``.toml``, and ``.yaml``/``.yml``.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext == ".json":
            with open(path, "r") as f:
                return cls.from_dict(json.load(f))
        elif ext == ".toml":
            if tomllib is None:
                raise RuntimeError(
                    "TOML support requires Python 3.11+ or the 'tomli' package"
                )
            with open(path, "rb") as f:
                return cls.from_dict(tomllib.load(f))
        elif ext in (".yaml", ".yml"):
            if yaml is None:
                raise RuntimeError(
                    "YAML support requires the 'pyyaml' package"
                )
            with open(path, "r") as f:
                return cls.from_dict(yaml.safe_load(f))
        else:
            raise ValueError(f"Unsupported config format: {ext}")

    def save(self, path: str) -> None:
        """Save config to a file.

        Supports ``.json``, ``.toml`` (requires Python 3.11+ or tomli),
        and ``.yaml``/``.yml`` (requires pyyaml).
        """
        ext = os.path.splitext(path)[1].lower()
        d = self.to_dict()
        if ext == ".json":
            with open(path, "w") as f:
                json.dump(d, f, indent=2)
        elif ext == ".yaml" or ext == ".yml":
            if yaml is None:
                raise RuntimeError("YAML support requires the 'pyyaml' package")
            with open(path, "w") as f:
                yaml.dump(d, f, default_flow_style=False)
        elif ext == ".toml":
            # Minimal TOML writer (no dependency for writing).
            _write_toml(path, d)
        else:
            raise ValueError(f"Unsupported config format: {ext}")


def _write_toml(path: str, d: Dict[str, Any]) -> None:
    """Write a simple TOML file from a nested dict."""
    lines: list[str] = []
    for section, values in d.items():
        lines.append(f"[{section}]")
        for key, val in values.items():
            if isinstance(val, str):
                lines.append(f'{key} = "{val}"')
            elif isinstance(val, bool):
                lines.append(f"{key} = {str(val).lower()}")
            elif isinstance(val, (int, float)):
                lines.append(f"{key} = {val}")
            else:
                lines.append(f'{key} = "{val}"')
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


# Default config singleton.
DEFAULT_CONFIG = NURBSConfig()