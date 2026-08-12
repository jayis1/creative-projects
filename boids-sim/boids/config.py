"""Configuration management for boids simulation.

Supports JSON, YAML (via stdlib fallback), and TOML config files,
plus a set of named presets for different flocking behaviors.
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict, fields
from typing import Any, Optional


@dataclass
class SimulationConfig:
    """Configuration for the boids simulation.

    All parameters have sensible defaults. Override any subset via
    constructor kwargs or config file loading.
    """

    # World dimensions
    width: float = 800.0
    height: float = 600.0

    # Population
    num_boids: int = 150

    # Boid physics
    max_speed: float = 4.0
    max_force: float = 0.2
    radius: float = 3.0

    # Perception radii for each behavior
    sep_perception: float = 30.0
    ali_perception: float = 60.0
    coh_perception: float = 60.0

    # Behavior weights
    w_sep: float = 1.5
    w_ali: float = 1.0
    w_coh: float = 1.0
    w_boundary: float = 1.0
    w_avoid: float = 2.0
    w_flee: float = 3.0
    w_seek: float = 0.5
    w_wander: float = 0.1

    # Simulation
    dt: float = 1.0
    boundary_margin: float = 50.0
    use_wrap: bool = False  # toroidal world if True

    # Spatial hash
    cell_size: float = 60.0

    # Predator settings
    predator_max_speed: float = 6.0
    predator_max_force: float = 0.3
    predator_chase_radius: float = 200.0
    predator_panic_dist: float = 80.0

    # Path following
    w_path: float = 1.0
    path_arrival_radius: float = 20.0
    path_loop: bool = False

    # Species
    num_species: int = 1  # 1 = single species (all boids interact)

    # Arrival behavior
    w_arrive: float = 0.5
    arrive_slow_radius: float = 100.0

    # Spatial index type: "grid" or "quadtree"
    spatial_index: str = "grid"

    # Trail rendering
    trail_length: int = 0  # 0 = disabled
    trail_fade: bool = True

    # Rendering
    background_color: str = "#1a1a2e"
    boid_color: str = "#e0e0e0"
    predator_color: str = "#ff4444"
    obstacle_color: str = "#888888"
    goal_color: str = "#ffd700"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationConfig":
        """Create config from dict, ignoring unknown keys."""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def save(self, path: str) -> None:
        save_config(self, path)

    @classmethod
    def load(cls, path: str) -> "SimulationConfig":
        return load_config(path)


# --------------------------------------------------------------------------- #
#  Presets
# --------------------------------------------------------------------------- #
PRESETS: dict[str, dict[str, Any]] = {
    "default": {},

    "tight-flock": {
        "w_sep": 2.0, "w_ali": 1.5, "w_coh": 1.5,
        "sep_perception": 25, "ali_perception": 50, "coh_perception": 50,
        "num_boids": 200, "max_speed": 3.5,
    },

    "loose-swarm": {
        "w_sep": 0.8, "w_ali": 0.5, "w_coh": 2.0,
        "sep_perception": 40, "ali_perception": 80, "coh_perception": 100,
        "num_boids": 150, "max_speed": 3.0,
    },

    "fast-murmuration": {
        "w_sep": 1.2, "w_ali": 2.0, "w_coh": 1.0,
        "num_boids": 300, "max_speed": 6.0, "max_force": 0.3,
        "sep_perception": 20, "ali_perception": 70, "coh_perception": 70,
        "use_wrap": True,
    },

    "schooling-fish": {
        "w_sep": 1.8, "w_ali": 1.2, "w_coh": 1.8,
        "num_boids": 250, "max_speed": 3.0, "max_force": 0.15,
        "sep_perception": 25, "ali_perception": 55, "coh_perception": 55,
        "use_wrap": True,
    },

    "chaos": {
        "w_sep": 3.0, "w_ali": 0.1, "w_coh": 0.1,
        "num_boids": 100, "max_speed": 5.0, "max_force": 0.4,
        "w_wander": 1.0,
    },

    "calm-glide": {
        "w_sep": 1.0, "w_ali": 1.0, "w_coh": 1.0,
        "num_boids": 80, "max_speed": 2.0, "max_force": 0.1,
        # FIX: removed duplicate 'max_force' key (was silently overwriting)
        "dt": 0.5,
    },

    "predator-hunt": {
        "num_boids": 200, "max_speed": 4.5,
        "w_sep": 2.0, "w_ali": 1.0, "w_coh": 0.8,
        "w_flee": 5.0, "predator_panic_dist": 120,
        "use_wrap": True,
    },

    "multi-species": {
        "num_boids": 200, "num_species": 3,
        "max_speed": 4.0, "max_force": 0.2,
        "w_sep": 1.8, "w_ali": 1.2, "w_coh": 1.2,
        "use_wrap": True, "trail_length": 10,
    },

    "path-followers": {
        "num_boids": 80, "max_speed": 3.5,
        "w_sep": 1.2, "w_ali": 0.8, "w_coh": 0.8,
        "w_path": 2.0, "path_loop": True, "path_arrival_radius": 25,
        "spatial_index": "quadtree",
    },

    "quadtree-demo": {
        "num_boids": 300, "max_speed": 4.0,
        "spatial_index": "quadtree",
        "w_sep": 1.5, "w_ali": 1.0, "w_coh": 1.0,
        "use_wrap": True,
    },
}


def get_preset(name: str) -> SimulationConfig:
    """Get a named preset configuration."""
    if name not in PRESETS:
        raise ValueError(
            f"Unknown preset '{name}'. Available: {', '.join(sorted(PRESETS))}"
        )
    return SimulationConfig.from_dict(PRESETS[name])


def list_presets() -> list[str]:
    """List all available preset names."""
    return sorted(PRESETS.keys())


# --------------------------------------------------------------------------- #
#  Config file I/O
# --------------------------------------------------------------------------- #
def save_config(config: SimulationConfig, path: str) -> None:
    """Save config to JSON, YAML, or TOML based on file extension."""
    data = config.to_dict()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    elif ext in (".yaml", ".yml"):
        _save_yaml(data, path)
    elif ext == ".toml":
        _save_toml(data, path)
    else:
        raise ValueError(f"Unsupported config format: {ext} (use .json/.yaml/.toml)")


def load_config(path: str) -> SimulationConfig:
    """Load config from JSON, YAML, or TOML based on file extension."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path) as f:
            data = json.load(f)
    elif ext in (".yaml", ".yml"):
        data = _load_yaml(path)
    elif ext == ".toml":
        data = _load_toml(path)
    else:
        raise ValueError(f"Unsupported config format: {ext} (use .json/.yaml/.toml)")
    return SimulationConfig.from_dict(data)


