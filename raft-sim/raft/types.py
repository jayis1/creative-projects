"""Core data types for the Raft simulator."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class NodeRole(enum.Enum):
    """Role of a Raft node at a given moment."""

    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    """A single entry in a node's replicated log.

    Attributes:
        term: The leader's term when this entry was created.
        command: The client command payload (opaque to Raft).
        index: 1-based log index (assigned by the leader).
    """

    term: int
    command: Any
    index: int = 0  # assigned when appended

    def __post_init__(self) -> None:
        # term must be non-negative; index is assigned later but should
        # never be negative once set.
        if self.term < 0:
            raise ValueError(f"term must be non-negative, got {self.term}")

    def __repr__(self) -> str:  # pragma: no cover
        return f"LogEntry(term={self.term}, index={self.index}, cmd={self.command!r})"


@dataclass
class NodeState:
    """Persistent + volatile Raft state for a single node.

    Persistent state (would be on disk in a real implementation):
        current_term, voted_for, log

    Volatile state (in memory):
        commit_index, last_applied

    Leader-only volatile state:
        next_index[], match_index[]
    """

    # Persistent
    current_term: int = 0
    voted_for: int | None = None  # node id or None
    log: list[LogEntry] = field(default_factory=list)

    # Volatile
    commit_index: int = 0  # highest log index known committed (0 = none)
    last_applied: int = 0  # highest log index applied to state machine

    # Leader-only
    next_index: dict[int, int] = field(default_factory=dict)
    match_index: dict[int, int] = field(default_factory=dict)

    # ---- Log helpers ----

    @property
    def last_log_index(self) -> int:
        """Index of the last entry (0 if log is empty)."""
        return len(self.log)

    @property
    def last_log_term(self) -> int:
        """Term of the last entry (0 if log is empty)."""
        if not self.log:
            return 0
        return self.log[-1].term

    def get_entry(self, index: int) -> LogEntry | None:
        """Return the entry at 1-based *index*, or ``None`` if out of range."""
        if index < 1 or index > len(self.log):
            return None
        return self.log[index - 1]

    def term_at_index(self, index: int) -> int:
        """Term of the entry at *index* (0 if no entry)."""
        entry = self.get_entry(index)
        return entry.term if entry else 0


# ---------------------------------------------------------------------------
# RPC messages
# ---------------------------------------------------------------------------


@dataclass
class RequestVoteRequest:
    """RequestVote RPC — sent by candidates to gather votes."""

    term: int
    candidate_id: int
    last_log_index: int
    last_log_term: int


@dataclass
class RequestVoteResponse:
    """Response to a RequestVote RPC."""

    term: int
    vote_granted: bool
    voter_id: int


@dataclass
class AppendEntriesRequest:
    """AppendEntries (heartbeat) RPC — sent by the leader.

    *prev_log_index* / *prev_log_term* describe the entry immediately
    preceding the new entries being sent.  An empty *entries* list makes
    this a heartbeat.
    """

    term: int
    leader_id: int
    prev_log_index: int
    prev_log_term: int
    entries: list[LogEntry]
    leader_commit: int


@dataclass
class AppendEntriesResponse:
    """Response to an AppendEntries RPC.

    When *success* is ``False`` the follower may include
    *conflict_index* / *conflict_term* to accelerate log backtracking
    (optimization from §5.3).
    """

    term: int
    success: bool
    follower_id: int
    # Conflict optimization fields
    conflict_index: int = 0
    conflict_term: int = 0


@dataclass
class InstallSnapshotRequest:
    """InstallSnapshot RPC — sent by leader when follower log is too far behind."""

    term: int
    leader_id: int
    last_included_index: int
    last_included_term: int
    offset: int
    data: bytes
    done: bool


@dataclass
class InstallSnapshotResponse:
    """Response to an InstallSnapshot RPC."""

    term: int
    follower_id: int