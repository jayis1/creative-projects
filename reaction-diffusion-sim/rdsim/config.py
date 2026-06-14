"""
Configuration management for rdsim.

Supports loading simulation configurations from YAML, TOML, and JSON files.
Provides a validated SimulationConfig dataclass for programmatic configuration.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

logger = logging.getLogger(__name__)

try:
    import toml as tomllib
    HAS_TOML = True
except ImportError:
    HAS_TOML = False


@dataclass
class PerturbationConfig:
    """Configuration for initial perturbation."""
    type: str = "center_square"
    size: int = 20
    u_val: float = 0.0
    v_val: float = 1.0
    noise: float = 0.01
    center: Optional[tuple] = None
    count: int = 5
    radius: int = 0
    thickness: int = 3
    width: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d = {k: v for k, v in d.items() if v is not None}
        return d


@dataclass
class VisualizationConfig:
    """Configuration for visualization output."""
    field: str = "v"
    cmap: str = "inferno"
    output: str = "output.png"
    gif_path: Optional[str] = None
    gif_frames: int = 60
    gif_fps: int = 15
    grid_view: bool = False
    grid_rows: int = 3
    grid_cols: int = 3
    video_path: Optional[str] = None
    video_fps: int = 30
    frames_dir: Optional[str] = None
    every: int = 100


@dataclass
class SimulationConfig:
    """Complete simulation configuration with validation.

    This dataclass holds all parameters needed to configure and run
    a reaction-diffusion simulation. It can be created programmatically
    or loaded from a YAML/TOML/JSON configuration file.

    Example:
        >>> config = SimulationConfig(model="gray-scott", grid_size=128, steps=5000)
        >>> config.validate()  # raises ValueError if invalid
    """
    # Model
    model: str = "gray-scott"
    preset: Optional[str] = None

    # Grid
    grid_size: int = 128
    steps: int = 5000
    dt: float = 1.0

    # Model parameters (model-specific overrides)
    params: Dict[str, float] = field(default_factory=dict)

    # Integration
    method: str = "euler"
    adaptive: bool = False
    clamp: bool = True

    # Boundary conditions
    bc: str = "periodic"

    # Perturbation
    perturbation: Optional[PerturbationConfig] = None

    # Visualization
    viz: VisualizationConfig = field(default_factory=VisualizationConfig)

    # Statistics
    stats: bool = False
    stats_file: Optional[str] = None

    # Checkpoint
    checkpoint: Optional[str] = None
    resume: Optional[str] = None

    # Logging
    log_level: str = "INFO"
    seed: Optional[int] = None

    def validate(self) -> None:
        """Validate configuration parameters. Raises ValueError if invalid."""
        from rdsim.models import MODELS

        if self.model not in MODELS:
            raise ValueError(
                f"Unknown model '{self.model}'. "
                f"Available: {', '.join(MODELS.keys())}"
            )

        if self.grid_size < 4:
            raise ValueError(f"grid_size must be >= 4, got {self.grid_size}")

        if self.grid_size > 4096:
            logger.warning(
                f"grid_size={self.grid_size} is very large; "
                f"memory usage will be significant"
            )

        if self.steps < 1:
            raise ValueError(f"steps must be >= 1, got {self.steps}")

        if self.dt <= 0:
            raise ValueError(f"dt must be > 0, got {self.dt}")

        if self.method not in ("euler", "rk2"):
            raise ValueError(
                f"method must be 'euler' or 'rk2', got '{self.method}'"
            )

        if self.bc not in ("periodic", "dirichlet", "neumann"):
            raise ValueError(
                f"bc must be 'periodic', 'dirichlet', or 'neumann', "
                f"got '{self.bc}'"
            )

        if self.preset is not None:
            from rdsim.presets import get_preset
            try:
                get_preset(self.preset)
            except KeyError as e:
                raise ValueError(str(e))

        logger.debug("Configuration validated successfully")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for serialization."""
        d = asdict(self)
        return d

    def to_yaml(self, filepath: str) -> None:
        """Save configuration to a YAML file."""
        with open(filepath, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
        logger.info(f"Configuration saved to {filepath}")

    def to_json(self, filepath: str) -> None:
        """Save configuration to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Configuration saved to {filepath}")


def load_config(filepath: Union[str, Path]) -> SimulationConfig:
    """Load a simulation configuration from a file.

    Supports YAML (.yaml, .yml), TOML (.toml), and JSON (.json) formats.

    Args:
        filepath: Path to the configuration file.

    Returns:
        SimulationConfig instance.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file format is unsupported or content is invalid.

    Example:
        >>> config = load_config("simulation.yaml")
        >>> config.validate()
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    suffix = filepath.suffix.lower()
    raw: Dict[str, Any] = {}

    with open(filepath) as f:
        if suffix in (".yaml", ".yml"):
            raw = yaml.safe_load(f) or {}
        elif suffix == ".toml":
            if not HAS_TOML:
                raise ImportError(
                    "toml package is required for TOML config files. "
                    "Install with: pip install toml"
                )
            raw = tomllib.load(f)
        elif suffix == ".json":
            raw = json.load(f)
        else:
            raise ValueError(
                f"Unsupported config format: {suffix}. "
                f"Use .yaml, .yml, .toml, or .json"
            )

    logger.info(f"Loaded configuration from {filepath}")

    # Parse nested dicts into dataclasses
    pert_data = raw.pop("perturbation", None)
    pert = None
    if pert_data is not None and isinstance(pert_data, dict):
        pert = PerturbationConfig(**pert_data)

    viz_data = raw.pop("viz", raw.pop("visualization", None))
    viz = VisualizationConfig()
    if viz_data is not None and isinstance(viz_data, dict):
        viz = VisualizationConfig(**viz_data)

    config = SimulationConfig(
        perturbation=pert,
        viz=viz,
        **{k: v for k, v in raw.items() if k not in ("perturbation", "viz", "visualization")},
    )

    return config