# --- YAML support (minimal, stdlib-only) ---
def _save_yaml(data: dict, path: str) -> None:
    """Write a flat dict as simple YAML (key: value)."""
    lines = []
    for k, v in data.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, str):
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f"{k}: {v}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def _load_yaml(path: str) -> dict:
    """Parse a simple flat YAML file."""
    data: dict[str, Any] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # type inference
            if val.lower() in ("true", "false"):
                data[key] = val.lower() == "true"
            else:
                try:
                    if "." in val:
                        data[key] = float(val)
                    else:
                        data[key] = int(val)
                except ValueError:
                    data[key] = val
    return data


# --- TOML support (stdlib tomllib in 3.11+, fallback to manual) ---
def _save_toml(data: dict, path: str) -> None:
    """Write a flat dict as TOML."""
    lines = []
    for k, v in data.items():
        if isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        elif isinstance(v, (int, float)):
            lines.append(f"{k} = {v}")
        else:
            lines.append(f'{k} = "{v}"')
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def _load_toml(path: str) -> dict:
    """Load TOML using stdlib tomllib if available, else manual parse."""
    try:
        import tomllib
        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        # Python < 3.11: manual parse for flat key=value TOML
        data: dict[str, Any] = {}
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("["):
                    continue
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if val.lower() in ("true", "false"):
                    data[key] = val.lower() == "true"
                else:
                    try:
                        if "." in val:
                            data[key] = float(val)
                        else:
                            data[key] = int(val)
                    except ValueError:
                        data[key] = val
        return data