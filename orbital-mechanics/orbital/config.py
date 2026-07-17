"""Configuration management for the orbital-mechanics library.

Supports YAML, JSON, and TOML config files describing a satellite,
its central body, and propagation parameters.  Falls back to JSON
parsing if PyYAML/tomllib are unavailable (Python 3.11+ ships
``tomllib`` in the stdlib; YAML requires the optional ``pyyaml``
package).

Example config (YAML)::

    body: earth
    satellite:
      a_km: 7000
      e: 0.01
      i_deg: 51.6
      raan_deg: 0
      argp_deg: 30
      nu_deg: 0
    propagation:
      method: rkf45        # kepler | rk4 | cowell | rkf45 | universal | j2_secular
      dt_s: 86400
      step_s: 60
      rtol: 1.0e-9
      atol: 1.0e-12
    ground_station:
      lat_deg: 40.0
      lon_deg: 0.0
      min_elevation_deg: 5.0
    output:
      states_csv: orbit_states.csv
      groundtrack_csv: groundtrack.csv
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .bodies import Body, EARTH, MOON, SUN, MARS, VENUS


BODIES: Dict[str, Body] = {
    "earth": EARTH, "moon": MOON, "sun": SUN,
    "mars": MARS, "venus": VENUS,
}

VALID_METHODS = {"kepler", "rk4", "cowell", "rkf45", "universal", "j2_secular"}


@dataclass
class SatelliteConfig:
    a: float
    e: float
    i: float
    raan: float
    argp: float
    nu: float

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SatelliteConfig":
        if "a_km" in d:
            a = float(d["a_km"]) * 1000.0
        elif "a_m" in d:
            a = float(d["a_m"])
        else:
            a = 0.0
        return cls(
            a=a,
            e=float(d.get("e", 0)),
            i=math.radians(float(d.get("i_deg", d.get("i_rad", 0)))),
            raan=math.radians(float(d.get("raan_deg", d.get("raan_rad", 0)))),
            argp=math.radians(float(d.get("argp_deg", d.get("argp_rad", 0)))),
            nu=math.radians(float(d.get("nu_deg", d.get("nu_rad", 0)))),
        )


@dataclass
class PropagationConfig:
    method: str = "kepler"
    dt: float = 3600.0
    step: float = 60.0
    rtol: float = 1e-9
    atol: float = 1e-12

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PropagationConfig":
        method = str(d.get("method", "kepler")).lower()
        if method not in VALID_METHODS:
            raise ValueError(f"Unknown propagation method '{method}'; "
                             f"valid: {VALID_METHODS}")
        return cls(
            method=method,
            dt=float(d.get("dt_s", 3600)),
            step=float(d.get("step_s", 60)),
            rtol=float(d.get("rtol", 1e-9)),
            atol=float(d.get("atol", 1e-12)),
        )


@dataclass
class GroundStationConfig:
    lat: float = 0.0
    lon: float = 0.0
    min_elevation: float = math.radians(5.0)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GroundStationConfig":
        return cls(
            lat=math.radians(float(d.get("lat_deg", 0))),
            lon=math.radians(float(d.get("lon_deg", 0))),
            min_elevation=math.radians(float(d.get("min_elevation_deg", 5.0))),
        )


@dataclass
class OutputConfig:
    states_csv: Optional[str] = None
    groundtrack_csv: Optional[str] = None
    passes_txt: Optional[str] = None
    verbose: bool = False

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OutputConfig":
        return cls(
            states_csv=d.get("states_csv"),
            groundtrack_csv=d.get("groundtrack_csv"),
            passes_txt=d.get("passes_txt"),
            verbose=bool(d.get("verbose", False)),
        )


@dataclass
class OrbitConfig:
    """Top-level configuration object."""

    body: Body = EARTH
    satellite: SatelliteConfig = field(default_factory=lambda: SatelliteConfig(
        a=7_000_000, e=0.0, i=0, raan=0, argp=0, nu=0))
    propagation: PropagationConfig = field(default_factory=PropagationConfig)
    ground_station: Optional[GroundStationConfig] = None
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OrbitConfig":
        body_name = str(d.get("body", "earth")).lower()
        if body_name not in BODIES:
            raise ValueError(f"Unknown body '{body_name}'; valid: {list(BODIES)}")
        return cls(
            body=BODIES[body_name],
            satellite=SatelliteConfig.from_dict(d.get("satellite", {})),
            propagation=PropagationConfig.from_dict(d.get("propagation", {})),
            ground_station=GroundStationConfig.from_dict(d["ground_station"])
            if "ground_station" in d else None,
            output=OutputConfig.from_dict(d.get("output", {})),
        )


def load_config(path: str) -> OrbitConfig:
    """Load a configuration file (YAML, JSON, or TOML).

    The format is detected from the file extension.
    """
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as f:
        text = f.read()

    if ext == ".json":
        data = json.loads(text)
    elif ext == ".toml":
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(text)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("YAML config requires the 'pyyaml' package.") from exc
        data = yaml.safe_load(text)
    else:
        # Try JSON as a fallback.
        data = json.loads(text)

    return OrbitConfig.from_dict(data)