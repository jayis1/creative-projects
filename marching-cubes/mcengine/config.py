"""Configuration file support for batch rendering and preset definitions.

Supports JSON and TOML configuration files that describe one or more
render jobs.  Each job specifies the algorithm, sampler, resolution,
bounds, isolevel, output format, and optional transformations.

Example JSON config::

    {
        "jobs": [
            {
                "name": "sphere",
                "algorithm": "mc",
                "sampler": "sphere",
                "sampler_params": {"radius": 1.5},
                "resolution": 48,
                "bounds": [-2, -2, -2, 2, 2, 2],
                "isolevel": 0.0,
                "output": "sphere.obj",
                "preview": true
            },
            {
                "name": "gyroid",
                "algorithm": "mc",
                "sampler": "gyroid",
                "resolution": 64,
                "bounds": [-3, 3],
                "output": "gyroid.stl"
            }
        ]
    }

This module also provides a set of built-in presets for common surfaces.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from .samplers import (
    SphereSampler, TorusSampler, OctahedronSampler, SteinerSampler,
    Genus2Sampler, GyroidSampler, HeartSampler, SuperquadricSampler,
    HyperboloidSampler, NoisySampler, BooleanOpsSampler, Sampler,
)


# Built-in presets: quick-start configurations for common surfaces.
PRESETS: Dict[str, Dict[str, Any]] = {
    "sphere": {
        "algorithm": "mc",
        "sampler": "sphere",
        "sampler_params": {"radius": 1.0},
        "resolution": 32,
        "bounds": [-1.5, 1.5],
        "isolevel": 0.0,
    },
    "torus": {
        "algorithm": "mc",
        "sampler": "torus",
        "sampler_params": {"R": 1.0, "r": 0.35},
        "resolution": 48,
        "bounds": [-1.5, 1.5],
        "isolevel": 0.0,
    },
    "gyroid": {
        "algorithm": "mc",
        "sampler": "gyroid",
        "resolution": 64,
        "bounds": [-3, 3],
        "isolevel": 0.0,
    },
    "octahedron_dc": {
        "algorithm": "dc",
        "sampler": "octahedron",
        "sampler_params": {"r": 1.0},
        "resolution": 16,
        "bounds": [-1.5, 1.5],
        "isolevel": 0.0,
    },
    "heart": {
        "algorithm": "mc",
        "sampler": "heart",
        "resolution": 48,
        "bounds": [-1.5, 1.5],
        "isolevel": 0.0,
    },
    "genus2": {
        "algorithm": "mc",
        "sampler": "genus2",
        "resolution": 48,
        "bounds": [-2, 2],
        "isolevel": 0.0,
    },
}


SAMPLER_CLASSES = {
    "sphere": SphereSampler,
    "torus": TorusSampler,
    "octahedron": OctahedronSampler,
    "steiner": SteinerSampler,
    "genus2": Genus2Sampler,
    "gyroid": GyroidSampler,
    "heart": HeartSampler,
    "superquadric": SuperquadricSampler,
    "hyperboloid": HyperboloidSampler,
}


def _parse_bounds(bounds: Any) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Parse bounds from a list of 2 or 6 floats."""
    if isinstance(bounds, str):
        parts = [float(x) for x in bounds.split(",")]
    else:
        parts = [float(x) for x in bounds]
    if len(parts) == 2:
        lo, hi = parts
        return ((lo, lo, lo), (hi, hi, hi))
    elif len(parts) == 6:
        return ((parts[0], parts[1], parts[2]), (parts[3], parts[4], parts[5]))
    else:
        raise ValueError(f"bounds must have 2 or 6 values, got {len(parts)}")


def _make_sampler(name: str, params: Optional[Dict[str, Any]] = None) -> Sampler:
    """Create a sampler instance from name and parameters dict."""
    name = name.lower()
    if name not in SAMPLER_CLASSES:
        raise ValueError(f"unknown sampler: {name!r}. Available: {list(SAMPLER_CLASSES)}")
    cls = SAMPLER_CLASSES[name]
    params = params or {}
    return cls(**params)


def load_config(path: str) -> Dict[str, Any]:
    """Load a JSON or TOML configuration file."""
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as fh:
        content = fh.read()
    if ext == ".json":
        return json.loads(content)
    elif ext == ".toml":
        try:
            import tomllib  # Python 3.11+
            return tomllib.loads(content)
        except ImportError:
            try:
                import tomli
                return tomli.loads(content)
            except ImportError:
                raise ImportError("TOML support requires Python 3.11+ or the 'tomli' package")
    else:
        # Default to JSON
        return json.loads(content)


def save_config(config: Dict[str, Any], path: str) -> None:
    """Save a configuration dict as a JSON file."""
    with open(path, "w") as fh:
        json.dump(config, fh, indent=2)


def normalize_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a job dict: fill in defaults and validate fields."""
    normalized = {
        "name": job.get("name", "unnamed"),
        "algorithm": job.get("algorithm", "mc"),
        "sampler": job.get("sampler", "sphere"),
        "sampler_params": job.get("sampler_params", {}),
        "resolution": job.get("resolution", 32),
        "bounds": job.get("bounds", [-1.5, 1.5]),
        "isolevel": job.get("isolevel", 0.0),
        "output": job.get("output", None),
        "format": job.get("format", None),
        "preview": job.get("preview", False),
        "preview_width": job.get("preview_width", 60),
        "preview_height": job.get("preview_height", 20),
        "simplify_target": job.get("simplify_target", 0),
        "subdivide": job.get("subdivide", 0),
        "transform": job.get("transform", {}),
    }
    if normalized["algorithm"] not in ("mc", "mt", "dc"):
        raise ValueError(f"invalid algorithm: {normalized['algorithm']!r}")
    return normalized


def get_preset(name: str) -> Dict[str, Any]:
    """Get a built-in preset by name."""
    name = name.lower()
    if name not in PRESETS:
        raise ValueError(f"unknown preset: {name!r}. Available: {list(PRESETS)}")
    return normalize_job(PRESETS[name])


def list_presets() -> List[str]:
    """Return a list of preset names."""
    return sorted(PRESETS.keys())