"""Cluster driver — orchestrates a set of Raft nodes over a network.

The :class:`Cluster` creates N nodes, registers them with a
:class:`raft.network.Network`, and drives the simulation by ticking
nodes and draining network messages.  It also provides high-level
operations like partitioning, healing, and submitting commands.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from raft.network import Network, NetworkConfig
from raft.node import KVStateMachine, RaftNode, StateMachine
from raft.types import NodeRole


class ClusterEvent(enum.Enum):
    """Significant cluster events that observers can be notified about."""

    LEADER_ELECTED = "leader_elected"
    ELECTION_STARTED = "election_started"
    LOG_COMMITTED = "log_committed"
    SNAPSHOT_TAKEN = "snapshot_taken"
    MEMBERSHIP_CHANGE = "membership_change"


@dataclass
class ClusterStats:
    """Aggregate cluster statistics."""

    total_steps: int = 0
    total_messages_delivered: int = 0
    total_elections: int = 0
    leader_changes: int = 0
    commands_committed: int = 0


class Cluster:
    """A Raft cluster of N nodes.

    Example::

        cluster = Cluster(size=5)
        cluster.run_until_leader(timeout=50)
        leader = cluster.get_leader()
        cluster.submit("set", "x", 42)
        cluster.run_for(duration=20)
        assert cluster.all_agree("x") == 42
    """

    def __init__(
        self,
        size: int = 5,
        network_config: NetworkConfig | None = None,
        state_machine_factory: Callable[[], StateMachine] | None = None,
        election_timeout_range: tuple[float, float] = (5.0, 10.0),
        heartbeat_interval: float = 1.0,
        snapshot_threshold: int = 50,
        seed: int | None = None,
    ) -> None:
        if size < 1:
            raise ValueError("cluster size must be ≥ 1")
        self.size = size
        self.network = Network(network_config or NetworkConfig(seed=seed))
        self._sm_factory = state_machine_factory or KVStateMachine
        self._rng = random.Random(seed)
        self.nodes: dict[int, RaftNode] = {}
        self.stats = ClusterStats()
        self._event_log: list[tuple[float, ClusterEvent, dict]] = []
        self._last_leader: int | None = None

        # Create nodes.
        all_ids = list(range(size))
        for nid in all_ids:
            peers = [x for x in all_ids if x != nid]
            node = RaftNode(
                node_id=nid,
                peers=peers,
                network=self.network,
                state_machine=self._sm_factory(),
                election_timeout_range=election_timeout_range,
                heartbeat_interval=heartbeat_interval,
                snapshot_threshold=snapshot_threshold,
                rng=random.Random(seed + nid + 1 if seed is not None else None),
            )
            self.nodes[nid] = node
            self.network.register(nid)

    # ------------------------------------------------------------------
    # Simulation control
    # ------------------------------------------------------------------

    def step(self) -> int:
        """Advance the simulation by one step.

        Each step:
        1. Deliver pending messages (drain network).
        2. Let each node process its inbox.
        3. Tick each node (timers).
        """
        self.stats.total_steps += 1
        delivered = self.network.drain()
        self.stats.total_messages_delivered += delivered

        # Deliver messages to nodes.
        for nid, node in self.nodes.items():
            msgs = self.network.inbox(nid)
            for src, payload, _recv in msgs:
                node.handle_message(src, payload)

        # Tick all nodes.
        for node in self.nodes.values():
            node.tick()

        # Track leader changes.
        leader = self.get_leader()
        if leader is not None and leader != self._last_leader:
            self.stats.leader_changes += 1
            self._log_event(
                ClusterEvent.LEADER_ELECTED,
                {"leader": leader, "term": self.nodes[leader].state.current_term},
            )
            self._last_leader = leader

        return delivered

    def run_for(self, duration: float, step_size: float = 0.5) -> int:
        """Run the simulation for *duration* time units."""
        end_time = self.network.time + duration
        steps = 0
        while self.network.time < end_time:
            self.network.advance(step_size)
            self.step()
            steps += 1
        return steps

    def run_until_leader(self, timeout: float = 100.0, step_size: float = 0.5) -> int | None:
        """Run until a leader is elected or *timeout* is reached.

        Returns the leader's id or ``None`` if no leader was elected.
        """
        end_time = self.network.time + timeout
        while self.network.time < end_time:
            self.network.advance(step_size)
            self.step()
            leader = self.get_leader()
            if leader is not None:
                return leader
        return None

    def run_until_committed(
        self, command_index: int, timeout: float = 100.0, step_size: float = 0.5
    ) -> bool:
        """Run until *command_index* is committed on a quorum or timeout."""
        end_time = self.network.time + timeout
        while self.network.time < end_time:
            self.network.advance(step_size)
            self.step()
            committed = sum(
                1 for n in self.nodes.values() if n.state.commit_index >= command_index
            )
            if committed > len(self.nodes) // 2:
                return True
        return False

    def run_until_all_applied(
        self, index: int, timeout: float = 100.0, step_size: float = 0.5
    ) -> bool:
        """Run until *index* is applied on all nodes or timeout."""
        end_time = self.network.time + timeout
        while self.network.time < end_time:
            self.network.advance(step_size)
            self.step()
            if all(n.state.last_applied >= index for n in self.nodes.values()):
                return True
        return False

    # ------------------------------------------------------------------
    # Node inspection
    # ------------------------------------------------------------------

    def get_leader(self) -> int | None:
        """Return the current leader's id, or ``None`` if there is no leader."""
        leaders = [nid for nid, n in self.nodes.items() if n.is_leader]
        if len(leaders) == 1:
            return leaders[0]
        if len(leaders) > 1:
            # Multiple leaders in different terms — return the one with
            # the highest term.
            return max(leaders, key=lambda l: self.nodes[l].state.current_term)
        return None

    def get_followers(self) -> list[int]:
        return [nid for nid, n in self.nodes.items() if n.role == NodeRole.FOLLOWER]

    def get_candidates(self) -> list[int]:
        return [nid for nid, n in self.nodes.items() if n.role == NodeRole.CANDIDATE]

    def get_node(self, node_id: int) -> RaftNode:
        return self.nodes[node_id]

    # ------------------------------------------------------------------
    # Client commands
    # ------------------------------------------------------------------

    def submit(self, *command: Any) -> bool:
        """Submit a command to the current leader.

        Returns ``True`` if accepted, ``False`` if no leader.
        """
        leader = self.get_leader()
        if leader is None:
            return False
        return self.nodes[leader].submit_command(list(command))

    def submit_to(self, node_id: int, *command: Any) -> bool:
        """Submit a command to a specific node (even if not leader)."""
        return self.nodes[node_id].submit_command(list(command))

    def submit_batch(self, commands: list[list[Any]]) -> int:
        """Submit multiple commands to the leader in one go.

        Returns the number of commands successfully accepted.
        """
        leader = self.get_leader()
        if leader is None:
            return 0
        node = self.nodes[leader]
        count = 0
        for cmd in commands:
            if node.submit_command(cmd):
                count += 1
        # Trigger one round of replication.
        if count > 0:
            node._send_heartbeats()
        return count

    def submit_and_wait(
        self, *command: Any, timeout: float = 50.0
    ) -> bool:
        """Submit a command and run until it's committed on a quorum.

        Returns ``True`` if committed within *timeout*, ``False`` otherwise.
        """
        leader = self.get_leader()
        if leader is None:
            return False
        node = self.nodes[leader]
        target_index = node.last_log_index + 1
        if not node.submit_command(list(command)):
            return False
        return self.run_until_committed(target_index, timeout=timeout)

    # ------------------------------------------------------------------
    # Network failure injection
    # ------------------------------------------------------------------

    def partition_node(self, node_id: int) -> None:
        """Isolate *node_id* from all other nodes."""
        for other in self.nodes:
            if other != node_id:
                self.network.partition(node_id, other)

    def heal_node(self, node_id: int) -> None:
        """Heal all partitions involving *node_id*."""
        for other in self.nodes:
            if other != node_id:
                self.network.heal_partition(node_id, other)

    def partition_groups(self, group_a: list[int], group_b: list[int]) -> None:
        self.network.partition_groups(set(group_a), set(group_b))

    def heal_all(self) -> None:
        self.network.heal_all()

    # ------------------------------------------------------------------
    # Consistency checking
    # ------------------------------------------------------------------

    def all_agree(self, key: Any) -> Any | None:
        """Check that all applied state machines agree on *key*.

        Returns the common value if they agree, ``None`` if they disagree
        or no node has applied anything.
        """
        values = set()
        for node in self.nodes.values():
            if isinstance(node.sm, KVStateMachine):
                values.add(node.sm._store.get(key))
            else:
                # Generic state machine — can't introspect.
                return None
        if len(values) == 1:
            return values.pop()
        return None

    def log_consistent(self) -> bool:
        """Check that all committed entries are identical across nodes.

        Nodes with snapshots will have compacted away early entries; we
        only compare entries that are present on *all* nodes (i.e. entries
        above the maximum snapshot boundary).  The state-machine values
        should be consistent via :meth:`all_agree`.
        """
        # Find the highest snapshot boundary — entries below this may be
        # compacted on some nodes.
        max_snap = max(n.log_store.last_included_index for n in self.nodes.values())
        # Only compare entries above max_snap.
        min_commit = min(n.state.commit_index for n in self.nodes.values())
        if min_commit <= max_snap:
            return True  # nothing to compare above all snapshots
        ref = None
        for node in self.nodes.values():
            entries = []
            for idx in range(max_snap + 1, min_commit + 1):
                e = node.log_store.get_entry(idx)
                if e is not None:
                    entries.append((e.term, e.command))
            if ref is None:
                ref = entries
            elif entries != ref:
                return False
        return True

    def has_leader(self) -> bool:
        return self.get_leader() is not None

    def quorum_healthy(self) -> bool:
        """True if a majority of nodes can communicate with each other."""
        # Simplified: check that no partition splits the majority.
        # We consider the largest connected component.
        # For now, just check that a leader exists.
        return self.has_leader()

    # ------------------------------------------------------------------
    # Status / reporting
    # ------------------------------------------------------------------

    def status(self) -> list[dict[str, Any]]:
        """Return status dicts for all nodes, sorted by id."""
        return [self.nodes[nid].status() for nid in sorted(self.nodes)]

    def event_log(self) -> list[tuple[float, ClusterEvent, dict]]:
        return list(self._event_log)

    def _log_event(self, event: ClusterEvent, data: dict) -> None:
        self._event_log.append((self.network.time, event, data))

    def summary(self) -> str:
        """Human-readable cluster summary."""
        lines = [f"Cluster(size={self.size}, time={self.network.time:.1f})"]
        leader = self.get_leader()
        lines.append(f"  Leader: {leader}")
        for nid in sorted(self.nodes):
            n = self.nodes[nid]
            lines.append(
                f"  Node {nid}: {n.role.value:10s} term={n.state.current_term} "
                f"log=[..{n.last_log_index}] commit={n.state.commit_index} "
                f"applied={n.state.last_applied}"
            )
        lines.append(f"  Messages delivered: {self.stats.total_messages_delivered}")
        lines.append(f"  Leader changes: {self.stats.leader_changes}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire cluster (network, nodes, stats)."""
        self.network.reset()
        for nid in self.nodes:
            self.network.register(nid)
        self.stats = ClusterStats()
        self._event_log.clear()
        self._last_leader = None