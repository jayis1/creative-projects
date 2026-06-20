"""Configuration management for the Raft simulator.

Supports loading cluster and network configuration from YAML or JSON files,
making it easy to reproduce experiments and share setups.

Example YAML config::

    # cluster.yaml
    cluster:
      size: 5
      seed: 42
      election_timeout_range: [4.0, 8.0]
      heartbeat_interval: 1.0
      snapshot_threshold: 50
    network:
      base_latency: 1.0
      jitter: 0.5
      drop_rate: 0.0
      reorder: false
      seed: 42

Example JSON config::

    {
      "cluster": {"size": 7, "seed": 100},
      "network": {"base_latency": 0.5, "jitter": 0.3}
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from raft.network import NetworkConfig


@dataclass
class ClusterConfig:
    """High-level configuration for a Raft cluster.

    Attributes mirror :class:`raft.cluster.Cluster` constructor params.
    """

    size: int = 5
    seed: int | None = None
    election_timeout_range: tuple[float, float] = (5.0, 10.0)
    heartbeat_interval: float = 1.0
    snapshot_threshold: int = 50
    network: NetworkConfig = field(default_factory=NetworkConfig)
    # Feature flags
    prevote_enabled: bool = False
    crash_recovery_enabled: bool = False
    linearizable_reads: bool = False

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError("cluster size must be ≥ 1")
        lo, hi = self.election_timeout_range
        if lo <= 0 or hi <= 0:
            raise ValueError("election timeout values must be positive")
        if lo > hi:
            raise ValueError(
                f"election_timeout_range lower bound {lo} > upper bound {hi}"
            )
        if self.heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval must be positive")
        if self.snapshot_threshold < 1:
            raise ValueError("snapshot_threshold must be ≥ 1")


def _coerce_network_config(data: dict[str, Any]) -> NetworkConfig:
    """Build a NetworkConfig from a raw dict, ignoring unknown keys."""
    known = {
        "base_latency",
        "jitter",
        "drop_rate",
        "reorder",
        "seed",
    }
    filtered = {k: v for k, v in data.items() if k in known}
    return NetworkConfig(**filtered)


def load_config(path: str | Path) -> ClusterConfig:
    """Load a :class:`ClusterConfig` from a YAML or JSON file.

    The file extension determines the parser (``.yaml``/``.yml`` or ``.json``).

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file content is invalid.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    text = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        raw = yaml.safe_load(text)
    elif p.suffix == ".json":
        raw = json.loads(text)
    else:
        # Try YAML first (superset of JSON), fall back to JSON.
        try:
            raw = yaml.safe_load(text)
        except Exception:
            raw = json.loads(text)

    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping, got {type(raw).__name__}")

    cluster_data = dict(raw.get("cluster", {}))
    network_data = dict(raw.get("network", {}))

    # Build NetworkConfig.
    net_cfg = _coerce_network_config(network_data)

    # Extract cluster-level keys.
    known_cluster = {
        "size",
        "seed",
        "election_timeout_range",
        "heartbeat_interval",
        "snapshot_threshold",
        "prevote_enabled",
        "crash_recovery_enabled",
        "linearizable_reads",
    }
    cluster_kwargs: dict[str, Any] = {
        k: v for k, v in cluster_data.items() if k in known_cluster
    }
    # Coerce election_timeout_range from list if needed.
    if "election_timeout_range" in cluster_kwargs:
        etr = cluster_kwargs["election_timeout_range"]
        if isinstance(etr, (list, tuple)) and len(etr) == 2:
            cluster_kwargs["election_timeout_range"] = (float(etr[0]), float(etr[1]))
        else:
            raise ValueError("election_timeout_range must be [lo, hi]")

    return ClusterConfig(network=net_cfg, **cluster_kwargs)


def save_config(config: ClusterConfig, path: str | Path) -> None:
    """Serialize a :class:`ClusterConfig` to a YAML or JSON file."""
    p = Path(path)
    data: dict[str, Any] = {
        "cluster": {
            "size": config.size,
            "seed": config.seed,
            "election_timeout_range": list(config.election_timeout_range),
            "heartbeat_interval": config.heartbeat_interval,
            "snapshot_threshold": config.snapshot_threshold,
            "prevote_enabled": config.prevote_enabled,
            "crash_recovery_enabled": config.crash_recovery_enabled,
            "linearizable_reads": config.linearizable_reads,
        },
        "network": {
            "base_latency": config.network.base_latency,
            "jitter": config.network.jitter,
            "drop_rate": config.network.drop_rate,
            "reorder": config.network.reorder,
            "seed": config.network.seed,
        },
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix in (".yaml", ".yml"):
        p.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    else:
        p.write_text(json.dumps(data, indent=2))