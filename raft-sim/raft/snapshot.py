"""Snapshot support for the Raft simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from raft.types import LogEntry


@dataclass
class Snapshot:
    """A point-in-time snapshot of the state machine.

    Raft uses snapshots to compact the log.  A snapshot records the last
    included log index/term, and an opaque *state* blob representing the
    state machine at that point.  Log entries up to and including
    *last_included_index* can be discarded.
    """

    last_included_index: int
    last_included_term: int
    state: Any = None
    # Membership configuration captured at snapshot time (set ids).
    members: set[int] = field(default_factory=set)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Snapshot(idx={self.last_included_index}, "
            f"term={self.last_included_term}, "
            f"members={sorted(self.members)})"
        )

    def contains_index(self, index: int) -> bool:
        """True if *index* is covered by (i.e. ≤) this snapshot."""
        return index <= self.last_included_index


class SnapshotStore:
    """Manages a node's snapshot and the log entries it has retained.

    The logical log is the concatenation of the snapshot (up to
    *last_included_index*) and the remaining *entries* (starting at
    *last_included_index + 1*).  Indexing is 1-based and consistent with
    :class:`raft.types.NodeState`.
    """

    def __init__(self) -> None:
        self._snapshot: Snapshot | None = None
        self._entries: list[LogEntry] = []

    # ------------------------------------------------------------------
    # Snapshot management
    # ------------------------------------------------------------------

    @property
    def snapshot(self) -> Snapshot | None:
        return self._snapshot

    @property
    def has_snapshot(self) -> bool:
        return self._snapshot is not None

    @property
    def last_included_index(self) -> int:
        return self._snapshot.last_included_index if self._snapshot else 0

    @property
    def last_included_term(self) -> int:
        return self._snapshot.last_included_term if self._snapshot else 0

    def take_snapshot(
        self,
        up_to_index: int,
        term_at_index: int,
        state: Any,
        members: set[int],
    ) -> Snapshot:
        """Create a snapshot covering entries up to *up_to_index*.

        Entries ≤ *up_to_index* are removed from the in-memory log.
        Returns the new :class:`Snapshot`.
        """
        if self._snapshot and up_to_index <= self._snapshot.last_included_index:
            # Already covered by an existing snapshot — nothing to do.
            return self._snapshot

        # Drop entries up to and including up_to_index.
        # Entries are stored relative to (last_included_index + 1).
        base = self.last_included_index
        # How many physical entries to discard?
        discard = up_to_index - base
        if discard > 0:
            self._entries = self._entries[discard:]
        elif discard < 0:
            # Shouldn't happen, but guard anyway.
            raise ValueError(
                f"Cannot snapshot back to index {up_to_index} below "
                f"current base {base}"
            )

        snap = Snapshot(
            last_included_index=up_to_index,
            last_included_term=term_at_index,
            state=state,
            members=set(members),
        )
        self._snapshot = snap
        return snap

    # ------------------------------------------------------------------
    # Log access (logical view)
    # ------------------------------------------------------------------

    @property
    def entries(self) -> list[LogEntry]:
        """The retained (post-snapshot) entries."""
        return self._entries

    @property
    def last_log_index(self) -> int:
        """Highest log index (snapshot or last entry)."""
        if self._entries:
            entry = self._entries[-1]
            # entry.index is the logical index
            return entry.index
        return self.last_included_index

    @property
    def last_log_term(self) -> int:
        """Term of the highest log index."""
        if self._entries:
            return self._entries[-1].term
        return self.last_included_term

    def term_at_index(self, index: int) -> int:
        """Term of the entry at *index* (0 if unknown/compacted away)."""
        if index <= self.last_included_index:
            if index == self.last_included_index:
                return self.last_included_term
            # Before snapshot — unknown, but Raft only needs the term of
            # entries at or after the snapshot boundary.
            return 0
        entry = self.get_entry(index)
        return entry.term if entry else 0

    def get_entry(self, index: int) -> LogEntry | None:
        """Return entry at 1-based *index* or ``None``."""
        if index <= self.last_included_index:
            return None
        offset = index - self.last_included_index - 1
        if 0 <= offset < len(self._entries):
            return self._entries[offset]
        return None

    def append_entries(self, new_entries: list[LogEntry]) -> None:
        """Append new entries (with logical indices already assigned)."""
        for e in new_entries:
            # Ensure index is set correctly.
            expected_index = self.last_included_index + len(self._entries) + 1
            if e.index == 0:
                e.index = expected_index
            self._entries.append(e)

    def truncate_from(self, index: int) -> list[LogEntry]:
        """Remove all entries with index ≥ *index*.

        Returns the removed entries (for debugging / state-machine rollback).
        """
        if index <= self.last_included_index:
            # Truncating into the snapshot region — discard snapshot too.
            removed = list(self._entries)
            self._entries = []
            self._snapshot = None
            return removed
        offset = index - self.last_included_index - 1
        if offset < 0:
            offset = 0
        removed = self._entries[offset:]
        self._entries = self._entries[:offset]
        return removed

    def entry_slice(self, start_index: int) -> list[LogEntry]:
        """Return entries with index ≥ *start_index*."""
        if start_index <= self.last_included_index:
            # Would need snapshot — caller should use InstallSnapshot instead.
            return list(self._entries)
        offset = start_index - self.last_included_index - 1
        if offset < 0:
            offset = 0
        return list(self._entries[offset:])