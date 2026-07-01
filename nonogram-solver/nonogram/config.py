"""
Configuration management for the nonogram solver.

Supports loading configuration from JSON, YAML, or TOML files, with
sensible defaults and validation. Configuration controls solver parameters,
rendering options, generator settings, and logging behavior.

Example config file (JSON)::

    {
        "solver": {
            "max_iterations": 5000,
            "max_backtracks": 50000,
            "use_mrv": true
        },
        "generator": {
            "default_density": 0.55,
            "default_max_attempts": 200
        },
        "rendering": {
            "cell_size": 20,
            "filled_color": [40, 40, 40],
            "empty_color": [255, 255, 255],
            "unknown_color": [200, 200, 200]
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    }
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

try:
    import tomllib  # Python 3.11+
    _HAS_TOMLIB = True
except ImportError:
    _HAS_TOMLIB = False

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# --------------------------------------------------------------------------- #
# Dataclasses for typed configuration
# --------------------------------------------------------------------------- #

@dataclass
class SolverConfig:
    """Solver parameters."""
    max_iterations: int = 10000
    max_backtracks: int = 100000
    use_mrv: bool = True

    def validate(self) -> None:
        if self.max_iterations < 1:
            raise ValueError("solver.max_iterations must be >= 1")
        if self.max_backtracks < 0:
            raise ValueError("solver.max_backtracks must be >= 0")


@dataclass
class GeneratorConfig:
    """Generator parameters."""
    default_density: float = 0.55
    default_max_attempts: int = 200

    def validate(self) -> None:
        if not (0 < self.default_density < 1):
            raise ValueError("generator.default_density must be in (0, 1)")
        if self.default_max_attempts < 1:
            raise ValueError("generator.default_max_attempts must be >= 1")


@dataclass
class RenderingConfig:
    """Rendering parameters."""
    cell_size: int = 20
    filled_color: Tuple[int, int, int] = (40, 40, 40)
    empty_color: Tuple[int, int, int] = (255, 255, 255)
    unknown_color: Tuple[int, int, int] = (200, 200, 200)

    def validate(self) -> None:
        if self.cell_size < 1:
            raise ValueError("rendering.cell_size must be >= 1")
        for name in ("filled_color", "empty_color", "unknown_color"):
            val = getattr(self, name)
            if not (isinstance(val, (tuple, list)) and len(val) == 3):
                raise ValueError(f"rendering.{name} must be a 3-tuple of ints")
            if not all(0 <= int(v) <= 255 for v in val):
                raise ValueError(f"rendering.{name} values must be 0-255")


@dataclass
class LoggingConfig:
    """Logging parameters."""
    level: str = "WARNING"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_file: Optional[str] = None

    def validate(self) -> None:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level.upper() not in valid:
            raise ValueError(f"logging.level must be one of {valid}")


@dataclass
class AppConfig:
    """Top-level application configuration."""
    solver: SolverConfig = field(default_factory=SolverConfig)
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    rendering: RenderingConfig = field(default_factory=RenderingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def validate(self) -> None:
        """Validate all sub-configs; raises ValueError on first issue."""
        self.solver.validate()
        self.generator.validate()
        self.rendering.validate()
        self.logging.validate()

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert tuples to lists for JSON serialisation.
        r = d["rendering"]
        for k in ("filled_color", "empty_color", "unknown_color"):
            r[k] = list(r[k])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AppConfig":
        cfg = cls()
        if "solver" in d:
            cfg.solver = SolverConfig(**d["solver"])
        if "generator" in d:
            cfg.generator = GeneratorConfig(**d["generator"])
        if "rendering" in d:
            r = d["rendering"]
            # Ensure colours are tuples.
            for k in ("filled_color", "empty_color", "unknown_color"):
                if k in r:
                    r[k] = tuple(r[k])
            cfg.rendering = RenderingConfig(**r)
        if "logging" in d:
            cfg.logging = LoggingConfig(**d["logging"])
        cfg.validate()
        return cfg


# --------------------------------------------------------------------------- #
# File loaders
# --------------------------------------------------------------------------- #

def load_config(path: str) -> AppConfig:
    """Load configuration from a JSON, YAML, or TOML file.

    The file extension determines the parser:
        ``.json`` → JSON
        ``.yaml`` / ``.yml`` → YAML (requires PyYAML)
        ``.toml`` → TOML (requires Python 3.11+ or ``tomli``)

    Parameters
    ----------
    path : str
        Path to the configuration file.

    Returns
    -------
    AppConfig
        Parsed and validated configuration.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the file format is unsupported or the configuration is invalid.
    ImportError
        If a required parser library is not installed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    suffix = p.suffix.lower()
    text = p.read_text()

    if suffix == ".json":
        data = json.loads(text)
    elif suffix in (".yaml", ".yml"):
        if not _HAS_YAML:
            raise ImportError("PyYAML is required to load YAML config files")
        data = yaml.safe_load(text)  # type: ignore
    elif suffix == ".toml":
        if _HAS_TOMLIB:
            data = tomllib.loads(text)  # type: ignore
        else:
            raise ImportError("tomllib (Python 3.11+) or tomli is required for TOML")
    else:
        raise ValueError(
            f"Unsupported config format '{suffix}'. Use .json, .yaml, or .toml"
        )

    return AppConfig.from_dict(data)


def save_config(config: AppConfig, path: str) -> None:
    """Save configuration to a JSON, YAML, or TOML file."""
    p = Path(path)
    suffix = p.suffix.lower()
    data = config.to_dict()

    if suffix == ".json":
        p.write_text(json.dumps(data, indent=2))
    elif suffix in (".yaml", ".yml"):
        if not _HAS_YAML:
            raise ImportError("PyYAML is required to save YAML config files")
        p.write_text(yaml.dump(data, default_flow_style=False))  # type: ignore
    elif suffix == ".toml":
        # Simple TOML serialiser (no external dep needed for flat-ish structure).
        p.write_text(_to_toml(data))
    else:
        raise ValueError(
            f"Unsupported config format '{suffix}'. Use .json, .yaml, or .toml"
        )


def _to_toml(data: dict, prefix: str = "") -> str:
    """Minimal TOML serialiser for AppConfig-shaped dicts."""
    lines: List[str] = []
    for key, val in data.items():
        if isinstance(val, dict):
            section = f"{prefix}.{key}" if prefix else key
            lines.append(f"\n[{section}]")
            lines.append(_to_toml(val, section))
        elif isinstance(val, (list, tuple)):
            arr = ", ".join(str(v) if not isinstance(v, str) else f'"{v}"' for v in val)
            lines.append(f'{key} = [{arr}]')
        elif isinstance(val, bool):
            lines.append(f'{key} = {"true" if val else "false"}')
        elif isinstance(val, str):
            lines.append(f'{key} = "{val}"')
        else:
            lines.append(f"{key} = {val}")
    return "\n".join(lines)


def setup_logging(config: LoggingConfig) -> logging.Logger:
    """Configure the root logger from a LoggingConfig."""
    level = getattr(logging, config.level.upper(), logging.WARNING)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if config.log_file:
        handlers.append(logging.FileHandler(config.log_file))
    logging.basicConfig(
        level=level,
        format=config.format,
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("nonogram")


# Default singleton for convenience.
DEFAULT_CONFIG = AppConfig()