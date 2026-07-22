"""
Configuration file support for network-flow-solver.

Loads solver and problem configuration from JSON or YAML files.

Example config (JSON)::

    {
      "algorithm": "dinic",
      "source": 0,
      "sink": 5,
      "network_file": "network.json",
      "output_file": "result.json",
      "logging": {"level": "INFO", "file": "run.log"},
      "benchmark": {"sizes": [10, 50, 100], "edge_prob": 0.3, "seed": 42}
    }

Example config (YAML)::

    algorithm: dinic
    source: 0
    sink: 5
    network_file: network.json
    logging:
      level: DEBUG
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SolverConfig:
    """Configuration for a solver run."""
    algorithm: str = "dinic"
    source: int = 0
    sink: int = -1
    network_file: str = ""
    output_file: str = ""
    show_flows: bool = False
    target_flow: float | None = None
    log_level: str = "WARNING"
    log_file: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def load_config(path: str) -> SolverConfig:
    """Load a configuration file (JSON or YAML).

    YAML support requires PyYAML to be installed.  JSON is always supported
    (stdlib only).

    Parameters
    ----------
    path : str
        Path to the config file (``.json`` or ``.yaml``/``.yml``).

    Returns
    -------
    SolverConfig
    """
    p = Path(path)
    text = p.read_text()

    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml
            data = yaml.safe_load(text)
        except ImportError:
            raise ImportError(
                "YAML config requires PyYAML. Install with: pip install pyyaml"
            )
    else:
        data = json.loads(text)

    return config_from_dict(data)


def config_from_dict(data: dict[str, Any]) -> SolverConfig:
    """Build a SolverConfig from a plain dict."""
    known_keys = {
        "algorithm", "source", "sink", "network_file", "output_file",
        "show_flows", "target_flow", "log_level", "log_file",
    }
    # Extract logging sub-dict if present
    if "logging" in data and isinstance(data["logging"], dict):
        log = data["logging"]
        if "level" in log:
            data.setdefault("log_level", log["level"])
        if "file" in log:
            data.setdefault("log_file", log["file"])

    extra = {k: v for k, v in data.items() if k not in known_keys and k != "logging"}
    return SolverConfig(
        algorithm=data.get("algorithm", "dinic"),
        source=data.get("source", 0),
        sink=data.get("sink", -1),
        network_file=data.get("network_file", ""),
        output_file=data.get("output_file", ""),
        show_flows=data.get("show_flows", False),
        target_flow=data.get("target_flow"),
        log_level=data.get("log_level", "WARNING"),
        log_file=data.get("log_file"),
        extra=extra,
    )


def save_config(config: SolverConfig, path: str) -> None:
    """Save a SolverConfig to a JSON file."""
    data = {
        "algorithm": config.algorithm,
        "source": config.source,
        "sink": config.sink,
        "network_file": config.network_file,
        "output_file": config.output_file,
        "show_flows": config.show_flows,
        "target_flow": config.target_flow,
        "log_level": config.log_level,
        "log_file": config.log_file,
    }
    Path(path).write_text(json.dumps(data, indent=2))