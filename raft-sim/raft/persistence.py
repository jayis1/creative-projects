"""Persistence and serialization for Raft node state.

In a real Raft implementation, persistent state (current_term, voted_for,
log) must survive crashes.  This module provides JSON-based serialization
for node state and snapshots, enabling save/restore of cluster state.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Any

from raft.cluster import ClusterStats
from raft.node import KVStateMachine, RaftNode, StateMachine
from raft.snapshot import Snapshot, SnapshotStore
from raft.types import LogEntry, NodeRole, NodeState


def serialize_log_entry(entry: LogEntry) -> dict[str, Any]:
    """Serialize a LogEntry to a JSON-compatible dict."""
    return {
        "term": entry.term,
        "command": entry.command,
        "index": entry.index,
    }


def deserialize_log_entry(data: dict[str, Any]) -> LogEntry:
    """Deserialize a dict back to a LogEntry."""
    return LogEntry(
        term=data["term"],
        command=data["command"],
        index=data.get("index", 0),
    )


def serialize_node_state(node: RaftNode) -> dict[str, Any]:
    """Serialize a node's persistent + volatile state to a dict."""
    state = node.state
    log_entries = [serialize_log_entry(e) for e in node.log_store.entries]

    result: dict[str, Any] = {
        "node_id": node.id,
        "role": node.role.value,
        "current_term": state.current_term,
        "voted_for": state.voted_for,
        "commit_index": state.commit_index,
        "last_applied": state.last_applied,
        "members": sorted(node.members),
        "peers": list(node.peers),
        "log_entries": log_entries,
        "next_index": dict(state.next_index),
        "match_index": dict(state.match_index),
    }

    # Include snapshot if present.
    if node.log_store.has_snapshot:
        snap = node.log_store.snapshot
        assert snap is not None
        result["snapshot"] = {
            "last_included_index": snap.last_included_index,
            "last_included_term": snap.last_included_term,
            "state": snap.state,
            "members": sorted(snap.members),
        }

    # Include state machine state if it's a KV store.
    if isinstance(node.sm, KVStateMachine):
        result["state_machine"] = node.sm._store

    return result


def deserialize_node_state(
    data: dict[str, Any],
    network: Any,
    state_machine: StateMachine | None = None,
) -> RaftNode:
    """Reconstruct a RaftNode from serialized data."""
    sm = state_machine or KVStateMachine()

    # Restore state machine if data includes it and sm is a KV store.
    if "state_machine" in data and isinstance(sm, KVStateMachine):
        sm.restore(data["state_machine"])

    node = RaftNode(
        node_id=data["node_id"],
        peers=data.get("peers", []),
        network=network,
        state_machine=sm,
    )

    node.state.current_term = data["current_term"]
    node.state.voted_for = data["voted_for"]
    node.state.commit_index = data["commit_index"]
    node.state.last_applied = data["last_applied"]
    node.members = set(data.get("members", [node.id] + node.peers))
    node.role = NodeRole(data["role"])

    # Restore log entries.
    for entry_data in data.get("log_entries", []):
        node.log_store.append_entries([deserialize_log_entry(entry_data)])

    # Restore snapshot if present.
    if "snapshot" in data:
        snap_data = data["snapshot"]
        node.log_store.take_snapshot(
            snap_data["last_included_index"],
            snap_data["last_included_term"],
            snap_data["state"],
            set(snap_data["members"]),
        )

    # Restore leader-only state.
    node.state.next_index = dict(data.get("next_index", {}))
    node.state.match_index = dict(data.get("match_index", {}))

    return node


def serialize_cluster(cluster: Any) -> dict[str, Any]:
    """Serialize an entire cluster to a dict."""
    return {
        "size": cluster.size,
        "time": cluster.network.time,
        "nodes": {
            str(nid): serialize_node_state(cluster.nodes[nid])
            for nid in sorted(cluster.nodes)
        },
        "stats": {
            "total_steps": cluster.stats.total_steps,
            "total_messages_delivered": cluster.stats.total_messages_delivered,
            "total_elections": cluster.stats.total_elections,
            "leader_changes": cluster.stats.leader_changes,
            "commands_committed": cluster.stats.commands_committed,
        },
    }


def save_cluster(cluster: Any, path: str | Path) -> None:
    """Save cluster state to a JSON file."""
    data = serialize_cluster(cluster)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def load_cluster(
    path: str | Path,
    network: Any,
    state_machine_factory: Any | None = None,
) -> Any:
    """Load cluster state from a JSON file.

    Returns a :class:`raft.cluster.Cluster` with restored node states.
    Note: the network must be freshly created; message queue is not
    persisted.
    """
    from raft.cluster import Cluster

    data = json.loads(Path(path).read_text())
    size = data["size"]

    # BUG FIX: Use the passed network instead of creating a new one.
    # Previously, a new Cluster was created with its own network, making
    # the `network` parameter misleading and causing the passed network
    # to be discarded.
    cluster = Cluster.__new__(Cluster)
    cluster.size = size
    cluster.network = network  # Use the passed network
    cluster._sm_factory = KVStateMachine
    cluster._rng = random.Random()
    cluster.nodes = {}
    cluster.stats = ClusterStats()
    cluster._event_log = []
    cluster._last_leader = None

    # Register all nodes with the network.
    for nid in range(size):
        network.register(nid)

    # Restore each node.
    for nid_str, node_data in data["nodes"].items():
        nid = int(nid_str)
        sm = state_machine_factory() if state_machine_factory else KVStateMachine()
        node = deserialize_node_state(node_data, network, sm)
        cluster.nodes[nid] = node

    # Restore stats.
    if "stats" in data:
        cluster.stats.total_steps = data["stats"].get("total_steps", 0)
        cluster.stats.total_messages_delivered = data["stats"].get(
            "total_messages_delivered", 0
        )
        cluster.stats.leader_changes = data["stats"].get("leader_changes", 0)

    return cluster