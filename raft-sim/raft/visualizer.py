"""ASCII visualization for Raft cluster state.

Renders the cluster as an ASCII diagram showing node roles, terms,
log progress, and network partitions.  Also supports rendering a
timeline of events.
"""

from __future__ import annotations

from typing import Any

from raft.cluster import Cluster
from raft.node import RaftNode
from raft.types import NodeRole


# Role symbols for compact display.
ROLE_SYMBOLS = {
    NodeRole.LEADER: "★",
    NodeRole.CANDIDATE: "?",
    NodeRole.FOLLOWER: "○",
}

ROLE_LABELS = {
    NodeRole.LEADER: "LDR",
    NodeRole.CANDIDATE: "CND",
    NodeRole.FOLLOWER: "FLW",
}


def render_cluster_ascii(cluster: Cluster, width: int = 80) -> str:
    """Render the cluster state as an ASCII diagram.

    Shows each node with its role, term, log/commit/applied progress,
    and a compact log visualization.  Partitions are shown as ✗ between
    nodes.
    """
    lines = []
    lines.append("=" * width)
    lines.append(
        f"  Raft Cluster  |  size={cluster.size}  "
        f"time={cluster.network.time:.1f}  "
        f"leader={cluster.get_leader()}  "
        f"changes={cluster.stats.leader_changes}"
    )
    lines.append("=" * width)

    # Partition matrix header.
    node_ids = sorted(cluster.nodes)
    leader = cluster.get_leader()

    for nid in node_ids:
        node = cluster.nodes[nid]
        sym = ROLE_SYMBOLS[node.role]
        label = ROLE_LABELS[node.role]
        term = node.state.current_term
        commit = node.state.commit_index
        applied = node.state.last_applied
        log_len = len(node.log_store.entries)
        snap_idx = node.log_store.last_included_index
        snap_str = f" snap={snap_idx}" if snap_idx > 0 else ""

        # Log visualization: show committed vs uncommitted entries.
        log_bar = _render_log_bar(node, max_entries=min(40, max(log_len, commit)))

        marker = " ← leader" if nid == leader else ""
        lines.append(
            f"  {sym} Node {nid} [{label}] T{term}  "
            f"commit={commit} applied={applied} "
            f"log={log_len}{snap_str}{marker}"
        )
        if log_bar:
            lines.append(f"    {log_bar}")

    # Partition summary.
    partitioned_pairs = []
    for i in node_ids:
        for j in node_ids:
            if i < j and cluster.network.is_partitioned(i, j):
                partitioned_pairs.append((i, j))
    if partitioned_pairs:
        lines.append("")
        lines.append("  Partitions: " + ", ".join(f"{a}✗{b}" for a, b in partitioned_pairs))
    else:
        lines.append("")
        lines.append("  Network: all connected")

    lines.append("=" * width)
    return "\n".join(lines)


def _render_log_bar(node: RaftNode, max_entries: int = 40) -> str:
    """Render a compact bar showing log entry terms.

    Each entry is shown as a digit (term mod 10) or '.' for empty.
    Committed entries are uppercase, uncommitted lowercase.
    """
    if max_entries == 0:
        return ""
    parts = []
    for idx in range(1, max_entries + 1):
        entry = node.log_store.get_entry(idx)
        if entry is None:
            if idx <= node.log_store.last_included_index:
                parts.append("S")  # snapshot
            else:
                parts.append(".")
        else:
            digit = str(entry.term % 10)
            if idx <= node.state.commit_index:
                parts.append(digit)
            else:
                parts.append(digit.lower())
    return "[" + "".join(parts) + "]"


def render_timeline(events: list[tuple[float, Any, dict]], max_events: int = 20) -> str:
    """Render a timeline of cluster events."""
    lines = ["  Event Timeline:"]
    lines.append("  " + "-" * 60)
    for t, event, data in events[-max_events:]:
        event_str = event.value if hasattr(event, "value") else str(event)
        data_str = ", ".join(f"{k}={v}" for k, v in sorted(data.items()))
        lines.append(f"  [{t:7.1f}] {event_str:20s} {data_str}")
    return "\n".join(lines)


def render_partition_matrix(cluster: Cluster) -> str:
    """Render a node-to-node connectivity matrix."""
    node_ids = sorted(cluster.nodes)
    lines = ["  Connectivity Matrix:"]
    # Header row.
    header = "    " + " ".join(f"{n:2d}" for n in node_ids)
    lines.append(header)
    for i in node_ids:
        row = f"  {i:2d} "
        for j in node_ids:
            if i == j:
                row += " - "
            elif cluster.network.is_partitioned(i, j):
                row += " ✗ "
            else:
                row += " · "
        lines.append(row)
    return "\n".join(lines)


def render_log_diff(cluster: Cluster) -> str:
    """Render a side-by-side comparison of log entries across nodes."""
    node_ids = sorted(cluster.nodes)
    max_idx = max(n.last_log_index for n in cluster.nodes.values())
    if max_idx == 0:
        return "  (empty logs)"

    lines = ["  Log Comparison (term@index):"]
    header = "  idx  " + "  ".join(f"N{n}" for n in node_ids)
    lines.append(header)
    lines.append("  " + "-" * (6 + 5 * len(node_ids)))

    for idx in range(1, min(max_idx + 1, 30)):
        row = f"  {idx:3d}  "
        for nid in node_ids:
            node = cluster.nodes[nid]
            entry = node.log_store.get_entry(idx)
            if entry is not None:
                cell = f"{entry.term}@{idx}"
            elif idx <= node.log_store.last_included_index:
                cell = "snap"
            else:
                cell = "  - "
            row += f"{cell:>5s} "
        lines.append(row)
    return "\n".join(lines)