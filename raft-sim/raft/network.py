"""Network model for the Raft simulator.

The :class:`Network` is a discrete-event message bus.  Messages are
queued and delivered by :meth:`Network.drain` with configurable latency,
packet loss, partitioning, and reordering.  This makes it possible to
test Raft under realistic failure scenarios.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable

from raft.types import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    InstallSnapshotRequest,
    InstallSnapshotResponse,
    RequestVoteRequest,
    RequestVoteResponse,
)


# A message is a tuple of (src, dst, payload, send_time, deliver_at).
Message = tuple[int, int, Any, float, float]


@dataclass
class NetworkConfig:
    """Configuration for the simulated network."""

    base_latency: float = 1.0
    jitter: float = 0.5
    drop_rate: float = 0.0  # probability of dropping a message
    reorder: bool = False  # allow reordering (drain may shuffle)
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.base_latency < 0:
            raise ValueError("base_latency must be non-negative")
        if self.jitter < 0:
            raise ValueError("jitter must be non-negative")
        if not 0.0 <= self.drop_rate <= 1.0:
            raise ValueError("drop_rate must be in [0, 1]")


class Network:
    """A simulated asynchronous network connecting Raft nodes.

    Nodes communicate via :meth:`send` which enqueues a message; messages
    are actually delivered to recipient inboxes when :meth:`drain` is
    called (advancing the simulation clock).
    """

    def __init__(self, config: NetworkConfig | None = None) -> None:
        self.config = config or NetworkConfig()
        self._rng = random.Random(self.config.seed)
        self._queue: list[Message] = []
        self._time: float = 0.0
        # Set of (src, dst) pairs that are partitioned (cannot communicate).
        self._partitioned: set[tuple[int, int]] = set()
        # Inboxes: node_id -> list of (src, payload, recv_time)
        self._inboxes: dict[int, list[tuple[int, Any, float]]] = {}
        # Statistics
        self.sent_count: int = 0
        self.dropped_count: int = 0
        self.delivered_count: int = 0

    @property
    def time(self) -> float:
        return self._time

    # ------------------------------------------------------------------
    # Node registration
    # ------------------------------------------------------------------

    def register(self, node_id: int) -> None:
        self._inboxes.setdefault(node_id, [])

    # ------------------------------------------------------------------
    # Partition control
    # ------------------------------------------------------------------

    def partition(self, a: int, b: int) -> None:
        """Partition nodes *a* and *b* (bidirectional)."""
        self._partitioned.add((a, b))
        self._partitioned.add((b, a))

    def heal_partition(self, a: int, b: int) -> None:
        """Heal the partition between *a* and *b*."""
        self._partitioned.discard((a, b))
        self._partitioned.discard((b, a))

    def partition_groups(self, group_a: set[int], group_b: set[int]) -> None:
        """Partition two groups of nodes from each other."""
        for a in group_a:
            for b in group_b:
                self.partition(a, b)

    def heal_all(self) -> None:
        """Heal all partitions."""
        self._partitioned.clear()

    def is_partitioned(self, a: int, b: int) -> bool:
        return (a, b) in self._partitioned

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def send(self, src: int, dst: int, payload: Any) -> None:
        """Enqueue a message from *src* to *dst*."""
        if self.is_partitioned(src, dst):
            self.dropped_count += 1
            return
        self.sent_count += 1
        if self._rng.random() < self.config.drop_rate:
            self.dropped_count += 1
            return
        latency = self.config.base_latency + self._rng.uniform(
            0, self.config.jitter
        )
        deliver_at = self._time + max(0.0, latency)
        self._queue.append((src, dst, payload, self._time, deliver_at))

    def broadcast(
        self, src: int, peers: list[int], payload_factory: Callable[[int], Any]
    ) -> None:
        """Send (potentially different) messages to all *peers*.

        *payload_factory* is called with each peer id to produce the
        per-recipient payload.
        """
        for peer in peers:
            self.send(src, peer, payload_factory(peer))

    # ------------------------------------------------------------------
    # Draining (delivery)
    # ------------------------------------------------------------------

    def drain(self, max_messages: int = 10000) -> int:
        """Deliver all messages whose deliver_at ≤ current time.

        Advances the simulation clock to the earliest undelivered message
        time if needed.  Returns the number of messages delivered.
        """
        delivered = 0
        if self.config.reorder:
            # Shuffle eligible messages to simulate reordering.
            eligible = [m for m in self._queue if m[4] <= self._time]
            self._rng.shuffle(eligible)
        else:
            eligible = sorted(
                (m for m in self._queue if m[4] <= self._time),
                key=lambda m: m[4],
            )

        for msg in eligible:
            self._queue.remove(msg)
            src, dst, payload, _send, _deliv = msg
            if self.is_partitioned(src, dst):
                # Partition occurred after send — drop.
                self.dropped_count += 1
                continue
            self._inboxes.setdefault(dst, []).append((src, payload, self._time))
            delivered += 1
            self.delivered_count += 1

        # Advance time to next message if queue isn't empty and nothing
        # was delivered (so the simulation can progress).
        if delivered == 0 and self._queue:
            next_time = min(m[4] for m in self._queue)
            if next_time > self._time:
                self._time = next_time
            # Try draining again at the new time.
            remaining = self.drain(max_messages)
            return delivered + remaining

        return delivered

    def advance(self, dt: float) -> None:
        """Advance simulation time by *dt*."""
        self._time += dt

    def set_time(self, t: float) -> None:
        self._time = t

    # ------------------------------------------------------------------
    # Inbox access
    # ------------------------------------------------------------------

    def inbox(self, node_id: int) -> list[tuple[int, Any, float]]:
        """Return and clear the inbox for *node_id*."""
        msgs = self._inboxes.get(node_id, [])
        self._inboxes[node_id] = []
        return msgs

    def pending_count(self) -> int:
        return len(self._queue)

    def reset(self) -> None:
        """Reset the network to a clean state."""
        self._queue.clear()
        self._inboxes.clear()
        self._partitioned.clear()
        self._time = 0.0
        self.sent_count = 0
        self.dropped_count = 0
        self.delivered_count = 0