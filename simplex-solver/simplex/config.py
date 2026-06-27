"""Configuration-file support for simplex-solver.

Reads solver configuration from JSON, TOML, or YAML files (auto-detected by
file extension) and merges with CLI overrides.  This lets users persist
their preferred solver settings (iteration limits, pivot rule, MILP node
cap, log level, etc.) in a project-level config file instead of repeating
flags on every invocation.

Supported config keys (all optional)::

    max_iter:       10000          # Simplex pivot limit per solve
    max_nodes:      10000          # MILP node limit
    bland:          true            # Use Bland's anti-cycling rule
    use_cuts:       true            # Enable Gomory cuts in MILP
    eps:            1.0e-7          # Integrality tolerance
    log_level:      "WARNING"       # DEBUG / INFO / WARNING / ERROR
    output_format:  "text"          # text / json / table
    sensitivity:    false           # Run sensitivity analysis by default

Example ``simplex.json``::

    {
      "max_iter": 50000,
      "bland": false,
      "log_level": "INFO"
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

__all__ = ["SolverConfig", "load_config", "save_config", "DEFAULT_CONFIG_PATH"]


DEFAULT_CONFIG_PATH = Path.home() / ".simplex" / "config.json"


@dataclass
class SolverConfig:
    """Solver configuration with sensible defaults."""

    max_iter: int = 10_000
    max_nodes: int = 10_000
    bland: bool = True
    use_cuts: bool = True
    eps: float = 1e-7
    log_level: str = "WARNING"
    output_format: str = "json"  # "json", "text", "table"
    sensitivity: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("extra", None)
        d.update(self.extra)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SolverConfig":
        """Build a :class:`SolverConfig` from a dict, storing unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values() if f.name != "extra"}
        kwargs: dict[str, Any] = {}
        extra: dict[str, Any] = {}
        for k, v in data.items():
            if k in known:
                kwargs[k] = v
            else:
                extra[k] = v
        cfg = cls(**kwargs)
        cfg.extra = extra
        return cfg

    def merge(self, overrides: dict[str, Any]) -> "SolverConfig":
        """Return a new config with ``overrides`` applied (non-None values)."""
        d = self.to_dict()
        for k, v in overrides.items():
            if v is not None:
                d[k] = v
        return SolverConfig.from_dict(d)


def _load_toml(path: str) -> dict[str, Any]:
    """Load a TOML file using stdlib ``tomllib`` (Python 3.11+) or ``tomli``."""
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore
        except ModuleNotFoundError:
            raise ImportError(
                "TOML support requires Python 3.11+ or the 'tomli' package"
            )
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _load_yaml(path: str) -> dict[str, Any]:
    """Load a YAML file (requires PyYAML)."""
    try:
        import yaml
    except ModuleNotFoundError:
        raise ImportError("YAML support requires the 'pyyaml' package")
    with open(path) as fh:
        data = yaml.safe_load(fh)
    return data or {}


def load_config(path: str | os.PathLike | None = None) -> SolverConfig:
    """Load a :class:`SolverConfig` from a file.

    If ``path`` is ``None``, looks for a config file in these locations
    (first match wins):

    1. ``./simplex.json`` (current directory)
    2. ``./simplex.toml``
    3. ``./simplex.yaml``
    4. ``~/.simplex/config.json``

    If no config file is found (or ``path`` points to a nonexistent file),
    returns the default :class:`SolverConfig`.
    """
    if path is not None:
        path = Path(path)
        if not path.exists():
            return SolverConfig()
        return _load_from_path(path)
    # Search default locations.
    candidates = [
        Path.cwd() / "simplex.json",
        Path.cwd() / "simplex.toml",
        Path.cwd() / "simplex.yaml",
        Path.cwd() / "simplex.yml",
        DEFAULT_CONFIG_PATH,
    ]
    for p in candidates:
        if p.exists():
            return _load_from_path(p)
    return SolverConfig()


def _load_from_path(path: Path) -> SolverConfig:
    suffix = path.suffix.lower()
    if suffix == ".json":
        with open(path) as fh:
            data = json.load(fh)
    elif suffix == ".toml":
        data = _load_toml(str(path))
    elif suffix in (".yaml", ".yml"):
        data = _load_yaml(str(path))
    else:
        # Try JSON first, then TOML.
        try:
            with open(path) as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, ValueError):
            data = _load_toml(str(path))
    if not isinstance(data, dict):
        raise ValueError(f"config file {path} must contain a mapping, got {type(data)}")
    return SolverConfig.from_dict(data)


def save_config(config: SolverConfig, path: str | os.PathLike) -> None:
    """Write ``config`` to ``path`` in JSON format."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(config.to_dict(), fh, indent=2, default=str)
        fh.write("\n")