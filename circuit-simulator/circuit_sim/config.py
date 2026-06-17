"""Simulation configuration and settings."""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


@dataclass
class SimConfig:
    """Simulation configuration.

    Attributes:
        step_ns: Simulation time step in nanoseconds (default: 1).
        default_gate_delay_ns: Default gate propagation delay in nanoseconds (default: 1).
        default_sequential_delay_ns: Default sequential element delay in nanoseconds (default: 3).
        default_clock_period_ns: Default clock period in nanoseconds (default: 20).
        default_clock_duty_cycle: Default clock duty cycle (default: 0.5).
        convergence_multiplier: Multiplier for convergence iteration limit (default: 2).
        convergence_base: Base convergence iteration limit (default: 50).
        trace_all_wires: Whether to trace all wires by default (default: False).
        log_level: Logging level (default: 'WARNING').
    """

    step_ns: int = 1
    default_gate_delay_ns: int = 1
    default_sequential_delay_ns: int = 3
    default_clock_period_ns: int = 20
    default_clock_duty_cycle: float = 0.5
    convergence_multiplier: int = 2
    convergence_base: int = 50
    trace_all_wires: bool = False
    log_level: str = "WARNING"

    def to_dict(self) -> dict:
        """Convert config to a dictionary."""
        return asdict(self)

    def to_json(self, path: Optional[str] = None) -> str:
        """Serialize config to JSON. Optionally write to a file."""
        data = json.dumps(self.to_dict(), indent=2)
        if path:
            Path(path).write_text(data)
            logger.info("Config written to %s", path)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "SimConfig":
        """Create a SimConfig from a dictionary."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_json(cls, path_or_str: str) -> "SimConfig":
        """Load a SimConfig from a JSON file path or JSON string."""
        try:
            p = Path(path_or_str)
            if p.exists():
                data = json.loads(p.read_text())
            else:
                data = json.loads(path_or_str)
        except (OSError, ValueError):
            data = json.loads(path_or_str)
        return cls.from_dict(data)

    @classmethod
    def from_toml(cls, path: str) -> "SimConfig":
        """Load a SimConfig from a TOML file."""
        if tomllib is None:
            raise ImportError(
                "TOML support requires Python 3.11+ or the 'tomli' package. "
                "Install it with: pip install tomli"
            )
        data = tomllib.loads(Path(path).read_text())
        # Look for [circuit_sim] section, or use root
        section = data.get("circuit_sim", data)
        return cls.from_dict(section)


# Default global config instance
DEFAULT_CONFIG = SimConfig()