"""Raft node — the core consensus state machine.

This module implements a single Raft node including:

* Leader election (RequestVote RPCs, randomized election timeouts)
* Log replication (AppendEntries RPCs, conflict optimization)
* Commitment and applying to a state machine
* Snapshotting (InstallSnapshot RPC)
* Membership changes (joint consensus / single-node add-remove)

The node is driven externally by :class:`raft.cluster.Cluster` which
ticks the clock and delivers messages from the :class:`raft.network.Network`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable

from raft.snapshot import Snapshot, SnapshotStore
from raft.types import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    InstallSnapshotRequest,
    InstallSnapshotResponse,
    LogEntry,
    NodeRole,
    NodeState,
    RequestVoteRequest,
    RequestVoteResponse,
)


# ---------------------------------------------------------------------------
# State machine interface
# ---------------------------------------------------------------------------


class StateMachine:
    """Minimal state-machine interface.

    Subclass this to implement your own replicated state machine.  The
    default in-memory implementation is a simple key-value store.
    """

    def apply(self, command: Any) -> Any:
        """Apply *command* and return the result."""
        raise NotImplementedError

    def snapshot(self) -> Any:
        """Return an opaque snapshot of the current state."""
        raise NotImplementedError

    def restore(self, state: Any) -> None:
        """Restore from a snapshot."""
        raise NotImplementedError


class KVStateMachine(StateMachine):
    """A simple replicated key-value store.

    Commands are tuples: ``("set", key, value)`` or ``("del", key)``.
    Reads (``("get", key)``) are applied but do not mutate state.
    """

    def __init__(self) -> None:
        self._store: dict[Any, Any] = {}

    def apply(self, command: Any) -> Any:
        if not isinstance(command, (tuple, list)) or len(command) < 1:
            raise ValueError(f"Invalid command: {command!r}")
        op = command[0]
        if op == "set":
            _, key, value = command
            self._store[key] = value
            return value
        elif op == "del":
            _, key = command
            return self._store.pop(key, None)
        elif op == "get":
            _, key = command
            return self._store.get(key)
        elif op == "noop":
            return None
        else:
            raise ValueError(f"Unknown op: {op!r}")

    def snapshot(self) -> Any:
        return dict(self._store)

    def restore(self, state: Any) -> None:
        self._store = dict(state)


# ---------------------------------------------------------------------------
# Raft node
# ---------------------------------------------------------------------------


@dataclass
class NodeStats:
    """Statistics tracked per node."""

    elections_started: int = 0
    votes_received: int = 0
    votes_granted: int = 0
    append_entries_sent: int = 0
    append_entries_received: int = 0
    entries_committed: int = 0
    entries_applied: int = 0
    snapshots_taken: int = 0
    snapshots_installed: int = 0
    became_leader: int = 0
    became_candidate: int = 0
    became_follower: int = 0


class RaftNode:
    """A single Raft consensus node.

    The node is passive: it responds to incoming RPCs and to periodic
    *tick()* calls that drive election timeouts and heartbeats.
    """

    def __init__(
        self,
        node_id: int,
        peers: list[int],
        network: Any,
        state_machine: StateMachine | None = None,
        election_timeout_range: tuple[float, float] = (5.0, 10.0),
        heartbeat_interval: float = 1.0,
        snapshot_threshold: int = 50,
        rng: random.Random | None = None,
    ) -> None:
        self.id = node_id
        # peers does NOT include self
        self.peers = list(peers)
        self.network = network
        self.sm = state_machine or KVStateMachine()
        self.log_store = SnapshotStore()
        self.state = NodeState()
        self.role = NodeRole.FOLLOWER
        self.election_timeout_range = election_timeout_range
        self.heartbeat_interval = heartbeat_interval
        self.snapshot_threshold = snapshot_threshold
        self._rng = rng or random.Random()

        # Timers
        self._election_deadline: float = 0.0
        self._heartbeat_deadline: float = 0.0

        # Votes
        self._votes: set[int] = set()

        # Membership tracking (joint consensus support)
        # 'members' is the set of node ids in the current config.
        self.members: set[int] = set([node_id] + list(peers))

        # Stats
        self.stats = NodeStats()

        # Initialize election timer
        self._reset_election_timer()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def last_log_index(self) -> int:
        return self.log_store.last_log_index

    @property
    def last_log_term(self) -> int:
        return self.log_store.last_log_term

    @property
    def is_leader(self) -> bool:
        return self.role == NodeRole.LEADER

    @property
    def is_candidate(self) -> bool:
        return self.role == NodeRole.CANDIDATE

    # ------------------------------------------------------------------
    # Timer helpers
    # ------------------------------------------------------------------

    def _reset_election_timer(self) -> None:
        lo, hi = self.election_timeout_range
        self._election_deadline = self.network.time + self._rng.uniform(lo, hi)

    def _reset_heartbeat_timer(self) -> None:
        self._heartbeat_deadline = self.network.time + self.heartbeat_interval

    def election_timeout_expired(self) -> bool:
        return self.network.time >= self._election_deadline

    def heartbeat_due(self) -> bool:
        return self.network.time >= self._heartbeat_deadline

    # ------------------------------------------------------------------
    # Tick — called periodically by the cluster driver
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """Called by the cluster driver on each simulation step."""
        if self.is_leader:
            if self.heartbeat_due():
                self._send_heartbeats()
                self._reset_heartbeat_timer()
        else:
            if self.election_timeout_expired():
                self._start_election()

    # ------------------------------------------------------------------
    # Leader election
    # ------------------------------------------------------------------

    def _start_election(self) -> None:
        """Transition to candidate and start a new election."""
        self.state.current_term += 1
        self.role = NodeRole.CANDIDATE
        self.state.voted_for = self.id
        self._votes = {self.id}
        self._reset_election_timer()
        self.stats.elections_started += 1
        self.stats.became_candidate += 1

        last_idx = self.last_log_index
        last_term = self.last_log_term
        term = self.state.current_term

        for peer in self.peers:
            req = RequestVoteRequest(
                term=term,
                candidate_id=self.id,
                last_log_index=last_idx,
                last_log_term=last_term,
            )
            self.network.send(self.id, peer, req)

    def _handle_request_vote(
        self, src: int, req: RequestVoteRequest
    ) -> None:
        """Process a RequestVote RPC from *src*."""
        # Step down if we see a higher term.
        if req.term > self.state.current_term:
            self._step_down(req.term)

        vote_granted = False
        if req.term < self.state.current_term:
            # Stale request — reject.
            vote_granted = False
        elif self.state.voted_for is None or self.state.voted_for == req.candidate_id:
            # Check log up-to-dateness: candidate's log must be at least
            # as up-to-date as ours.
            if self._is_log_up_to_date(req.last_log_index, req.last_log_term):
                vote_granted = True
                self.state.voted_for = req.candidate_id
                self._reset_election_timer()

        resp = RequestVoteResponse(
            term=self.state.current_term,
            vote_granted=vote_granted,
            voter_id=self.id,
        )
        self.network.send(self.id, src, resp)
        self.stats.votes_granted += (1 if vote_granted else 0)

    def _is_log_up_to_date(self, last_idx: int, last_term: int) -> bool:
        """Raft's log-up-to-date comparison (§5.4.1)."""
        my_last_term = self.last_log_term
        my_last_idx = self.last_log_index
        if last_term != my_last_term:
            return last_term > my_last_term
        return last_idx >= my_last_idx

    def _handle_request_vote_response(
        self, src: int, resp: RequestVoteResponse
    ) -> None:
        """Process a RequestVote response."""
        if resp.term > self.state.current_term:
            self._step_down(resp.term)
            return
        if not self.is_candidate:
            return  # election already over
        if resp.term != self.state.current_term:
            return  # stale
        if resp.vote_granted:
            self._votes.add(src)
            self.stats.votes_received += 1
            if self._has_quorum(len(self._votes)):
                self._become_leader()

    def _has_quorum(self, count: int) -> bool:
        total = len(self.members)
        return count > total // 2

    def _become_leader(self) -> None:
        """Transition to leader and initialize next_index/match_index."""
        self.role = NodeRole.LEADER
        self.stats.became_leader += 1
        # Initialize next_index = last_log_index + 1 for each peer.
        self.state.next_index = {
            p: self.last_log_index + 1 for p in self.peers
        }
        self.state.match_index = {p: 0 for p in self.peers}
        # Immediately send heartbeats.
        self._send_heartbeats()
        self._reset_heartbeat_timer()

    def _step_down(self, term: int) -> None:
        """Revert to follower at the given (higher) term."""
        self.state.current_term = term
        self.state.voted_for = None
        self.role = NodeRole.FOLLOWER
        self.stats.became_follower += 1
        self._reset_election_timer()

    # ------------------------------------------------------------------
    # Log replication
    # ------------------------------------------------------------------

    def _send_heartbeats(self) -> None:
        """Send AppendEntries (heartbeat or data) to all peers."""
        for peer in self.peers:
            self._send_append_entries(peer)

    def _send_append_entries(self, peer: int) -> None:
        """Send AppendEntries to a single peer.

        If the peer is so far behind that the next entry is before the
        snapshot boundary, send an InstallSnapshot RPC instead.
        """
        next_idx = self.state.next_index.get(peer, 1)

        # BUG FIX: Check if the peer needs a snapshot instead of
        # AppendEntries. Previously this check was never performed,
        # so lagging followers never received InstallSnapshot RPCs.
        if next_idx <= self.log_store.last_included_index and self.log_store.has_snapshot:
            self._maybe_send_snapshot(peer)
            return

        prev_log_index = next_idx - 1
        prev_log_term = self.log_store.term_at_index(prev_log_index)

        # Gather entries starting from next_idx.
        entries = self.log_store.entry_slice(next_idx)
        # Limit batch size to avoid huge messages (optional).
        # We send all available entries for simplicity.

        req = AppendEntriesRequest(
            term=self.state.current_term,
            leader_id=self.id,
            prev_log_index=prev_log_index,
            prev_log_term=prev_log_term,
            entries=entries,
            leader_commit=self.state.commit_index,
        )
        self.network.send(self.id, peer, req)
        self.stats.append_entries_sent += 1

    def _handle_append_entries(
        self, src: int, req: AppendEntriesRequest
    ) -> None:
        """Process an AppendEntries RPC from *src*."""
        self.stats.append_entries_received += 1

        # Step down if higher term.
        if req.term > self.state.current_term:
            self._step_down(req.term)

        success = False
        conflict_index = 0
        conflict_term = 0

        if req.term < self.state.current_term:
            # Stale leader — reject.
            resp = AppendEntriesResponse(
                term=self.state.current_term,
                success=False,
                follower_id=self.id,
            )
            self.network.send(self.id, src, resp)
            return

        # We accept this leader — reset election timer.
        self.role = NodeRole.FOLLOWER
        self._reset_election_timer()

        # Log consistency check.
        if req.prev_log_index > 0:
            prev_entry = self.log_store.get_entry(req.prev_log_index)
            if prev_entry is None:
                # Missing entry — find conflict info.
                # If the prev index is within snapshot, report snapshot boundary.
                if req.prev_log_index <= self.log_store.last_included_index:
                    conflict_index = self.log_store.last_included_index
                    conflict_term = self.log_store.last_included_term
                else:
                    # Report the last entry we have.
                    conflict_index = self.last_log_index
                    conflict_term = self.last_log_term
                resp = AppendEntriesResponse(
                    term=self.state.current_term,
                    success=False,
                    follower_id=self.id,
                    conflict_index=conflict_index,
                    conflict_term=conflict_term,
                )
                self.network.send(self.id, src, resp)
                return
            if prev_entry.term != req.prev_log_term:
                # Term mismatch — find first index of the conflicting term.
                conflict_term = prev_entry.term
                conflict_index = req.prev_log_index
                # Walk backwards to find the first entry of this term.
                while conflict_index > 1:
                    e = self.log_store.get_entry(conflict_index - 1)
                    if e is None or e.term != conflict_term:
                        break
                    conflict_index -= 1
                resp = AppendEntriesResponse(
                    term=self.state.current_term,
                    success=False,
                    follower_id=self.id,
                    conflict_index=conflict_index,
                    conflict_term=conflict_term,
                )
                self.network.send(self.id, src, resp)
                return

        # Consistency check passed — append new entries.
        if req.entries:
            for entry in req.entries:
                existing = self.log_store.get_entry(entry.index)
                if existing is not None:
                    if existing.term != entry.term:
                        # Conflict — truncate from here.
                        self.log_store.truncate_from(entry.index)
                        self.log_store.append_entries([entry])
                    else:
                        # Already have this entry — skip.
                        continue
                else:
                    self.log_store.append_entries([entry])
        else:
            pass  # heartbeat

        # Advance commit_index.
        if req.leader_commit > self.state.commit_index:
            new_commit = min(req.leader_commit, self.last_log_index)
            if new_commit > self.state.commit_index:
                self.state.commit_index = new_commit
                self._apply_committed()

        resp = AppendEntriesResponse(
            term=self.state.current_term,
            success=True,
            follower_id=self.id,
        )
        self.network.send(self.id, src, resp)

    def _handle_append_entries_response(
        self, src: int, resp: AppendEntriesResponse
    ) -> None:
        """Process an AppendEntries response."""
        if resp.term > self.state.current_term:
            self._step_down(resp.term)
            return
        if not self.is_leader:
            return

        if resp.success:
            # Update next_index and match_index for this follower.
            # match_index = prev_log_index + len(entries sent).
            # We approximate by looking at what we sent: next_index was
            # the start; match_index becomes last_log_index if follower
            # has everything, or we can compute from the response.
            # Simpler: match_index = next_index - 1 + entries_sent.
            # Since we don't track entries_sent per RPC here, we set
            # match_index to the follower's last_log_index which equals
            # our last_log_index if it accepted everything.
            sent_next = self.state.next_index.get(src, 1)
            # After success, follower has all entries from sent_next onward.
            # If we sent entries, match_index advances to our last_log_index.
            # If heartbeat, match_index stays at sent_next - 1.
            if self.last_log_index >= sent_next:
                self.state.match_index[src] = self.last_log_index
                self.state.next_index[src] = self.last_log_index + 1
            else:
                # Heartbeat only — match_index = prev_log_index.
                self.state.match_index[src] = sent_next - 1

            self._advance_commit_index()
        else:
            # Failure — use conflict info to fast-backtrack.
            if resp.conflict_index > 0:
                self.state.next_index[src] = resp.conflict_index
            else:
                # Decrement next_index by 1 (classic slow backtrack).
                self.state.next_index[src] = max(1, self.state.next_index.get(src, 1) - 1)
            # Retry immediately.
            self._send_append_entries(src)

    def _advance_commit_index(self) -> None:
        """Update commit_index to the highest index replicated on a quorum."""
        # Find the highest N such that majority of match_index[] >= N
        # and log[N].term == current_term.
        if not self.is_leader:
            return
        # Gather match indices including self (self has all entries).
        indices = sorted(self.state.match_index.values())
        # Include self: we match our own log fully.
        all_indices = indices + [self.last_log_index]
        all_indices.sort()
        # Majority index = the median (for odd count) or just above middle.
        n = len(all_indices)
        # The quorum position: indices[n // 2] gives the value such that
        # at least (n - n//2) nodes have match_index >= that value.
        # But we need a strict majority (> half), so:
        quorum_pos = n // 2
        commit_candidate = all_indices[quorum_pos]
        # Only commit entries from current term (§5.4.2).
        if commit_candidate > self.state.commit_index:
            entry = self.log_store.get_entry(commit_candidate)
            if entry and entry.term == self.state.current_term:
                # BUG FIX: Track the number of newly committed entries.
                newly_committed = commit_candidate - self.state.commit_index
                self.state.commit_index = commit_candidate
                self.stats.entries_committed += newly_committed
                self._apply_committed()
                # Send heartbeats to propagate commit.
                self._send_heartbeats()

    def _apply_committed(self) -> None:
        """Apply entries up to commit_index to the state machine."""
        while self.state.last_applied < self.state.commit_index:
            self.state.last_applied += 1
            entry = self.log_store.get_entry(self.state.last_applied)
            if entry is not None:
                self.sm.apply(entry.command)
                self.stats.entries_applied += 1

    # ------------------------------------------------------------------
    # Client command submission (leader only)
    # ------------------------------------------------------------------

    def submit_command(self, command: Any) -> bool:
        """Submit a client command to the leader.

        Returns ``True`` if the command was appended to the log,
        ``False`` if this node is not the leader.
        """
        if not self.is_leader:
            return False
        entry = LogEntry(term=self.state.current_term, command=command)
        entry.index = self.last_log_index + 1
        self.log_store.append_entries([entry])
        # Trigger replication.
        self._send_heartbeats()
        # Maybe snapshot.
        self._maybe_snapshot()
        return True

    def _maybe_snapshot(self) -> None:
        """Take a snapshot if the retained log has grown past the threshold.

        We snapshot when the number of *retained* entries (entries still
        in memory, not covered by a snapshot) exceeds the threshold AND
        there are committed entries to snapshot.  This is more robust
        than comparing last_log_index - commit_index because the commit
        may have already caught up by the time we check.
        """
        retained = len(self.log_store.entries)
        if retained >= self.snapshot_threshold and self.state.commit_index > self.log_store.last_included_index:
            self.take_snapshot(self.state.commit_index)

    def take_snapshot(self, up_to_index: int) -> Snapshot:
        """Take a snapshot up to *up_to_index*."""
        if up_to_index <= self.log_store.last_included_index:
            return self.log_store.snapshot  # type: ignore[return-value]
        term = self.log_store.term_at_index(up_to_index)
        state = self.sm.snapshot()
        snap = self.log_store.take_snapshot(
            up_to_index, term, state, set(self.members)
        )
        self.stats.snapshots_taken += 1
        return snap

    # ------------------------------------------------------------------
    # InstallSnapshot RPC
    # ------------------------------------------------------------------

    def _handle_install_snapshot(
        self, src: int, req: InstallSnapshotRequest
    ) -> None:
        """Process an InstallSnapshot RPC."""
        if req.term > self.state.current_term:
            self._step_down(req.term)

        if req.term < self.state.current_term:
            resp = InstallSnapshotResponse(
                term=self.state.current_term, follower_id=self.id
            )
            self.network.send(self.id, src, resp)
            return

        # Accept the snapshot.
        self.role = NodeRole.FOLLOWER
        self._reset_election_timer()

        # In a real implementation, this would be chunked.  Here we
        # assume the full snapshot arrives in one message (done=True).
        if req.done:
            self.log_store.take_snapshot(
                req.last_included_index,
                req.last_included_term,
                req.data,
                set(self.members),
            )
            self.sm.restore(req.data)
            if self.state.commit_index < req.last_included_index:
                self.state.commit_index = req.last_included_index
            if self.state.last_applied < req.last_included_index:
                self.state.last_applied = req.last_included_index
            self.stats.snapshots_installed += 1

        resp = InstallSnapshotResponse(
            term=self.state.current_term, follower_id=self.id
        )
        self.network.send(self.id, src, resp)

    def _maybe_send_snapshot(self, peer: int) -> None:
        """If a peer is too far behind, send a snapshot instead."""
        next_idx = self.state.next_index.get(peer, 1)
        if next_idx <= self.log_store.last_included_index and self.log_store.has_snapshot:
            snap = self.log_store.snapshot
            assert snap is not None
            req = InstallSnapshotRequest(
                term=self.state.current_term,
                leader_id=self.id,
                last_included_index=snap.last_included_index,
                last_included_term=snap.last_included_term,
                offset=0,
                data=snap.state,
                done=True,
            )
            self.network.send(self.id, peer, req)
            self.state.next_index[peer] = snap.last_included_index + 1
            self.state.match_index[peer] = snap.last_included_index

    # ------------------------------------------------------------------
    # Message dispatch
    # ------------------------------------------------------------------

    def handle_message(self, src: int, msg: Any) -> None:
        """Dispatch an incoming message to the appropriate handler."""
        if isinstance(msg, RequestVoteRequest):
            self._handle_request_vote(src, msg)
        elif isinstance(msg, RequestVoteResponse):
            self._handle_request_vote_response(src, msg)
        elif isinstance(msg, AppendEntriesRequest):
            self._handle_append_entries(src, msg)
        elif isinstance(msg, AppendEntriesResponse):
            self._handle_append_entries_response(src, msg)
        elif isinstance(msg, InstallSnapshotRequest):
            self._handle_install_snapshot(src, msg)
        elif isinstance(msg, InstallSnapshotResponse):
            # Update next_index for this follower after snapshot install.
            if self.is_leader:
                self.state.match_index[src] = max(
                    self.state.match_index.get(src, 0),
                    self.log_store.last_included_index,
                )
                self.state.next_index[src] = self.log_store.last_included_index + 1
        else:
            raise TypeError(f"Unknown message type: {type(msg).__name__}")

    # ------------------------------------------------------------------
    # Membership changes (simplified joint consensus)
    # ------------------------------------------------------------------

    def add_member(self, node_id: int) -> bool:
        """Add a new member to the cluster (leader only).

        This implements a simplified single-step membership change: the
        leader appends a special configuration entry to its log and
        replicates it.  Once committed, the new member is active.
        """
        if not self.is_leader:
            return False
        if node_id in self.members:
            return False  # already a member
        # Append a membership config-entry.
        self.members.add(node_id)
        if node_id not in self.peers:
            self.peers.append(node_id)
        self.state.next_index[node_id] = self.last_log_index + 1
        self.state.match_index[node_id] = 0
        self.submit_command(("add_member", node_id))
        return True

    def remove_member(self, node_id: int) -> bool:
        """Remove a member from the cluster (leader only)."""
        if not self.is_leader:
            return False
        if node_id not in self.members:
            return False
        self.members.discard(node_id)
        if node_id in self.peers:
            self.peers.remove(node_id)
        self.state.next_index.pop(node_id, None)
        self.state.match_index.pop(node_id, None)
        self.submit_command(("remove_member", node_id))
        return True

    # ------------------------------------------------------------------
    # Status / introspection
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Return a status dictionary for introspection."""
        return {
            "id": self.id,
            "role": self.role.value,
            "term": self.state.current_term,
            "voted_for": self.state.voted_for,
            "last_log_index": self.last_log_index,
            "last_log_term": self.last_log_term,
            "commit_index": self.state.commit_index,
            "last_applied": self.state.last_applied,
            "members": sorted(self.members),
            "has_snapshot": self.log_store.has_snapshot,
            "snapshot_index": self.log_store.last_included_index,
            "stats": {
                "elections_started": self.stats.elections_started,
                "votes_received": self.stats.votes_received,
                "votes_granted": self.stats.votes_granted,
                "append_entries_sent": self.stats.append_entries_sent,
                "append_entries_received": self.stats.append_entries_received,
                "entries_committed": self.stats.entries_committed,
                "entries_applied": self.stats.entries_applied,
                "snapshots_taken": self.stats.snapshots_taken,
                "snapshots_installed": self.stats.snapshots_installed,
                "became_leader": self.stats.became_leader,
                "became_candidate": self.stats.became_candidate,
                "became_follower": self.stats.became_follower,
            },
        }