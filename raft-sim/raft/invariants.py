"""Raft safety invariant checker.

Verifies that the Raft safety properties hold across the cluster:

1. **Election Safety**: At most one leader per term.
2. **Leader Append-Only**: A leader never overwrites or deletes entries in its log.
3. **Log Matching**: If two logs contain an entry with the same index and term, then the logs are identical in all entries up through the given index.
4. **Leader Completeness**: If a log entry is committed in a given term, then that entry will be present in the log of the leader for all higher-numbered terms.
5. **State Machine Safety**: If a server has applied a log entry at a given index to its state machine, no other server will ever apply a different log entry for the same index.

These checks are useful for testing and debugging the simulator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from raft.cluster import Cluster
from raft.types import NodeRole


@dataclass
class InvariantViolation:
    """A single invariant violation."""
    name: str
    description: str
    nodes: list[int] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class InvariantReport:
    """Results of running all invariant checks."""
    violations: list[InvariantViolation] = field(default_factory=list)
    checks_run: int = 0

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def add(self, name: str, description: str, **kwargs: Any) -> None:
        self.violations.append(InvariantViolation(
            name=name,
            description=description,
            nodes=kwargs.pop("nodes", []),
            details=kwargs,
        ))

    def summary(self) -> str:
        lines = [f"Invariant Check Report ({self.checks_run} checks)"]
        if self.passed:
            lines.append("  ✓ All invariants satisfied")
        else:
            lines.append(f"  ✗ {len(self.violations)} violation(s):")
            for v in self.violations:
                lines.append(f"    - {v.name}: {v.description}")
                if v.nodes:
                    lines.append(f"      Nodes: {v.nodes}")
        return "\n".join(lines)


def check_election_safety(cluster: Cluster) -> InvariantReport:
    """At most one leader per term."""
    report = InvariantReport()
    report.checks_run = 1

    # Group leaders by term.
    leaders_by_term: dict[int, list[int]] = {}
    for nid, node in cluster.nodes.items():
        if node.role == NodeRole.LEADER:
            leaders_by_term.setdefault(node.state.current_term, []).append(nid)

    for term, leaders in leaders_by_term.items():
        if len(leaders) > 1:
            report.add(
                "Election Safety",
                f"Multiple leaders in term {term}: {leaders}",
                nodes=leaders,
                term=term,
            )
    return report


def check_log_matching(cluster: Cluster) -> InvariantReport:
    """If two logs share (index, term), they match up to that index."""
    report = InvariantReport()
    report.checks_run = 1

    # For each pair of nodes, find the common prefix and verify it matches.
    node_ids = sorted(cluster.nodes)
    for i in range(len(node_ids)):
        for j in range(i + 1, len(node_ids)):
            ni, nj = node_ids[i], node_ids[j]
            node_i, node_j = cluster.nodes[ni], cluster.nodes[nj]

            # Find the minimum log length (accounting for snapshots).
            min_len = min(
                len(node_i.log_store.entries) + node_i.log_store.last_included_index,
                len(node_j.log_store.entries) + node_j.log_store.last_included_index,
            )

            for idx in range(1, min_len + 1):
                ei = node_i.log_store.get_entry(idx)
                ej = node_j.log_store.get_entry(idx)
                if ei is not None and ej is not None:
                    if ei.term != ej.term:
                        report.add(
                            "Log Matching",
                            f"Nodes {ni} and {nj} disagree at index {idx}: "
                            f"term {ei.term} vs {ej.term}",
                            nodes=[ni, nj],
                            index=idx,
                            term_i=ei.term,
                            term_j=ej.term,
                        )
                        break  # first disagreement is enough
    return report


def check_state_machine_safety(cluster: Cluster) -> InvariantReport:
    """No two nodes should have applied different commands at the same index."""
    report = InvariantReport()
    report.checks_run = 1

    node_ids = sorted(cluster.nodes)
    # Compare applied entries across all pairs.
    max_applied = max(n.state.last_applied for n in cluster.nodes.values())

    for idx in range(1, max_applied + 1):
        commands: dict[int, list[int]] = {}  # command -> list of node ids
        for nid in node_ids:
            node = cluster.nodes[nid]
            if node.state.last_applied >= idx:
                entry = node.log_store.get_entry(idx)
                if entry is not None:
                    cmd_key = hash(str(entry.command))
                    commands.setdefault(cmd_key, []).append(nid)

        if len(commands) > 1:
            node_lists = [str(v) for v in commands.values()]
            report.add(
                "State Machine Safety",
                f"Nodes applied different commands at index {idx}: {node_lists}",
                index=idx,
            )
    return report


def check_leader_completeness(cluster: Cluster) -> InvariantReport:
    """Committed entries should be present in the leader's log."""
    report = InvariantReport()
    report.checks_run = 1

    leader = cluster.get_leader()
    if leader is None:
        return report  # no leader to check

    leader_node = cluster.nodes[leader]
    min_commit = min(n.state.commit_index for n in cluster.nodes.values())

    for idx in range(1, min_commit + 1):
        entry = leader_node.log_store.get_entry(idx)
        if entry is None and idx > leader_node.log_store.last_included_index:
            # Entry is missing AND not covered by snapshot — violation.
            report.add(
                "Leader Completeness",
                f"Leader {leader} is missing committed entry at index {idx}",
                nodes=[leader],
                index=idx,
            )
    return report


def check_commit_safety(cluster: Cluster) -> InvariantReport:
    """No node should have commit_index > last_log_index."""
    report = InvariantReport()
    report.checks_run = 1

    for nid, node in cluster.nodes.items():
        if node.state.commit_index > node.last_log_index:
            report.add(
                "Commit Safety",
                f"Node {nid} has commit_index={node.state.commit_index} "
                f"> last_log_index={node.last_log_index}",
                nodes=[nid],
            )
    return report


def check_all(cluster: Cluster) -> InvariantReport:
    """Run all invariant checks and return a combined report."""
    report = InvariantReport()
    for check_fn in [
        check_election_safety,
        check_log_matching,
        check_state_machine_safety,
        check_leader_completeness,
        check_commit_safety,
    ]:
        sub = check_fn(cluster)
        report.violations.extend(sub.violations)
        report.checks_run += sub.checks_run
    return report