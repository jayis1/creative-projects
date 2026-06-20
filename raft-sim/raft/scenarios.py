"""Pre-defined network failure scenarios for testing Raft resilience.

Each scenario is a generator that takes a :class:`raft.cluster.Cluster`
and yields ``(duration, action)`` tuples, where *action* is a callable
that modifies the cluster's network.  This lets you replay complex
failure patterns deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generator

from raft.cluster import Cluster


@dataclass
class ScenarioStep:
    """A single step in a failure scenario.

    Attributes:
        duration: How long to run the cluster after applying the action.
        action: A callable that modifies the cluster's network state,
            or ``None`` for a no-op (just run).
        label: Human-readable description for logging.
    """

    duration: float
    action: Callable[[Cluster], None] | None = None
    label: str = ""


def leader_partition_scenario(
    heal: bool = True,
    post_duration: float = 30.0,
) -> list[ScenarioStep]:
    """Isolate the leader, then optionally heal.

    Classic Raft test: the leader is partitioned from all followers.
    A new leader should be elected by the majority.  After healing,
    the old leader should step down and catch up.
    """
    steps: list[ScenarioStep] = []

    def isolate_leader(cluster: Cluster) -> None:
        leader = cluster.get_leader()
        if leader is not None:
            cluster.partition_node(leader)

    steps.append(ScenarioStep(
        duration=30.0, action=isolate_leader, label="Isolate leader"
    ))

    if heal:
        steps.append(ScenarioStep(
            duration=post_duration, action=lambda c: c.heal_all(), label="Heal all"
        ))

    return steps


def split_brain_scenario() -> list[ScenarioStep]:
    """Split the cluster into two equal groups (potential split-brain).

    With an even-sized cluster, this creates two groups of equal size.
    Neither can achieve a majority, so no leader should be elected in
    either group.  This tests that Raft prevents split-brain.
    """
    return [
        ScenarioStep(
            duration=20.0,
            action=lambda c: c.partition_groups(
                list(range(c.size // 2)), list(range(c.size // 2, c.size))
            ),
            label="Split into equal groups",
        ),
        ScenarioStep(
            duration=30.0,
            action=lambda c: c.heal_all(),
            label="Heal all",
        ),
    ]


def rolling_partition_scenario() -> list[ScenarioStep]:
    """Sequentially isolate each node, then heal.

    Simulates rolling node failures/restarts.
    """
    steps: list[ScenarioStep] = []
    for nid in range(10):  # arbitrary upper bound; cluster may be smaller
        steps.append(ScenarioStep(
            duration=15.0,
            action=lambda c, n=nid: c.partition_node(n) if n < c.size else None,
            label=f"Isolate node {nid}",
        ))
        steps.append(ScenarioStep(
            duration=10.0,
            action=lambda c, n=nid: c.heal_node(n) if n < c.size else None,
            label=f"Heal node {nid}",
        ))
    return steps


def flaky_network_scenario(drop_rate: float = 0.3) -> list[ScenarioStep]:
    """Simulate a flaky network with high packet loss.

    This doesn't partition nodes but makes message delivery unreliable.
    Tests that Raft can still make progress with unreliable networking.
    """
    def set_drop_rate(cluster: Cluster, rate: float) -> None:
        cluster.network.config.drop_rate = rate

    return [
        ScenarioStep(
            duration=40.0,
            action=lambda c: set_drop_rate(c, drop_rate),
            label=f"Set drop rate to {drop_rate}",
        ),
        ScenarioStep(
            duration=20.0,
            action=lambda c: set_drop_rate(c, 0.0),
            label="Restore reliable network",
        ),
    ]


def cascading_failure_scenario() -> list[ScenarioStep]:
    """Cascading failure: isolate nodes one by one until quorum is lost."""
    steps: list[ScenarioStep] = []
    for nid in range(10):
        steps.append(ScenarioStep(
            duration=10.0,
            action=lambda c, n=nid: c.partition_node(n) if n < c.size else None,
            label=f"Isolate node {nid}",
        ))
    steps.append(ScenarioStep(
        duration=30.0,
        action=lambda c: c.heal_all(),
        label="Heal all",
    ))
    return steps


def run_scenario(
    cluster: Cluster,
    steps: list[ScenarioStep],
    verbose: bool = True,
) -> dict[str, Any]:
    """Execute a failure scenario on *cluster*.

    Returns a results dict with final leader, consistency status, and
    per-step summaries.
    """
    results: dict[str, Any] = {
        "steps": [],
        "final_leader": None,
        "log_consistent": False,
        "leader_changes": 0,
    }

    for i, step in enumerate(steps):
        if verbose:
            print(f"  Step {i + 1}/{len(steps)}: {step.label}")

        if step.action is not None:
            step.action(cluster)

        cluster.run_for(step.duration)

        leader = cluster.get_leader()
        step_result = {
            "label": step.label,
            "duration": step.duration,
            "leader_after": leader,
            "term": cluster.nodes[leader].state.current_term if leader is not None else 0,
        }
        results["steps"].append(step_result)

        if verbose:
            print(f"    Leader: {leader}, Term: {step_result['term']}")

    results["final_leader"] = cluster.get_leader()
    results["log_consistent"] = cluster.log_consistent()
    results["leader_changes"] = cluster.stats.leader_changes

    return results