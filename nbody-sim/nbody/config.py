"""Configuration management for nbody-sim.

Supports loading simulation configurations from YAML, JSON, or TOML files.

A config file maps directly to :class:`Simulation` constructor arguments
plus initial-condition preset parameters. Example YAML:

.. code-block:: yaml

    preset: plummer
    n_bodies: 200
    dt: 0.01
    theta: 0.7
    softening: 0.5
    G: 1.0
    steps: 2000
    recenter_com: true
    snapshot_every: 20
    render:
      width: 512
      height: 512
      view_size: 15.0
      trails: true
      color_by_mass: true
    output:
      log: energy.csv
      render_dir: frames/
      save_json: run.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


@dataclass
class RenderConfig:
    """Rendering options for a config-file run."""
    enabled: bool = False
    width: int = 512
    height: int = 512
    view_size: float = 15.0
    trails: bool = True
    color_by_mass: bool = False
    color_by_speed: bool = False
    out_dir: str = "frames"


@dataclass
class OutputConfig:
    """Output options for a config-file run."""
    log_csv: str = ""
    save_json: str = ""
    verbose: bool = False


@dataclass
class SimConfig:
    """Full configuration for a simulation run."""
    preset: str = "two-body"
    n_bodies: int = 100
    seed: int = 0
    dt: float = 0.01
    theta: float = 0.5
    softening: float = 1.0
    G: float = 1.0
    steps: int = 1000
    recenter_com: bool = False
    adaptive_dt: bool = False
    adaptive_eta: float = 0.02
    dt_min: float = 1e-6
    dt_max: float = 0.1
    snapshot_every: int = 0
    benchmark: bool = False
    render: RenderConfig = field(default_factory=RenderConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        d: Dict[str, Any] = {
            "preset": self.preset,
            "n_bodies": self.n_bodies,
            "seed": self.seed,
            "dt": self.dt,
            "theta": self.theta,
            "softening": self.softening,
            "G": self.G,
            "steps": self.steps,
            "recenter_com": self.recenter_com,
            "adaptive_dt": self.adaptive_dt,
            "adaptive_eta": self.adaptive_eta,
            "dt_min": self.dt_min,
            "dt_max": self.dt_max,
            "snapshot_every": self.snapshot_every,
            "benchmark": self.benchmark,
        }
        d["render"] = {
            "enabled": self.render.enabled,
            "width": self.render.width,
            "height": self.render.height,
            "view_size": self.render.view_size,
            "trails": self.render.trails,
            "color_by_mass": self.render.color_by_mass,
            "color_by_speed": self.render.color_by_speed,
            "out_dir": self.render.out_dir,
        }
        d["output"] = {
            "log_csv": self.output.log_csv,
            "save_json": self.output.save_json,
            "verbose": self.output.verbose,
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SimConfig":
        """Build a config from a plain dict, filling defaults for missing keys."""
        render_d = d.get("render", {})
        output_d = d.get("output", {})
        return cls(
            preset=d.get("preset", "two-body"),
            n_bodies=int(d.get("n_bodies", 100)),
            seed=int(d.get("seed", 0)),
            dt=float(d.get("dt", 0.01)),
            theta=float(d.get("theta", 0.5)),
            softening=float(d.get("softening", 1.0)),
            G=float(d.get("G", 1.0)),
            steps=int(d.get("steps", 1000)),
            recenter_com=bool(d.get("recenter_com", False)),
            adaptive_dt=bool(d.get("adaptive_dt", False)),
            adaptive_eta=float(d.get("adaptive_eta", 0.02)),
            dt_min=float(d.get("dt_min", 1e-6)),
            dt_max=float(d.get("dt_max", 0.1)),
            snapshot_every=int(d.get("snapshot_every", 0)),
            benchmark=bool(d.get("benchmark", False)),
            render=RenderConfig(
                enabled=bool(render_d.get("enabled", False)),
                width=int(render_d.get("width", 512)),
                height=int(render_d.get("height", 512)),
                view_size=float(render_d.get("view_size", 15.0)),
                trails=bool(render_d.get("trails", True)),
                color_by_mass=bool(render_d.get("color_by_mass", False)),
                color_by_speed=bool(render_d.get("color_by_speed", False)),
                out_dir=str(render_d.get("out_dir", "frames")),
            ),
            output=OutputConfig(
                log_csv=str(output_d.get("log_csv", "")),
                save_json=str(output_d.get("save_json", "")),
                verbose=bool(output_d.get("verbose", False)),
            ),
        )


def load_config(path: str) -> SimConfig:
    """Load a :class:`SimConfig` from a file.

    Supports ``.yaml``/``.yml``, ``.json``, and ``.toml`` extensions.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml"):
        if yaml is None:
            raise ImportError("PyYAML is required for YAML config files")
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    elif ext == ".json":
        with open(path) as f:
            data = json.load(f)
    elif ext == ".toml":
        if tomllib is None:
            raise ImportError("Python 3.11+ is required for TOML config files")
        with open(path, "rb") as f:
            data = tomllib.load(f)
    else:
        raise ValueError(
            f"Unsupported config format '{ext}'. "
            "Use .yaml, .yml, .json, or .toml"
        )
    return SimConfig.from_dict(data)


def save_config(cfg: SimConfig, path: str) -> None:
    """Save a :class:`SimConfig` to a file based on extension."""
    ext = os.path.splitext(path)[1].lower()
    d = cfg.to_dict()
    if ext in (".yaml", ".yml"):
        if yaml is None:
            raise ImportError("PyYAML is required for YAML config files")
        with open(path, "w") as f:
            yaml.dump(d, f, default_flow_style=False, sort_keys=False)
    elif ext == ".json":
        with open(path, "w") as f:
            json.dump(d, f, indent=2)
    elif ext == ".toml":
        # Simple TOML writer — doesn't support nested tables deeply, but
        # we flatten the render/output sections.
        lines: list[str] = []
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"[{k}]")
                for sk, sv in v.items():
                    if isinstance(sv, bool):
                        lines.append(f'{sk} = {"true" if sv else "false"}')
                    elif isinstance(sv, str):
                        lines.append(f'{sk} = "{sv}"')
                    else:
                        lines.append(f"{sk} = {sv}")
                lines.append("")
            elif isinstance(v, bool):
                lines.append(f'{k} = {"true" if v else "false"}')
            elif isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            else:
                lines.append(f"{k} = {v}")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
    else:
        raise ValueError(f"Unsupported config format '{ext}'")


__all__ = ["SimConfig", "RenderConfig", "OutputConfig", "load_config", "save_config"]