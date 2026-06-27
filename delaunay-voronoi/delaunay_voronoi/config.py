"""
Configuration management via JSON, YAML, or TOML files.

The toolkit accepts a configuration dict that controls rendering styles,
algorithm parameters, output formats, and CLI defaults.  This module
provides:

  * :class:`Config` — a typed configuration dataclass with defaults
  * :func:`load_config` — auto-detect format by file extension
  * :func:`save_config` — write config to JSON or TOML

YAML support uses the stdlib ``json`` fallback when ``pyyaml`` is not
installed (a YAML file is converted via a minimal parser for simple
flat configs, or the user is directed to install pyyaml).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class RenderConfig:
    """Rendering style options."""
    width: int = 800
    height: int = 600
    background: str = "#0f0f17"
    delaunay_color: str = "#3a506b"
    voronoi_color: str = "#e0a458"
    point_color: str = "#5bc0be"
    hull_color: str = "#9bf6ff"
    point_radius: float = 3.0
    show_points: bool = True
    show_delaunay: bool = True
    show_voronoi: bool = True
    show_hull: bool = True


@dataclass
class AlgorithmConfig:
    """Algorithm parameters."""
    num_points: int = 30
    seed: int = 42
    lloyd_iterations: int = 0
    ruppert_min_angle: float = 30.0
    ruppert_max_area: Optional[float] = None
    ruppert_max_points: int = 10000


@dataclass
class Config:
    """Top-level configuration."""
    render: RenderConfig = field(default_factory=RenderConfig)
    algorithm: AlgorithmConfig = field(default_factory=AlgorithmConfig)
    output_dir: str = "."
    log_level: str = "INFO"

    # ----- conversion -----

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        render_data = data.get("render", {})
        algo_data = data.get("algorithm", {})
        return cls(
            render=RenderConfig(**{k: v for k, v in render_data.items()
                                    if k in RenderConfig.__dataclass_fields__}),
            algorithm=AlgorithmConfig(**{k: v for k, v in algo_data.items()
                                          if k in AlgorithmConfig.__dataclass_fields__}),
            output_dir=data.get("output_dir", "."),
            log_level=data.get("log_level", "INFO"),
        )

    # ----- file I/O -----

    @classmethod
    def load(cls, path: str) -> "Config":
        """Load configuration from a JSON, YAML, or TOML file."""
        return load_config(path)

    def save(self, path: str) -> None:
        """Save configuration to a JSON or TOML file."""
        save_config(self, path)


# --------------------------------------------------------------------------- #
#  Format-specific loaders
# --------------------------------------------------------------------------- #

def _load_json(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _save_json(data: Dict[str, Any], path: str) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_toml(path: str) -> Dict[str, Any]:
    """Load a TOML file using the stdlib ``tomllib`` (Python ≥ 3.11)."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            raise ImportError(
                "TOML support requires Python ≥ 3.11 (tomllib) or the "
                "'tomli' package."
            )
    with open(path, "rb") as f:
        return tomllib.load(f)


def _save_toml(data: Dict[str, Any], path: str) -> None:
    """Save a dict as TOML (minimal writer, no external deps)."""
    lines: list[str] = []
    _write_toml_section(data, lines, prefix="")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def _write_toml_section(data: Dict[str, Any], lines: list[str], prefix: str) -> None:
    scalars: Dict[str, Any] = {}
    tables: Dict[str, Dict[str, Any]] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            tables[k] = v
        else:
            scalars[k] = v
    if prefix:
        lines.append(f"[{prefix}]")
    for k, v in scalars.items():
        lines.append(f"{k} = {_toml_value(v)}")
    for k, v in tables.items():
        lines.append("")
        _write_toml_section(v, lines, prefix=f"{prefix}.{k}" if prefix else k)


def _toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if v is None:
        return '""'
    return json.dumps(str(v))


def _load_yaml(path: str) -> Dict[str, Any]:
    """Load a YAML file using ``pyyaml`` if available, else a minimal parser."""
    try:
        import yaml  # type: ignore
    except ImportError:
        # Minimal flat YAML parser (key: value, 2-space nested tables)
        return _minimal_yaml_load(path)
    with open(path) as f:
        return yaml.safe_load(f)


def _minimal_yaml_load(path: str) -> Dict[str, Any]:
    """Parse simple flat/nested YAML without external deps.

    Supports:
      - ``key: value``
      - 2-space indentation for nested tables
      - int, float, bool, str values
    """
    result: Dict[str, Any] = {}
    stack: list[tuple[int, Dict[str, Any]]] = [(0, result)]
    with open(path) as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            key, _, val_raw = stripped.partition(":")
            key = key.strip()
            val_raw = val_raw.strip()
            # Pop stack to correct indent
            while stack and stack[-1][0] > indent:
                stack.pop()
            if not val_raw:
                # New table
                table: Dict[str, Any] = {}
                if stack:
                    stack[-1][1][key] = table
                stack.append((indent + 2, table))
            else:
                val = _parse_scalar(val_raw)
                if stack:
                    stack[-1][1][key] = val
    return result


def _parse_scalar(s: str) -> Any:
    s = s.strip()
    if s.lower() in ("true", "yes"):
        return True
    if s.lower() in ("false", "no"):
        return False
    if s.lower() in ("null", "none", "~"):
        return None
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #

def load_config(path: str) -> Config:
    """Load a configuration file (auto-detect by extension)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        data = _load_json(path)
    elif ext == ".toml":
        data = _load_toml(path)
    elif ext in (".yaml", ".yml"):
        data = _load_yaml(path)
    else:
        raise ValueError(f"Unsupported config format: {ext}")
    return Config.from_dict(data)


def save_config(config: Config, path: str) -> None:
    """Save a configuration to file (JSON or TOML by extension)."""
    ext = os.path.splitext(path)[1].lower()
    data = config.to_dict()
    if ext == ".json":
        _save_json(data, path)
    elif ext == ".toml":
        _save_toml(data, path)
    else:
        raise ValueError(f"Unsupported config format: {ext}")


def default_config() -> Config:
    """Return the default configuration."""
    return Config()