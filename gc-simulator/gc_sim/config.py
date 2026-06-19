"""Configuration loading for the GC simulator.

Supports JSON, YAML and TOML configuration files describing heap size,
collector choice, allocator choice and scenario parameters.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class SimConfig:
    """Configuration for a :class:`~gc_sim.simulator.GCSimulator` run."""

    heap_size: int = 1024
    collector: str = "mark_sweep"
    allocator: str = "bump"
    allocator_policy: str = "first_fit"
    collector_kwargs: Dict[str, Any] = field(default_factory=dict)
    scenario: str = "linked_list"
    scenario_params: Dict[str, Any] = field(default_factory=dict)
    num_collections: int = 1
    output_format: str = "text"  # text, json, dot
    seed: Optional[int] = None

    def validate(self) -> None:
        if self.heap_size <= 0:
            raise ValueError("heap_size must be positive")
        if self.collector not in ("mark_sweep", "mark_compact", "copying",
                                  "ref_count", "generational"):
            raise ValueError(f"unknown collector: {self.collector}")
        if self.allocator not in ("bump", "free_list"):
            raise ValueError(f"unknown allocator: {self.allocator}")
        if self.allocator_policy not in ("first_fit", "best_fit",
                                          "worst_fit"):
            raise ValueError(f"unknown allocator_policy: {self.allocator_policy}")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SimConfig":
        return cls(
            heap_size=d.get("heap_size", 1024),
            collector=d.get("collector", "mark_sweep"),
            allocator=d.get("allocator", "bump"),
            allocator_policy=d.get("allocator_policy", "first_fit"),
            collector_kwargs=d.get("collector_kwargs", {}),
            scenario=d.get("scenario", "linked_list"),
            scenario_params=d.get("scenario_params", {}),
            num_collections=d.get("num_collections", 1),
            output_format=d.get("output_format", "text"),
            seed=d.get("seed"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heap_size": self.heap_size,
            "collector": self.collector,
            "allocator": self.allocator,
            "allocator_policy": self.allocator_policy,
            "collector_kwargs": self.collector_kwargs,
            "scenario": self.scenario,
            "scenario_params": self.scenario_params,
            "num_collections": self.num_collections,
            "output_format": self.output_format,
            "seed": self.seed,
        }


def load_config(path: str) -> SimConfig:
    """Load a :class:`SimConfig` from a JSON, YAML or TOML file.

    The format is determined by the file extension.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    text = p.read_text()
    ext = p.suffix.lower()
    if ext == ".json":
        data = json.loads(text)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise ImportError("PyYAML is required to load YAML configs") from e
        data = yaml.safe_load(text)
    elif ext == ".toml":
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        data = tomllib.loads(text)
    else:
        raise ValueError(f"unsupported config format: {ext}")
    cfg = SimConfig.from_dict(data)
    cfg.validate()
    return cfg


def save_config(cfg: SimConfig, path: str) -> None:
    """Save a :class:`SimConfig` to a JSON or YAML file."""
    p = Path(path)
    ext = p.suffix.lower()
    data = cfg.to_dict()
    if ext == ".json":
        p.write_text(json.dumps(data, indent=2))
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise ImportError("PyYAML is required to save YAML configs") from e
        p.write_text(yaml.dump(data, default_flow_style=False))
    elif ext == ".toml":
        # tomllib only reads; write a minimal TOML by hand
        lines = []
        for k, v in data.items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, (int, float, bool)):
                lines.append(f"{k} = {v}")
            elif v is None:
                lines.append(f"{k} = ")
            else:
                lines.append(f"{k} = {json.dumps(v)}")
        p.write_text("\n".join(lines) + "\n")
    else:
        raise ValueError(f"unsupported config format: {ext}")