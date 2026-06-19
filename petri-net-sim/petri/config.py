"""Configuration file support (JSON/YAML) for Petri net definitions.

Allows defining nets declaratively instead of programmatically.
Supports JSON and YAML formats with a simple, readable schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .net import PetriNet, Place, Transition


# Schema for config files:
# {
#   "name": "my-net",
#   "places": [
#     {"name": "p1", "initial": 1, "capacity": null},
#     {"name": "p2", "initial": 0}
#   ],
#   "transitions": [
#     {"name": "t1", "label": "do something", "rate": 2.5}
#   ],
#   "arcs": [
#     {"source": "p1", "target": "t1", "weight": 1},
#     {"source": "t1", "target": "p2", "weight": 1}
#   ]
# }


def load_config(path: str) -> PetriNet:
    """Load a Petri net from a JSON or YAML configuration file.

    The format is detected by file extension (.json, .yaml, .yml).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = p.suffix.lower()
    if suffix == ".json":
        data = json.loads(p.read_text())
    elif suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("PyYAML is required for YAML config files. Install with: pip install pyyaml") from exc
        data = yaml.safe_load(p.read_text())
    else:
        # Try JSON as fallback
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            raise ValueError(f"Unsupported config format: {suffix}. Use .json, .yaml, or .yml")

    return from_config_dict(data)


def from_config_dict(data: dict) -> PetriNet:
    """Build a PetriNet from a configuration dictionary."""
    if not isinstance(data, dict):
        raise ValueError("Config must be a dictionary")

    net = PetriNet(name=data.get("name", "config-net"))

    # Add places
    for pdef in data.get("places", []):
        if not isinstance(pdef, dict) or "name" not in pdef:
            raise ValueError(f"Invalid place definition: {pdef}")
        net.add_place(Place(
            name=pdef["name"],
            initial=pdef.get("initial", 0),
            capacity=pdef.get("capacity"),
        ))

    # Add transitions
    for tdef in data.get("transitions", []):
        if not isinstance(tdef, dict) or "name" not in tdef:
            raise ValueError(f"Invalid transition definition: {tdef}")
        net.add_transition(Transition(
            name=tdef["name"],
            label=tdef.get("label", ""),
        ))

    # Add arcs
    for adef in data.get("arcs", []):
        if not isinstance(adef, dict) or "source" not in adef or "target" not in adef:
            raise ValueError(f"Invalid arc definition: {adef}")
        net.add_arc(
            source=adef["source"],
            target=adef["target"],
            weight=adef.get("weight", 1),
        )

    return net


def to_config_dict(net: PetriNet) -> dict:
    """Serialize a PetriNet to a configuration dictionary."""
    return {
        "name": net.name,
        "places": [
            {"name": p.name, "initial": p.initial, "capacity": p.capacity}
            for p in net.places.values()
        ],
        "transitions": [
            {"name": t.name, "label": t.label}
            for t in net.transitions.values()
        ],
        "arcs": net.to_dict()["arcs"],
    }


def save_config(net: PetriNet, path: str, format: str = "json") -> None:
    """Save a PetriNet to a configuration file.

    format: "json" or "yaml"
    """
    data = to_config_dict(net)
    p = Path(path)

    if format == "json" or p.suffix == ".json":
        p.write_text(json.dumps(data, indent=2))
    elif format == "yaml" or p.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("PyYAML is required for YAML output. Install with: pip install pyyaml") from exc
        p.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    else:
        raise ValueError(f"Unknown format: {format}. Use 'json' or 'yaml'.")