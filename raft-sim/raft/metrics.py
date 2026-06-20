"""Metrics collection and export for the Raft simulator.

Provides a :class:`MetricsCollector` that can be registered as a cluster
observer and exports metrics as JSON or CSV.

Example::

    from raft.metrics import MetricsCollector
    from raft import Cluster, NetworkConfig

    collector = MetricsCollector()
    cluster = Cluster(size=5, seed=42, network_config=NetworkConfig(seed=42))
    cluster.add_observer(collector)
    cluster.run_until_leader(timeout=100)
    cluster.submit("set", "x", 1)
    cluster.run_for(20)

    collector.export_json("metrics.json")
    collector.export_csv("metrics.csv")
    print(collector.summary())
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from raft.cluster import Cluster, ClusterEvent


@dataclass
class MetricSnapshot:
    """A point-in-time snapshot of cluster metrics."""

    sim_time: float
    wall_time: float
    event_type: str
    event_data: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects cluster events and exports metrics.

    Register this as a cluster observer::

        collector = MetricsCollector()
        cluster.add_observer(collector)
    """

    def __init__(self) -> None:
        self._snapshots: list[MetricSnapshot] = []
        self._event_counts: dict[str, int] = {}
        self._leader_changes: int = 0
        self._elections: int = 0
        self._commands_committed: int = 0
        self._crashes: int = 0
        self._restarts: int = 0
        self._start_wall: float = time.time()

    def __call__(self, event: ClusterEvent, data: dict[str, Any]) -> None:
        """Observer callback — records each event."""
        event_name = event.value
        self._event_counts[event_name] = self._event_counts.get(event_name, 0) + 1
        self._snapshots.append(
            MetricSnapshot(
                sim_time=data.get("_sim_time", 0.0),
                wall_time=time.time() - self._start_wall,
                event_type=event_name,
                event_data={k: v for k, v in data.items() if k != "_sim_time"},
            )
        )
        if event == ClusterEvent.LEADER_ELECTED:
            self._leader_changes += 1
        elif event == ClusterEvent.ELECTION_STARTED:
            self._elections += 1
        elif event == ClusterEvent.LOG_COMMITTED:
            self._commands_committed += data.get("newly", 0)
        elif event == ClusterEvent.NODE_CRASHED:
            self._crashes += 1
        elif event == ClusterEvent.NODE_RESTARTED:
            self._restarts += 1

    def collect_from_cluster(self, cluster: Cluster) -> dict[str, Any]:
        """Collect a comprehensive metrics snapshot from a cluster."""
        nodes = cluster.nodes
        return {
            "sim_time": cluster.network.time,
            "cluster_size": cluster.size,
            "leader": cluster.get_leader(),
            "leader_changes": cluster.stats.leader_changes,
            "total_elections": cluster.stats.total_elections,
            "commands_committed": cluster.stats.commands_committed,
            "messages_delivered": cluster.stats.total_messages_delivered,
            "total_steps": cluster.stats.total_steps,
            "crashed_nodes": cluster.crashed_nodes(),
            "alive_nodes": cluster.alive_nodes(),
            "nodes": {
                str(nid): {
                    "role": nodes[nid].role.value,
                    "term": nodes[nid].state.current_term,
                    "commit_index": nodes[nid].state.commit_index,
                    "last_applied": nodes[nid].state.last_applied,
                    "log_length": len(nodes[nid].log_store.entries),
                    "has_snapshot": nodes[nid].log_store.has_snapshot,
                    "snapshots_taken": nodes[nid].stats.snapshots_taken,
                    "snapshots_installed": nodes[nid].stats.snapshots_installed,
                    "crashed": nodes[nid].is_crashed,
                }
                for nid in sorted(nodes)
            },
            "event_counts": dict(self._event_counts),
            "leader_changes_observed": self._leader_changes,
            "elections_observed": self._elections,
            "commands_committed_observed": self._commands_committed,
            "crashes_observed": self._crashes,
            "restarts_observed": self._restarts,
        }

    def summary(self) -> str:
        """Return a human-readable summary of collected metrics."""
        lines = ["Metrics Summary:"]
        lines.append(f"  Leader changes: {self._leader_changes}")
        lines.append(f"  Elections: {self._elections}")
        lines.append(f"  Commands committed: {self._commands_committed}")
        lines.append(f"  Node crashes: {self._crashes}")
        lines.append(f"  Node restarts: {self._restarts}")
        lines.append(f"  Total events: {len(self._snapshots)}")
        lines.append("  Event counts:")
        for event_name, count in sorted(self._event_counts.items()):
            lines.append(f"    {event_name}: {count}")
        return "\n".join(lines)

    def export_json(self, path: str | Path, cluster: Cluster | None = None) -> None:
        """Export metrics to a JSON file."""
        data: dict[str, Any] = {
            "events": [
                {
                    "sim_time": s.sim_time,
                    "wall_time": s.wall_time,
                    "event_type": s.event_type,
                    "event_data": s.event_data,
                }
                for s in self._snapshots
            ],
            "summary": {
                "leader_changes": self._leader_changes,
                "elections": self._elections,
                "commands_committed": self._commands_committed,
                "crashes": self._crashes,
                "restarts": self._restarts,
                "event_counts": dict(self._event_counts),
            },
        }
        if cluster is not None:
            data["cluster"] = self.collect_from_cluster(cluster)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, default=str))

    def export_csv(self, path: str | Path) -> None:
        """Export event-level metrics to a CSV file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sim_time", "wall_time", "event_type", "event_data"])
            for s in self._snapshots:
                writer.writerow([
                    s.sim_time,
                    f"{s.wall_time:.4f}",
                    s.event_type,
                    json.dumps(s.event_data, default=str),
                ])

    @property
    def snapshots(self) -> list[MetricSnapshot]:
        """All recorded event snapshots."""
        return list(self._snapshots)